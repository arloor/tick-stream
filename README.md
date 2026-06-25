# Tick Stream

Tick Stream 是一个 Python tick 监控服务，用于订阅 A 股标的池行情，识别价格、动量和盘口异动，并通过飞书 OpenAPI 发送结构化告警。

## 功能

- 从本地 YAML 文件加载标的池、GM、飞书和异动规则配置。
- 通过 GM SDK 订阅启用状态的标的。
- 检测短窗口价格跳变、稳健动量 z-score 异常、盘口撤单/挂单压力、买卖盘失衡、价差压力和深度塌陷。
- 按标的和异常类型做冷却抑制，避免重复告警刷屏。
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
25 passed
```

已用真实 GM 终端验证 25 个 A 股/指数标的当前行情可返回，并用 `--blocking` 模式进入 GM 事件循环接收真实 tick。飞书 `tenant_access_token` 获取和结构化 `post` 消息发送也已真实跑通。
