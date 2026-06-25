# Quickstart: Tick Anomaly Alerts

This guide validates the planned feature end to end before live monitoring.

## Prerequisites

- Python 3.12.
- GM SDK installable with the mirror documented in `GM-API.md`.
- GM terminal is running and reachable from this machine.
- Feishu self-built app has bot/message permissions and valid app credentials.
- Recipient ID and recipient ID type are provided through environment variables.

## 1. Create Environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install gm -U -i https://mirrors.aliyun.com/pypi/simple/
python -m pip install pydantic PyYAML requests pytest jsonschema
```

## 2. Provide Secrets Through Environment

```bash
export GM_TOKEN="replace-with-local-gm-token"
export FEISHU_APP_ID="cli_xxxxxxxxxxxxxxxx"
export FEISHU_APP_SECRET="replace-with-app-secret"
export FEISHU_RECEIVE_ID_TYPE="chat_id"
export FEISHU_RECEIVE_ID="oc_xxxxxxxxxxxxxxxx"
export FEISHU_TOKEN_REFRESH_MARGIN_SECONDS="300"
export FEISHU_MAX_ATTEMPTS="3"
export FEISHU_RETRY_BACKOFF_SECONDS="1,5,30"
```

Do not commit real values.

## 3. Create Local Config

Create `config/watchlist.yml` using [contracts/config.schema.json](./contracts/config.schema.json) as the contract. Minimal example:

```yaml
gm:
  token_env: GM_TOKEN
  serv_addr: "192.168.5.127:7001"
  strategy_id: "replace-with-strategy-id"
  mode: live

feishu:
  app_id_env: FEISHU_APP_ID
  app_secret_env: FEISHU_APP_SECRET
  receive_id_type_env: FEISHU_RECEIVE_ID_TYPE
  receive_id_env: FEISHU_RECEIVE_ID
  token_refresh_margin_seconds_env: FEISHU_TOKEN_REFRESH_MARGIN_SECONDS
  max_attempts_env: FEISHU_MAX_ATTEMPTS
  retry_backoff_seconds_env: FEISHU_RETRY_BACKOFF_SECONDS

watchlist:
  - symbol: SHSE.600519
    name: 贵州茅台
    active: true
    rule_profile: default

rules:
  default:
    price_window_seconds: 30
    price_return_threshold_pct: 1.5
    momentum_impulse_seconds: 10
    momentum_baseline_seconds: 180
    momentum_z_threshold: 3.0
    orderbook_window_seconds: 30
    orderbook_min_consecutive_ticks: 2
    orderbook_cancel_ratio_threshold: 0.35
    orderbook_imbalance_ratio_threshold: 0.70
    orderbook_standalone_min_severity: high
    min_ticks_short_window: 3
    min_ticks_baseline_window: 20
    cooldown_seconds: 180
    severity_thresholds:
      warning:
        price_return_pct: 1.5
        momentum_z: 3.0
        orderbook_cancel_ratio: 0.25
        orderbook_imbalance_ratio: 0.60
      high:
        price_return_pct: 2.5
        momentum_z: 4.0
        orderbook_cancel_ratio: 0.35
        orderbook_imbalance_ratio: 0.70
      critical:
        price_return_pct: 3.5
        momentum_z: 5.0
        orderbook_cancel_ratio: 0.50
        orderbook_imbalance_ratio: 0.85
    ignored_sessions:
      - start: "09:25:00"
        end: "09:30:00"

audit:
  dir: var/audit
  write_tick_summaries: true
```

## 4. Validate Config

```bash
tick-stream validate-config --config config/watchlist.yml
```

Expected:

- Exit code `0`.
- JSON output contains `status: ok`.
- No secret values are printed.

## 5. Replay Tick Fixture Without Sending Notifications

```bash
tick-stream replay --config config/watchlist.yml --ticks tests/fixtures/ticks/sample.jsonl --dry-run-notify
```

Expected:

- Fixture ticks are accepted or rejected with clear quality reasons.
- Known price jump, momentum, and sustained order book liquidity scenarios create anomaly events.
- Fixtures without order book fields still run price and momentum detection and mark the order book detector unavailable.
- Feishu payloads validate against [contracts/feishu-message.md](./contracts/feishu-message.md).
- No HTTP request is sent when `--dry-run-notify` is set.

## 6. Test Feishu Authentication and Message Contract

Use a dedicated test recipient before production groups:

```bash
tick-stream replay --config config/watchlist.yml --ticks tests/fixtures/ticks/single-alert.jsonl
```

Expected:

- The application obtains a `tenant_access_token`.
- One structured Feishu `post` message is sent.
- Audit log records notification status as `sent` and stores the returned message ID when available.

## 7. Run Live Monitoring

```bash
tick-stream run --config config/watchlist.yml
```

Expected startup:

- GM connection status is `healthy`.
- Feishu status is `healthy`.
- Active symbol count matches the config.
- Process subscribes only to active watchlist symbols.

## 8. Inspect Health

```bash
tick-stream health --audit-dir var/audit
```

Expected:

- Latest GM and Feishu status are visible.
- Last accepted tick time is recent during market hours.
- Pending notification count is zero or explained by visible failure reasons.

## Validation Matrix

| Scenario | Command | Expected Result |
| --- | --- | --- |
| Config schema valid | `validate-config` | Exit `0`, status `ok` |
| Price jump replay | `replay --dry-run-notify` | Price anomaly event generated |
| Momentum replay | `replay --dry-run-notify` | Momentum anomaly event generated |
| Order book replay | `replay --dry-run-notify` | Sustained cancellation or imbalance event generated when depth fields are present |
| Duplicate cooldown | `replay --dry-run-notify` | Duplicate notifications suppressed |
| Feishu token failure | mocked replay/integration test | Token refresh or sanitized failure |
| Feishu 5xx | mocked replay/integration test | Bounded retry then sent/failed state |
| Live startup | `run` | GM and Feishu health visible |
