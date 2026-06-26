import os
import tempfile

import pytest

_TMPDIR = tempfile.mkdtemp()
_DB_PATH = os.path.join(_TMPDIR, "test.db")
os.environ["WRITEAUTO_DATA_DIR"] = _TMPDIR
os.environ["WRITEAUTO_DB_PATH"] = _DB_PATH


def pytest_unconfigure():
    import shutil
    if os.path.exists(_TMPDIR):
        shutil.rmtree(_TMPDIR, ignore_errors=True)


@pytest.fixture
def temp_db():
    if os.path.exists(_DB_PATH):
        os.unlink(_DB_PATH)
    return _DB_PATH
