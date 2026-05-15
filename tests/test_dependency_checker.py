import time
import pytest

from cronwatcher.job_dependency import DependencyGraph
from cronwatcher.heartbeat import HeartbeatTracker
from cronwatcher.dependency_checker import DependencyChecker, CheckResult


@pytest.fixture
def graph():
    g = DependencyGraph()
    g.add_dependency(downstream="reports", upstream="etl")
    g.add_dependency(downstream="reports", upstream="transform")
    g.add_dependency(downstream="transform", upstream="etl")
    return g


@pytest.fixture
def tracker():
    return HeartbeatTracker()


@pytest.fixture
def checker(graph, tracker):
    return DependencyChecker(graph, tracker, max_staleness_seconds=3600.0)


class TestCheckResult:
    def test_passed_when_no_violations(self):
        result = CheckResult(job_name="myjob")
        assert result.passed is True

    def test_failed_when_violations_present(self):
        from cronwatcher.job_dependency import DependencyViolation
        v = DependencyViolation(upstream="etl", downstream="reports")
        result = CheckResult(job_name="reports", violations=[v])
        assert result.passed is False

    def test_repr_ok(self):
        result = CheckResult(job_name="myjob")
        assert "OK" in repr(result)
        assert "myjob" in repr(result)

    def test_repr_blocked_lists_upstreams(self):
        from cronwatcher.job_dependency import DependencyViolation
        v = DependencyViolation(upstream="etl", downstream="reports")
        result = CheckResult(job_name="reports", violations=[v])
        assert "BLOCKED" in repr(result)
        assert "etl" in repr(result)


class TestDependencyChecker:
    def test_no_upstreams_always_passes(self, checker, tracker):
        result = checker.check("etl")
        assert result.passed is True

    def test_fails_when_upstream_never_seen(self, checker, tracker):
        result = checker.check("transform")
        assert result.passed is False
        upstream_names = [v.upstream for v in result.violations]
        assert "etl" in upstream_names

    def test_passes_when_upstream_recently_seen(self, checker, tracker):
        tracker.record("etl")
        result = checker.check("transform")
        assert result.passed is True

    def test_fails_when_upstream_too_stale(self, graph, tracker):
        stale_checker = DependencyChecker(graph, tracker, max_staleness_seconds=0.01)
        tracker.record("etl")
        time.sleep(0.05)
        result = stale_checker.check("transform")
        assert result.passed is False

    def test_multiple_upstreams_partial_completion(self, checker, tracker):
        tracker.record("etl")
        # transform not recorded
        result = checker.check("reports")
        assert result.passed is False
        upstream_names = [v.upstream for v in result.violations]
        assert "transform" in upstream_names
        assert "etl" not in upstream_names

    def test_all_upstreams_satisfied(self, checker, tracker):
        tracker.record("etl")
        tracker.record("transform")
        result = checker.check("reports")
        assert result.passed is True

    def test_check_all_returns_result_per_job(self, checker, tracker):
        tracker.record("etl")
        results = checker.check_all(["etl", "transform", "reports"])
        assert len(results) == 3
        names = [r.job_name for r in results]
        assert "etl" in names
        assert "transform" in names
        assert "reports" in names

    def test_check_all_empty_list(self, checker):
        results = checker.check_all([])
        assert results == []
