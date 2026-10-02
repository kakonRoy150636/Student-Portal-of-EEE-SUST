"""One place for the size of a page.

Nothing here paginates in SQL; the departmental tables this portal serves are
small (a cohort, a year of events), and every one of these lists was previously
unbounded -- a client could ask for the whole table and the server would build
it in memory. The bounds below are the safety net: each handler slices what the
service returned. Services that already take a ``limit`` (resources, alumni
directory, news, projects, career) pass it down instead.
"""

from __future__ import annotations

from typing import Sequence, TypeVar

T = TypeVar("T")

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


def page(items: Sequence[T], limit: int, offset: int = 0) -> list[T]:
    """Return one window of ``items`` with both bounds enforced."""
    bounded_limit = max(1, min(limit, MAX_PAGE_SIZE))
    bounded_offset = max(0, offset)
    return list(items[bounded_offset : bounded_offset + bounded_limit])
