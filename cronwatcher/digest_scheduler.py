"""Schedules periodic digest flushes using a background thread."""

from __future__ import annotations

import logging
import threading
from typing import Optional

from cronwatcher.alert_digest import AlertDigest, DigestReport

logger = logging.getLogger(__name__)


class DigestScheduler:
    """Runs AlertDigest.flush() on a fixed interval in a daemon thread."""

    def __init__(self, digest: AlertDigest, interval_seconds: float = 300.0) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        self._digest = digest
        self._interval = interval_seconds
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_report: Optional[DigestReport] = None

    @property
    def last_report(self) -> Optional[DigestReport]:
        return self._last_report

    def start(self) -> None:
        """Start the background flush thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("DigestScheduler already running")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="digest-scheduler")
        self._thread.start()
        logger.info("DigestScheduler started (interval=%.1fs)", self._interval)

    def stop(self, timeout: float = 5.0) -> None:
        """Signal the background thread to stop and wait for it."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)
        logger.info("DigestScheduler stopped")

    def _loop(self) -> None:
        while not self._stop_event.wait(timeout=self._interval):
            self._run_flush()
        # Final flush on shutdown
        self._run_flush()

    def _run_flush(self) -> None:
        try:
            report = self._digest.flush()
            self._last_report = report
            logger.debug("Digest flushed: %d alert(s)", report.total_alerts)
        except Exception:
            logger.exception("Unexpected error during scheduled digest flush")
