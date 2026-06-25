# Research: Tick Anomaly Alerts

## Decision: Python 3.12 with GM SDK for tick ingestion

Use Python 3.12 and the `gm` SDK as the market data integration. The live process will initialize GM credentials and terminal address from operator-provided configuration, subscribe to watchlist symbols, and route every accepted `on_tick` event into the detection engine.

**Rationale**: The user explicitly requested Python and pointed to `GM-API.md`, which states Python 3.12 and GM SDK are the prepared tools. `GM-API.md` lists `subscribe`, `context.data`, `run`, `set_token`, `set_serv_addr`, and related GM APIs as the expected integration surface.

**Alternatives considered**:

- Polling `current` snapshots: simpler, but misses tick-level movement and adds latency.
- Direct internal GM runtime APIs: useful for advanced gateway work, but unnecessary for a first alert-only strategy and more brittle than the public strategy flow.

## Decision: Alert-only strategy boundary

The implementation will not call GM trading APIs such as order placement, cancellation, cash, or positions. It will only use market data and symbol metadata APIs needed for subscription, filtering, and display.

**Rationale**: The spec requires clear separation from trade execution. Keeping this boundary sharp reduces operational risk and simplifies testing.

**Alternatives considered**:

- Include optional trading context in alerts: rejected for v1 because it expands scope and creates account-permission concerns.

## Decision: Deterministic anomaly detection rules

Use three independently testable detectors:

1. **Price jump detector**: For each symbol, maintain a rolling short window, default 30 seconds. Trigger when the latest valid price changes by at least the configured absolute return threshold, default 1.5%, against the earliest valid tick in the window, or exceeds a robust baseline threshold derived from recent short-window returns.
2. **Momentum detector**: Compute short-term velocity over a default 10-second impulse window and compare it with a default 3-minute baseline using a robust z-score based on median and median absolute deviation. Trigger when absolute z-score is at least 3.0 and there are enough ticks in both windows.
3. **Order book liquidity detector**: When bid/ask depth fields are available, maintain a default 30-second order book window. Trigger only when sustained large order additions, large cancellations, or buy/sell side imbalance exceeds configured thresholds for at least two consecutive accepted ticks. By default, order book anomalies can create standalone alerts only at `high` or `critical` severity; lower-severity order book signals enhance simultaneous price or momentum events.

Severity defaults:

- `warning`: price move >= 1.5%, momentum z-score >= 3.0, or order book signal qualifies as an enhancer
- `high`: price move >= 2.5%, momentum z-score >= 4.0, cancellation/addition ratio >= 35%, or one-side book imbalance >= 70%
- `critical`: price move >= 3.5%, momentum z-score >= 5.0, cancellation/addition ratio >= 50%, or one-side book imbalance >= 85%

**Rationale**: These rules are transparent, reproducible under replay, robust to outliers, and usable before labeled production data exists. The combination catches obvious jumps, gradual acceleration, and suspicious liquidity shifts while avoiding alerts from one-tick order book flicker.

**Alternatives considered**:

- Machine learning anomaly detection: rejected for v1 because it needs historical labeling, monitoring, and explainability work.
- Fixed percent-only rules: too noisy across stocks with different liquidity and volatility.
- Volume-only momentum: not reliable when tick volume fields are absent or inconsistent.
- Treat every large cancellation as an alert: rejected because normal A-share order book updates can be bursty; sustained confirmation and severity gating are needed.

## Decision: Expanded anomaly method catalogue and phased adoption

Keep v1 alert decisions deterministic, but compute and audit a richer set of interpretable microstructure features so thresholds can be calibrated from replay data and later promoted into more advanced detectors. The detector set should be grouped into four tiers.

### Tier 1: Adopt in v1

These methods are transparent, fast, explainable in Feishu messages, and testable with small fixtures.

- **Short-window return shock**: Compare latest price with the earliest accepted tick in a short window and with a robust recent-return baseline.
- **Momentum acceleration**: Compare short impulse velocity against a longer baseline using robust z-score.
- **Realized volatility burst**: Track short-window realized volatility and alert when it jumps relative to the same symbol's intraday baseline. This catches violent oscillation even when net return is small.
- **Order flow imbalance (OFI)**: Track net pressure from best bid/ask quantity changes, limit order additions, market-order-like consumption, and cancellations. Research on order book events finds short-horizon price changes are more robustly related to order flow imbalance than to raw trade volume.
- **Queue imbalance**: Track bid-side versus ask-side displayed quantity at top levels. Extreme imbalance is a pressure signal, but should require persistence and market-state filters.
- **Depth/spread stress**: Track sudden spread widening, top-of-book depth collapse, and recovery failure. Treat as liquidity risk and severity enhancer.
- **Cancellation/addition pressure**: Track large cancellations or order additions by side and level. Require at least two consecutive ticks or a minimum duration before standalone alerting.
- **Volume/turnover burst**: Track current tick or rolling turnover versus an intraday baseline. Use as an enhancer unless paired with price, momentum, or order book pressure.

