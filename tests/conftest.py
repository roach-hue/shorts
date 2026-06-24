"""pytest bootstrap. pyproject sets pythonpath=['src'] for the package import;
this also guarantees `import fixtures` (this dir) and exposes the repo root.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for p in (SRC, ROOT / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import pytest


@pytest.fixture
def repo_root() -> Path:
    return ROOT
