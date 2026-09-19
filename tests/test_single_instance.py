import os
import signal

from ameath_linux.single_instance import InstanceLock


def test_second_launch_can_show_or_quit_running_instance(tmp_path, monkeypatch):
    path = tmp_path / "ameath.lock"
    primary = InstanceLock(path)
    secondary = InstanceLock(path)
    assert primary.acquire()
    assert not secondary.acquire()
    delivered = []
    monkeypatch.setattr(os, "kill", lambda pid, sig: delivered.append((pid, sig)))

    assert secondary.notify_running("show")
    assert secondary.notify_running("quit")
    assert delivered == [(os.getpid(), signal.SIGUSR1), (os.getpid(), signal.SIGTERM)]

    primary.release()
    assert not path.exists()
