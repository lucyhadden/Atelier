import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


@pytest.fixture
def db(tmp_path, monkeypatch):
    """A throwaway database and image dir, so tests never touch ./data."""
    monkeypatch.setenv("ATELIER_DATA_DIR", str(tmp_path))

    from atelier.config import get_settings

    get_settings.cache_clear()

    # db.py binds its engine at import time, so build a fresh one here.
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from atelier.models import Base

    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    yield session
    session.close()
    get_settings.cache_clear()


@pytest.fixture
def sample_image(tmp_path, monkeypatch):
    """A real JPEG on disk inside the configured image dir."""
    monkeypatch.setenv("ATELIER_DATA_DIR", str(tmp_path))
    from PIL import Image

    from atelier.config import get_settings

    get_settings.cache_clear()
    path = get_settings().image_dir / "pin_test.jpg"
    Image.new("RGB", (800, 600), (200, 190, 170)).save(path)
    return path.name
