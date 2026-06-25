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
  "content": "{\"post\":{\"zh_cn\":{\"title\":\"A股异动告警 | 贵州茅台 600519.SH | HIGH\",\"content\":[[{\"tag\":\"text\",\"text\":\"类型：价格异动 + 盘口增强\\n\"},{\"tag\":\"text\",\"text\":\"方向：上涨\\n\"},{\"tag\":\"text\",\"text\":\"触发时间：2026-06-25 10:30:00\\n\"},{\"tag\":\"text\",\"text\":\"最新价：1688.00\\n\"},{\"tag\":\"text\",\"text\":\"30秒涨跌幅：2.64%\\n\"},{\"tag\":\"text\",\"text\":\"动量z-score：4.20\\n\"},{\"tag\":\"text\",\"text\":\"盘口：卖一至卖五撤单比例42%，买盘占比76%\\n\"},{\"tag\":\"text\",\"text\":\"原因：30秒价格变化超过2.5%，动量显著高于3分钟基准，盘口出现持续单侧流动性变化\"}]]}}}"
}
```

Content rules:

- `content` must be a JSON-serialized string, not an object.
- Title must include anomaly category, symbol/name, and severity.
- Body must include anomaly type, direction, trigger time, latest price, measured value, severity, and reason.
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
