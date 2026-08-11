"""Open Library provider — free API, no key required.

Good as a first real provider and a fallback source: decent title/author
coverage, weaker on narrators/duration (it's a book database, not audiobook-
specific). Pair this with an audiobook-specific provider (e.g. Audnexus)
for narrator/duration data later.
"""
from __future__ import annotations

from datetime import date

import httpx

from audiobook_fetcher.domain.models import AudiobookCandidate, Query
from audiobook_fetcher.providers.base import MetadataProvider

SEARCH_URL = "https://openlibrary.org/search.json"


class OpenLibraryProvider:
    name = "openlibrary"

    async def search(self, query: Query) -> list[AudiobookCandidate]:
        params = {"title": query.title, "limit": 10}
        if query.author:
            params["author"] = query.author

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(SEARCH_URL, params=params)
            response.raise_for_status()
            data = response.json()

        candidates: list[AudiobookCandidate] = []
        for doc in data.get("docs", []):
            published_date = None
            if year := doc.get("first_publish_year"):
                published_date = date(year, 1, 1)

            candidates.append(
                AudiobookCandidate(
                    source_name=self.name,
                    source_id=doc.get("key", ""),
                    title=doc.get("title", query.title),
                    authors=doc.get("author_name", []),
                    published_date=published_date,
                    publisher=(doc.get("publisher") or [None])[0],
                    cover_url=(
                        f"https://covers.openlibrary.org/b/id/{doc['cover_i']}-L.jpg"
                        if doc.get("cover_i")
                        else None
                    ),
                )
            )
        return candidates


PROVIDER = OpenLibraryProvider()
