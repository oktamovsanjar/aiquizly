"""
Integration testlar uchun conftest.py

Parent conftest.py (tests/conftest.py) utils.api ni mock qiladi.
Integration testlar real utils.api modulini talab qiladi —
shu sababli bu yerda mock ni sys.modules dan o'chiramiz.
"""

import sys


def pytest_runtest_setup(item):
    """Har bir integration test oldidan utils.api mock ni olib tashlaymiz."""
    for key in list(sys.modules.keys()):
        if key in ("utils.api", "utils"):
            del sys.modules[key]
