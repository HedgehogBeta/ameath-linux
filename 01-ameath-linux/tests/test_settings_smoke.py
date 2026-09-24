import importlib
import pkgutil

import ameath_linux


def test_settings_module_imports():
    module = importlib.import_module("ameath_linux.settings")
    assert module.SettingsDialog is not None


def test_all_package_modules_import():
    names = [
        module.name
        for module in pkgutil.iter_modules(ameath_linux.__path__)
        if module.name != "__main__"
    ]
    for name in names:
        importlib.import_module(f"ameath_linux.{name}")
