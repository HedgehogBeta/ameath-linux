from __future__ import annotations

import threading
import webbrowser
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt5 import QtCore, QtGui, QtWidgets

from . import __version__
from .config import is_auto_startup_enabled, save_config
from .constants import GITEE_RELEASES_URL, SCALE_OPTIONS, TRANSPARENCY_OPTIONS
from .paths import MUSIC_DIR, asset_path
from .platform_linux import is_wayland, open_path
from .update import ReleaseInfo, check_latest, is_newer

if TYPE_CHECKING:
    from .manager import PetManager


PINK_STYLE = """
QDialog, QWidget { background: #fff1f6; color: #4a2a3a; }
QTabWidget::pane { border: 1px solid #f3c2d4; background: white; }
QTabBar::tab { background: #ffe1ee; padding: 9px 18px; margin-right: 2px; }
QTabBar::tab:selected { background: #ffd1e5; color: #e84d8e; }
QGroupBox { border: 1px solid #f3c2d4; border-radius: 7px; margin-top: 12px; padding-top: 10px; background: white; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #e84d8e; }
QPushButton { background: #ff69b4; color: white; border: 0; border-radius: 5px; padding: 7px 13px; }
QPushButton:disabled { background: #d9bdc8; }
QPushButton:hover { background: #e84d8e; }
QComboBox, QSpinBox, QListWidget, QTextEdit { background: white; border: 1px solid #f3c2d4; border-radius: 4px; padding: 4px; }
QSlider::groove:horizontal { height: 5px; background: #f3c2d4; border-radius: 2px; }
QSlider::handle:horizontal { width: 15px; margin: -5px 0; background: #ff69b4; border-radius: 7px; }
"""


