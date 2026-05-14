"""Routes alerts to notifiers based on job tags."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cronwatcher.alerting import Alert
from cronwatcher.notifier import NotifierBase
from cronwatcher.job_tagger import JobTagger


@dataclass
class AlertRouter:
    """Dispatches alerts to notifiers registered for specific tags.

    If a job carries a tag that has a registered notifier, that notifier
    is used.  A *default* notifier is used as a fallback when no tag
    matches (or when the job has no tags at all).
    """

    tagger: JobTagger
    default_notifier: Optional[NotifierBase] = None
    _tag_notifiers: Dict[str, NotifierBase] = field(default_factory=dict, init=False)

    def register_for_tag(self, tag: str, notifier: NotifierBase) -> None:
        """Associate *notifier* with *tag*."""
        self._tag_notifiers[tag] = notifier

    def route(self, alert: Alert) -> List[bool]:
        """Send *alert* to every notifier whose tag the job carries.

        Falls back to *default_notifier* when no tag-specific notifier
        matches.  Returns a list of send-result booleans (one per
        notifier that was invoked).
        """
        job_tags = self.tagger.tags_for_job(alert.job_name)

        matched: List[NotifierBase] = [
            notifier
            for tag, notifier in self._tag_notifiers.items()
            if tag in job_tags
        ]

        if not matched and self.default_notifier is not None:
            matched = [self.default_notifier]

        return [notifier.send(alert) for notifier in matched]

    def registered_tags(self) -> List[str]:
        """Return the list of tags that have a dedicated notifier."""
        return list(self._tag_notifiers.keys())
