"""Every metadata source — scraper or API — implements this Protocol.

The orchestrator doesn't care how a provider gets its data, only that it
returns AudiobookCandidate objects for a Query. This is what makes providers
pluggable: adding a new site or API means writing one class, nothing else
changes.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from audiobook_fetcher.domain.models import AudiobookCandidate, Query


@runtime_checkable
class MetadataProvider(Protocol):
    """Structural interface — no need to inherit, just match the shape."""

    name: str

    async def search(self, query: Query) -> list[AudiobookCandidate]:
        """Return candidates for the query. Never raises for 'no results' —
        return an empty list. Only raise for actual failures (network, parse
        errors the caller should know about) so the orchestrator can decide
        whether to skip this provider or surface the error.
        """
        ...


def discover_providers() -> list[MetadataProvider]:
    """Auto-discover providers dropped into this package.

    Any module in audiobook_fetcher/providers/ that defines a top-level
    PROVIDER instance implementing MetadataProvider gets picked up
    automatically — no registration step needed.
    """
    import importlib
    import pkgutil

    providers: list[MetadataProvider] = []
    package = importlib.import_module("audiobook_fetcher.providers")

    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        if module_name in ("base",):
            continue
        module = importlib.import_module(f"audiobook_fetcher.providers.{module_name}")
        candidate = getattr(module, "PROVIDER", None)
        if isinstance(candidate, MetadataProvider):
            providers.append(candidate)

    return providers
