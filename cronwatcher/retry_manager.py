"""Manages retry state across multiple jobs and triggers alerts on exhaustion."""

from datetime import datetime
from typing import Dict, Optional

from cronwatcher.alerting import Alert, AlertManager
from cronwatcher.retry_policy import RetryPolicy, RetryState


class RetryManager:
    """Coordinates retry policies and state for all registered jobs."""

    def __init__(
        self,
        alert_manager: AlertManager,
        default_policy: Optional[RetryPolicy] = None,
    ) -> None:
        self._alert_manager = alert_manager
        self._default_policy = default_policy or RetryPolicy()
        self._policies: Dict[str, RetryPolicy] = {}
        self._states: Dict[str, RetryState] = {}

    def register_policy(self, job_name: str, policy: RetryPolicy) -> None:
        """Register a custom retry policy for a job."""
        self._policies[job_name] = policy

    def _get_policy(self, job_name: str) -> RetryPolicy:
        return self._policies.get(job_name, self._default_policy)

    def _get_state(self, job_name: str) -> RetryState:
        if job_name not in self._states:
            self._states[job_name] = RetryState(job_name=job_name)
        return self._states[job_name]

    def record_failure(self, job_name: str, at: Optional[datetime] = None) -> bool:
        """Record a job failure. Returns True if a retry should be scheduled."""
        policy = self._get_policy(job_name)
        state = self._get_state(job_name)
        state.record_attempt(at=at)

        if policy.is_exhausted(state.attempt):
            alert = Alert(
                job_name=job_name,
                reason=(
                    f"Job '{job_name}' failed after {state.attempt} attempt(s); "
                    "retry policy exhausted."
                ),
                last_seen=state.last_attempt_at,
            )
            self._alert_manager.trigger(alert)
            return False
        return True

    def record_success(self, job_name: str) -> None:
        """Record a successful execution and reset retry state."""
        state = self._get_state(job_name)
        state.record_success()
        state.reset()

    def next_retry_at(self, job_name: str) -> Optional[datetime]:
        """Return when the next retry should fire, or None if exhausted."""
        policy = self._get_policy(job_name)
        state = self._get_state(job_name)
        if state.last_attempt_at is None:
            return None
        return policy.next_retry_at(state.last_attempt_at, state.attempt)

    def get_state(self, job_name: str) -> RetryState:
        return self._get_state(job_name)
