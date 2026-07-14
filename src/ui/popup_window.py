from __future__ import annotations

import contextlib
import queue
import signal
import threading
import tkinter as tk
from typing import Any

from src.audio_agent import AudioAgent
from src.config import AUDIO, ICON_PATH, MODEL, UI
from src.llm_agent import LLMAgent
from src.logger import get_logger
from src.transcription_agent import TranscriptionAgent
from src.ui.behaviors import StatusDotAnimator, fade_in
from src.ui.components import (
    ActionButton,
    AudioWaveform,
    LoadingSpinner,
    StatusBar,
    TranscriptArea,
)
from src.ui.theme import Theme
from src.ui.tray import TrayIcon
from src.utils.clipboard import copy_to_clipboard
from src.utils.lockfile import acquire, release

logger = get_logger(__name__)


class PopupWindow:
    def __init__(self, auto_start_recording: bool = False) -> None:
        if not acquire():
            raise RuntimeError("Popup already running")

        self._state: str = "LOADING"
        self._closing: bool = False
        self._recording: bool = False
        self._auto_start_recording: bool = bool(auto_start_recording or UI.auto_start_recording)
        self._model_ready: bool = False
        self._drag_x: int = 0
        self._drag_y: int = 0

        self.root = tk.Tk()
        self.root.title("Transcritor Whisper")
        self.root.configure(bg=Theme.BG_PRIMARY)
        self.root.minsize(UI.min_width, UI.min_height)

        if UI.always_on_top:
            self.root.attributes("-topmost", True)

        self._set_geometry()

        self.root.overrideredirect(True)
        self.root.attributes("-alpha", 0.0)

        self.audio_queue: queue.Queue[Any] = queue.Queue(maxsize=AUDIO.queue_maxsize)

        self._build_layout()

        self.audio_agent = AudioAgent(
            self.audio_queue,
            AUDIO,
            on_level=self.waveform.set_level,
        )
        self.transcription_agent = TranscriptionAgent(
            audio_queue=self.audio_queue,
            on_result=lambda text: self.root.after(0, self._insert_text, text),
            config=MODEL,
        )
        self.llm_agent = LLMAgent()

        self._bind_shortcuts()
        self._register_hotkey_signal()
        self._update_status_meta()
        self._set_visual_state("LOADING")

        self._tray = TrayIcon(
            on_toggle=lambda: self.root.after(0, self._on_toggle_visibility),
            on_quit=lambda: self.root.after(0, self._on_close),
        )
        self._tray.start(ICON_PATH)

        self.root.after(0, fade_in, self.root, 0.0)
        self.root.after(10, self._load_model_async)

    def run(self) -> None:
        try:
            self.root.mainloop()
        finally:
            self._on_close()

    def _set_geometry(self) -> None:
        mon_w, mon_h, mon_x, mon_y = self._get_primary_monitor()
        x = mon_x + int((mon_w - UI.width) / 2)
        y = mon_y + int((mon_h - UI.height) / 2)
        self.root.geometry(f"{UI.width}x{UI.height}+{x}+{y}")

    @staticmethod
    def _get_primary_monitor() -> tuple[int, int, int, int]:

        import subprocess

        try:
            result = subprocess.run(
                ["xrandr", "--query"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            for line in result.stdout.splitlines():
                if " connected" not in line:
                    continue
                is_primary = "primary" in line
                import re

                match = re.search(r"(\d+)x(\d+)\+(\d+)\+(\d+)", line)
                if match and is_primary:
                    return (
                        int(match.group(1)),
                        int(match.group(2)),
                        int(match.group(3)),
                        int(match.group(4)),
                    )
            for line in result.stdout.splitlines():
                if " connected" not in line:
                    continue
                import re

                match = re.search(r"(\d+)x(\d+)\+(\d+)\+(\d+)", line)
                if match:
                    return (
                        int(match.group(1)),
                        int(match.group(2)),
                        int(match.group(3)),
                        int(match.group(4)),
                    )
        except Exception:
            pass

        import tkinter as tk

        temp = tk.Tk()
        w = temp.winfo_screenwidth()
        h = temp.winfo_screenheight()
        temp.destroy()
        return (w, h, 0, 0)

    def _show_window(self) -> None:
        try:
            deiconify = getattr(self.root, "deiconify", None)
            if callable(deiconify):
                deiconify()

            lift = getattr(self.root, "lift", None)
            if callable(lift):
                lift()

            focus_force = getattr(self.root, "focus_force", None)
            if callable(focus_force):
                focus_force()

            if UI.always_on_top:
                self.root.attributes("-topmost", True)
        except tk.TclError:
            logger.exception("Failed to raise popup window")

    def _build_layout(self) -> None:
        accent_line = tk.Frame(self.root, bg=Theme.ACCENT, height=2)
        accent_line.pack(fill=tk.X)

        self.header = tk.Frame(self.root, bg=Theme.BG_HEADER, height=44)
        self.header.pack(fill=tk.X)
        self.header.pack_propagate(False)

        self.dot_canvas = tk.Canvas(
            self.header,
            width=16,
            height=16,
            bg=Theme.BG_HEADER,
            highlightthickness=0,
        )
        self.dot_canvas.pack(side=tk.LEFT, padx=(14, 8))
        self.dot_id = self.dot_canvas.create_oval(3, 3, 13, 13, fill=Theme.COLOR_IDLE, outline="")
        self.dot_animator = StatusDotAnimator(self.root, self.dot_canvas, self.dot_id)

        self.title_label = tk.Label(
            self.header,
            text="🎙 Whisper Transcriber",
            bg=Theme.BG_HEADER,
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_HEADER,
        )
        self.title_label.pack(side=tk.LEFT)

        self.close_btn = tk.Button(
            self.header,
            text="✕",
            command=self._on_close,
            bg=Theme.BG_HEADER,
            fg=Theme.TEXT_SECONDARY,
            activebackground=Theme.BTN_DANGER_BG,
            activeforeground=Theme.BTN_DANGER_FG,
            relief=tk.FLAT,
            bd=0,
            width=3,
            font=("Inter", 11),
            highlightthickness=0,
            cursor="hand2",
        )
        self.close_btn.pack(side=tk.RIGHT, padx=(0, 6))

        self.min_btn = tk.Button(
            self.header,
            text="─",
            command=self._on_minimize,
            bg=Theme.BG_HEADER,
            fg=Theme.TEXT_SECONDARY,
            activebackground=Theme.BORDER,
            activeforeground=Theme.TEXT_PRIMARY,
            relief=tk.FLAT,
            bd=0,
            width=3,
            font=("Inter", 11),
            highlightthickness=0,
            cursor="hand2",
        )
        self.min_btn.pack(side=tk.RIGHT, padx=(0, 2))

        tk.Frame(self.root, bg=Theme.BORDER, height=1).pack(fill=tk.X)

        self.status_bar = StatusBar(self.root)
        self.status_bar.pack(fill=tk.X)

        tk.Frame(self.root, bg=Theme.SEPARATOR, height=1).pack(fill=tk.X)

        self.footer = tk.Frame(self.root, bg=Theme.BG_FOOTER, height=56)
        self.footer.pack(side=tk.BOTTOM, fill=tk.X)
        self.footer.pack_propagate(False)

        tk.Frame(self.root, bg=Theme.BORDER, height=1).pack(side=tk.BOTTOM, fill=tk.X)

        self.waveform = AudioWaveform(self.root)
        self.waveform.pack(side=tk.BOTTOM, fill=tk.X)

        self.transcript = TranscriptArea(self.root)
        self.transcript.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.toggle_btn = ActionButton(
            self.footer,
            text="⏺ Gravar",
            command=self._on_toggle_recording,
            variant="primary",
            width=12,
        )
        self.toggle_btn.pack(side=tk.LEFT, padx=(14, 8), pady=10)
        self.toggle_btn.configure(state=tk.DISABLED)

        self.rewrite_btn = ActionButton(
            self.footer,
            text="✨ Reescrever",
            command=self._on_rewrite,
            variant="ghost",
            width=12,
        )
        self.rewrite_btn.pack(side=tk.LEFT, padx=4, pady=10)

        self.copy_all_btn = ActionButton(
            self.footer,
            text="📋 Copiar",
            command=self._on_copy_all,
            variant="ghost",
            width=10,
        )
        self.copy_all_btn.pack(side=tk.LEFT, padx=4, pady=10)

        self.clear_btn = ActionButton(
            self.footer,
            text="🗑 Limpar",
            command=self._on_clear,
            variant="ghost",
            width=10,
        )
        self.clear_btn.pack(side=tk.LEFT, padx=4, pady=10)

        shortcut_hint = tk.Label(
            self.footer,
            text="Ctrl+Shift+Espaço",
            bg=Theme.BG_FOOTER,
            fg=Theme.TEXT_DISABLED,
            font=Theme.FONT_LABEL,
        )
        shortcut_hint.pack(side=tk.RIGHT, padx=14)

        self.loading = LoadingSpinner(self.root)

        for widget in (self.header, self.title_label, self.dot_canvas):
            widget.bind("<ButtonPress-1>", self._on_drag_start)
            widget.bind("<B1-Motion>", self._on_drag_motion)

    def _bind_shortcuts(self) -> None:
        self.root.bind("<Escape>", lambda _event: self._on_minimize())
        self.root.bind("<Control-Shift-C>", lambda _event: self._on_copy_all())
        self.root.bind("<Control-Shift-L>", lambda _event: self._on_clear())
        self.root.bind("<Control-Shift-space>", lambda _event: self._on_toggle_recording())

    def _register_hotkey_signal(self) -> None:
        sigusr1 = getattr(signal, "SIGUSR1", None)
        if sigusr1 is None:
            return

        try:
            signal.signal(sigusr1, self._on_hotkey_signal)
        except (ValueError, OSError):
            logger.exception("Unable to register hotkey signal handler")

    def _on_hotkey_signal(self, _signum: int, _frame: Any) -> None:
        if self._closing:
            return
        self.root.after(0, self._handle_global_hotkey)

    def _handle_global_hotkey(self) -> None:
        if self._closing:
            return

        try:
            state = self.root.state()
            if state == "withdrawn" or state == "iconic":
                self._show_window()
        except tk.TclError:
            pass

        if not self._model_ready:
            self._auto_start_recording = True
            return

        if self._recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _on_drag_start(self, event: tk.Event[tk.Misc]) -> None:
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag_motion(self, event: tk.Event[tk.Misc]) -> None:
        try:
            x = self.root.winfo_x() + (event.x - self._drag_x)
            y = self.root.winfo_y() + (event.y - self._drag_y)
            self.root.geometry(f"+{x}+{y}")
        except tk.TclError:
            pass

    def _load_model_async(self) -> None:
        self.loading.show("Whisper small · CUDA · PT-BR")

        def worker() -> None:
            try:
                self.transcription_agent.load_model(
                    on_progress=lambda message: self.root.after(
                        0, self.loading.set_message, message
                    )
                )
                self.root.after(0, self._on_model_ready)
            except Exception as exc:
                logger.exception("Model loading failed")
                self.root.after(0, self._on_model_failed, str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _on_model_ready(self) -> None:
        self._model_ready = True
        self._update_status_meta()
        self.loading.hide()
        self.transcription_agent.start()
        self.toggle_btn.configure(state=tk.NORMAL)
        self._set_visual_state("IDLE")
        if self._auto_start_recording:
            self._start_recording()

    def _update_status_meta(self) -> None:
        model_size = MODEL.size
        device = MODEL.device
        compute_type = MODEL.compute_type

        details_getter = getattr(self.transcription_agent, "get_runtime_details", None)
        if callable(details_getter):
            model_size, device, compute_type = details_getter()

        self.status_bar.set_meta(
            f"modelo: {model_size} · PT-BR · {device.upper()} ({compute_type})"
        )

    def _on_model_failed(self, reason: str) -> None:
        self.loading.hide()
        self._set_visual_state("IDLE")
        self.status_bar.set_state(f"Erro ao carregar modelo: {reason}", Theme.COLOR_RECORDING)

    def _on_toggle_recording(self) -> None:
        if self._closing or not self._model_ready:
            return

        if self._recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self) -> None:
        if self._recording or self._closing:
            return

        try:
            self.audio_agent.start()
        except Exception:
            logger.exception("Failed to start audio agent")
            self.status_bar.set_state("Erro: microfone indisponível", Theme.COLOR_RECORDING)
            return

        self._recording = True
        self.toggle_btn.configure(text="⏹ Parar")
        self.toggle_btn.set_variant("danger")
        self._set_visual_state("RECORDING")
        self.waveform.start(self.audio_queue)
        logger.info("Recording started")

    def _stop_recording(self) -> None:
        if not self._recording:
            return

        self._recording = False
        self.audio_agent.stop()
        self.waveform.stop()
        self.toggle_btn.configure(text="⏺ Gravar")
        self.toggle_btn.set_variant("primary")
        self._set_visual_state("IDLE")
        logger.info("Recording stopped")

    def _insert_text(self, text: str) -> None:
        if self._closing:
            return
        self.transcript.append(text)

    def _on_rewrite(self) -> None:
        if self._state == "RECORDING":
            return

        text = self.transcript.get_text()
        if not text:
            return

        self.toggle_btn.configure(state=tk.DISABLED)
        self.rewrite_btn.configure(state=tk.DISABLED)
        self.clear_btn.configure(state=tk.DISABLED)
        self.status_bar.set_state("✨ Reescrevendo com IA...", Theme.COLOR_PROCESSING)

        self.transcript.clear()

        def _on_chunk(chunk: str) -> None:
            self.root.after(0, lambda: self.transcript.text_widget.insert(tk.END, chunk))
            self.root.after(0, lambda: self.transcript.text_widget.see(tk.END))

        def _on_done() -> None:
            self.root.after(0, self._rewrite_finished)

        def _on_error(err: str) -> None:
            self.root.after(
                0,
                lambda: self.status_bar.set_state(f"Erro: {err}", Theme.BTN_DANGER_BG),
            )
            self.root.after(2000, self._rewrite_finished)

        self.llm_agent.rewrite_text(text, _on_chunk, _on_done, _on_error)

    def _rewrite_finished(self) -> None:
        self.toggle_btn.configure(state=tk.NORMAL)
        self.rewrite_btn.configure(state=tk.NORMAL)
        self.clear_btn.configure(state=tk.NORMAL)
        self._set_visual_state(self._state)

    def _on_copy_all(self) -> None:
        text = self.transcript.get_text()
        if not text:
            return

        if copy_to_clipboard(text):
            self.status_bar.set_state("✓ Copiado para o clipboard", Theme.COLOR_SUCCESS)
        else:
            self.status_bar.set_state("Erro ao copiar", Theme.COLOR_RECORDING)

        self.root.after(2000, self._restore_status_state)

    def _on_clear(self) -> None:
        self.transcript.clear()
        self.status_bar.set_state("✓ Texto limpo", Theme.TEXT_SECONDARY)
        self.root.after(1500, self._restore_status_state)

    def _restore_status_state(self) -> None:
        if self._recording:
            self.status_bar.set_state("🔴 Gravando...", Theme.COLOR_RECORDING)
        else:
            self.status_bar.set_state("⏸ Pronto para gravar", Theme.TEXT_SECONDARY)

    def _set_visual_state(self, state: str) -> None:
        self._state = state
        self.dot_animator.set_state(state)

        if state == "LOADING":
            self.status_bar.set_state("⏳ Carregando modelo...", Theme.COLOR_PROCESSING)
        elif state == "RECORDING":
            self.status_bar.set_state("🔴 Gravando...", Theme.COLOR_RECORDING)
        elif state == "IDLE":
            self.status_bar.set_state("⏸ Pronto para gravar", Theme.TEXT_SECONDARY)

    def _on_minimize(self) -> None:
        if self._closing:
            return

        try:
            self.root.withdraw()
        except tk.TclError:
            logger.exception("Failed to hide popup window")

    def _on_toggle_visibility(self) -> None:
        try:
            state = self.root.state()
            if state == "withdrawn" or state == "iconic":
                self._show_window()
            else:
                self.root.withdraw()
        except tk.TclError:
            pass

    def _on_close(self) -> None:
        if self._closing:
            return
        self._closing = True

        logger.info("Closing popup window")

        if self._recording:
            self._stop_recording()

        try:
            self.transcription_agent.stop()
        except Exception:
            logger.exception("Error stopping transcription agent")

        try:
            self._tray.stop()
        except Exception:
            logger.exception("Error stopping tray icon")

        with contextlib.suppress(Exception):
            self.dot_animator.stop()

        release()

        try:
            self.root.quit()
            self.root.destroy()
        except tk.TclError:
            pass
