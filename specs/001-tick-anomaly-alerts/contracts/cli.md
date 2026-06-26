# CLI Contract: Tick Anomaly Alerts

The application exposes a Python CLI named `tick-stream`.

## Command: validate-config

```bash
tick-stream validate-config --config config/watchlist.yml
```

Behavior:

- Reads and validates configuration against [config.schema.json](./config.schema.json).
- Verifies required sections: GM connection, Feishu notification settings, watchlist, rule profiles, audit settings.
- Does not connect to GM or Feishu.

Exit codes:

- `0`: configuration is valid.
- `2`: configuration is invalid.
- `1`: unexpected runtime error.

Required output:

```json
{
  "status": "ok",
  "symbol_count": 12,
  "rule_profiles": ["default"]
}
```

## Command: replay

```bash
tick-stream replay --config config/watchlist.yml --ticks tests/fixtures/ticks/sample.jsonl --dry-run-notify
```

Behavior:

- Reads JSONL tick fixtures.
- Applies the same normalization, detection, reportability filtering, alert aggregation, suppression, and notification preparation flow used in live mode.
- Supports fixtures with or without order book depth fields; when depth fields are present, order book liquidity anomalies are evaluated.
- With `--dry-run-notify`, validates Feishu payloads but does not send HTTP requests.

Exit codes:

- `0`: replay completed and all expected contract checks passed.
- `3`: replay completed but labeled expectations failed.
- `2`: configuration or fixture input invalid.
- `1`: unexpected runtime error.

Required summary output:

```json
{
  "status": "completed",
  "ticks_read": 1000,
  "ticks_accepted": 995,
  "anomalies_detected": 4,
  "orderbook_detector_status": "available",
  "notifications_prepared": 3,
  "notifications_sent": 0,
  "dry_run_notify": true
}
```

## Command: run

```bash
tick-stream run --config config/watchlist.yml
```

Behavior:

- Validates configuration.
- Initializes GM SDK connection.
- Subscribes to active watchlist symbols.
- Emits startup health JSON and exits without entering the GM SDK event loop.
- Writes JSONL health audit records.

## Command: run --blocking

```bash
tick-stream run --config config/watchlist.yml --blocking
```

Behavior:

- Validates configuration.
- Initializes GM SDK connection through the GM strategy runtime.
- Subscribes to active watchlist symbols.
- Processes live ticks until interrupted.
- Applies reportability filtering, alert aggregation, cooldown suppression, and Feishu sending for reportable anomaly groups.
- Writes JSONL audit records.

Exit codes:

- `0`: stopped cleanly after operator interrupt or configured shutdown.
- `4`: GM connection or subscription setup failed.
- `5`: Feishu authentication or notification setup failed.
- `1`: unexpected runtime error.

Required startup output:

```json
{
  "status": "running",
  "active_symbol_count": 12,
  "gm_connection_status": "healthy",
  "feishu_status": "healthy"
}
```

## Command: health

```bash
tick-stream health --audit-dir var/audit
```

Behavior:

- Reads latest health/audit records.
- Emits current monitoring status without exposing secrets.

Required output:

```json
{
  "gm_connection_status": "healthy",
  "feishu_status": "healthy",
  "active_symbol_count": 12,
  "last_tick_at": "2026-06-25T10:30:00+08:00",
  "pending_notification_count": 0
}
```
