"""Type-Definitionen für App-Detection-Registry."""

from __future__ import annotations

from typing import TypedDict


class AppInfo(TypedDict):
    """Server-App-Inventur-Eintrag matching WHITEPAPER §JSON-Schema §apps."""

    name: str
    version: str
    path: str
    config_file: str
