"""Tests for cronwatcher.alert_router."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from cronwatcher.alert_router import AlertRouter
from cronwatcher.alerting import Alert
from cronwatcher.job_registry import JobRegistry
from cronwatcher.job_tagger import JobTagger


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def registry():
    r = JobRegistry()
    r.register("billing", "*/5 * * * *")
    r.register("report", "0 * * * *")
    r.register("untagged", "0 0 * * *")
    return r


@pytest.fixture()
def tagger(registry):
    t = JobTagger(registry)
    t.tag_job("billing", "critical")
    t.tag_job("billing", "finance")
    t.tag_job("report", "finance")
    return t


@pytest.fixture()
def router(tagger):
    return AlertRouter(tagger=tagger)


def _alert(job_name: str) -> Alert:
    return Alert(
        job_name=job_name,
        kind="overdue",
        message=f"{job_name} is overdue",
        last_seen=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# Tests — AlertRouter
# ---------------------------------------------------------------------------

class TestAlertRouter:
    def test_registered_tags_empty_initially(self, router):
        assert router.registered_tags() == []

    def test_register_for_tag_adds_to_list(self, router):
        notifier = MagicMock()
        router.register_for_tag("critical", notifier)
        assert "critical" in router.registered_tags()

    def test_route_calls_matched_notifier(self, router):
        notifier = MagicMock(return_value=True)
        notifier.send = MagicMock(return_value=True)
        router.register_for_tag("critical", notifier)

        results = router.route(_alert("billing"))

        notifier.send.assert_called_once()
        assert results == [True]

    def test_route_calls_multiple_notifiers_for_multiple_tags(self, router):
        n_critical = MagicMock()
        n_critical.send = MagicMock(return_value=True)
        n_finance = MagicMock()
        n_finance.send = MagicMock(return_value=True)

        router.register_for_tag("critical", n_critical)
        router.register_for_tag("finance", n_finance)

        results = router.route(_alert("billing"))  # billing has both tags

        n_critical.send.assert_called_once()
        n_finance.send.assert_called_once()
        assert len(results) == 2

    def test_route_uses_default_when_no_tag_matches(self, router):
        default = MagicMock()
        default.send = MagicMock(return_value=True)
        router.default_notifier = default

        results = router.route(_alert("untagged"))

        default.send.assert_called_once()
        assert results == [True]

    def test_route_returns_empty_when_no_match_and_no_default(self, router):
        results = router.route(_alert("untagged"))
        assert results == []

    def test_route_does_not_call_default_when_tag_matches(self, router):
        tag_notifier = MagicMock()
        tag_notifier.send = MagicMock(return_value=True)
        default = MagicMock()
        default.send = MagicMock(return_value=True)

        router.register_for_tag("finance", tag_notifier)
        router.default_notifier = default

        router.route(_alert("report"))  # report has "finance" tag

        tag_notifier.send.assert_called_once()
        default.send.assert_not_called()
