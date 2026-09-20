import os


# GUI tests do not need a real desktop and should not contend with a running pet.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
