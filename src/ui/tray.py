from __future__ import annotations

import contextlib
import threading
from collections.abc import Callable
from pathlib import Path

from src.logger import get_logger

logger = get_logger(__name__)

try:
    import pystray
    from PIL import Image

    PYSTRAY_AVAILABLE = True
except ImportError:
    PYSTRAY_AVAILABLE = False
    logger.info("pystray/Pillow not installed; tray icon disabled")


class TrayIcon:
    def __init__(
        self,
        on_toggle: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        self._on_toggle = on_toggle
        self._on_quit = on_quit
        self._icon: object | None = None
        self._thread: threading.Thread | None = None

    @property
    def available(self) -> bool:
        return PYSTRAY_AVAILABLE

    def start(self, icon_path: str | Path) -> None:
        if not PYSTRAY_AVAILABLE:
            return

        path = Path(icon_path)
        if not path.exists():
            logger.warning("Tray icon image not found at %s", path)
            return

        try:
            image = Image.open(str(path))
        except Exception:
            logger.exception("Failed to load tray icon image")
            return

        menu = pystray.Menu(
            pystray.MenuItem(
                "Mostrar / Ocultar",
                self._handle_toggle,
                default=True,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Sair", self._handle_quit),
        )

        self._icon = pystray.Icon(
            name="whisper-transcriber",
            icon=image,
            title="Whisper Transcriber",
            menu=menu,
        )

        self._thread = threading.Thread(
            target=self._icon.run,
            daemon=True,
            name="tray-icon",
        )
        self._thread.start()
        logger.info("System tray icon started")

    def stop(self) -> None:
        if self._icon is not None:
            with contextlib.suppress(Exception):
                self._icon.stop()
            self._icon = None
        logger.debug("System tray icon stopped")

    def _handle_toggle(self, _icon: object = None, _item: object = None) -> None:
        try:
            self._on_toggle()
        except Exception:
            logger.exception("Tray toggle callback error")

    def _handle_quit(self, _icon: object = None, _item: object = None) -> None:
        try:
            self._on_quit()
        except Exception:
            logger.exception("Tray quit callback error")
