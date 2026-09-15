"""
conftest.py — adds the backend root to sys.path so `import app.*` works
when pytest is invoked from any directory.
"""
import sys
from pathlib import Path

# backend/ directory is the parent of tests/
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))
