"""
bifrost.py — Bootstrap shim.

This file exists at the repo root for backward compatibility with launch
scripts and manual ``python bifrost.py`` invocations.  The canonical,
actively-maintained entry point lives at  bot/bifrost.py .

DO NOT add features here.  All code belongs in  bot/bifrost.py .
"""

import os
import sys

# Ensure the 'bot' package directory is importable.
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_here, "bot"))

from bifrost import main  # noqa: E402  — bot/bifrost.py

if __name__ == "__main__":
    main()
