"""Job inhibition: temporarily suppress alerting for specific jobs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional


@dataclass
class InhibitEntry:
    job_name: str
    reason: str
    inhibited_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    expires_at: Optional[float] = None  # None means indefinite

    def is_active(self, now: Optional[float] = None) -> bool:
        """Return True if the inhibition is currently active."""
        if now is None:
            now = datetime.now(timezone.utc).timestamp()
        if self.expires_at is None:
            return True
        return now < self.expires_at

    def seconds_remaining(self, now: Optional[float] = None) -> Optional[float]:
        """Return seconds until expiry, or None if indefinite."""
        if self.expires_at is None:
            return None
        if now is None:
            now = datetime.now(timezone.utc).timestamp()
        return max(0.0, self.expires_at - now)

    def __repr__(self) -> str:
        expiry = "indefinite" if self.expires_at is None else f"expires={self.expires_at:.0f}"
        return f"<InhibitEntry job={self.job_name!r} reason={self.reason!r} {expiry}>"


class JobInhibitor:
    """Tracks which jobs are currently inhibited from alerting."""

    def __init__(self) -> None:
        self._entries: Dict[str, InhibitEntry] = {}

    def inhibit(
        self,
        job_name: str,
        reason: str,
        duration_seconds: Optional[float] = None,
    ) -> InhibitEntry:
        """Inhibit alerts for *job_name*. Optionally expires after *duration_seconds*."""
        now = datetime.now(timezone.utc).timestamp()
        expires_at = (now + duration_seconds) if duration_seconds is not None else None
        entry = InhibitEntry(
            job_name=job_name,
            reason=reason,
            inhibited_at=now,
            expires_at=expires_at,
        )
        self._entries[job_name] = entry
        return entry

    def release(self, job_name: str) -> bool:
        """Remove inhibition for *job_name*. Returns True if an entry existed."""
        return self._entries.pop(job_name, None) is not None

    def is_inhibited(self, job_name: str) -> bool:
        """Return True if *job_name* has an active inhibition."""
        entry = self._entries.get(job_name)
        if entry is None:
            return False
        if not entry.is_active():
            # Auto-expire
            del self._entries[job_name]
            return False
        return True

    def active_inhibitions(self) -> Dict[str, InhibitEntry]:
        """Return a dict of all currently active inhibitions (prunes expired)."""
        now = datetime.now(timezone.utc).timestamp()
        expired = [k for k, v in self._entries.items() if not v.is_active(now)]
        for k in expired:
            del self._entries[k]
        return dict(self._entries)

    def __len__(self) -> int:
        return len(self.active_inhibitions())
