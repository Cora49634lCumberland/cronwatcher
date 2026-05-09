"""Tests for cronwatcher.gate_middleware.GateMiddleware."""

import pytest
from unittest.mock import MagicMock, patch
from cronwatcher.execution_gate import ExecutionGate, LockEntry
from cronwatcher.gate_middleware import GateMiddleware
import time


@pytest.fixture
def gate() -> ExecutionGate:
    return ExecutionGate()


@pytest.fixture
def middleware(gate) -> GateMiddleware:
    return GateMiddleware(gate, timeout_seconds=300, pid=42)


class TestGateMiddleware:
    def test_run_executes_callable(self, middleware):
        fn = MagicMock()
        result = middleware.run("job_a", fn)
        fn.assert_called_once()
        assert result is True

    def test_run_releases_lock_after_execution(self, gate, middleware):
        middleware.run("job_a", lambda: None)
        assert not gate.is_locked("job_a")

    def test_run_skips_when_already_locked(self, gate, middleware):
        # Lock held by a different pid
        gate.acquire("job_b", pid=999, timeout_seconds=300)
        fn = MagicMock()
        result = middleware.run("job_b", fn)
        fn.assert_not_called()
        assert result is False

    def test_run_returns_false_on_exception(self, middleware):
        def boom():
            raise RuntimeError("exploded")

        result = middleware.run("bad_job", boom)
        assert result is False

    def test_lock_released_even_on_exception(self, gate, middleware):
        def boom():
            raise ValueError("oops")

        middleware.run("exc_job", boom)
        assert not gate.is_locked("exc_job")

    def test_run_allows_rerun_after_completion(self, middleware):
        fn = MagicMock()
        middleware.run("repeat", fn)
        middleware.run("repeat", fn)
        assert fn.call_count == 2

    def test_run_expired_lock_allows_execution(self, gate):
        mw = GateMiddleware(gate, timeout_seconds=300, pid=55)
        gate._locks["stale"] = LockEntry(
            job_name="stale", pid=99, acquired_at=time.time() - 400, timeout_seconds=300
        )
        fn = MagicMock()
        result = mw.run("stale", fn)
        fn.assert_called_once()
        assert result is True

    def test_skipped_job_logs_warning(self, gate, middleware, caplog):
        import logging
        gate.acquire("locked_job", pid=999)
        with caplog.at_level(logging.WARNING, logger="cronwatcher.gate_middleware"):
            middleware.run("locked_job", lambda: None)
        assert any("Skipping" in r.message for r in caplog.records)
