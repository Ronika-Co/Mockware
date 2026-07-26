from pathlib import Path

import pytest


@pytest.fixture
def samples_dir() -> Path:
    return Path(__file__).parent / "samples"


@pytest.fixture
def tmp_output(tmp_path: Path) -> Path:
    return tmp_path / "output"