### Tier 2: Add after enough replay fixtures exist

These methods are still interpretable, but need more data calibration.

- **Aggressor-side trade imbalance**: Infer buyer-initiated versus seller-initiated trades using quote/tick rules when the feed does not directly provide trade direction. Classic trade classification literature highlights quote/trade timing issues and unclassifiable inside-spread trades, so the signal should be treated as probabilistic rather than absolute.
- **VPIN-style flow toxicity**: Bucket trades by volume and estimate buy/sell volume imbalance and trade intensity. Useful as a risk/volatility warning, but it requires reliable trade classification or bulk volume classification and enough volume history.
- **CUSUM or Shiryaev-Roberts change detection**: Maintain sequential change scores for return, volatility, OFI, and trade intensity. Good for structural breaks that are smaller than hard thresholds but persistent.
- **Bayesian online changepoint detection**: Estimate the probability that the current regime has changed. Useful for combining multiple features, but heavier than simple thresholds.
- **Relative strength residual**: Compare symbol return/momentum with index, sector, or watchlist peer baseline. Alert when the symbol is abnormal after removing market-wide movement.
- **Lead-lag confirmation**: For related symbols or sector leaders, raise severity if the target moves ahead of peers with supporting order book pressure; lower severity when the whole sector moves together.

### Tier 3: Research/backtest only for now

These can be valuable, but should not drive live Feishu alerts until replay evidence proves low false positives.

- **Isolation Forest / Local Outlier Factor / One-Class SVM**: Train on feature vectors such as return, volatility, volume burst, OFI, queue imbalance, cancellation pressure, spread, and depth. scikit-learn distinguishes outlier detection from novelty detection; the latter requires a cleaner normal training set, which is hard during market regime shifts.
- **Online Half-Space Trees**: Online isolation-style scoring for streaming data. River documents Half-Space Trees as an online variant of isolation forests, useful when anomalies are spread out, but weaker when anomalies cluster in windows.
- **Matrix Profile / discord detection**: Useful in offline replay to discover unusual subsequences and validate whether deterministic rules miss recurring shapes. Online variants exist, but v1 should use it for calibration, not live alerting.
- **Hawkes/intensity models**: Model self-exciting trade/order intensity. Potentially good for quote stuffing or event clustering, but overkill without high-quality event timestamps and calibration.
- **Deep sequence models**: LSTM/Transformer autoencoders or order-book forecasting models. Rejected for v1 because they need substantial clean historical data, explainability work, and model monitoring.

### Tier 4: Context filters and alert hygiene

These are not standalone anomaly methods, but they strongly reduce false positives.

- **Session-aware thresholds**: Use stricter rules near open, close, auction windows, after halts/suspensions, and around limit-up/limit-down states.
- **Liquidity bucket thresholds**: Separate thresholds for high-liquidity, mid-liquidity, and thinly traded symbols.
- **Minimum evidence score**: Require at least two independent signals for `high` or `critical` unless one signal is extremely large.
- **Cooldown with escalation**: Continue suppressing duplicates, but allow severity escalation when new evidence appears.
- **Explainability requirement**: Every alert must include the top contributing signals, not only a model score.

**Rationale**: A deterministic v1 gives clear operator trust and straightforward tests. Computing a richer feature layer from day one creates a bridge to more advanced methods without letting black-box scores spray alerts into Feishu. Order book event research supports OFI and depth-aware signals; VPIN research supports volume-imbalance toxicity as a volatility/risk measure; online changepoint methods are suitable for regime shifts; standard anomaly libraries are useful once normal training windows and replay labels exist.

**Adoption recommendation**:

- Implement Tier 1 in v1.
- Record Tier 2 feature values in audit logs where data is available, but gate live alerts behind explicit config.
- Keep Tier 3 as offline research until replay benchmarks show improved precision/recall over deterministic rules.
- Treat Tier 4 as mandatory alert hygiene.

**Alternatives considered**:

- Jump straight to ML anomaly scoring: rejected because it weakens alert explainability and needs labeled or at least clean normal data.
- Use only price/momentum: too narrow; it misses liquidity and pressure anomalies that may precede price movement.
- Use every computed feature as a standalone alert: rejected because correlated features would create duplicate/noisy notifications.

## Decision: Tick quality and market-state filtering

