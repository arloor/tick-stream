# Feishu Message Contract

## Authentication

Use `tenant_access_token` in the request header:

```http
Authorization: Bearer {tenant_access_token}
Content-Type: application/json; charset=utf-8
```

The token is acquired with Feishu app credentials read from the local YAML configuration and refreshed before expiry. Token values, app secrets, recipient identifiers, and raw configuration dumps must not be written to source-controlled files or audit logs.

## Send Message Request

Endpoint:

```http
POST https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={receive_id_type}
```

Supported `receive_id_type` values for this feature:

- `chat_id`
- `open_id`
- `user_id`
- `union_id`
- `email`

Request body:

```json
{
  "receive_id": "oc_xxxxxxxxxxxxxxxxx",
  "msg_type": "post",
  "content": "{\"zh_cn\":{\"title\":\"A股异动告警 | SHSE.600104 | HIGH\",\"content\":[[{\"tag\":\"text\",\"text\":\"类型：price_jump+momentum_spike+orderbook_liquidity\"}],[{\"tag\":\"text\",\"text\":\"方向：up\"}],[{\"tag\":\"text\",\"text\":\"触发时间：2026-06-25T10:30:00+08:00\"}],[{\"tag\":\"text\",\"text\":\"最新价：10.36\"}],[{\"tag\":\"text\",\"text\":\"等级：high\"}],[{\"tag\":\"text\",\"text\":\"price_jump: {\\\"price_return_pct\\\": 2.64, \\\"window_seconds\\\": 30}\"}],[{\"tag\":\"text\",\"text\":\"momentum_spike: {\\\"momentum_z\\\": 6.2, \\\"impulse_return_pct\\\": 1.1}\"}],[{\"tag\":\"text\",\"text\":\"orderbook_liquidity: {\\\"cancel_add_ratio\\\": 0.66, \\\"queue_imbalance_ratio\\\": 0.91}\"}],[{\"tag\":\"text\",\"text\":\"原因：30秒窗口内价格、动量和盘口信号共振\"}]]}}"
}
```

Content rules:

- `content` must be a JSON-serialized string, not an object.
- For `im/v1/messages` with `msg_type=post`, the serialized object uses language keys such as `zh_cn` at the top level.
- Title must include anomaly category, symbol/name, and severity.
- Body must include anomaly type, direction, trigger time, latest price, measured value, severity, and reason.
- A single message may include multiple reportable anomaly events for the same symbol when they fall inside the configured alert aggregation window.
- When multiple signal types are present, the body must include one measurement line per signal type.
- When order book signals contributed to the alert, body must include cancellation/addition/imbalance measurements.
- Message text must not include GM token, Feishu app secret, tenant token, recipient IDs, raw configuration dumps, or raw stack traces.

## Success Response Handling

Expected successful response shape:

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "message_id": "om_xxxxxxxxxxxxxxxxx"
  }
}
```

Contract behavior:

- `code == 0` marks the notification as `sent`.
- Store `message_id` when present.
- Write a notification audit record without token values.

## Failure Response Handling

Example failure shape:

```json
{
  "code": 99991663,
  "msg": "tenant access token invalid"
}
```

Contract behavior:

- Token-related errors trigger one forced token refresh before retrying the message.
- Recoverable network errors and 5xx responses use bounded retry backoff.
- 4xx request validation errors are marked `failed` without infinite retry.
- Every failed attempt writes a notification audit record with sanitized error details.

## References

- Feishu message create: https://open.feishu.cn/document/server-docs/im-v1/message/create?lang=zh-CN
- Feishu tenant token: https://open.feishu.cn/document/server-docs/authentication-management/access-token/tenant_access_token_internal
