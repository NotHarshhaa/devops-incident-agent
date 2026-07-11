"""Base collector abstraction.

A *collector* gathers :class:`Evidence` about an incident from one data
source (Prometheus, Loki, Kubernetes, GitHub, Jenkins, ...).

Design goals:
    * Works offline: if not configured or ``MOCK_MODE`` is on, the collector
      returns realistic synthetic evidence instead of failing.
    * Never crashes an investigation: live-collection errors are caught and
      downgraded to mock evidence with a note.
    * Lazy dependencies: heavy SDKs are imported inside ``_collect_live``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..config import Settings, get_settings
from ..models import Evidence, Incident


class Collector(ABC):
    """Base class for all evidence collectors."""

    name: str = "base"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    # ---- public API ------------------------------------------------- #
    def collect(self, incident: Incident) -> list[Evidence]:
        """Gather evidence, transparently falling back to mock data."""
        if self.settings.mock_mode or not self.available():
            return self._mock(incident)
        try:
            return self._collect_live(incident)
        except Exception as exc:  # noqa: BLE001
            evidence = self._mock(incident)
            evidence.insert(
                0,
                Evidence(
                    source=self.name,
                    summary=f"Live collection failed, using mock data: {exc}",
                    detail=str(exc),
                ),
            )
            return evidence

    # ---- to be implemented by subclasses ---------------------------- #
    @abstractmethod
    def available(self) -> bool:
        """Return True when the collector is configured for live access."""
        raise NotImplementedError

    @abstractmethod
    def _mock(self, incident: Incident) -> list[Evidence]:
        """Return synthetic evidence for offline/demo use."""
        raise NotImplementedError

    def _collect_live(self, incident: Incident) -> list[Evidence]:
        """Collect real evidence. Default: no live support -> mock."""
        return self._mock(incident)
