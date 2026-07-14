from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

BASE_DIR: Path = Path(__file__).resolve().parent.parent
LOGS_DIR: Path = Path.home() / ".local" / "share" / "whisper-transcriber"
LOCK_FILE: Path = Path("/tmp/whisper_popup.lock")
DAEMON_LOCK_FILE: Path = Path("/tmp/whisper_daemon.lock")
ICON_PATH: Path = BASE_DIR / "assets" / "icon.png"
POPUP_WINDOW_TITLE: str = "Transcritor Whisper"

ModelSize = Literal["tiny", "base", "small", "medium", "large-v3"]
ModelDevice = Literal["cuda", "cpu"]
ModelComputeType = Literal["float16", "int8", "float32"]


def _literal_from_env(value: str | None, allowed: Sequence[str], default: str) -> str:
    if value is None:
        return default
    normalized: str = value.strip().lower()
    return normalized if normalized in allowed else default


@dataclass
class AudioConfig:
    sample_rate: int = 16000
    channels: int = 1
    dtype: str = "float32"
    blocksize: int = 4096
    queue_maxsize: int = 100
    chunk_secs: float = 3.0


@dataclass
class ModelConfig:
    size: ModelSize = "small"
    device: ModelDevice = "cuda"
    compute_type: ModelComputeType = "float16"
    language: str = "pt"
    beam_size: int = 5
    cpu_fallback: bool = True


@dataclass
class HotkeyConfig:
    combination: str = "<ctrl>+<shift>+space"


@dataclass
class UIConfig:
    width: int = 680
    height: int = 460
    min_width: int = 420
    min_height: int = 300
    always_on_top: bool = True
    auto_start_recording: bool = False


AUDIO: AudioConfig = AudioConfig()

_default_device: str = _literal_from_env(
    os.environ.get("WHISPER_DEVICE"),
    allowed=("cuda", "cpu"),
    default="cuda",
)
_default_size: str = _literal_from_env(
    os.environ.get("WHISPER_MODEL"),
    allowed=("tiny", "base", "small", "medium", "large-v3"),
    default="small",
)
_default_compute_type: str = _literal_from_env(
    os.environ.get("WHISPER_COMPUTE_TYPE"),
    allowed=("float16", "int8", "float32"),
    default="float16" if _default_device == "cuda" else "int8",
)

MODEL: ModelConfig = ModelConfig(
    size=cast(ModelSize, _default_size),
    device=cast(ModelDevice, _default_device),
    compute_type=cast(ModelComputeType, _default_compute_type),
)
HOTKEY: HotkeyConfig = HotkeyConfig()
UI: UIConfig = UIConfig()