class SettingsDialog(QtWidgets.QDialog):
    update_result = QtCore.pyqtSignal(object)

    def __init__(self, manager: "PetManager"):
        super().__init__()
        self.manager = manager
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setWindowTitle("Ameath 设置")
        self.setWindowIcon(QtGui.QIcon(str(asset_path("gifs", "ameath_content.png"))))
        self.resize(900, 760)
        self.setMinimumSize(720, 580)
        self.setStyleSheet(PINK_STYLE)
        self.latest_release: ReleaseInfo | None = None
        self._seeking = False

        layout = QtWidgets.QVBoxLayout(self)
        self.tabs = QtWidgets.QTabWidget()
        layout.addWidget(self.tabs, 1)
        self.tabs.addTab(self._personalization_tab(), "个性化")
        self.tabs.addTab(self._music_tab(), "音乐")
        self.tabs.addTab(self._update_tab(), "检查更新")
        self.tabs.addTab(self._about_tab(), "关于")
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        buttons.rejected.connect(self.close)
        layout.addWidget(buttons)
        self.update_result.connect(self._handle_update_result)

    def _scroll_tab(self, content: QtWidgets.QWidget) -> QtWidgets.QScrollArea:
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setWidget(content)
        return scroll

    def _group(self, title: str) -> tuple[QtWidgets.QGroupBox, QtWidgets.QFormLayout]:
        box = QtWidgets.QGroupBox(title)
        form = QtWidgets.QFormLayout(box)
        form.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        return box, form

    def _personalization_tab(self) -> QtWidgets.QWidget:
        content = QtWidgets.QWidget()
        outer = QtWidgets.QVBoxLayout(content)

        appearance, form = self._group("外观")
        scale = QtWidgets.QComboBox()
        scale.addItems([f"{value:.1f}x" for value in SCALE_OPTIONS])
        scale.setCurrentIndex(self.manager.config["scale_index"])
        scale.currentIndexChanged.connect(self.manager.set_scale)
        form.addRow("缩放比例", scale)
        opacity = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        opacity.setRange(0, len(TRANSPARENCY_OPTIONS) - 1)
        opacity.setValue(self.manager.config["transparency_index"])
        opacity.valueChanged.connect(self.manager.set_transparency)
        form.addRow("窗口透明度", opacity)
        outer.addWidget(appearance)

        behavior, form = self._group("行为")
        follow = QtWidgets.QCheckBox("跟随鼠标")
        follow.setChecked(self.manager.follow_mouse)
        follow.toggled.connect(self.manager.set_follow_mouse)
        form.addRow(follow)
        click = QtWidgets.QCheckBox("鼠标穿透（开启后请用托盘恢复）")
        click.setChecked(self.manager.click_through)
        click.toggled.connect(self.manager.set_click_through)
        form.addRow(click)
        snap = QtWidgets.QCheckBox("暂停时贴靠活动窗口")
        snap.setChecked(self.manager.config["window_snap"])
        snap.toggled.connect(self.manager.set_window_snap)
        form.addRow(snap)
        wander = QtWidgets.QComboBox()
        wander.addItems(("始终移动", "概率停驻", "到点停驻"))
        wander.setCurrentIndex(self.manager.config["wander_idle_stay_mode"])
        wander.currentIndexChanged.connect(self.manager.set_wander_mode)
        form.addRow("游荡停驻模式", wander)
        priority = QtWidgets.QComboBox()
        priority.addItems(("始终置顶", "全屏时隐藏", "仅桌面层"))
        priority.setCurrentIndex(self.manager.display_priority - 1)
        priority.currentIndexChanged.connect(
            lambda index: self.manager.set_display_priority(index + 1)
        )
        form.addRow("显示层级", priority)
        instances = QtWidgets.QSpinBox()
        instances.setRange(1, 80)
        instances.setValue(len(self.manager.pets))
        instances.valueChanged.connect(self.manager.set_instance_count)
        form.addRow("桌宠数量", instances)
        outer.addWidget(behavior)

        display, form = self._group("显示区域")
        all_screens = QtWidgets.QCheckBox("使用全部屏幕")
        all_screens.setChecked(self.manager.config["total_screen"])
        screen = QtWidgets.QComboBox()
        screen.addItems(
            [f"屏幕 {i + 1}：{s.name()}" for i, s in enumerate(self.manager.app.screens())]
        )
        screen.setCurrentIndex(
            min(self.manager.config["screen_index"], max(0, screen.count() - 1))
        )
        screen.setEnabled(not all_screens.isChecked())

        def update_area() -> None:
            screen.setEnabled(not all_screens.isChecked())
            self.manager.set_display_area(all_screens.isChecked(), screen.currentIndex())

        all_screens.toggled.connect(update_area)
        screen.currentIndexChanged.connect(lambda _index: update_area())
        form.addRow(all_screens)
        form.addRow("单屏选择", screen)
        outer.addWidget(display)

        sound, form = self._group("声音")
        voice_enabled = QtWidgets.QCheckBox("启用拖拽语音")
        voice_enabled.setChecked(self.manager.config["voice_enabled"])
        voice_enabled.toggled.connect(lambda value: self.manager.set_voice(enabled=value))
        form.addRow(voice_enabled)
        voice_volume = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        voice_volume.setRange(0, 150)
        voice_volume.setValue(self.manager.config["voice_volume"])
        voice_volume.valueChanged.connect(lambda value: self.manager.set_voice(volume=value))
        form.addRow("语音音量", voice_volume)
        music_enabled = QtWidgets.QCheckBox("启用音乐播放器")
        music_enabled.setChecked(self.manager.config["music_enabled"])
        music_enabled.toggled.connect(lambda value: self.manager.set_music(enabled=value))
        form.addRow(music_enabled)
        music_volume = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        music_volume.setRange(0, 100)
        music_volume.setValue(self.manager.config["music_volume"])
        music_volume.valueChanged.connect(lambda value: self.manager.set_music(volume=value))
        form.addRow("音乐音量", music_volume)
        outer.addWidget(sound)

        startup, form = self._group("启动")
        auto = QtWidgets.QCheckBox("登录 Linux 桌面后自动启动")
        auto.setChecked(is_auto_startup_enabled())
        auto.toggled.connect(self.manager.set_startup)
        form.addRow(auto)
        start_paused = QtWidgets.QCheckBox("启动后立即暂停")
        start_paused.setChecked(self.manager.config["start_paused"])

        def save_start_paused(value: bool) -> None:
            self.manager.config["start_paused"] = value
            save_config(self.manager.config)

        start_paused.toggled.connect(save_start_paused)
        form.addRow(start_paused)
        position = QtWidgets.QComboBox()
        positions = [
            ("随机", "random"),
            ("右下", "bottom_right"),
            ("左下", "bottom_left"),
            ("右上", "top_right"),
            ("左上", "top_left"),
            ("中央", "center"),
        ]
        for label, value in positions:
            position.addItem(label, value)
        current = self.manager.config.get("startup_position", "random")
        position.setCurrentIndex(max(0, [value for _, value in positions].index(current)))

        def save_position(_index: int) -> None:
            self.manager.config["startup_position"] = position.currentData()
            save_config(self.manager.config)

        position.currentIndexChanged.connect(save_position)
        form.addRow("初始位置", position)
        outer.addWidget(startup)
        if is_wayland():
            warning = QtWidgets.QLabel(
                "Wayland 提示：窗口置顶、穿透、活动窗口贴靠会受组合器安全策略限制。"
            )
            warning.setWordWrap(True)
            outer.addWidget(warning)
        outer.addStretch()
        return self._scroll_tab(content)

    def _music_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        folder = QtWidgets.QLabel(f"📁 {MUSIC_DIR}")
        folder.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        layout.addWidget(folder)
        self.music_list = QtWidgets.QListWidget()
        layout.addWidget(self.music_list, 1)
        row = QtWidgets.QHBoxLayout()
        previous = QtWidgets.QPushButton("上一首")
        self.music_toggle = QtWidgets.QPushButton("播放")
        next_button = QtWidgets.QPushButton("下一首")
        previous.clicked.connect(self.manager.music.previous)
        self.music_toggle.clicked.connect(self.manager.music.toggle)
        next_button.clicked.connect(self.manager.music.next)
        row.addStretch()
        row.addWidget(previous)
        row.addWidget(self.music_toggle)
        row.addWidget(next_button)
        row.addStretch()
        layout.addLayout(row)
        self.progress = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.progress.setRange(0, 0)
        self.progress.sliderPressed.connect(lambda: setattr(self, "_seeking", True))
        self.progress.sliderReleased.connect(self._finish_seek)
        layout.addWidget(self.progress)
        actions = QtWidgets.QHBoxLayout()
        import_button = QtWidgets.QPushButton("导入音乐")
        refresh = QtWidgets.QPushButton("刷新")
        open_folder = QtWidgets.QPushButton("打开歌曲文件夹")
        import_button.clicked.connect(self._import_music)
        refresh.clicked.connect(self.manager.music.refresh)
        open_folder.clicked.connect(lambda: open_path(MUSIC_DIR))
        actions.addWidget(import_button)
        actions.addWidget(refresh)
        actions.addWidget(open_folder)
        actions.addStretch()
        layout.addLayout(actions)
        self.music_list.itemDoubleClicked.connect(
            lambda item: self.manager.music.play(self.music_list.row(item))
        )
        self.manager.music.files_changed.connect(self._refresh_music_list)
        self.manager.music.track_changed.connect(self._select_track)
        self.manager.music.state_changed.connect(self._music_state)
        self.manager.music.position_changed.connect(self._music_position)
        self._refresh_music_list()
        return widget

    def _refresh_music_list(self) -> None:
        self.music_list.clear()
        self.music_list.addItems([path.name for path in self.manager.music.files])
        if self.manager.music.current_index >= 0:
            self.music_list.setCurrentRow(self.manager.music.current_index)

    def _select_track(self, name: str) -> None:
        matches = self.music_list.findItems(name, QtCore.Qt.MatchExactly)
        if matches:
            self.music_list.setCurrentItem(matches[0])

    def _music_state(self, playing: bool, paused: bool) -> None:
        self.music_toggle.setText("继续" if paused else ("暂停" if playing else "播放"))

    def _music_position(self, position: float, duration: float) -> None:
        if self._seeking:
            return
        self.progress.setRange(0, max(0, round(duration * 1000)))
        self.progress.setValue(round(position * 1000))

    def _finish_seek(self) -> None:
        self._seeking = False
        self.manager.music.seek(self.progress.value() / 1000)

    def _import_music(self) -> None:
        paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "导入音乐",
            str(Path.home()),
            "音频 (*.mp3 *.wav *.flac *.ogg *.m4a)",
        )
        if paths:
            self.manager.music.import_files(paths)

    def _update_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        title = QtWidgets.QLabel(f"当前版本：{__version__}")
        font = title.font()
        font.setPointSize(font.pointSize() + 4)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)
        self.update_status = QtWidgets.QLabel("点击按钮检查 Gitee 发布页")
        layout.addWidget(self.update_status)
        self.update_notes = QtWidgets.QTextEdit()
        self.update_notes.setReadOnly(True)
        layout.addWidget(self.update_notes, 1)
        row = QtWidgets.QHBoxLayout()
        self.check_update_button = QtWidgets.QPushButton("检查更新")
        self.open_release_button = QtWidgets.QPushButton("打开发布页")
        self.open_release_button.setEnabled(False)
        self.check_update_button.clicked.connect(self._check_update)
        self.open_release_button.clicked.connect(self._open_release)
        row.addWidget(self.check_update_button)
        row.addWidget(self.open_release_button)
        row.addStretch()
        layout.addLayout(row)
        return widget

    def _check_update(self) -> None:
        self.check_update_button.setEnabled(False)
        self.update_status.setText("正在检查更新…")

        def worker() -> None:
            try:
                result: object = check_latest()
            except Exception as error:
                result = error
            self.update_result.emit(result)

        threading.Thread(target=worker, daemon=True).start()

    def _handle_update_result(self, result: object) -> None:
        self.check_update_button.setEnabled(True)
        if isinstance(result, Exception):
            self.update_status.setText(f"检查失败：{result}")
            return
        self.latest_release = result
        assert isinstance(result, ReleaseInfo)
        newer = is_newer(result.version, __version__)
        self.update_status.setText(
            f"发现新版本 {result.version}" if newer else f"已是最新版本（上游 {result.version}）"
        )
        self.update_notes.setPlainText(result.notes)
        self.open_release_button.setEnabled(True)

    def _open_release(self) -> None:
        url = self.latest_release.asset_url if self.latest_release else GITEE_RELEASES_URL
        webbrowser.open(url or GITEE_RELEASES_URL)

    def _about_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        image = QtWidgets.QLabel()
        pixmap = QtGui.QPixmap(str(asset_path("gifs", "ameath_content.png")))
        image.setPixmap(pixmap.scaled(180, 180, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        image.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(image)
        title = QtWidgets.QLabel("远航星 · Ameath")
        title.setAlignment(QtCore.Qt.AlignCenter)
        font = title.font()
        font.setPointSize(font.pointSize() + 7)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)
        text = QtWidgets.QLabel(
            f"Linux 移植版 {__version__}\n\n"
            "原项目：sinlatansen / -fugu-\n"
            "GIF 素材：@_BLZ_\n"
            "许可证：MIT\n\n"
            "“但愿我会让你感到骄傲，但愿我没有让你失望。”"
        )
        text.setAlignment(QtCore.Qt.AlignCenter)
        text.setWordWrap(True)
        layout.addWidget(text)
        link = QtWidgets.QPushButton("打开上游项目发布页")
        link.clicked.connect(lambda: webbrowser.open(GITEE_RELEASES_URL))
        layout.addWidget(link, alignment=QtCore.Qt.AlignCenter)
        layout.addStretch()
        return widget

