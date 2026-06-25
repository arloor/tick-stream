# Feature Specification: Tick Anomaly Alerts

**Feature Branch**: `no-active-git-branch`

**Created**: 2026-06-25

**Status**: Draft

**Input**: User description: "我需要写一个量化程序，订阅标的池的股票的 tick 数据，识别股价异动和动量异常；如果发现有异常则通过飞书的 openapi 发送结构化的通知"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 监控标的池 tick 异常 (Priority: P1)

作为量化研究员或交易监控人员，我希望系统持续订阅标的池内股票的 tick 数据，并在价格、动量或盘口流动性显著偏离时识别异常事件，以便及时发现潜在交易机会或风险。

**Why this priority**: 没有可靠的异常识别，就无法产生有价值的通知；这是整个功能的核心价值。

**Independent Test**: 准备一个包含多只股票的标的池和一组可回放 tick 数据，其中包含正常行情、价格跳变、动量突增、大额挂单突变和短窗撤单场景；验证系统只为满足异常规则的 tick 序列产生异常事件。

**Acceptance Scenarios**:

1. **Given** 标的池包含股票 A 且 A 的连续 tick 价格在设定观察窗口内超过价格异动阈值，**When** 系统处理这些 tick，**Then** 系统记录一条价格异动异常事件，事件包含股票、触发时间、触发价格、变化幅度和异常等级。
2. **Given** 标的池包含股票 B 且 B 的短期动量相对基准窗口明显增强，**When** 系统处理这些 tick，**Then** 系统记录一条动量异常事件，事件包含股票、触发时间、动量指标、参考窗口和异常等级。
3. **Given** 标的池包含股票 C 且 C 的买卖盘挂单量在短时间内出现持续大额撤单或单侧挂单量异常堆积，**When** 系统处理这些 tick，**Then** 系统记录一条盘口流动性异常事件，事件包含方向、撤单或挂单变化量、观察窗口和异常等级。
4. **Given** 某只股票不在当前标的池内，**When** 系统收到该股票的 tick 数据，**Then** 系统不会为该股票产生异常事件。

---

### User Story 2 - 发送结构化飞书通知 (Priority: P2)

作为交易监控人员，我希望每个异常事件都能以结构化格式发送到指定飞书接收方，以便快速判断异常类型、严重程度、相关标的和下一步关注点。

**Why this priority**: 异常事件只有及时、清晰地送达使用者，才可以转化为行动。

**Independent Test**: 使用一组已触发异常的事件样本，验证每条需要通知的异常都产生一条结构化通知，并且通知字段完整、可读、便于筛选。

**Acceptance Scenarios**:

1. **Given** 系统产生一条高等级价格异动事件，**When** 通知发送流程执行，**Then** 飞书接收方收到一条结构化通知，至少包含异常类型、股票代码、股票名称、触发时间、最新价、变化幅度、异常等级和简短原因。
2. **Given** 同一股票在短时间内重复触发相同异常，**When** 通知发送流程执行，**Then** 系统按照去重或聚合规则避免刷屏，同时保留最新异常状态。
3. **Given** 通知发送失败，**When** 失败可恢复，**Then** 系统重试发送并记录最终发送状态。

---

### User Story 3 - 管理监控范围和告警规则 (Priority: P3)

作为量化研究员，我希望可以调整标的池、异常阈值、观察窗口和通知策略，以便适配不同市场阶段、不同股票流动性和不同风险偏好。

**Why this priority**: 市场状态会变化，固定规则容易产生过多噪声或漏报，需要可调规则支持长期使用。

**Independent Test**: 修改标的池和规则配置后，使用同一组 tick 回放数据验证监控范围与异常触发结果按新规则变化。

**Acceptance Scenarios**:

1. **Given** 标的池新增股票 C，**When** 新配置生效后系统收到 C 的 tick 数据，**Then** 系统开始对 C 执行异常识别。
2. **Given** 某类异常阈值被调高，**When** 系统处理相同 tick 序列，**Then** 低于新阈值的波动不再触发通知。
3. **Given** 某只股票被暂停监控，**When** 系统收到该股票 tick 数据，**Then** 系统不产生异常事件和通知。

### Edge Cases

