"""Версия приложения (файл VERSION в корне проекта или BOT_VERSION в env)."""

from __future__ import annotations

import os
import platform
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_VERSION_FILE = _ROOT / "VERSION"


def get_version() -> str:
    try:
        file_version = _VERSION_FILE.read_text(encoding="utf-8").strip()
        if file_version:
            return file_version
    except OSError:
        pass
    env = os.getenv("BOT_VERSION", "").strip()
    if env:
        return env
    return "dev"


def runtime_info() -> dict[str, str]:
    return {
        "version": get_version(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "in_docker": str(Path("/.dockerenv").exists()),
    }
