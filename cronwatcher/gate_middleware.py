"""Middleware that wraps job execution with ExecutionGate lock management."""

from __future__ import annotations

import logging
import os
from typing import Callable, Optional

from cronwatcher.execution_gate import ExecutionGate

logger = logging.getLogger(__name__)


class GateMiddleware:
    """Wraps a callable job with acquire/release lifecycle via ExecutionGate.

    Usage::

        gate = ExecutionGate()
        middleware = GateMiddleware(gate)
        success = middleware.run("my_job", my_callable)
    """

    def __init__(
        self,
        gate: ExecutionGate,
        timeout_seconds: float = 300.0,
        pid: Optional[int] = None,
    ) -> None:
        self._gate = gate
        self._timeout = timeout_seconds
        self._pid = pid if pid is not None else os.getpid()

    def run(self, job_name: str, fn: Callable[[], None]) -> bool:
        """Acquire lock, execute *fn*, release lock.

        Returns True if the job ran, False if it was skipped due to an
        existing lock or if an exception occurred during execution.
        """
        acquired = self._gate.acquire(
            job_name, pid=self._pid, timeout_seconds=self._timeout
        )
        if not acquired:
            existing_lock = self._gate.get_lock(job_name)
            existing_pid = existing_lock.pid if existing_lock else None
            logger.warning(
                "[gate] Skipping %r — already locked (pid=%s)",
                job_name,
                existing_pid,
            )
            return False

        logger.debug("[gate] Lock acquired for %r (pid=%s)", job_name, self._pid)
        try:
            fn()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("[gate] Job %r raised an exception: %s", job_name, exc)
            return False
        finally:
            released = self._gate.release(job_name, pid=self._pid)
            if released:
                logger.debug("[gate] Lock released for %r", job_name)
            else:
                logger.warning(
                    "[gate] Could not release lock for %r (pid mismatch?)", job_name
                )
