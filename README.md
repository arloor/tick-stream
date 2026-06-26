# Tick Stream

Tick Stream 是一个 Python tick 监控服务，用于订阅 A 股标的池行情，识别价格、动量和盘口异动，并通过飞书 OpenAPI 发送结构化告警。

## 功能

- 从本地 YAML 文件加载标的池、GM、飞书和异动规则配置。
- 通过 GM SDK 订阅启用状态的标的。
- 检测短窗口价格跳变、稳健动量 z-score 异常、盘口撤单/挂单压力、买卖盘失衡、价差压力和深度塌陷。
- 先记录候选异常，再按成交活跃度、实际价格位移和盘口确认条件筛选飞书通知，避免盘口或动量噪音刷屏。
- 按标的和异常类型做聚合与冷却抑制，避免重复告警刷屏。
- 使用 `tenant_access_token` 鉴权，通过飞书 `post` 消息发送结构化通知。
- 写入追加式 JSONL 审计记录，并对 token、secret、receive_id 等敏感字段做脱敏。

本服务只做监控和告警，不调用 GM 交易下单接口。

## 本地安装

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install gm -U -i https://mirrors.aliyun.com/pypi/simple/
python -m pip install -e .
```

如果只运行测试，也可以先安装测试和运行时依赖：

```bash
python -m pip install pytest PyYAML jsonschema requests
python -m pytest -q
```

## 配置

复制示例配置到本地配置文件，然后替换占位值：

```bash
cp config/watchlist.example.yml config/watchlist.local.yml
```

不要提交包含真实凭证或接收人 ID 的配置文件。`.gitignore` 已忽略 `config/*.local.yml`、`config/*.secret.yml` 和 `var/` 下的审计/回放产物。

必须配置的字段：

- `gm.token`、`gm.serv_addr`、`gm.strategy_id`
- `feishu.app_id`、`feishu.app_secret`、`feishu.receive_id_type`、`feishu.receive_id`
- `watchlist` 中启用的监听标的
- `rules` 中的规则 profile
- `audit.dir` 审计目录

所有参数都从 YAML 读取；GM 和飞书凭证不需要环境变量。

## 常用命令

校验配置：

```bash
tick-stream validate-config --config config/watchlist.local.yml
```

回放 fixture tick，但不发送飞书消息：

```bash
tick-stream replay --config config/watchlist.local.yml --ticks tests/fixtures/ticks/sample.jsonl --dry-run-notify
```

切分历史 tick 文件，生成按日期/标的分片和单日合并文件：

```bash
tick-stream partition-ticks \
  --input var/replay/history_ticks_20260624_20260626.jsonl \
  --out-dir var/replay/ticks \
  --merged-dir var/replay/merged
```

回放单日合并文件：

```bash
tick-stream replay --config config/watchlist.local.yml --ticks var/replay/merged/watchlist_2026-06-25.jsonl --dry-run-notify
```

也可以直接回放某个日期分区目录，程序会按事件时间排序：

```bash
tick-stream replay --config config/watchlist.local.yml --ticks var/replay/ticks/trading_date=2026-06-25 --dry-run-notify
```

回放一条告警并真实发送飞书消息：

```bash
tick-stream replay --config config/watchlist.local.yml --ticks tests/fixtures/ticks/single-alert.jsonl
```

启动真实 GM tick 监听：

```bash
tick-stream run --config config/watchlist.local.yml --blocking
```

只做启动检查，不进入 GM 事件循环：

```bash
tick-stream run --config config/watchlist.local.yml
```

查看最近健康状态：

```bash
tick-stream health --audit-dir var/audit
```

## 飞书配置

创建飞书/Lark 自建应用，并开通机器人/消息发送相关权限。通知模块会通过以下接口获取 `tenant_access_token`：

```text
https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal
```

随后调用 `im/v1/messages` 发送消息，请求包含：

- `Authorization: Bearer <tenant_access_token>`
- YAML 中配置的 `receive_id_type`
- `msg_type: post`
- 中文结构化告警内容：标的、异常等级、异常类型、原因、测量值和触发时间

注意：实测 `im/v1/messages` 的 `post` 消息内容需要使用顶层 `zh_cn` 结构，不能包一层 `post.zh_cn`，否则飞书会返回 `230001 invalid message content`。

生产群推送前，建议先使用专门的测试接收人验证权限和消息格式。

## GM 前置条件

- 按 `GM-API.md` 安装 GM SDK。
- 保持 GM 终端运行，并确保 `gm.serv_addr` 可访问。
- 确认 token 和 strategy ID 有效。
- 启动时只会订阅 `watchlist` 中 `active: true` 的标的。

## 已验证情况

当前测试命令：

```bash
.venv/bin/python -m pytest -q
```

预期结果：

```text
32 passed
```

已用真实 GM 终端验证 25 个 A 股/指数标的当前行情可返回，并用 `--blocking` 模式进入 GM 事件循环接收真实 tick。飞书 `tenant_access_token` 获取和结构化 `post` 消息发送也已真实跑通。

## 历史回放分析

最新回放配置：`var/replay/watchlist_history_20260624_20260626_v6.yml`。

回放数据来自 GM `history(..., frequency="tick")`，覆盖 `2026-06-24` 至 `2026-06-26` 的 25 个 A 股/指数标的。该回放使用 `--dry-run-notify`，不会真实发送飞书。

| 指标 | 数量 |
| --- | ---: |
| 原始 tick | `329,673` |
| 接受 tick | `315,577` |
| 候选异常 | `5,911` |
| dry-run 飞书通知 | `90` |
| 实际发送 | `0` |

候选异常构成：

| 类型 | 候选异常数 |
| --- | ---: |
| `orderbook_liquidity` | `5,376` |
| `momentum_spike` | `532` |
| `price_jump` | `3` |

最终通知构成：

| 类型 | 通知内事件数 |
| --- | ---: |
| `momentum_spike` | `73` |
| `orderbook_liquidity` | `17` |
| `price_jump` | `1` |

通知分组里 `89` 条是单事件通知，`1` 条聚合了 2 个事件。被过滤的事件里，`5,706` 个属于 `not reportable`，`25` 个属于冷却期重复。

通知最多的标的：

| 标的 | 通知内事件数 |
| --- | ---: |
| `SHSE.688808` | `25` |
| `SHSE.603268` | `13` |
| `SHSE.603186` | `13` |
| `SHSE.603005` | `10` |
| `SZSE.300433` | `5` |

回放结论：

- `volume_burst_ratio` 已使用 GM `last_volume`/`last_amount` 计算，不再是空值或恒为 0。
- 动量通知不再只看 z-score；需要足够大的实际 impulse、成交活跃度放大，或“盘口压力 + 最低成交活跃度”确认。
- 单独盘口通知需要同时满足严重等级、短窗价格变化和成交活跃度放大；大部分盘口抖动只进入审计，不推飞书。
- 同一标的同一主异常类型在 `opposite_direction_guard_seconds` 内反向触发时，会按剧烈震荡/whipsaw 处理，只写 suppression 审计，不再作为普通反向告警单独推送。
- 通知量从 v4 的 `1,182` 条压到 v6 的 `90` 条，主要减少的是缺少成交/价格确认的盘口和动量噪音。

## Tick 文件组织

历史 tick 建议同时保留两种形态：

```text
var/replay/ticks/
└── trading_date=2026-06-25/
    ├── SHSE.000001.jsonl
    ├── SHSE.600104.jsonl
    └── manifest.json

var/replay/merged/
└── watchlist_2026-06-25.jsonl
```

- `trading_date=.../SYMBOL.jsonl`：用于单票排查、profile 校准和局部重放。
- `manifest.json`：记录当天 symbol 数、tick 数、文件路径和首末 tick 时间。
- `merged/watchlist_YYYY-MM-DD.jsonl`：用于全标的市场回放，保持事件时间顺序，适合检查告警总量和联动上下文。
