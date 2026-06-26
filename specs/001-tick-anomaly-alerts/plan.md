# Implementation Plan: Tick Anomaly Alerts

**Branch**: `no-active-git-branch` | **Date**: 2026-06-25 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-tick-anomaly-alerts/spec.md`

## Summary

Build a Python 3.12 quantitative monitoring program that subscribes to tick data for a configurable stock watchlist through the GM SDK, detects intraday price jumps, confirmed short-term momentum spikes, and sustained order book liquidity anomalies, classifies audit-only versus reportable events, aggregates reportable events per symbol over a configurable window, suppresses repeated symbol-direction alerts, and sends structured Feishu notifications through the message creation API using `tenant_access_token` authentication. The first version is alert-only: it will not place orders, recommend mandatory trades, or call GM trading APIs.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: `gm` SDK for market data subscription, `requests` or `httpx` for Feishu OpenAPI calls, `pydantic` for configuration and payload validation, `PyYAML` for YAML configuration files, `pytest` for tests

**Storage**: Local files for configuration and replay fixtures; in-memory rolling windows for live tick analysis; append-only JSONL audit files for accepted ticks, anomaly events, suppression decisions, and notification attempts

**Testing**: `pytest` with unit tests for detectors, contract tests for CLI/config/message payloads, replay integration tests using recorded tick fixtures, and mocked Feishu HTTP responses

**Target Platform**: Operator workstation or server that can reach the GM terminal service and Feishu OpenAPI; Python process runs during configured A-share monitoring sessions

**Project Type**: Single Python CLI/application package

**Performance Goals**: Monitor 500 active symbols and make 95% of reportable anomaly groups visible to recipients within 5 seconds after their configured aggregation window closes

**Constraints**: Do not hardcode GM token, Feishu app secret, Feishu recipient IDs, Feishu recipient type, retry settings, or token refresh settings in source; all runtime parameters are loaded from a local YAML config file; real credential-bearing config files must not be committed; keep notification retries bounded; prevent duplicate alert storms; avoid order placement and trading side effects

**Scale/Scope**: Initial scope covers one watchlist, one Feishu notification destination set, price anomaly, momentum anomaly, and order book liquidity anomaly detection, replay validation, and runtime health reporting

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The project constitution currently contains placeholder principles only, so there are no active project-specific gates to enforce. Default quality gates for this feature:

- Keep alerting separate from trading execution.
- Keep secrets and Feishu notification parameters out of source-controlled files.
- Provide replayable tests for anomaly detection and mocked-contract tests for Feishu notifications.
- Maintain an audit trail for events and notification outcomes.

Pre-design gate result: PASS.

## Project Structure

### Documentation (this feature)

```text
specs/001-tick-anomaly-alerts/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md
│   ├── config.schema.json
│   └── feishu-message.md
└── tasks.md
```

### Source Code (repository root)

```text
pyproject.toml
src/
└── tick_stream/
    ├── __init__.py
    ├── alerts.py
    ├── cli.py
    ├── config.py
    ├── gm_client.py
    ├── health.py
    ├── live_strategy.py
    ├── models.py
    ├── notifier.py
    ├── replay.py
    ├── runner.py
    ├── utils.py
    └── detection/
        ├── __init__.py
        ├── engine.py
        ├── features.py
        ├── filters.py
        ├── momentum.py
        ├── normalization.py
        ├── orderbook.py
        ├── price.py
        ├── reporting.py
        ├── windows.py
        └── suppression.py

tests/
├── contract/
│   ├── test_cli_contract.py
│   ├── test_config_schema.py
│   └── test_feishu_payload.py
├── fixtures/
│   └── ticks/
├── integration/
│   ├── test_replay_alert_flow.py
│   └── test_notification_retry.py
└── unit/
    ├── test_feature_snapshot.py
    ├── test_feishu_token.py
    ├── test_momentum_detector.py
    ├── test_orderbook_detector.py
    ├── test_price_detector.py
    ├── test_reporting.py
    └── test_suppression.py
```

**Structure Decision**: Use a single Python package under `src/tick_stream` because the feature is one deployable monitoring process with shared models, detection, notification, replay, and CLI concerns. Tests are split by unit, integration, and contract layers so detector logic can be validated independently from GM and Feishu integrations.

## Complexity Tracking

No constitution violations or extra complexity exceptions are required.

## Phase 0: Research Summary

Research output is recorded in [research.md](./research.md). Key decisions:

- Use GM SDK event-driven tick subscription through Python 3.12.
- Use deterministic anomaly detectors: short-window price jump, momentum z-score against a rolling baseline with actual-return and baseline-quality safeguards, and sustained order book liquidity anomalies based on large order additions, cancellations, and side imbalance.
- Use reportability filtering before Feishu preparation: momentum-only events require sufficient actual return, direct volume/turnover burst, or order book pressure accompanied by minimum volume/turnover activity; standalone order book events require configured severity plus short-window price movement and volume/turnover burst confirmation.
- Aggregate reportable events for the same symbol within a configurable window before sending one Feishu notification, then suppress repeated symbol-direction alerts within cooldown.
- Compute a broader interpretable feature layer for replay calibration: realized volatility burst, order flow imbalance, queue imbalance, depth/spread stress, cancellation/addition pressure, turnover burst, and optional relative-strength residuals.
- Keep advanced methods such as VPIN, CUSUM/SR, Bayesian online changepoint detection, Isolation Forest/LOF, online Half-Space Trees, and Matrix Profile in research/backtest mode until replay metrics justify live alerting.
- Use Feishu `tenant_access_token` authentication, cache tokens until near expiry, and send structured `post` messages through `POST /open-apis/im/v1/messages`.
- Resolve GM and Feishu runtime parameters directly from the local YAML config, including app credentials, recipient type, recipient ID, retry policy, and token refresh margin.
- Use JSONL audit logs and replay fixtures for validation before any live run.

## Phase 1: Design Summary

Design artifacts:

- [data-model.md](./data-model.md): watchlist, tick, rule, anomaly, notification, token cache, audit, and health entities.
- [contracts/cli.md](./contracts/cli.md): command contract for validation, replay, live run, and health checks.
- [contracts/config.schema.json](./contracts/config.schema.json): operator configuration schema.
- [contracts/feishu-message.md](./contracts/feishu-message.md): outbound Feishu message request/response contract.
- [quickstart.md](./quickstart.md): setup and validation guide.

Post-design constitution check: PASS. The design keeps secrets out of source code and expects real credential-bearing YAML configs to remain local, includes replayable detector validation, mocks external notification calls in tests, and does not include trading execution.
