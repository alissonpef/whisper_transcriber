from __future__ import annotations

import contextlib
import sys


def main() -> None:
    auto_start = "--record" in sys.argv
    start_in_tray = "--tray" in sys.argv

    from src.ui.popup_window import PopupWindow

    try:
        window = PopupWindow(auto_start_recording=auto_start)
        if start_in_tray:
            window.root.after(0, window.root.withdraw)
        window.run()
    except RuntimeError:
        import os
        import signal

        from src.utils.lockfile import get_pid

        pid = get_pid()
        if pid is not None:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.kill(pid, signal.SIGUSR1)
        sys.exit(0)


if __name__ == "__main__":
    main()
