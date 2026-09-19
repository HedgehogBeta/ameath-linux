from __future__ import annotations

import math
import random
import time
from typing import TYPE_CHECKING

from PyQt5 import QtCore, QtGui, QtWidgets

from .animation import Animation
from .constants import (
    DISPLAY_ALWAYS_TOP,
    DISPLAY_DESKTOP_ONLY,
    DISPLAY_HIDE_FULLSCREEN,
    EDGE_ESCAPE_CHANCE,
    FOLLOW_DISTANCE,
    FOLLOW_START_DIST,
    FOLLOW_STOP_DIST,
    INERTIA_FACTOR,
    INTENT_FACTOR,
    JITTER,
    JITTER_INTERVAL,
    MOTION_CURIOUS,
    MOTION_FOLLOW,
    MOTION_REST,
    MOTION_WANDER,
    MOVE_INTERVAL,
    OUTSIDE_TARGET_CHANCE,
    PAUSED_ANIMATION_MAX,
    PAUSED_ANIMATION_MIN,
    RESPAWN_MARGIN,
    REST_CHANCE,
    REST_DISTANCE,
    REST_DURATION_MAX,
    REST_DURATION_MIN,
    SCALE_OPTIONS,
    SPEED_CURIOUS,
    SPEED_FOLLOW,
    SPEED_WANDER,
    SPEED_X,
    SPEED_Y,
    STAY_PUT_CHANCE,
    STOP_CHANCE,
    STOP_DURATION_MAX,
    STOP_DURATION_MIN,
    TARGET_CHANGE_MAX,
    TARGET_CHANGE_MIN,
    TRANSPARENCY_OPTIONS,
)
from .platform_linux import active_window, active_window_is_fullscreen

if TYPE_CHECKING:
    from .manager import PetManager


