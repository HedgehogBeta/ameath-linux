import gc
import weakref

from PyQt5 import QtCore, QtWidgets

from ameath_linux.config import DEFAULT_CONFIG
from ameath_linux import manager as manager_module


class _Signal:
    def __init__(self):
        self.callback = None

    def connect(self, callback):
        self.callback = callback


class _WeakTray:
    Trigger = 3

    @staticmethod
    def isSystemTrayAvailable():
        return True

    def __init__(self, *_args):
        self.activated = _Signal()
        self._menu = lambda: None

    def setToolTip(self, _text):
        pass

    def setContextMenu(self, menu):
        self._menu = weakref.ref(menu)

    def contextMenu(self):
        return self._menu()

    def show(self):
        pass

    def hide(self):
        pass


class _Pet:
    def __init__(self, *_args):
        self.user_hidden = False
        self.visible = True

    def hide(self):
        self.visible = False

    def show(self):
        self.visible = True

    def close(self):
        self.visible = False

    def deleteLater(self):
        pass


class _Voice:
    def configure(self, *_args):
        pass

    def stop(self):
        pass


class _Music:
    def __init__(self, *_args):
        self.playing = False
        self.paused = False

    def toggle(self):
        self.playing = not self.playing

    def stop(self):
        self.playing = False


def test_tray_menu_and_callbacks_survive_garbage_collection(monkeypatch):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    monkeypatch.setattr(manager_module.QtWidgets, "QSystemTrayIcon", _WeakTray)
    monkeypatch.setattr(manager_module, "PetWidget", _Pet)
    monkeypatch.setattr(manager_module, "VoicePlayer", _Voice)
    monkeypatch.setattr(manager_module, "MusicPlayer", _Music)
    monkeypatch.setattr(manager_module, "load_config", lambda: dict(DEFAULT_CONFIG))
    monkeypatch.setattr(manager_module, "save_config", lambda _config: None)

    manager = manager_module.PetManager(app)
    gc.collect()

    assert manager.tray.contextMenu() is not None
    labels = [action.text() for action in manager.tray.contextMenu().actions()]
    assert "隐藏" in labels
    assert "退出" in labels

    hide = next(
        action for action in manager.tray.contextMenu().actions() if action.text() == "隐藏"
    )
    hide.trigger()
    assert manager.visible is False

