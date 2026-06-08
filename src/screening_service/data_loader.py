"""Helpers for loading bundled sample watchlist data."""

from __future__ import annotations

import json
from importlib import resources
from typing import NotRequired, TypedDict


class WatchlistEntry(TypedDict):
    watchlist_id: str
    primary_name: str
    entity_type: str
    aliases: list[str]
    countries: list[str]
    birth_year: int | None
    risk_notes: NotRequired[str]


def load_sample_watchlist() -> list[WatchlistEntry]:
    """Load the bundled synthetic watchlist JSON file."""

    resource = resources.files("screening_service").joinpath(
            "data",
            "watchlist.sample.json",
    )

    with resource.open("r", encoding="utf-8") as file_obj:
        payload = json.load(file_obj)

    if not isinstance(payload, list):
        raise ValueError("Bundled watchlist must be a JSON array")

    return payload
