import json
from pathlib import Path

import pytest

VECTOR_DIR = Path(__file__).parent / "vectors"


@pytest.fixture(scope="session")
def published():
    return json.loads((VECTOR_DIR / "published.json").read_text())
