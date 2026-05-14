"""Tests for cronwatcher.alert_aggregator."""

from datetime import datetime

import pytest

from cronwatcher.alert_aggregator import AlertAggregator, AlertBatch
from cronwatcher.alerting import Alert


def _make_alert(job_name: str = "test_job") -> Alert:
    return Alert(
        job_name=job_name,
        reason="overdue",
        last_seen=datetime(2024, 1, 1, 12, 0, 0),
    )


@pytest.fixture
def aggregator() -> AlertAggregator:
    return AlertAggregator(max_size=3)


class TestAlertBatch:
    def test_empty_batch_size_is_zero(self):
        batch = AlertBatch()
        assert batch.size == 0

    def test_add_increases_size(self):
        batch = AlertBatch()
        batch.add(_make_alert())
        assert batch.size == 1

    def test_job_names_lists_all_names(self):
        batch = AlertBatch()
        batch.add(_make_alert("job_a"))
        batch.add(_make_alert("job_b"))
        assert batch.job_names == ["job_a", "job_b"]

    def test_summary_contains_job_name(self):
        batch = AlertBatch()
        batch.add(_make_alert("my_job"))
        assert "my_job" in batch.summary()

    def test_summary_empty_batch(self):
        batch = AlertBatch()
        assert "No alerts" in batch.summary()

    def test_summary_includes_count(self):
        batch = AlertBatch()
        batch.add(_make_alert("a"))
        batch.add(_make_alert("b"))
        assert "2 alerts" in batch.summary()


class TestAlertAggregator:
    def test_invalid_max_size_raises(self):
        with pytest.raises(ValueError, match="max_size"):
            AlertAggregator(max_size=0)

    def test_collect_returns_none_below_max(self, aggregator):
        result = aggregator.collect(_make_alert())
        assert result is None

    def test_pending_count_increments(self, aggregator):
        aggregator.collect(_make_alert())
        aggregator.collect(_make_alert())
        assert aggregator.pending_count == 2

    def test_collect_returns_batch_at_max_size(self, aggregator):
        aggregator.collect(_make_alert("a"))
        aggregator.collect(_make_alert("b"))
        batch = aggregator.collect(_make_alert("c"))
        assert isinstance(batch, AlertBatch)
        assert batch.size == 3

    def test_buffer_cleared_after_auto_flush(self, aggregator):
        for name in ["a", "b", "c"]:
            aggregator.collect(_make_alert(name))
        assert aggregator.pending_count == 0

    def test_flush_returns_all_pending(self, aggregator):
        aggregator.collect(_make_alert("x"))
        aggregator.collect(_make_alert("y"))
        batch = aggregator.flush()
        assert batch.size == 2
        assert aggregator.pending_count == 0

    def test_flush_empty_buffer_returns_empty_batch(self, aggregator):
        batch = aggregator.flush()
        assert batch.size == 0

    def test_has_pending_false_when_empty(self, aggregator):
        assert not aggregator.has_pending()

    def test_has_pending_true_after_collect(self, aggregator):
        aggregator.collect(_make_alert())
        assert aggregator.has_pending()

    def test_has_pending_false_after_flush(self, aggregator):
        aggregator.collect(_make_alert())
        aggregator.flush()
        assert not aggregator.has_pending()
