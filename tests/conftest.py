"""Makes ``src/`` importable for the test suite.

Works under both ``pytest`` and ``python -m unittest discover -s tests``.
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
