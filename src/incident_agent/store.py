"""Very small report store.

Defaults to an in-memory dict so the app runs with zero infrastructure.
If ``REDIS_URL`` is configured the store transparently persists reports to
Redis (lazily imported) as JSON.
"""

from __future__ import annotations

from threading import Lock
from typing import Optional

from .config import Settings, get_settings
from .models import Report


class ReportStore:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._mem: dict[str, Report] = {}
        self._lock = Lock()
        self._redis = None
        if self.settings.redis_url:
            try:
                import redis  # lazy

                self._redis = redis.Redis.from_url(
                    self.settings.redis_url, decode_responses=True
                )
                self._redis.ping()
            except Exception:  # noqa: BLE001 - fall back to memory
                self._redis = None

    def _key(self, report_id: str) -> str:
        return f"incident_report:{report_id}"

    def save(self, report: Report) -> None:
        if self._redis is not None:
            self._redis.set(self._key(report.id), report.model_dump_json())
        with self._lock:
            self._mem[report.id] = report

    def get(self, report_id: str) -> Optional[Report]:
        with self._lock:
            if report_id in self._mem:
                return self._mem[report_id]
        if self._redis is not None:
            data = self._redis.get(self._key(report_id))
            if data:
                return Report.model_validate_json(data)
        return None

    def list_ids(self) -> list[str]:
        with self._lock:
            return list(self._mem.keys())


_store: Optional[ReportStore] = None


def get_store() -> ReportStore:
    global _store
    if _store is None:
        _store = ReportStore()
    return _store
