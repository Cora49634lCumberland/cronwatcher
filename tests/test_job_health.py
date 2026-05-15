"""Tests for cronwatcher.job_health."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cronwatcher.job_health import HealthScore, JobHealthScorer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scorer(
    overdue: bool = False,
    silent: bool = False,
    drift_secs: float | None = None,
    recovered: bool = False,
) -> JobHealthScorer:
    heartbeat = MagicMock()
    heartbeat.is_overdue.return_value = overdue

    drift_analyzer = MagicMock()
    if drift_secs is not None:
        record = MagicMock()
        record.drift_seconds.return_value = drift_secs
        drift_analyzer.latest.return_value = record
    else:
        drift_analyzer.latest.return_value = None

    silence_detector = MagicMock()
    silence_detector.check.return_value = MagicMock() if silent else None

    recovery_detector = MagicMock()
    recovery_detector.check_job.return_value = MagicMock() if recovered else None

    return JobHealthScorer(
        heartbeat=heartbeat,
        drift_analyzer=drift_analyzer,
        silence_detector=silence_detector,
        recovery_detector=recovery_detector,
    )


# ---------------------------------------------------------------------------
# HealthScore label tests
# ---------------------------------------------------------------------------

class TestHealthScore:
    def test_label_healthy(self):
        hs = HealthScore("job", 0.9, False, False, None, False)
        assert hs.label == "healthy"

    def test_label_degraded(self):
        hs = HealthScore("job", 0.6, False, False, None, False)
        assert hs.label == "degraded"

    def test_label_critical(self):
        hs = HealthScore("job", 0.2, True, True, None, False)
        assert hs.label == "critical"

    def test_repr_contains_job_name(self):
        hs = HealthScore("backup", 0.75, False, False, None, False)
        assert "backup" in repr(hs)
        assert "0.75" in repr(hs)


# ---------------------------------------------------------------------------
# JobHealthScorer tests
# ---------------------------------------------------------------------------

class TestJobHealthScorer:
    def test_healthy_job_scores_one(self):
        scorer = _make_scorer()
        result = scorer.score_job("noop", 3600)
        assert result.score == pytest.approx(1.0)
        assert result.label == "healthy"

    def test_overdue_reduces_score(self):
        scorer = _make_scorer(overdue=True)
        result = scorer.score_job("late_job", 3600)
        assert result.score == pytest.approx(0.5)
        assert result.is_overdue is True

    def test_silent_reduces_score(self):
        scorer = _make_scorer(silent=True)
        result = scorer.score_job("quiet_job", 3600)
        assert result.score == pytest.approx(0.7)
        assert result.is_silent is True

    def test_overdue_and_silent_critical(self):
        scorer = _make_scorer(overdue=True, silent=True)
        result = scorer.score_job("dead_job", 3600)
        assert result.score == pytest.approx(0.2)
        assert result.label == "critical"

    def test_drift_applies_penalty(self):
        scorer = _make_scorer(drift_secs=20.0)
        result = scorer.score_job("drifty", 3600)
        assert result.drift_seconds == pytest.approx(20.0)
        assert result.score == pytest.approx(1.0 - 20 * 0.01)

    def test_drift_capped_at_max_penalty(self):
        scorer = _make_scorer(drift_secs=1000.0)
        result = scorer.score_job("very_drifty", 3600)
        assert result.score == pytest.approx(1.0 - 0.4)

    def test_recovery_boosts_score(self):
        scorer = _make_scorer(overdue=False, recovered=True)
        result = scorer.score_job("recovered_job", 3600)
        assert result.score == pytest.approx(1.0)
        assert result.recently_recovered is True

    def test_score_all_returns_list(self):
        scorer = _make_scorer()
        results = scorer.score_all({"job_a": 60, "job_b": 3600})
        assert len(results) == 2
        names = {r.job_name for r in results}
        assert names == {"job_a", "job_b"}
