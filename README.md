# cronwatcher

A daemon that monitors cron job execution times and alerts on drift or silent failures.

---

## Installation

```bash
pip install cronwatcher
```

Or install from source:

```bash
git clone https://github.com/youruser/cronwatcher.git && cd cronwatcher && pip install .
```

---

## Usage

Define your jobs in a `cronwatcher.yaml` config file:

```yaml
jobs:
  daily-backup:
    schedule: "0 2 * * *"
    max_drift_seconds: 300
    alert: email
  hourly-sync:
    schedule: "0 * * * *"
    max_drift_seconds: 60
    alert: slack
```

Start the daemon:

```bash
cronwatcher start --config cronwatcher.yaml
```

Check status of monitored jobs:

```bash
cronwatcher status
```

When a job runs late beyond its `max_drift_seconds` threshold, or fails to run at all, cronwatcher fires an alert via your configured channel (email, Slack, PagerDuty, etc.).

---

## Configuration

| Field | Description | Default |
|---|---|---|
| `schedule` | Cron expression for expected run time | required |
| `max_drift_seconds` | Seconds of delay before alerting | `60` |
| `alert` | Alert channel (`email`, `slack`, `pagerduty`) | `email` |

---

## License

MIT © 2024 cronwatcher contributors