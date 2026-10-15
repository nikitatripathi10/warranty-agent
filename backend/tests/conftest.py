"""
Pytest configuration and shared fixtures for Warranty Radar test suite.

Run the full suite:
    cd backend
    venv\\Scripts\\pytest tests/ -v --tb=short

Run a specific module:
    venv\\Scripts\\pytest tests/test_extraction_precision.py -v
    venv\\Scripts\\pytest tests/test_alert_timeliness.py -v
    venv\\Scripts\\pytest tests/test_unit_coverage.py -v
    venv\\Scripts\\pytest tests/test_enhancements.py -v

Run only fast tests (skip DB-heavy):
    venv\\Scripts\\pytest tests/ -v -m "not db"
"""

import pathlib
import sys

# Ensure 'backend/' is on sys.path so all `app.*` imports work without
# installing the package. This also makes the backend tests runnable from
# any working directory (e.g. from the repo root).
_backend_root = pathlib.Path(__file__).parent.parent.resolve()
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))
