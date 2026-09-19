from __future__ import annotations

from PyQt5 import QtCore, QtGui, QtWidgets

from .animation import AssetBank
from .audio import MusicPlayer, VoicePlayer
from .config import load_config, save_config, set_auto_startup
from .paths import asset_path
from .pet import PetWidget


class PetManager(QtCore.QObject):
    def __init__(self, app: QtWidgets.QApplication):
        super().__init__()
        self.app = app
        self.config = load_config()
        self.assets = AssetBank(asset_path("gifs"))
        self.pets: list[PetWidget] = []
        self.visible = True
        self.follow_mouse = self.config["follow_mouse"]
        self.click_through = self.config["click_through"]
        if self.click_through and not QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
            # Without a tray there would be no way to turn input back on.
            self.click_through = False
            self.config["click_through"] = False
            save_config(self.config)
        self.display_priority = self.config["display_priority"]
        self.is_paused = False
        self.settings_dialog = None
        self.voice = VoicePlayer()
        self.voice.configure(
            self.config["voice_enabled"], self.config["voice_volume"]
        )
        self.music = MusicPlayer(self.config["music_volume"])
        self.tray: QtWidgets.QSystemTrayIcon | None = None
        self.tray_menu: QtWidgets.QMenu | None = None
        self.set_instance_count(self.config["instance_count"], persist=False)
        self._create_tray()

    def activity_rect(self) -> QtCore.QRect:
        screens = self.app.screens()
        if not screens:
            return QtCore.QRect(0, 0, 1920, 1080)
        if not self.config["total_screen"]:
            index = min(self.config["screen_index"], len(screens) - 1)
            return QtCore.QRect(screens[index].availableGeometry())
        result = QtCore.QRect(screens[0].availableGeometry())
        for screen in screens[1:]:
            result = result.united(screen.availableGeometry())
        return result

    def screen_rects(self) -> list[tuple[int, int, int, int]]:
        return [
            (g.x(), g.y(), g.width(), g.height())
            for g in (screen.geometry() for screen in self.app.screens())
        ]

    def _persist(self, **values) -> None:
        self.config.update(values)
        save_config(self.config)

    def set_instance_count(self, count: int, persist: bool = True) -> None:
        count = min(max(1, int(count)), 80)
        while len(self.pets) < count:
            pet = PetWidget(self, len(self.pets))
            pet.user_hidden = not self.visible
            if not self.visible:
                pet.hide()
            self.pets.append(pet)
        while len(self.pets) > count:
            pet = self.pets.pop()
            pet.close()
            pet.deleteLater()
        if persist:
            self._persist(instance_count=count)

    def set_scale(self, index: int) -> None:
        for pet in self.pets:
            pet.set_scale(index)
        if self.pets:
            self.assets.retain_scale(self.pets[0].scale)
        self._persist(scale_index=index)

    def set_transparency(self, index: int) -> None:
        for pet in self.pets:
            pet.set_transparency(index)
        self._persist(transparency_index=index)

    def set_follow_mouse(self, enabled: bool) -> None:
        self.follow_mouse = bool(enabled)
        for pet in self.pets:
            pet.follow_mouse = self.follow_mouse
        self._persist(follow_mouse=self.follow_mouse)

    def set_click_through(self, enabled: bool) -> None:
        self.click_through = bool(enabled)
        for pet in self.pets:
            pet.set_click_through(self.click_through)
        self._persist(click_through=self.click_through)

    def set_display_priority(self, mode: int, persist: bool = True) -> None:
        self.display_priority = min(max(1, int(mode)), 3)
        for pet in self.pets:
            pet.set_display_priority(self.display_priority)
        if persist:
            self._persist(display_priority=self.display_priority)

    def set_wander_mode(self, mode: int) -> None:
        mode = min(max(0, int(mode)), 2)
        for pet in self.pets:
            pet.wander_idle_stay_mode = mode
        self._persist(wander_idle_stay_mode=mode)

    def set_window_snap(self, enabled: bool) -> None:
        for pet in self.pets:
            pet.window_snap = bool(enabled)
        self._persist(window_snap=bool(enabled))

    def set_voice(self, enabled: bool | None = None, volume: int | None = None) -> None:
        if enabled is not None:
            self.config["voice_enabled"] = bool(enabled)
        if volume is not None:
            self.config["voice_volume"] = min(max(0, int(volume)), 150)
        self.voice.configure(
            self.config["voice_enabled"], self.config["voice_volume"]
        )
        save_config(self.config)

    def set_music(self, enabled: bool | None = None, volume: int | None = None) -> None:
        if enabled is not None:
            self.config["music_enabled"] = bool(enabled)
            if not enabled:
                self.music.stop()
        if volume is not None:
            self.config["music_volume"] = min(max(0, int(volume)), 100)
            self.music.set_volume(self.config["music_volume"])
        save_config(self.config)

    def set_display_area(self, total_screen: bool, screen_index: int) -> None:
        self.config["total_screen"] = bool(total_screen)
        self.config["screen_index"] = max(0, int(screen_index))
        save_config(self.config)
        for pet in self.pets:
            rect = self.activity_rect()
            pet.x = min(max(pet.x, rect.left()), max(rect.left(), rect.right() - pet.width()))
            pet.y = min(max(pet.y, rect.top()), max(rect.top(), rect.bottom() - pet.height()))
            pet.move(round(pet.x), round(pet.y))
            pet.target_x, pet.target_y = pet._random_target()

    def set_startup(self, enabled: bool) -> None:
        set_auto_startup(enabled)
        self._persist(auto_startup=bool(enabled))

    def toggle_pause(self) -> None:
        self.is_paused = not self.is_paused
        for pet in self.pets:
            pet.set_paused(self.is_paused)

    def hide_all(self) -> None:
        self.visible = False
        for pet in self.pets:
            pet.user_hidden = True
            pet.hide()

    def show_all(self) -> None:
        self.visible = True
        for pet in self.pets:
            pet.user_hidden = False
            pet.show()

    def toggle_visible(self) -> None:
        self.hide_all() if self.visible else self.show_all()

    def show_settings(self, tab: int = 0) -> None:
        from .settings import SettingsDialog

        if self.settings_dialog is None:
            self.settings_dialog = SettingsDialog(self)
            self.settings_dialog.destroyed.connect(self._settings_destroyed)
        self.settings_dialog.tabs.setCurrentIndex(tab)
        self.settings_dialog.show()
        self.settings_dialog.raise_()
        self.settings_dialog.activateWindow()

    def _settings_destroyed(self) -> None:
        self.settings_dialog = None

    def show_quick_menu(self, position: QtCore.QPoint) -> None:
        menu = self._build_menu()
        menu.exec_(position)

    def _build_menu(self) -> QtWidgets.QMenu:
        menu = QtWidgets.QMenu()

        def run(action) -> None:
            action()
            self._sync_menu(menu)

        music_action = menu.addAction(
            "⏹ 停止演出" if self.music.playing and not self.music.paused else "▶ 演出开始"
        )
        music_action.setObjectName("music")
        music_action.setEnabled(self.config["music_enabled"])
        music_action.triggered.connect(lambda _checked=False: run(self.music.toggle))
        menu.addSeparator()
        follow = menu.addAction("跟随鼠标")
        follow.setObjectName("follow")
        follow.setCheckable(True)
        follow.setChecked(self.follow_mouse)
        follow.triggered.connect(lambda value: run(lambda: self.set_follow_mouse(value)))
        pause = menu.addAction("继续" if self.is_paused else "暂停")
        pause.setObjectName("pause")
        pause.triggered.connect(lambda _checked=False: run(self.toggle_pause))
        click = menu.addAction("鼠标穿透")
        click.setObjectName("click-through")
        click.setCheckable(True)
        click.setChecked(self.click_through)
        click.triggered.connect(lambda value: run(lambda: self.set_click_through(value)))
        menu.addSeparator()
        visible = menu.addAction("隐藏" if self.visible else "显示")
        visible.setObjectName("visible")
        visible.triggered.connect(lambda _checked=False: run(self.toggle_visible))
        menu.addAction("音乐播放器", lambda: self.show_settings(1))
        menu.addAction("更多设置…", lambda: self.show_settings(0))
        menu.addSeparator()
        menu.addAction("退出", self.quit)
        menu.aboutToShow.connect(lambda: self._sync_menu(menu))
        return menu

    def _sync_menu(self, menu: QtWidgets.QMenu) -> None:
        for action in menu.actions():
            name = action.objectName()
            if name == "music":
                action.setText(
                    "⏹ 停止演出"
                    if self.music.playing and not self.music.paused
                    else "▶ 演出开始"
                )
                action.setEnabled(self.config["music_enabled"])
            elif name == "follow":
                action.setChecked(self.follow_mouse)
            elif name == "pause":
                action.setText("继续" if self.is_paused else "暂停")
            elif name == "click-through":
                action.setChecked(self.click_through)
            elif name == "visible":
                action.setText("隐藏" if self.visible else "显示")

    def _create_tray(self) -> None:
        if not QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
            return
        icon = QtGui.QIcon(str(asset_path("gifs", "ameath_content.png")))
        self.tray = QtWidgets.QSystemTrayIcon(icon, self.app)
        self.tray.setToolTip("远航星 · Ameath")
        self.tray_menu = self._build_menu()
        self.tray.setContextMenu(self.tray_menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    def refresh_tray_menu(self) -> None:
        if self.tray_menu:
            self._sync_menu(self.tray_menu)

    def _tray_activated(self, reason: QtWidgets.QSystemTrayIcon.ActivationReason) -> None:
        if reason == QtWidgets.QSystemTrayIcon.Trigger:
            self.toggle_visible()
            self.refresh_tray_menu()

    def quit(self) -> None:
        self.voice.stop()
        self.music.stop()
        for pet in list(self.pets):
            pet.close()
        if self.tray:
            self.tray.hide()
        self.tray_menu = None
        self.app.quit()
