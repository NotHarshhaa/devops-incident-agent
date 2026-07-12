"""Tests for the report store (in-memory + optional Redis backfill)."""

from __future__ import annotations

from incident_agent.config import Settings
from incident_agent.models import Incident, RootCause
from incident_agent.store import ReportStore


def _make_report():
    from incident_agent.models import Report

    return Report(
        incident=Incident(title="latency spike"),
        root_cause=RootCause(summary="test"),
    )


def test_save_and_get_roundtrip(settings):
    store = ReportStore(settings)
    report = _make_report()
    store.save(report)
    fetched = store.get(report.id)
    assert fetched is not None
    assert fetched.id == report.id


def test_get_missing_returns_none(settings):
    store = ReportStore(settings)
    assert store.get("does-not-exist") is None


def test_list_ids_reflects_saved_reports(settings):
    store = ReportStore(settings)
    report = _make_report()
    store.save(report)
    assert report.id in store.list_ids()


class _FakeRedis:
    """Minimal in-memory stand-in for the redis client used by ReportStore."""

    def __init__(self):
        self._data: dict[str, str] = {}

    def ping(self):
        return True

    def set(self, key: str, value: str):
        self._data[key] = value

    def get(self, key: str):
        return self._data.get(key)


def test_get_backfills_memory_cache_after_redis_hit(settings):
    # Regression: a Redis hit should populate the in-memory cache so
    # subsequent lookups don't need to round-trip to Redis again.
    store = ReportStore(settings)
    fake_redis = _FakeRedis()
    store._redis = fake_redis

    report = _make_report()
    store.save(report)
    assert store._key(report.id) in fake_redis._data

    # Simulate a fresh process: clear the in-memory cache but keep "Redis".
    store._mem.clear()
    assert report.id not in store._mem

    fetched = store.get(report.id)
    assert fetched is not None
    assert fetched.id == report.id
    # Now backfilled into memory.
    assert report.id in store._mem
