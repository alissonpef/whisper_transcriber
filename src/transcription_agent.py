from __future__ import annotations

import copy
import queue
import threading
from collections.abc import Callable
from typing import Any

import numpy as np
from numpy.typing import NDArray

from src.config import AUDIO, ModelConfig
from src.logger import get_logger

logger = get_logger(__name__)


class TranscriptionAgent:
    MAX_SEGMENT_SECS: float = 20.0

    SILENCE_FLUSH_COUNT: int = 6

    MIN_RMS_THRESHOLD: float = 0.003

    def __init__(
        self,
        audio_queue: queue.Queue[NDArray[np.float32]],
        on_result: Callable[[str], None],
        config: ModelConfig,
        model_override: Any | None = None,
    ) -> None:
        self._audio_queue: queue.Queue[NDArray[np.float32]] = audio_queue
        self._on_result: Callable[[str], None] = on_result
        self._config: ModelConfig = copy.copy(config)
        self._model: Any | None = model_override
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._fallback_lock = threading.Lock()

        self._active_device: str = self._config.device
        self._active_compute_type: str = self._config.compute_type

    def load_model(self, on_progress: Callable[[str], None] | None = None) -> None:
        if self._model is not None:
            if on_progress:
                on_progress("model-ready")
            return

        if on_progress:
            on_progress("loading-model")

        from faster_whisper import WhisperModel

        try:
            self._model = WhisperModel(
                self._config.size,
                device=self._config.device,
                compute_type=self._config.compute_type,
            )
            self._active_device = self._config.device
            self._active_compute_type = self._config.compute_type
        except Exception:
            if not self._config.cpu_fallback or self._config.device == "cpu":
                logger.exception("Failed to load Whisper model")
                raise

            logger.warning("CUDA load failed; falling back to CPU int8")
            self._model = WhisperModel(
                self._config.size,
                device="cpu",
                compute_type="int8",
            )
            self._active_device = "cpu"
            self._active_compute_type = "int8"

        if on_progress:
            on_progress("model-ready")

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return

        self.load_model()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._transcribe_loop, daemon=True)
        self._thread.start()
        logger.info("Transcription agent started")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

        while True:
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break

        logger.info("Transcription agent stopped")

    def get_runtime_details(self) -> tuple[str, str, str]:
        return self._config.size, self._active_device, self._active_compute_type

    def _transcribe_loop(self) -> None:
        segment_buffer: list[NDArray[np.float32]] = []
        segment_secs: float = 0.0
        silence_counter: int = 0

        while not self._stop_event.is_set():
            try:
                chunk = self._audio_queue.get(timeout=0.15)
                segment_buffer.append(chunk)
                chunk_secs = chunk.shape[0] / AUDIO.sample_rate
                segment_secs += chunk_secs
                silence_counter = 0

                if segment_secs >= self.MAX_SEGMENT_SECS:
                    self._finalize_segment(segment_buffer)
                    segment_buffer = []
                    segment_secs = 0.0

            except queue.Empty:
                silence_counter += 1

                if silence_counter >= self.SILENCE_FLUSH_COUNT and segment_buffer:
                    self._finalize_segment(segment_buffer)
                    segment_buffer = []
                    segment_secs = 0.0
                    silence_counter = 0

            except Exception:
                logger.exception("Transcription loop error")

    def _finalize_segment(self, buffer: list[NDArray[np.float32]]) -> None:
        audio = np.concatenate(buffer, axis=0).reshape(-1)

        rms = float(np.sqrt(np.mean(audio**2)))
        if rms < self.MIN_RMS_THRESHOLD:
            logger.debug("Skipping silent segment (RMS=%.5f)", rms)
            return

        text = self._transcribe_with_vad(audio)
        if text and len(text.strip()) > 0:
            cleaned = text.strip()
            self._on_result(cleaned + " ")
            logger.debug("Segment finalized: '%s'", cleaned[:80])

    def _transcribe_with_vad(self, audio: NDArray[np.float32]) -> str:
        if self._model is None:
            return ""

        try:
            text = self._run_model_vad(audio)
            if text:
                return text
        except Exception as exc:
            if self._should_fallback_runtime(exc) and self._fallback_to_cpu():
                try:
                    return self._run_model_vad(audio)
                except Exception:
                    logger.exception("CPU fallback retry failed")
            logger.exception("Model transcribe failed; continuing loop")

        return ""

    def _run_model_vad(self, audio: NDArray[np.float32]) -> str:
        if self._model is None:
            return ""

        segments, _ = self._model.transcribe(
            audio,
            language=self._config.language,
            beam_size=self._config.beam_size,
            vad_filter=True,
            vad_parameters=dict(
                threshold=0.45,
                min_speech_duration_ms=300,
                min_silence_duration_ms=500,
            ),
            condition_on_previous_text=False,
            no_speech_threshold=0.6,
        )

        parts: list[str] = []
        for segment in segments:
            text = str(getattr(segment, "text", "")).strip()
            if text and len(text) > 1:
                parts.append(text)

        return " ".join(parts).strip()

    def _should_fallback_runtime(self, exc: Exception) -> bool:
        if not self._config.cpu_fallback or self._active_device == "cpu":
            return False

        message = str(exc).lower()
        cuda_markers = (
            "cublas",
            "cudnn",
            "libcuda",
            "cuda",
            "cannot be loaded",
            "no cuda",
        )
        return any(marker in message for marker in cuda_markers)

    def _fallback_to_cpu(self) -> bool:
        with self._fallback_lock:
            if self._active_device == "cpu":
                return True

            try:
                from faster_whisper import WhisperModel

                logger.warning("Runtime CUDA failure; switching to CPU int8")
                self._model = WhisperModel(
                    self._config.size,
                    device="cpu",
                    compute_type="int8",
                )
                self._active_device = "cpu"
                self._active_compute_type = "int8"
                return True
            except Exception:
                logger.exception("Failed to initialize CPU fallback model")
                return False
