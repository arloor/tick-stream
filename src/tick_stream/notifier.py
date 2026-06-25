from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from typing import Any, Callable
from uuid import uuid4

import requests

from .models import AnomalyEvent, DeliveryStatus, FeishuTokenCache, NotificationMessage
from .utils import redact


HttpPost = Callable[..., Any]


class FeishuNotifier:
    token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    message_url = "https://open.feishu.cn/open-apis/im/v1/messages"

    def __init__(self, config: dict[str, Any], http_post: HttpPost | None = None) -> None:
        self.config = config
        self.http_post = http_post or requests.post
        self.cache = FeishuTokenCache(refresh_margin_seconds=int(config.get("token_refresh_margin_seconds", 300)))

    def build_message(self, events: list[AnomalyEvent]) -> NotificationMessage:
        if not events:
            raise ValueError("cannot build notification without events")
        primary = events[0]
        title = f"A股异动告警 | {primary.symbol} | {primary.severity.value.upper()}"
        lines = [
            f"类型：{'+'.join(e.anomaly_type.value for e in events)}",
            f"方向：{primary.direction.value}",
            f"触发时间：{primary.trigger_time.isoformat()}",
            f"最新价：{primary.trigger_price}",
            f"等级：{primary.severity.value}",
        ]
        for event in events:
            lines.append(f"{event.anomaly_type.value}: {json.dumps(event.measurement, ensure_ascii=False)}")
        lines.append(f"原因：{primary.reason}")
        content = {
            "zh_cn": {
                "title": title,
                "content": [[{"tag": "text", "text": line}] for line in lines],
            }
        }
        return NotificationMessage(
            notification_id=f"ntf_{uuid4().hex}",
            event_ids=[event.event_id for event in events],
            receive_id_type=self.config["receive_id_type"],
            receive_id=self.config["receive_id"],
            msg_type="post",
            content=content,
        )

    def _token_valid(self) -> bool:
        if not self.cache.tenant_access_token or not self.cache.expires_at:
            return False
        return datetime.now(timezone.utc) + timedelta(seconds=self.cache.refresh_margin_seconds) < self.cache.expires_at

    def get_token(self, force_refresh: bool = False) -> str:
        if not force_refresh and self._token_valid():
            return self.cache.tenant_access_token or ""
        resp = self.http_post(
            self.token_url,
            json={"app_id": self.config["app_id"], "app_secret": self.config["app_secret"]},
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=10,
        )
        data = _json_response(resp)
        if data.get("code", 0) != 0:
            self.cache.last_refresh_status = "failed"
            raise RuntimeError(f"feishu token failure: {redact(data)}")
        token = data.get("tenant_access_token")
        if not token:
            raise RuntimeError("feishu token response missing tenant_access_token")
        expire = int(data.get("expire", 7200))
        self.cache.tenant_access_token = token
        self.cache.expires_at = datetime.now(timezone.utc) + timedelta(seconds=expire)
        self.cache.last_refresh_status = "success"
        return token

    def send(self, message: NotificationMessage) -> NotificationMessage:
        backoff = list(self.config.get("retry_backoff_seconds", [1, 5, 30]))
        max_attempts = int(self.config.get("max_attempts", 3))
        force_refresh = False
        for attempt in range(1, max_attempts + 1):
            message.attempt_count = attempt
            message.last_attempt_at = datetime.now(timezone.utc)
            token = self.get_token(force_refresh=force_refresh)
            resp = self.http_post(
                self.message_url,
                params={"receive_id_type": message.receive_id_type},
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"},
                json={"receive_id": message.receive_id, "msg_type": message.msg_type, "content": json.dumps(message.content, ensure_ascii=False)},
                timeout=10,
            )
            data = _json_response(resp)
            code = data.get("code")
            if code == 0:
                message.delivery_status = DeliveryStatus.SENT
                message.feishu_message_id = (data.get("data") or {}).get("message_id")
                return message
            message.delivery_status = DeliveryStatus.FAILED
            message.failure_code = code
            message.failure_reason = data.get("msg", "unknown feishu failure")
            if "token" in str(message.failure_reason).lower() and not force_refresh:
                force_refresh = True
                continue
            if attempt >= max_attempts or (isinstance(code, int) and 400 <= code < 500):
                return message
            _ = backoff[min(attempt - 1, len(backoff) - 1)] if backoff else 0
        return message


def _json_response(resp: Any) -> dict[str, Any]:
    if isinstance(resp, dict):
        return resp
    if hasattr(resp, "json"):
        return resp.json()
    return json.loads(getattr(resp, "text", "{}"))
