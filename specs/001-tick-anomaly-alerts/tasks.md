# Tasks: Tick Anomaly Alerts

**Input**: Design documents from `specs/001-tick-anomaly-alerts/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Included because the specification, plan, and quickstart define replay, contract, integration, and mocked notification validation.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files and does not depend on incomplete tasks.
- **[Story]**: Maps to user stories in `spec.md`.
- Every task includes an exact file path.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize the Python package, test layout, and local-file safety boundaries.

- [X] T001 Create `pyproject.toml` with Python 3.12 metadata, dependencies (`gm`, `pydantic`, `PyYAML`, `requests`, `pytest`, `jsonschema`), and `tick-stream` console script
- [X] T002 Create package directories and package markers in `src/tick_stream/__init__.py` and `src/tick_stream/detection/__init__.py`
- [X] T003 [P] Create test scaffolding markers in `tests/conftest.py`, `tests/fixtures/config/.gitkeep`, and `tests/fixtures/ticks/.gitkeep`
- [X] T004 [P] Create `.gitignore` entries for `.venv/`, `var/audit/`, `config/*.local.yml`, and other credential-bearing local config files
- [X] T005 [P] Create `config/watchlist.example.yml` with placeholder GM and Feishu values matching `specs/001-tick-anomaly-alerts/contracts/config.schema.json`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core models, configuration, audit, CLI, and validation infrastructure that all user stories depend on.

**CRITICAL**: No user story work should begin until this phase is complete.

- [X] T006 Implement YAML config loading, `config.schema.json` validation, defaults, and secret-safe error messages in `src/tick_stream/config.py`
- [X] T007 [P] Define domain enums and dataclasses for watchlist symbols, ticks, order book snapshots, feature snapshots, anomaly rules, anomaly events, notifications, token cache, audit records, and health state in `src/tick_stream/models.py`
- [X] T008 [P] Implement append-only JSONL audit writer with secret redaction in `src/tick_stream/audit.py`
- [X] T009 [P] Implement monitoring health state serialization and secret-safe status output in `src/tick_stream/health.py`
- [X] T010 [P] Implement CLI command skeletons for `validate-config`, `replay`, `run`, and `health` in `src/tick_stream/cli.py`
- [X] T011 [P] Implement shared time parsing, numeric safety helpers, and stable JSON serialization in `src/tick_stream/utils.py`
- [X] T012 [P] Create valid and invalid YAML config fixtures in `tests/fixtures/config/valid_watchlist.yml` and `tests/fixtures/config/invalid_watchlist.yml`
- [X] T013 [P] Create config schema contract tests in `tests/contract/test_config_schema.py`
- [X] T014 Create CLI contract tests for `validate-config` success/failure behavior in `tests/contract/test_cli_contract.py`
- [X] T015 Implement reusable JSONL replay fixture reader and labeled-expectation parser in `src/tick_stream/replay.py`

**Checkpoint**: Foundation ready; user story implementation can now begin in priority order or in parallel by story.

---

## Phase 3: User Story 1 - 监控标的池 tick 异常 (Priority: P1) MVP

**Goal**: Subscribe/process watchlist tick data and detect price, momentum, and order book liquidity anomalies without sending Feishu messages.

**Independent Test**: Replay tick fixtures containing normal ticks, price jumps, momentum spikes, order book cancellations/additions, missing order book fields, duplicate ticks, out-of-order ticks, and out-of-watchlist symbols; verify only matching scenarios create anomaly events and feature audit records.

### Tests for User Story 1

- [X] T016 [P] [US1] Create tick normalization and quality-filter unit tests in `tests/unit/test_tick_normalization.py`
- [X] T017 [P] [US1] Create price jump detector unit tests in `tests/unit/test_price_detector.py`
- [X] T018 [P] [US1] Create momentum detector unit tests in `tests/unit/test_momentum_detector.py`
- [X] T019 [P] [US1] Create order book liquidity detector unit tests in `tests/unit/test_orderbook_detector.py`
- [X] T020 [P] [US1] Create feature snapshot unit tests for volatility, turnover burst, OFI, queue imbalance, spread, depth collapse, and unavailable feature reasons in `tests/unit/test_feature_snapshot.py`
- [X] T021 [US1] Create replay integration test for mixed normal/anomaly tick fixtures in `tests/integration/test_replay_alert_flow.py`

### Implementation for User Story 1

- [X] T022 [P] [US1] Implement tick normalization, duplicate rejection, out-of-order rejection, and missing-field quality status in `src/tick_stream/detection/normalization.py`
- [X] T023 [P] [US1] Implement rolling window storage for accepted ticks and per-symbol detector state in `src/tick_stream/detection/windows.py`
- [X] T024 [P] [US1] Implement FeatureSnapshot computation for realized volatility, turnover burst, OFI, queue imbalance, spread stress, depth collapse, cancellation/addition ratio, and feature availability in `src/tick_stream/detection/features.py`
- [X] T025 [P] [US1] Implement short-window price jump detector and severity mapping in `src/tick_stream/detection/price.py`
- [X] T026 [P] [US1] Implement robust momentum z-score detector and severity mapping in `src/tick_stream/detection/momentum.py`
- [X] T027 [P] [US1] Implement order book liquidity detector for sustained large additions, cancellations, and side imbalance in `src/tick_stream/detection/orderbook.py`
- [X] T028 [US1] Implement detection engine orchestration that emits AnomalyEvent objects with feature snapshot references in `src/tick_stream/detection/engine.py`
- [X] T029 [US1] Integrate replay processing, anomaly summaries, and dry-run notification preparation counts in `src/tick_stream/replay.py`
- [X] T030 [US1] Add JSONL tick fixtures for normal, price jump, momentum spike, order book anomaly, missing order book, duplicate, out-of-order, and out-of-watchlist scenarios in `tests/fixtures/ticks/sample.jsonl`
- [X] T031 [US1] Write feature and anomaly audit records during replay without credentials or raw config dumps in `src/tick_stream/audit.py`
- [X] T032 [US1] Wire the `tick-stream replay --dry-run-notify` command to the replay engine in `src/tick_stream/cli.py`

**Checkpoint**: User Story 1 is independently functional when replay fixtures produce expected anomaly events and no Feishu network calls.

---

## Phase 4: User Story 2 - 发送结构化飞书通知 (Priority: P2)

**Goal**: Convert reportable anomaly events into structured Feishu `post` messages, authenticate with `tenant_access_token`, send notifications, track delivery state, retry recoverable failures, and suppress duplicate alert storms.

**Independent Test**: Feed prepared anomaly events through the notification flow with mocked Feishu token/message endpoints; verify payload fields, token refresh, retry behavior, delivery states, sanitized audit records, and duplicate suppression.

### Tests for User Story 2

- [X] T033 [P] [US2] Create Feishu message payload contract tests in `tests/contract/test_feishu_payload.py`
- [X] T034 [P] [US2] Create Feishu token cache and forced-refresh unit tests in `tests/unit/test_feishu_token.py`
- [X] T035 [P] [US2] Create notification suppression and escalation unit tests in `tests/unit/test_suppression.py`
- [X] T036 [US2] Create mocked Feishu notification retry integration tests in `tests/integration/test_notification_retry.py`
- [X] T037 [US2] Extend CLI replay contract tests for `--dry-run-notify` and live notification summary fields in `tests/contract/test_cli_contract.py`

### Implementation for User Story 2

- [X] T038 [P] [US2] Implement Feishu `post` content builder with price, momentum, order book, severity, reason, and safe title fields in `src/tick_stream/notifier.py`
- [X] T039 [US2] Implement Feishu `tenant_access_token` acquisition, in-memory token cache, expiry margin handling, and forced refresh in `src/tick_stream/notifier.py`
- [X] T040 [US2] Implement Feishu message send, response parsing, bounded retry, recoverable/non-recoverable failure classification, and delivery-state updates in `src/tick_stream/notifier.py`
- [X] T041 [P] [US2] Implement cooldown, aggregation, severity escalation, and suppression-key logic in `src/tick_stream/detection/suppression.py`
- [X] T042 [US2] Integrate suppression before notification preparation in `src/tick_stream/replay.py`
- [X] T043 [US2] Write notification attempt, sent, failed, retried, and suppressed audit records without token values in `src/tick_stream/audit.py`
- [X] T044 [US2] Integrate real notification sending for replay without `--dry-run-notify` in `src/tick_stream/replay.py`
- [X] T045 [US2] Add `single-alert.jsonl` replay fixture that produces exactly one reportable Feishu notification in `tests/fixtures/ticks/single-alert.jsonl`

**Checkpoint**: User Story 2 is independently functional when mocked Feishu tests pass and one replay alert can produce a contract-compliant notification.

---

## Phase 5: User Story 3 - 管理监控范围和告警规则 (Priority: P3)

**Goal**: Allow operators to adjust watchlist membership, rule profiles, thresholds, ignored sessions, and notification settings through YAML configuration, then run live GM monitoring and health checks.

**Independent Test**: Modify YAML watchlist and rule thresholds, replay the same fixture, and verify monitored symbols and anomaly outcomes change accordingly; run live startup with a mocked GM client and verify subscription set, health output, and no trading API usage.

### Tests for User Story 3

- [X] T046 [P] [US3] Create rule profile, watchlist active/inactive, and threshold override unit tests in `tests/unit/test_config_rules.py`
- [X] T047 [P] [US3] Create market-state filter unit tests for ignored sessions, data gaps, and special market states in `tests/unit/test_market_filters.py`
- [X] T048 [US3] Create replay integration test showing config changes alter anomaly outcomes in `tests/integration/test_config_update_replay.py`
- [X] T049 [US3] Create mocked GM live startup and subscription integration tests in `tests/integration/test_live_gm_startup.py`
- [X] T050 [US3] Extend CLI contract tests for `run` startup output and `health` output in `tests/contract/test_cli_contract.py`

### Implementation for User Story 3

- [X] T051 [US3] Implement watchlist active/inactive filtering, per-symbol rule profile selection, and threshold override resolution in `src/tick_stream/config.py`
- [X] T052 [P] [US3] Implement market-state filters for ignored sessions, data gaps, missing order book availability, and special market status hooks in `src/tick_stream/detection/filters.py`
- [X] T053 [US3] Implement GM SDK initialization, token setup, terminal address setup, strategy ID setup, and active watchlist subscription in `src/tick_stream/gm_client.py`
- [X] T054 [US3] Implement live tick callback adapter that converts GM tick objects into TickRecord input for the detection engine in `src/tick_stream/gm_client.py`
- [X] T055 [US3] Implement live runtime orchestration for GM client, detection engine, suppression, notifier, audit, and shutdown handling in `src/tick_stream/runner.py`
- [X] T056 [US3] Wire `tick-stream run --config` to the live runtime and startup status output in `src/tick_stream/cli.py`
- [X] T057 [US3] Wire `tick-stream health --audit-dir` to read latest audit/health records and emit secret-safe JSON in `src/tick_stream/cli.py`
- [X] T058 [US3] Add local YAML example variants for active/inactive symbols and threshold changes in `tests/fixtures/config/watchlist_variant.yml`

**Checkpoint**: User Story 3 is independently functional when config-only changes alter replay/live behavior and health status is available without exposing secrets.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Hardening, metrics validation, documentation, and operational polish across all stories.

- [X] T059 [P] Add labeled replay fixtures for success criteria SC-001, SC-002, and SC-003 in `tests/fixtures/ticks/labeled_anomalies.jsonl`
- [X] T060 [P] Add replay metric tests for detection recall, false alert rate, duplicate reduction, and required notification fields in `tests/integration/test_success_criteria.py`
- [X] T061 [P] Add 500-symbol synthetic replay performance test for the 5-second reportability goal in `tests/integration/test_performance_500_symbols.py`
- [X] T062 [P] Add secret redaction contract tests for logs, CLI output, audit records, and Feishu message text in `tests/contract/test_secret_redaction.py`
- [X] T063 [P] Document local configuration handling, ignored config patterns, GM terminal prerequisites, and Feishu permission setup in `README.md`
- [X] T064 Update quickstart validation notes after implementation in `specs/001-tick-anomaly-alerts/quickstart.md`
- [X] T065 Run the full quickstart validation flow and record any deviations in `specs/001-tick-anomaly-alerts/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1) has no dependencies.
- Foundational (Phase 2) depends on Setup and blocks all user stories.
- User Story 1 (Phase 3) depends on Foundational and is the MVP.
- User Story 2 (Phase 4) depends on Foundational; it can be developed with prepared anomaly fixtures, but end-to-end replay notification depends on User Story 1 outputs.
- User Story 3 (Phase 5) depends on Foundational; live runtime integration benefits from User Story 1 detection and User Story 2 notification components.
- Polish (Phase 6) depends on the user stories selected for release.

### User Story Dependencies

- **US1 (P1)**: Start after Foundational; no dependency on US2 or US3.
- **US2 (P2)**: Start after Foundational using synthetic AnomalyEvent fixtures; full replay notification path depends on US1.
- **US3 (P3)**: Start after Foundational using mocked GM client; full live alert path depends on US1 and US2.

### Within Each User Story

- Tests should be written first and fail before implementation.
- Models and fixtures before services.
- Detector/notifier/runtime implementation before CLI integration.
- Audit and health integration before story checkpoint validation.

---

## Parallel Opportunities

- Setup tasks T003, T004, and T005 can run in parallel after T001/T002 are understood.
- Foundational tasks T007, T008, T009, T010, T011, T012, and T013 can run in parallel after T006 shape is agreed.
- US1 detector tests T016-T020 can run in parallel; detector implementations T022-T027 can also run in parallel before T028 integrates them.
- US2 payload/token/suppression tests T033-T035 can run in parallel; payload builder T038 and suppression T041 can run in parallel before notifier integration.
- US3 rule/filter/live startup tests T046-T050 can be split across test files; market filters T052 can run in parallel with GM client work T053.
- Polish tasks T059-T063 can run in parallel once core behavior exists.

## Parallel Example: User Story 1

```text
Task: "T017 [US1] Create price jump detector unit tests in tests/unit/test_price_detector.py"
Task: "T018 [US1] Create momentum detector unit tests in tests/unit/test_momentum_detector.py"
Task: "T019 [US1] Create order book liquidity detector unit tests in tests/unit/test_orderbook_detector.py"
Task: "T020 [US1] Create feature snapshot unit tests in tests/unit/test_feature_snapshot.py"
Task: "T025 [US1] Implement short-window price jump detector and severity mapping in src/tick_stream/detection/price.py"
Task: "T026 [US1] Implement robust momentum z-score detector and severity mapping in src/tick_stream/detection/momentum.py"
Task: "T027 [US1] Implement order book liquidity detector in src/tick_stream/detection/orderbook.py"
```

## Parallel Example: User Story 2

```text
Task: "T033 [US2] Create Feishu message payload contract tests in tests/contract/test_feishu_payload.py"
Task: "T034 [US2] Create Feishu token cache and forced-refresh unit tests in tests/unit/test_feishu_token.py"
Task: "T035 [US2] Create notification suppression and escalation unit tests in tests/unit/test_suppression.py"
Task: "T038 [US2] Implement Feishu post content builder in src/tick_stream/notifier.py"
Task: "T041 [US2] Implement cooldown and suppression-key logic in src/tick_stream/detection/suppression.py"
```

## Parallel Example: User Story 3

```text
Task: "T046 [US3] Create rule profile and watchlist tests in tests/unit/test_config_rules.py"
Task: "T047 [US3] Create market-state filter tests in tests/unit/test_market_filters.py"
Task: "T049 [US3] Create mocked GM live startup tests in tests/integration/test_live_gm_startup.py"
Task: "T052 [US3] Implement market-state filters in src/tick_stream/detection/filters.py"
Task: "T053 [US3] Implement GM SDK initialization and subscription in src/tick_stream/gm_client.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 setup.
2. Complete Phase 2 foundation.
3. Complete Phase 3 User Story 1.
4. Stop and validate replay detection with `tick-stream replay --dry-run-notify`.
5. Review anomaly audit records before adding Feishu delivery.

### Incremental Delivery

1. Setup + Foundational: package, config, models, audit, CLI shell.
2. US1: replayable anomaly detection MVP.
3. US2: structured Feishu notification with mocked and test-recipient validation.
4. US3: config-driven live monitoring and health.
5. Polish: metrics, performance, redaction, and quickstart validation.

### Parallel Team Strategy

1. Complete Setup + Foundational together.
2. Split US1 detectors by file: price, momentum, order book, feature snapshots.
3. Split US2 by payload/token/suppression/retry.
4. Split US3 by config rules, market filters, GM client, and health CLI.
5. Rejoin on quickstart validation and success criteria.

---

## Notes

- Keep the feature alert-only; do not call GM trading APIs.
- Keep real YAML configs with credentials out of version control.
- Every Feishu notification must be explainable from anomaly measurements.
- Tier 2 and Tier 3 research methods should remain audited/backtest-only unless later tasks explicitly promote them to live alerting.
