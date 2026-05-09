"""Tests for retry_policy and retry_manager modules."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from cronwatcher.retry_policy import RetryPolicy, RetryState
from cronwatcher.retry_manager import RetryManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def policy() -> RetryPolicy:
    return RetryPolicy(max_attempts=3, backoff_seconds=60.0, backoff_multiplier=2.0)


@pytest.fixture
def alert_manager() -> MagicMock:
    return MagicMock()


@pytest.fixture
def manager(alert_manager: MagicMock) -> RetryManager:
    return RetryManager(alert_manager=alert_manager, default_policy=RetryPolicy(max_attempts=3))


# ---------------------------------------------------------------------------
# RetryPolicy tests
# ---------------------------------------------------------------------------

class TestRetryPolicy:
    def test_delay_first_attempt_is_zero(self, policy: RetryPolicy) -> None:
        assert policy.delay_for_attempt(1) == 0.0

    def test_delay_second_attempt_equals_backoff(self, policy: RetryPolicy) -> None:
        assert policy.delay_for_attempt(2) == 60.0

    def test_delay_third_attempt_doubles(self, policy: RetryPolicy) -> None:
        assert policy.delay_for_attempt(3) == 120.0

    def test_delay_capped_at_max_backoff(self) -> None:
        p = RetryPolicy(backoff_seconds=60.0, backoff_multiplier=10.0, max_backoff_seconds=100.0)
        assert p.delay_for_attempt(5) == 100.0

    def test_is_exhausted_at_max(self, policy: RetryPolicy) -> None:
        assert policy.is_exhausted(3) is True

    def test_not_exhausted_below_max(self, policy: RetryPolicy) -> None:
        assert policy.is_exhausted(2) is False

    def test_next_retry_at_returns_none_when_exhausted(self, policy: RetryPolicy) -> None:
        now = datetime.utcnow()
        assert policy.next_retry_at(now, attempt=3) is None

    def test_next_retry_at_adds_delay(self, policy: RetryPolicy) -> None:
        now = datetime(2024, 1, 1, 12, 0, 0)
        result = policy.next_retry_at(now, attempt=1)
        assert result == now + timedelta(seconds=60.0)

    def test_invalid_max_attempts_raises(self) -> None:
        with pytest.raises(ValueError, match="max_attempts"):
            RetryPolicy(max_attempts=0)

    def test_invalid_multiplier_raises(self) -> None:
        with pytest.raises(ValueError, match="backoff_multiplier"):
            RetryPolicy(backoff_multiplier=0.5)


# ---------------------------------------------------------------------------
# RetryState tests
# ---------------------------------------------------------------------------

class TestRetryState:
    def test_initial_state(self) -> None:
        state = RetryState(job_name="backup")
        assert state.attempt == 0
        assert state.succeeded is False

    def test_record_attempt_increments(self) -> None:
        state = RetryState(job_name="backup")
        state.record_attempt()
        assert state.attempt == 1
        assert state.last_attempt_at is not None

    def test_reset_clears_state(self) -> None:
        state = RetryState(job_name="backup")
        state.record_attempt()
        state.reset()
        assert state.attempt == 0
        assert state.last_attempt_at is None


# ---------------------------------------------------------------------------
# RetryManager tests
# ---------------------------------------------------------------------------

class TestRetryManager:
    def test_record_failure_returns_true_when_retries_remain(
        self, manager: RetryManager
    ) -> None:
        assert manager.record_failure("job_a") is True

    def test_record_failure_returns_false_when_exhausted(
        self, manager: RetryManager, alert_manager: MagicMock
    ) -> None:
        manager.record_failure("job_a")
        manager.record_failure("job_a")
        result = manager.record_failure("job_a")
        assert result is False
        alert_manager.trigger.assert_called_once()

    def test_record_success_resets_state(self, manager: RetryManager) -> None:
        manager.record_failure("job_b")
        manager.record_success("job_b")
        assert manager.get_state("job_b").attempt == 0

    def test_custom_policy_respected(self, alert_manager: MagicMock) -> None:
        mgr = RetryManager(alert_manager=alert_manager)
        mgr.register_policy("job_c", RetryPolicy(max_attempts=1))
        result = mgr.record_failure("job_c")
        assert result is False
        alert_manager.trigger.assert_called_once()

    def test_next_retry_at_none_before_any_failure(self, manager: RetryManager) -> None:
        assert manager.next_retry_at("unknown_job") is None
