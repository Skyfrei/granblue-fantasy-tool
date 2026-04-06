import os, sys

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def load_stylesheet(file_path):
    path = resource_path(file_path)
    with open(path, "r") as f:
        return f.read()

STYLESHEET = load_stylesheet("style.qss")
