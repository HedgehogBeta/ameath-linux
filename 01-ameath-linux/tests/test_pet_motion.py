import random

from PyQt5 import QtCore, QtWidgets

from ameath_linux.animation import AssetBank
from ameath_linux.config import DEFAULT_CONFIG
from ameath_linux.paths import asset_path
from ameath_linux.pet import PetWidget


class _Manager:
    def __init__(self):
        self.config = dict(DEFAULT_CONFIG)
        self.assets = AssetBank(asset_path("gifs"))
        self.click_through = False
        self.follow_mouse = False
        self.display_priority = 1

    @staticmethod
    def activity_rect() -> QtCore.QRect:
        return QtCore.QRect(0, 0, 800, 600)


def _place_at_right_edge(pet: PetWidget) -> None:
    rect = pet._activity_rect()
    pet.x = float(rect.right() - pet.width() + 1)
    pet.y = float(rect.center().y())
    pet.vx = 3.0
    pet.vy = 0.0
    pet.target_x = float(rect.right() + 150)
    pet.target_y = pet.y
    pet.target_timer = 500
    pet.is_moving = True
    pet.is_idle_playing = False
    pet.move(round(pet.x), round(pet.y))


def test_crossing_screen_edge_does_not_teleport():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    pet = PetWidget(_Manager(), 0)

    random.seed(4)
    _place_at_right_edge(pet)
    before = pet.pos()

    pet._move_tick()

    after = pet.pos()
    delta = abs(after.x() - before.x()) + abs(after.y() - before.y())
    pet.close()
    assert delta <= 10


def test_edge_motion_never_teleports_across_random_outcomes():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    pet = PetWidget(_Manager(), 0)

    for seed in range(200):
        random.seed(seed)
        _place_at_right_edge(pet)
        before = pet.pos()
        for _ in range(10):
            pet._move_tick()
            after = pet.pos()
            delta = abs(after.x() - before.x()) + abs(after.y() - before.y())
            assert delta <= 10, f"seed={seed}, before={before}, after={after}"
            before = after

    pet.close()
