"""Fans a Query out to every discovered provider concurrently, scores each
candidate against the query, and returns a merged, ranked list.

This is the only place that knows "there are multiple providers" — everything
downstream (the TUI, the rename planner) just sees a flat, ranked
list[AudiobookCandidate].
"""
from __future__ import annotations

import asyncio
import logging

from rapidfuzz import fuzz

from audiobook_fetcher.domain.models import AudiobookCandidate, Query
from audiobook_fetcher.providers.base import MetadataProvider, discover_providers

logger = logging.getLogger(__name__)


def _score(candidate: AudiobookCandidate, query: Query) -> float:
    title_score = fuzz.token_set_ratio(candidate.title, query.title)

    author_score = 100.0
    if query.author:
        author_score = max(
            (fuzz.token_set_ratio(a, query.author) for a in candidate.authors),
            default=0.0,
        )

    # Title match matters more than author match.
    return round(0.7 * title_score + 0.3 * author_score, 2)


async def _search_one(provider: MetadataProvider, query: Query) -> list[AudiobookCandidate]:
    try:
        return await provider.search(query)
    except Exception:
        logger.warning("provider %s failed for query %r", provider.name, query, exc_info=True)
        return []


async def search_all(
    query: Query, providers: list[MetadataProvider] | None = None
) -> list[AudiobookCandidate]:
    """Query every provider concurrently, score, and return ranked candidates."""
    providers = providers if providers is not None else discover_providers()

    results = await asyncio.gather(*(_search_one(p, query) for p in providers))

    scored: list[AudiobookCandidate] = []
    for candidates in results:
        for candidate in candidates:
            candidate.match_score = _score(candidate, query)
            scored.append(candidate)

    # A provider may return the same work in multiple editions; keep best match.
    best_by_key: dict[tuple[str, str], AudiobookCandidate] = {}
    for candidate in scored:
        key = (candidate.source_name, candidate.source_id) if candidate.source_id else (
            candidate.source_name,
            candidate.title.casefold(),
        )
        if key not in best_by_key or candidate.match_score > best_by_key[key].match_score:
            best_by_key[key] = candidate

    result = list(best_by_key.values())
    result.sort(key=lambda c: c.match_score, reverse=True)
    return result
