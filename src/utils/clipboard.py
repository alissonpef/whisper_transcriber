from __future__ import annotations

import shutil
import subprocess

from src.logger import get_logger

logger = get_logger(__name__)


def _command_exists(binary: str) -> bool:
    return shutil.which(binary) is not None


def _copy_with_command(command: list[str], text: str) -> bool:
    try:
        subprocess.run(
            command,
            input=text,
            text=True,
            capture_output=True,
            check=True,
            timeout=2,
        )
        return True
    except (FileNotFoundError, subprocess.SubprocessError):
        return False


def _read_with_command(command: list[str]) -> str:
    try:
        result = subprocess.run(
            command,
            text=True,
            capture_output=True,
            check=True,
            timeout=2,
        )
        return result.stdout
    except (FileNotFoundError, subprocess.SubprocessError):
        return ""


def copy_to_clipboard(text: str) -> bool:

    command_candidates: list[tuple[str, list[str]]] = [
        ("xclip", ["xclip", "-selection", "clipboard"]),
        ("xsel", ["xsel", "--clipboard", "--input"]),
        ("wl-copy", ["wl-copy"]),
    ]

    for binary, command in command_candidates:
        if _command_exists(binary) and _copy_with_command(command, text):
            return True

    try:
        import pyperclip

        pyperclip.copy(text)
        return True
    except Exception:
        logger.warning("Clipboard copy failed on all available backends")
        return False


def get_from_clipboard() -> str:
    command_candidates: list[tuple[str, list[str]]] = [
        ("xclip", ["xclip", "-selection", "clipboard", "-o"]),
        ("xsel", ["xsel", "--clipboard", "--output"]),
        ("wl-paste", ["wl-paste", "--no-newline"]),
    ]

    for binary, command in command_candidates:
        if not _command_exists(binary):
            continue
        output: str = _read_with_command(command)
        if output:
            return output

    try:
        import pyperclip

        return str(pyperclip.paste())
    except Exception:
        logger.warning("Clipboard read failed on all available backends")
        return ""
