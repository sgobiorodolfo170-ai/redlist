import sys
from pathlib import Path

import pytest
from PyQt6.QtWidgets import QApplication


SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR.parent))


def pytest_configure(config):
    config.addinivalue_line("markers", "heavy: marks tests that need heavy dependencies (PaddlePaddle, PyQt6)")


@pytest.fixture
def temp_dir(tmp_path):
    return tmp_path


@pytest.fixture(scope="session", autouse=True)
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app
