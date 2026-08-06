#!/usr/bin/env python3
"""Skill entry point for xinchuang-command-converter.

Only static text parsing and string mapping are performed here. User-supplied
shell scripts are treated as plain text and are never executed, evaluated, or
passed to a subprocess.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scripts.convert_xinchuang import main as convert_main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(convert_main())