Before detection, normalize ticks and reject records with missing symbol, non-positive price, duplicated timestamp/price identity, or event time older than the latest accepted tick for the symbol. Normalize available bid/ask depth into an order book snapshot; when depth is missing, mark the order book detector unavailable while continuing price and momentum detection. Suppress detection during explicitly configured ignored sessions and treat data gaps as baseline resets. Use daily metadata when available to flag suspension, limit-up, limit-down, and special opening/closing windows.

**Rationale**: Tick feeds can contain duplicates, out-of-order records, stale updates, and market microstructure effects. Filtering these before detection reduces false alerts.

**Alternatives considered**:

- Run detectors on raw ticks: rejected because it would produce noisy and hard-to-debug alerts.

## Decision: Cooldown plus aggregation for repeated alerts

Use a suppression key of `(symbol, anomaly_type, direction)`. During the default 180-second cooldown, suppress duplicate alerts unless severity increases. If severity increases, send an update notification that includes the previous severity and latest measurement. If order book anomalies enhance a price or momentum event, group them under the same notification instead of sending separate messages.

**Rationale**: This satisfies the spec's duplicate reduction target while still escalating meaningful changes.

**Alternatives considered**:

- Send every trigger: rejected due to alert storms.
- One alert per symbol per day: too coarse and likely to hide later important moves.

## Decision: Feishu message creation with tenant_access_token

Use Feishu message creation API `POST /open-apis/im/v1/messages` with query parameter `receive_id_type`, request header `Authorization: Bearer {tenant_access_token}`, and a JSON body containing `receive_id`, `msg_type`, and `content`. Use `msg_type=post` for structured rich text messages in v1.

Acquire `tenant_access_token` from the self-built app token endpoint with `app_id` and `app_secret`, cache it, and refresh it before expiry. The official token endpoint returns an expiry value; published documentation describes a two-hour validity window for self-built app tenant tokens.

**Rationale**: The user explicitly required `tenant_access_token` authentication. The official Feishu documentation lists `tenant_access_token` as a supported credential for sending messages and documents the message create endpoint. `post` messages are easier to validate and less complex than interactive cards while still structured enough for alert triage.

**Alternatives considered**:

- Incoming webhook robot: rejected because the user specifically requested OpenAPI and tenant token auth.
- Interactive card as v1 default: powerful, but larger schema and unnecessary for initial structured alert delivery.

## Decision: Configuration and secret handling

Use a YAML config file for watchlist, detector thresholds, GM connection settings, Feishu parameters, audit paths, and retry policy. GM token, Feishu app ID, Feishu app secret, recipient type, recipient ID, token refresh margin, max attempts, and retry backoff are loaded directly from YAML. Source-controlled examples must use placeholders only; real credential-bearing YAML files must remain local and uncommitted.

**Rationale**: The project already uses YAML for operator configuration, so reading values directly keeps one configuration source. Keeping real credential-bearing YAML files out of version control still reduces accidental disclosure and makes local/live deployments explicit.

**Alternatives considered**:

- Hardcode values from `GM-API.md` or Feishu app settings: rejected because credentials and recipients should not be duplicated into source.
- A second configuration indirection layer: rejected by latest project decision because YAML should be the single configuration source.
- Prompt interactively for secrets on every run: poor fit for unattended market monitoring.

## Decision: JSONL audit trail

Write append-only JSONL records for accepted ticks summary, anomaly events, suppression decisions, notification attempts, and health snapshots.

**Rationale**: JSONL is simple, replayable, diff-friendly, and sufficient for v1. It also supports post-incident review without introducing database operations.

**Alternatives considered**:

- SQLite: useful once query and retention needs grow, but unnecessary for the initial plan.
- No persistence: rejected because the spec requires auditability and failed notification review.

## References

- Local: [GM-API.md](../../GM-API.md)
- Feishu message create: https://open.feishu.cn/document/server-docs/im-v1/message/create?lang=zh-CN
- Feishu tenant token: https://open.feishu.cn/document/server-docs/authentication-management/access-token/tenant_access_token_internal
- Cont, Kukanov, Stoikov, "The Price Impact of Order Book Events": https://arxiv.org/abs/1011.6402
- Lee and Ready, "Inferring Trade Direction from Intraday Data": https://doi.org/10.1111/j.1540-6261.1991.tb02683.x
- Easley, Lopez de Prado, O'Hara, "Flow Toxicity and Liquidity in a High Frequency World": https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1695596
- Adams and MacKay, "Bayesian Online Changepoint Detection": https://arxiv.org/abs/0710.3742
- scikit-learn novelty and outlier detection documentation: https://scikit-learn.org/stable/modules/outlier_detection.html
- River HalfSpaceTrees documentation: https://riverml.xyz/0.11.1/api/anomaly/HalfSpaceTrees/
- UCR Matrix Profile research page: https://www.cs.ucr.edu/~eamonn/MatrixProfile.html
