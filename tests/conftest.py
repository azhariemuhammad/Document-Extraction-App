import pytest


@pytest.fixture(autouse=True)
def isolated_dirs(tmp_path, monkeypatch):
    # every test gets its own empty cache and outputs folder
    monkeypatch.setenv("CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "outputs"))
