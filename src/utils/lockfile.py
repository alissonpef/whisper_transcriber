from __future__ import annotations

import os
from pathlib import Path

from src.config import LOCK_FILE
from src.logger import get_logger

logger = get_logger(__name__)


def _pid_is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _read_pid(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def get_pid() -> int | None:
    return _read_pid(LOCK_FILE)


def is_locked() -> bool:
    pid: int | None = get_pid()
    if pid is None:
        return False
    return _pid_is_running(pid)


def _try_create_lock(path: Path, pid: int) -> bool:
    flags: int = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    fd: int | None = None
    try:
        fd = os.open(path, flags)
        os.write(fd, f"{pid}".encode())
        return True
    except FileExistsError:
        return False
    finally:
        if fd is not None:
            os.close(fd)


def acquire() -> bool:
    current_pid: int = os.getpid()

    if _try_create_lock(LOCK_FILE, current_pid):
        logger.debug("Acquired lockfile with PID %s", current_pid)
        return True

    existing_pid: int | None = get_pid()
    if existing_pid is not None and _pid_is_running(existing_pid):
        logger.debug("Lockfile already held by live PID %s", existing_pid)
        return False

    release()
    if _try_create_lock(LOCK_FILE, current_pid):
        logger.info("Recovered stale lockfile and acquired new lock")
        return True

    logger.debug("Failed to acquire lockfile after stale recovery")
    return False


def release() -> None:
    try:
        LOCK_FILE.unlink(missing_ok=True)
        logger.debug("Released lockfile")
    except OSError:
        logger.exception("Unable to remove lockfile")
