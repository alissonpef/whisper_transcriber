from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import sys
from pathlib import Path

from src.config import DAEMON_LOCK_FILE, HOTKEY, LOCK_FILE
from src.logger import get_logger

logger = get_logger(__name__)

PROJECT_DIR: Path = Path(__file__).resolve().parent.parent
SCRIPTS_DIR: Path = PROJECT_DIR / "scripts"


def detect_session() -> str:
    return os.environ.get("XDG_SESSION_TYPE", "x11").strip().lower()


def _write_daemon_lock() -> None:
    try:
        DAEMON_LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")
    except OSError:
        logger.exception("Failed to write daemon lock file")


def _release_daemon_lock() -> None:
    with contextlib.suppress(OSError):
        DAEMON_LOCK_FILE.unlink(missing_ok=True)


def send_signal_to_popup() -> None:
    pid = _read_lock_pid(LOCK_FILE)
    if pid is not None:
        try:
            os.kill(pid, signal.SIGUSR1)
            logger.info("Sent SIGUSR1 to popup PID %s", pid)
            return
        except (ProcessLookupError, PermissionError):
            logger.warning("Stale popup lock (PID %s); launching new popup", pid)
            LOCK_FILE.unlink(missing_ok=True)

    run_popup = SCRIPTS_DIR / "run_popup.sh"
    if run_popup.exists():
        logger.info("Launching popup via %s", run_popup)
        subprocess.Popen(
            [str(run_popup), "--record"],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        logger.info("run_popup.sh not found; launching popup directly")
        subprocess.Popen(
            [sys.executable, "-m", "src.transcriber_popup", "--record"],
            cwd=str(PROJECT_DIR),
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def _read_lock_pid(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        pid = int(path.read_text(encoding="utf-8").strip())
        os.kill(pid, 0)
        return pid
    except (ValueError, OSError):
        return None


def run_x11_daemon() -> None:
    try:
        from pynput import keyboard
    except ImportError:
        logger.error("pynput is required for X11 hotkey listening")
        sys.exit(1)

    combination = HOTKEY.combination
    logger.info("X11 daemon: listening for %s", combination)
    print(f"[whisper-daemon] X11 mode · hotkey: {combination}")

    _write_daemon_lock()
    try:
        with keyboard.GlobalHotKeys({combination: send_signal_to_popup}) as hotkeys:
            hotkeys.join()
    finally:
        _release_daemon_lock()


def run_wayland_daemon() -> None:
    logger.info("Wayland daemon: waiting for SIGUSR1 signals")
    print("[whisper-daemon] Wayland mode · waiting for SIGUSR1 from GNOME shortcut")

    signal.signal(signal.SIGUSR1, _on_sigusr1)
    _write_daemon_lock()
    try:
        while True:
            signal.pause()
    except KeyboardInterrupt:
        pass
    finally:
        _release_daemon_lock()


def _on_sigusr1(_signum: int, _frame: object) -> None:
    logger.debug("SIGUSR1 received in daemon")
    send_signal_to_popup()


def main() -> None:
    session = detect_session()
    logger.info("Detected session type: %s", session)

    if "wayland" in session:
        run_wayland_daemon()
    else:
        run_x11_daemon()


if __name__ == "__main__":
    main()
