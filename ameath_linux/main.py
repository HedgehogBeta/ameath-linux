from __future__ import annotations

import os
import signal
import sys

from PyQt5 import QtCore, QtGui, QtWidgets

from .manager import PetManager
from .paths import asset_path
from .single_instance import InstanceLock


def _configure_qt() -> None:
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")


def main() -> int:
    _configure_qt()
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Ameath Linux")
    app.setApplicationDisplayName("远航星 · Ameath")
    app.setDesktopFileName("ameath-linux")
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(QtGui.QIcon(str(asset_path("gifs", "ameath_content.png"))))
    font_id = QtGui.QFontDatabase.addApplicationFont(str(asset_path("fonts", "zpix.ttf")))
    families = QtGui.QFontDatabase.applicationFontFamilies(font_id)
    if families:
        app.setFont(QtGui.QFont(families[0], 10))

    instance = InstanceLock()
    command = "quit" if "--quit" in sys.argv[1:] else "show"
    if not instance.acquire():
        return 0 if instance.notify_running(command) else 1

    manager = PetManager(app)

    def show_running_instance(*_args) -> None:
        manager.show_all()
        manager.refresh_tray_menu()
        for pet in manager.pets:
            pet.raise_()

    signal.signal(signal.SIGUSR1, show_running_instance)
    signal.signal(signal.SIGINT, lambda *_args: manager.quit())
    signal.signal(signal.SIGTERM, lambda *_args: manager.quit())
    app.aboutToQuit.connect(instance.release)
    signal_timer = QtCore.QTimer()
    signal_timer.timeout.connect(lambda: None)
    signal_timer.start(250)
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
