"""
In-memory storage for the MVP. No database, no Redis.
Keyed by document_id (uuid). Cleared on server restart — acceptable for a demo.
"""
from typing import Any

_STORE: dict[str, dict[str, Any]] = {}


def save(document_id: str, data: dict):
    _STORE[document_id] = data


def get(document_id: str) -> dict | None:
    return _STORE.get(document_id)


def exists(document_id: str) -> bool:
    return document_id in _STORE


def update(document_id: str, **kwargs):
    if document_id in _STORE:
        _STORE[document_id].update(kwargs)