class PetWidget(QtWidgets.QWidget):
    def __init__(self, manager: "PetManager", index: int):
        super().__init__()
        self.manager = manager
        self.instance_index = index
        self.setObjectName(f"ameath-pet-{index}")
        self.setWindowTitle(f"Ameath Desktop Pet {index + 1}")
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating, True)
        self.setMouseTracking(True)

        self.label = QtWidgets.QLabel(self)
        self.label.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignBottom)
        self.label.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.label.setStyleSheet("background: transparent;")

        self.animation_timer = QtCore.QTimer(self)
        self.animation_timer.setSingleShot(True)
        self.animation_timer.timeout.connect(self._advance_frame)
        self.move_timer = QtCore.QTimer(self)
        self.move_timer.setInterval(MOVE_INTERVAL)
        self.move_timer.timeout.connect(self._move_tick)
        self.visibility_timer = QtCore.QTimer(self)
        self.visibility_timer.setInterval(500)
        self.visibility_timer.timeout.connect(self._ensure_visibility)
        self.pause_animation_timer = QtCore.QTimer(self)
        self.pause_animation_timer.setSingleShot(True)
        self.pause_animation_timer.timeout.connect(self._play_paused_flourish)

        self.scale_index = manager.config["scale_index"]
        self.scale = SCALE_OPTIONS[self.scale_index]
        self.transparency_index = manager.config["transparency_index"]
        self.click_through = manager.click_through
        self.follow_mouse = manager.follow_mouse
        self.display_priority = manager.display_priority
        self.window_snap = manager.config["window_snap"]
        self.wander_idle_stay_mode = manager.config["wander_idle_stay_mode"]
        self.is_paused = False
        self.is_moving = True
        self.is_idle_playing = False
        self.idle_allows_move = False
        self.dragging = False
        self.moving_right = True
        self.motion_state = MOTION_WANDER
        self.rest_until = 0.0
        self.idle_until = 0.0
        self.hidden_by_fullscreen = False
        self.user_hidden = False
        self.frame_index = 0
        self.current_animation = Animation((), ())
        self._move_counter = 0
        self._jitter_x = 0.0
        self._jitter_y = 0.0
        self._last_mouse = QtGui.QCursor.pos()
        self._drag_offset = QtCore.QPoint()
        self._pre_drag_animation: Animation | None = None
        self._pre_drag_index = 0
        self.vx = SPEED_X
        self.vy = SPEED_Y

        self._load_animations()
        self._resize_for_scale()
        self._rebuild_window_flags(show=False)
        start = self._startup_position()
        self.x = float(start.x())
        self.y = float(start.y())
        self.move(start)
        self.target_x, self.target_y = self._random_target()
        self.target_timer = random.randint(TARGET_CHANGE_MIN, TARGET_CHANGE_MAX)
        self.set_transparency(self.transparency_index)
        self._set_animation(self.move_right_animation)
        self.show()
        self.move_timer.start()
        self.visibility_timer.start()
        if manager.config.get("start_paused"):
            self.set_paused(True)

    def _load_animations(self) -> None:
        bank = self.manager.assets
        self.move_right_animation = bank.animation("move.gif", self.scale)
        self.move_left_animation = bank.animation("move.gif", self.scale, True)
        self.drag_animation = bank.animation("drag.gif", self.scale)
        self.idle_animations = [
            bank.animation(f"idle{i}.gif", self.scale) for i in range(1, 5)
        ]
        self.screen_animations = [
            bank.animation(f"screen{i}.gif", self.scale) for i in range(1, 8)
        ]
        self.paused_animation = self.idle_animations[1]

    def _resize_for_scale(self) -> None:
        size = max(1, round(200 * self.scale))
        self.setFixedSize(size, size)
        self.label.setGeometry(self.rect())

    def _set_animation(self, animation: Animation, keep_index: bool = False) -> None:
        if not animation:
            return
        self.current_animation = animation
        if not keep_index:
            self.frame_index = 0
        self.frame_index %= len(animation.frames)
        self._show_frame()

    def _show_frame(self) -> None:
        if not self.current_animation:
            return
        self.label.setPixmap(self.current_animation.frames[self.frame_index])
        delay = self.current_animation.delays[self.frame_index]
        self.animation_timer.start(delay)

    def _advance_frame(self) -> None:
        if not self.current_animation:
            return
        self.frame_index = (self.frame_index + 1) % len(self.current_animation.frames)
        self._show_frame()

    def _activity_rect(self) -> QtCore.QRect:
        return self.manager.activity_rect()

    def _startup_position(self) -> QtCore.QPoint:
        rect = self._activity_rect()
        margin = min(60, max(0, min(rect.width(), rect.height()) // 8))
        max_x = max(rect.left(), rect.right() - self.width() + 1)
        max_y = max(rect.top(), rect.bottom() - self.height() + 1)
        position = self.manager.config.get("startup_position", "random")
        points = {
            "top_left": QtCore.QPoint(rect.left() + margin, rect.top() + margin),
            "top_right": QtCore.QPoint(max_x - margin, rect.top() + margin),
            "bottom_left": QtCore.QPoint(rect.left() + margin, max_y - margin),
            "bottom_right": QtCore.QPoint(max_x - margin, max_y - margin),
            "center": QtCore.QPoint(
                rect.left() + (rect.width() - self.width()) // 2,
                rect.top() + (rect.height() - self.height()) // 2,
            ),
        }
        if position in points:
            return points[position]
        return QtCore.QPoint(
            random.randint(rect.left(), max_x), random.randint(rect.top(), max_y)
        )

    def _random_target(self) -> tuple[float, float]:
        rect = self._activity_rect()
        max_x = max(rect.left(), rect.right() - self.width() + 1)
        max_y = max(rect.top(), rect.bottom() - self.height() + 1)
        if random.random() < OUTSIDE_TARGET_CHANCE:
            side = random.choice(("left", "right", "top", "bottom"))
            margin = RESPAWN_MARGIN + 50
            if side == "left":
                return rect.left() - margin, random.randint(rect.top(), max_y)
            if side == "right":
                return rect.right() + margin, random.randint(rect.top(), max_y)
            if side == "top":
                return random.randint(rect.left(), max_x), rect.top() - margin
            return random.randint(rect.left(), max_x), rect.bottom() + margin
        return random.randint(rect.left(), max_x), random.randint(rect.top(), max_y)

    def _respawn(self) -> None:
        rect = self._activity_rect()
        max_x = max(rect.left(), rect.right() - self.width() + 1)
        max_y = max(rect.top(), rect.bottom() - self.height() + 1)
        side = random.choice(("left", "right", "top", "bottom"))
        if side == "left":
            self.x, self.y = rect.left() - RESPAWN_MARGIN, random.randint(rect.top(), max_y)
        elif side == "right":
            self.x, self.y = rect.right() + RESPAWN_MARGIN, random.randint(rect.top(), max_y)
        elif side == "top":
            self.x, self.y = random.randint(rect.left(), max_x), rect.top() - RESPAWN_MARGIN
        else:
            self.x, self.y = random.randint(rect.left(), max_x), rect.bottom() + RESPAWN_MARGIN
        center_x = rect.center().x()
        center_y = rect.center().y()
        self.vx = 3 if self.x < center_x else -3
        self.vy = 2 if self.y < center_y else -2

    def _handle_edge(self) -> None:
        rect = self._activity_rect()
        max_x = max(rect.left(), rect.right() - self.width() + 1)
        max_y = max(rect.top(), rect.bottom() - self.height() + 1)
        escaped = self.x < rect.left() or self.x > max_x or self.y < rect.top() or self.y > max_y
        if not escaped:
            return
        if random.random() < EDGE_ESCAPE_CHANCE:
            self._respawn()
            return
        if self.x < rect.left() or self.x > max_x:
            self.vx = -self.vx
        if self.y < rect.top() or self.y > max_y:
            self.vy = -self.vy
        self.x = min(max(self.x, rect.left()), max_x)
        self.y = min(max(self.y, rect.top()), max_y)

    def _move_tick(self) -> None:
        if self.dragging:
            return
        if self.is_paused:
            self._update_paused_snap()
            return
        now = time.monotonic()
        if self.idle_until and now >= self.idle_until:
            self._switch_to_move()
        if self.motion_state == MOTION_REST:
            if now >= self.rest_until:
                self.motion_state = MOTION_WANDER
                self.target_x, self.target_y = self._random_target()
                self.target_timer = random.randint(TARGET_CHANGE_MIN, TARGET_CHANGE_MAX)
                self._switch_to_move()
            return
        if not self.is_moving:
            return
        if self.motion_state == MOTION_WANDER and not self.is_idle_playing:
            if random.random() < STOP_CHANCE:
                self._switch_to_idle()
                return

        cursor = QtGui.QCursor.pos()
        mouse_moved = cursor != self._last_mouse
        self._last_mouse = cursor
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        distance = max(1.0, math.hypot(dx, dy))

        if not self.follow_mouse and self.motion_state in (MOTION_FOLLOW, MOTION_CURIOUS):
            self.motion_state = MOTION_WANDER
        if self.follow_mouse:
            mouse_distance = math.hypot(cursor.x() - self.x, cursor.y() - self.y)
            if mouse_distance > FOLLOW_START_DIST:
                self.motion_state = MOTION_FOLLOW
            elif mouse_distance < FOLLOW_STOP_DIST:
                self.motion_state = MOTION_CURIOUS
            if mouse_moved:
                offset = FOLLOW_DISTANCE if self.motion_state == MOTION_FOLLOW else FOLLOW_STOP_DIST
                self.target_x = cursor.x() + random.randint(-offset, offset)
                self.target_y = cursor.y() + random.randint(-offset, offset)
                dx = self.target_x - self.x
                dy = self.target_y - self.y
                distance = max(1.0, math.hypot(dx, dy))
        elif self.motion_state == MOTION_WANDER and distance < REST_DISTANCE:
            if random.random() < REST_CHANCE and self.wander_idle_stay_mode != 0:
                self.motion_state = MOTION_REST
                self.rest_until = now + random.randint(REST_DURATION_MIN, REST_DURATION_MAX) / 1000
                self._switch_to_idle(self.rest_until)
                return
            self.target_x, self.target_y = self._random_target()
            self.target_timer = random.randint(TARGET_CHANGE_MIN, TARGET_CHANGE_MAX)

        if self.motion_state == MOTION_WANDER:
            self.target_timer -= 1
            if self.target_timer <= 0:
                self.target_x, self.target_y = self._random_target()
                self.target_timer = random.randint(TARGET_CHANGE_MIN, TARGET_CHANGE_MAX)

        speed = {
            MOTION_WANDER: SPEED_WANDER,
            MOTION_FOLLOW: SPEED_FOLLOW,
            MOTION_CURIOUS: SPEED_CURIOUS,
        }.get(self.motion_state, 1.0)
        desired_vx = dx / distance * SPEED_X * speed
        desired_vy = dy / distance * SPEED_Y * speed
        self.vx = self.vx * INERTIA_FACTOR + desired_vx * INTENT_FACTOR
        self.vy = self.vy * INERTIA_FACTOR + desired_vy * INTENT_FACTOR
        self._move_counter += 1
        if self._move_counter % JITTER_INTERVAL == 0:
            self._jitter_x = random.uniform(-JITTER, JITTER)
            self._jitter_y = random.uniform(-JITTER, JITTER)
        self.vx += self._jitter_x
        self.vy += self._jitter_y
        self.x += self.vx
        self.y += self.vy
        self._handle_edge()

        if not self.is_idle_playing:
            moving_right = self.vx >= 0
            if moving_right != self.moving_right:
                self.moving_right = moving_right
                self._set_animation(
                    self.move_right_animation if moving_right else self.move_left_animation
                )
        self.move(round(self.x), round(self.y))

    def _switch_to_idle(self, until: float | None = None) -> None:
        self.is_idle_playing = False
        self.idle_allows_move = False
        if self.wander_idle_stay_mode == 0:
            self.is_idle_playing = self.idle_allows_move = self.is_moving = True
        elif self.wander_idle_stay_mode == 2:
            self.is_idle_playing = True
            self.is_moving = False
        elif random.random() < STAY_PUT_CHANCE:
            self.is_idle_playing = True
            self.idle_allows_move = random.random() >= 0.5
            self.is_moving = self.idle_allows_move
        else:
            self.is_moving = False
        animation = random.choice(self.idle_animations)
        self._set_animation(animation)
        if not self.is_idle_playing:
            self.frame_index = random.randrange(len(animation.frames))
            self._show_frame()
        self.idle_until = until or (
            time.monotonic() + random.randint(STOP_DURATION_MIN, STOP_DURATION_MAX) / 1000
        )

    def _switch_to_move(self) -> None:
        if self.is_paused:
            return
        self.is_idle_playing = False
        self.idle_allows_move = False
        self.is_moving = True
        self.idle_until = 0.0
        self._set_animation(
            self.move_right_animation if self.moving_right else self.move_left_animation
        )

    def _update_paused_snap(self) -> None:
        if not self.window_snap:
            return
        info = active_window()
        if info is None or info.title.startswith("Ameath"):
            return
        target_x = info.x + info.width - self.width()
        target_y = info.y - self.height() + 5
        rect = self._activity_rect()
        if rect.contains(QtCore.QPoint(target_x, target_y)):
            self.x, self.y = float(target_x), float(target_y)
            self.move(target_x, target_y)
            if self.current_animation not in self.screen_animations:
                self._set_animation(random.choice(self.screen_animations))

    def _play_paused_flourish(self) -> None:
        if not self.is_paused:
            return
        choices = self.screen_animations if self.window_snap else self.idle_animations
        self._set_animation(random.choice(choices))
        self.pause_animation_timer.start(
            random.randint(PAUSED_ANIMATION_MIN, PAUSED_ANIMATION_MAX)
        )

    def set_paused(self, paused: bool) -> None:
        if self.is_paused == paused:
            return
        self.is_paused = paused
        if paused:
            self.is_moving = False
            self._set_animation(self.paused_animation)
            self.pause_animation_timer.start(
                random.randint(PAUSED_ANIMATION_MIN, PAUSED_ANIMATION_MAX)
            )
        else:
            self.pause_animation_timer.stop()
            self.motion_state = MOTION_WANDER
            self.target_x, self.target_y = self._random_target()
            self._switch_to_move()

    def set_scale(self, index: int) -> None:
        index = min(max(0, int(index)), len(SCALE_OPTIONS) - 1)
        if index == self.scale_index:
            return
        center = self.frameGeometry().center()
        self.scale_index = index
        self.scale = SCALE_OPTIONS[index]
        self.animation_timer.stop()
        self._load_animations()
        self._resize_for_scale()
        self.x = center.x() - self.width() / 2
        self.y = center.y() - self.height() / 2
        self.move(round(self.x), round(self.y))
        if self.is_paused:
            self._set_animation(self.paused_animation)
        else:
            self._set_animation(
                self.move_right_animation if self.moving_right else self.move_left_animation
            )

    def set_transparency(self, index: int) -> None:
        self.transparency_index = min(max(0, int(index)), len(TRANSPARENCY_OPTIONS) - 1)
        self.setWindowOpacity(TRANSPARENCY_OPTIONS[self.transparency_index])

    def set_click_through(self, enabled: bool) -> None:
        if self.click_through == enabled and self.isVisible():
            return
        self.click_through = enabled
        self._rebuild_window_flags()

    def set_display_priority(self, mode: int) -> None:
        mode = min(max(1, int(mode)), 3)
        if self.display_priority == mode and self.isVisible():
            return
        self.display_priority = mode
        self._rebuild_window_flags()

    def _rebuild_window_flags(self, show: bool = True) -> None:
        was_visible = self.isVisible() and not self.user_hidden
        position = self.pos()
        flags = QtCore.Qt.FramelessWindowHint | QtCore.Qt.Tool
        if self.display_priority in (DISPLAY_ALWAYS_TOP, DISPLAY_HIDE_FULLSCREEN):
            flags |= QtCore.Qt.WindowStaysOnTopHint
        elif self.display_priority == DISPLAY_DESKTOP_ONLY:
            flags |= QtCore.Qt.WindowStaysOnBottomHint
        if self.click_through:
            flags |= QtCore.Qt.WindowTransparentForInput
        self.setWindowFlags(flags)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, self.click_through)
        self.move(position)
        if show and was_visible:
            self.show()

    def _ensure_visibility(self) -> None:
        if self.user_hidden:
            return
        if self.display_priority == DISPLAY_HIDE_FULLSCREEN:
            fullscreen = active_window_is_fullscreen(self.manager.screen_rects())
            if fullscreen and self.isVisible():
                self.hidden_by_fullscreen = True
                self.hide()
            elif not fullscreen and self.hidden_by_fullscreen:
                self.hidden_by_fullscreen = False
                self.show()
        elif not self.isVisible():
            self.show()
        if self.isVisible() and self.display_priority == DISPLAY_ALWAYS_TOP:
            self.raise_()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            self.dragging = True
            self._drag_offset = event.globalPos() - self.frameGeometry().topLeft()
            self._pre_drag_animation = self.current_animation
            self._pre_drag_index = self.frame_index
            self._set_animation(self.drag_animation)
            self.manager.voice.play_random()
            event.accept()
        elif event.button() == QtCore.Qt.RightButton:
            self.manager.show_quick_menu(event.globalPos())
            event.accept()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if self.dragging and event.buttons() & QtCore.Qt.LeftButton:
            point = event.globalPos() - self._drag_offset
            self.x, self.y = float(point.x()), float(point.y())
            self.move(point)
            event.accept()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton and self.dragging:
            self.dragging = False
            self.manager.voice.stop()
            if self.is_paused:
                self._set_animation(self.paused_animation)
            else:
                self._switch_to_move()
            self.target_x, self.target_y = self._random_target()
            event.accept()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.animation_timer.stop()
        self.move_timer.stop()
        self.visibility_timer.stop()
        self.pause_animation_timer.stop()
        super().closeEvent(event)