- Tick 数据乱序、重复或缺少关键字段时，系统应跳过无效数据并记录原因，不应产生误导性异常。
- Tick 数据缺少盘口档位或盘口量字段时，系统应继续执行价格和动量识别，并明确标记盘口异常识别不可用。
- 标的池为空时，系统应保持运行状态并明确显示当前没有监控标的。
- 行情源短暂中断或恢复后，系统应标识数据缺口，并避免把恢复后的首个 tick 直接误判为异常。
- 股票停牌、涨跌停、集合竞价或开收盘附近的特殊行情阶段，应按业务规则降低误报。
- 同一股票同时满足价格异动、动量异常和盘口异常时，系统应能合并或关联事件，避免使用者收到割裂的信息。
- 通知接收方配置缺失或不可用时，系统应保留异常事件和发送失败状态，便于补发或排查。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST maintain a configurable stock watchlist that determines which symbols are monitored.
- **FR-002**: System MUST ingest tick data for all active watchlist symbols during configured monitoring periods.
- **FR-003**: System MUST ignore or quarantine tick records that are outside the watchlist, malformed, duplicated, or older than the latest accepted tick for the same symbol.
- **FR-004**: System MUST evaluate each monitored symbol against configurable price anomaly rules, including at minimum rapid price change over a short observation window.
- **FR-005**: System MUST evaluate each monitored symbol against configurable momentum anomaly rules, including at minimum short-term momentum compared with a baseline window.
- **FR-006**: System MUST evaluate order book liquidity anomalies when盘口 fields are available, including at minimum short-window large order additions, cancellations, and buy/sell side imbalance.
- **FR-007**: System MUST assign every detected anomaly an anomaly type, severity level, trigger reason, trigger timestamp, symbol, latest price, and relevant measurement values.
- **FR-008**: System MUST allow盘口异常 to either create standalone alerts or increase severity of simultaneous price and momentum anomalies according to configurable rules.
- **FR-009**: System MUST suppress, aggregate, or update repeated notifications for the same symbol and anomaly type within a configurable cooldown window.
- **FR-010**: System MUST send structured notifications for reportable anomalies to configured Feishu recipients.
- **FR-011**: System MUST track notification delivery status for each reportable anomaly, including pending, sent, failed, and retried states.
- **FR-012**: System MUST retry recoverable notification failures according to a bounded retry policy and preserve failures for operator review.
- **FR-013**: Users MUST be able to change watchlist membership, anomaly thresholds, observation windows, severity mapping, monitoring periods, and notification recipients without changing the anomaly event history.
- **FR-014**: System MUST keep an audit trail of accepted tick processing outcomes, detected anomalies, suppressed duplicate alerts, and notification attempts for later review.
- **FR-015**: System MUST expose enough runtime health information for users to know whether tick ingestion, anomaly detection, and notifications are operating normally.
- **FR-016**: System MUST clearly separate monitoring and notification from trade execution; this feature MUST NOT place orders or recommend mandatory trading actions.
- **FR-017**: System MUST keep sensitive notification credentials and recipient parameters out of source-controlled files and runtime logs.

### Key Entities *(include if feature involves data)*

- **Watchlist Symbol**: A stock selected for monitoring, including symbol, display name, market, active status, and optional per-symbol rule overrides.
- **Tick Record**: A market data update for a symbol, including event time, received time, latest price, volume or turnover when available,盘口 fields when available, and source quality status.
- **Order Book Snapshot**: The available bid/ask price and quantity levels carried by a tick, used to measure short-window additions, cancellations, and side imbalance.
- **Anomaly Rule**: A business rule defining anomaly type, threshold, observation window, baseline window, severity mapping, active monitoring period, and whether盘口异常 can create standalone alerts or only enhance related alerts.
- **Anomaly Event**: A detected abnormal market movement, including symbol, anomaly type, severity, trigger values, trigger reason, lifecycle status, and notification relationship.
- **Notification Message**: A structured alert prepared for Feishu recipients, including content fields, recipient target, delivery status, retry count, and failure reason when applicable.
- **Monitoring Health State**: The current operating condition of ingestion, detection, and notification flows, including last successful data time and active error states.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: During replay tests with labeled tick samples, at least 95% of labeled price anomaly scenarios are detected and at least 90% of normal scenarios do not produce false alerts.
- **SC-002**: During replay tests with labeled tick samples, at least 90% of labeled momentum anomaly scenarios are detected and at least 90% of normal momentum scenarios do not produce false alerts.
- **SC-003**: During replay tests with labeled盘口 samples, at least 85% of sustained order book liquidity anomaly scenarios are detected and at least 90% of normal盘口 fluctuations do not produce standalone alerts.
- **SC-004**: For 500 actively monitored symbols under normal market data volume, 95% of reportable anomalies are visible to recipients within 5 seconds of the triggering tick being accepted.
- **SC-005**: In a one-hour normal-market simulation, duplicate notifications for the same symbol and anomaly type are reduced by at least 80% compared with sending every raw trigger.
- **SC-006**: 100% of generated notifications contain the required structured fields: anomaly type, symbol, symbol name when available, trigger time, latest price, measured price/momentum/order-book value, severity, and reason.
- **SC-007**: Operators can update the watchlist and anomaly rule settings and verify the changed monitoring behavior within 2 minutes.
- **SC-008**: After a recoverable notification outage lasting up to 5 minutes, at least 99% of pending reportable anomaly notifications either send successfully after recovery or remain visible with a clear failed status.

## Assumptions

- The initial users are quantitative researchers, trading monitors, or operations staff who need intraday anomaly awareness rather than automated order execution.
- The monitored market is stock tick data, and the first version focuses on symbols explicitly included in the watchlist.
- Price anomaly, momentum anomaly, and盘口异常 thresholds will have sensible global defaults and may later be overridden per symbol or group.
- 盘口异常 is only evaluated when the tick feed exposes sufficient bid/ask price and quantity fields; otherwise this detector is reported as unavailable without blocking other detectors.
- Feishu is the required notification destination for the first version; other notification channels are outside the initial scope.
- Feishu credentials, recipient identifiers, and notification tuning parameters are supplied outside source-controlled files.
- The feature stores enough recent tick context to evaluate short observation windows, but long-term market research storage is outside the initial scope.
- This feature produces alerts for human review and does not provide investment advice or guarantee profitable decisions.
