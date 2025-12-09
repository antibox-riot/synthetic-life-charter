# umbra/store.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, Optional

from .models import UmbraFossil, UmbraContext


class UmbraStore(ABC):
    """
    Abstraction over persistence.
    You can back this with a DB, a file, or even just in-memory during tests.
    """

    @abstractmethod
    def save_fossil(self, fossil: UmbraFossil) -> None:
        ...

    @abstractmethod
    def get_fossil(self, fossil_id: str) -> Optional[UmbraFossil]:
        ...

    @abstractmethod
    def iter_fossils_for_session(self, session_id: str) -> Iterable[UmbraFossil]:
        ...

    @abstractmethod
    def count_unreconciled(self, session_id: Optional[str] = None) -> int:
        ...


class InMemoryUmbraStore(UmbraStore):
    """
    Simple default for local experimentation.
    """

    def __init__(self) -> None:
        self._by_id: dict[str, UmbraFossil] = {}
        self._by_session: dict[str, list[str]] = {}

    def save_fossil(self, fossil: UmbraFossil) -> None:
        self._by_id[fossil.fossil_id] = fossil
        if fossil.context.session_id:
            bucket = self._by_session.setdefault(fossil.context.session_id, [])
            if fossil.fossil_id not in bucket:
                bucket.append(fossil.fossil_id)

    def get_fossil(self, fossil_id: str) -> Optional[UmbraFossil]:
        return self._by_id.get(fossil_id)

    def iter_fossils_for_session(self, session_id: str):
        for fid in self._by_session.get(session_id, []):
            yield self._by_id[fid]

    def count_unreconciled(self, session_id: Optional[str] = None) -> int:
        # TODO: add a 'reconciled' flag in UmbraFossil.meta if you want this real.
        if session_id is None:
            return len(self._by_id)
        return len(self._by_session.get(session_id, []))
