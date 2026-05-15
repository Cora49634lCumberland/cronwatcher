"""Tests for cronwatcher.job_dependency."""
import pytest

from cronwatcher.job_dependency import DependencyGraph, DependencyViolation


@pytest.fixture
def graph() -> DependencyGraph:
    return DependencyGraph()


class TestDependencyGraph:
    def test_upstream_jobs_empty_by_default(self, graph: DependencyGraph) -> None:
        assert graph.upstream_jobs("job_a") == []

    def test_add_dependency_records_upstream(self, graph: DependencyGraph) -> None:
        graph.add_dependency("job_b", "job_a")
        assert graph.upstream_jobs("job_b") == ["job_a"]

    def test_multiple_upstreams(self, graph: DependencyGraph) -> None:
        graph.add_dependency("job_c", "job_a")
        graph.add_dependency("job_c", "job_b")
        assert graph.upstream_jobs("job_c") == ["job_a", "job_b"]

    def test_remove_dependency(self, graph: DependencyGraph) -> None:
        graph.add_dependency("job_b", "job_a")
        graph.remove_dependency("job_b", "job_a")
        assert graph.upstream_jobs("job_b") == []

    def test_remove_nonexistent_dependency_is_safe(self, graph: DependencyGraph) -> None:
        graph.remove_dependency("job_x", "job_y")  # should not raise

    def test_downstream_jobs(self, graph: DependencyGraph) -> None:
        graph.add_dependency("job_b", "job_a")
        graph.add_dependency("job_c", "job_a")
        assert graph.downstream_jobs("job_a") == ["job_b", "job_c"]

    def test_downstream_empty_when_no_dependents(self, graph: DependencyGraph) -> None:
        graph.add_dependency("job_b", "job_a")
        assert graph.downstream_jobs("job_b") == []

    def test_check_violations_no_violation_when_deps_met(self, graph: DependencyGraph) -> None:
        graph.add_dependency("job_b", "job_a")
        result = graph.check_violations("job_b", completed_jobs={"job_a"})
        assert result is None

    def test_check_violations_returns_violation_when_missing(self, graph: DependencyGraph) -> None:
        graph.add_dependency("job_b", "job_a")
        result = graph.check_violations("job_b", completed_jobs=set())
        assert isinstance(result, DependencyViolation)
        assert result.job_name == "job_b"
        assert "job_a" in result.missing_upstream

    def test_check_violations_partial_missing(self, graph: DependencyGraph) -> None:
        graph.add_dependency("job_c", "job_a")
        graph.add_dependency("job_c", "job_b")
        result = graph.check_violations("job_c", completed_jobs={"job_a"})
        assert result is not None
        assert result.missing_upstream == ["job_b"]

    def test_check_violations_no_deps_registered(self, graph: DependencyGraph) -> None:
        result = graph.check_violations("unknown_job", completed_jobs=set())
        assert result is None

    def test_all_jobs_returns_registered_jobs(self, graph: DependencyGraph) -> None:
        graph.add_dependency("job_b", "job_a")
        graph.add_dependency("job_c", "job_a")
        assert graph.all_jobs() == ["job_b", "job_c"]


class TestDependencyViolation:
    def test_repr_contains_job_and_missing(self) -> None:
        v = DependencyViolation(job_name="job_b", missing_upstream=["job_a"])
        r = repr(v)
        assert "job_b" in r
        assert "job_a" in r
