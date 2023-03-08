import pytest

from depmanager.common.shared.progress_bar import ProgressBar


@pytest.fixture
def progress_bar():
    return ProgressBar(100)
