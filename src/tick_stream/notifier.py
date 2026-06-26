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

    def __init__(self, config: dict[str, Any], http_post: HttpPost | None = None, symbol_names: dict[str, str] | None = None) -> None:
        self.config = config
        self.http_post = http_post or requests.post
        self.symbol_names = symbol_names or {}
        self.cache = FeishuTokenCache(refresh_margin_seconds=int(config.get("token_refresh_margin_seconds", 300)))

    def build_message(self, events: list[AnomalyEvent]) -> NotificationMessage:
        if not events:
            raise ValueError("cannot build notification without events")
        primary = events[0]
        symbol_label = _symbol_label(primary.symbol, self.symbol_names.get(primary.symbol))
        title = f"A股异动告警 | {symbol_label} | {_severity_label(primary.severity)}"
        lines = [
            f"类型：{' + '.join(_anomaly_label(e.anomaly_type) for e in events)}",
            f"方向：{_direction_label(primary.direction)}",
            f"触发时间：{primary.trigger_time.isoformat()}",
            f"最新价：{primary.trigger_price}",
            f"等级：{_severity_label(primary.severity)}",
        ]
        for event in events:
            lines.append(f"{_anomaly_label(event.anomaly_type)}：{_format_measurement(event)}")
        lines.append(f"原因：{_format_reason(primary)}")
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


def _symbol_label(symbol: str, name: str | None) -> str:
    return f"{symbol} {name}" if name else symbol


def _anomaly_label(anomaly_type: Any) -> str:
    return {
        "price_jump": "价格跳变",
        "momentum_spike": "动量异常",
        "orderbook_liquidity": "盘口流动性异常",
    }.get(str(anomaly_type), str(anomaly_type))


def _direction_label(direction: Any) -> str:
    return {"up": "向上", "down": "向下", "neutral": "中性"}.get(str(direction), str(direction))


def _severity_label(severity: Any) -> str:
    return {"warning": "提醒", "high": "高", "critical": "严重"}.get(str(severity), str(severity))


def _format_measurement(event: AnomalyEvent) -> str:
    parts = []
    for key, value in event.measurement.items():
        parts.append(f"{_measurement_label(key)}={_format_measurement_value(key, value)}")
    return "；".join(parts) if parts else "无额外测量值"


def _measurement_label(key: str) -> str:
    return {
        "price_return_pct": "价格涨跌幅",
        "window_seconds": "观察窗口",
        "momentum_z": "动量Z分数",
        "impulse_seconds": "脉冲窗口",
        "impulse_return_pct": "脉冲涨跌幅",
        "velocity_pct_per_second": "速度",
        "nonzero_baseline_samples": "有效基线样本",
        "alert_aggregation_window_seconds": "告警聚合窗口",
        "cancel_add_ratio": "撤挂压力",
        "queue_imbalance_ratio": "买卖盘失衡",
        "order_flow_imbalance": "盘口净压力",
    }.get(key, key)


def _format_measurement_value(key: str, value: Any) -> str:
    if not isinstance(value, (int, float)):
        return str(value)
    if key in {"price_return_pct", "impulse_return_pct"}:
        return f"{value:.2f}%"
    if key == "velocity_pct_per_second":
        return f"{value:.3f}%/秒"
    if key in {"cancel_add_ratio", "queue_imbalance_ratio"}:
        return f"{value * 100:.2f}%"
    if key in {"window_seconds", "impulse_seconds", "alert_aggregation_window_seconds"}:
        return f"{int(value)}秒"
    if key == "nonzero_baseline_samples":
        return f"{int(value)}个"
    if key == "order_flow_imbalance":
        return f"{value:,.0f}"
    return f"{value:.2f}"


def _format_reason(event: AnomalyEvent) -> str:
    measurement = event.measurement
    anomaly_type = str(event.anomaly_type)
    if anomaly_type == "price_jump":
        window = measurement.get("window_seconds")
        ret = measurement.get("price_return_pct")
        if isinstance(window, (int, float)) and isinstance(ret, (int, float)):
            return f"{int(window)}秒窗口价格涨跌幅为 {ret:.2f}%，达到价格跳变条件。"
    if anomaly_type == "momentum_spike":
        z = measurement.get("momentum_z")
        impulse = measurement.get("impulse_return_pct")
        seconds = measurement.get("impulse_seconds")
        velocity = measurement.get("velocity_pct_per_second")
        samples = measurement.get("nonzero_baseline_samples")
        pieces = []
        if isinstance(seconds, (int, float)):
            pieces.append(f"{int(seconds)}秒脉冲窗口")
        if isinstance(impulse, (int, float)):
            pieces.append(f"脉冲涨跌幅 {impulse:.2f}%")
        if isinstance(z, (int, float)):
            pieces.append(f"动量Z分数 {z:.2f}")
        if isinstance(velocity, (int, float)):
            pieces.append(f"速度 {velocity:.3f}%/秒")
        if isinstance(samples, (int, float)):
            pieces.append(f"有效基线样本 {int(samples)} 个")
        if pieces:
            return "，".join(pieces) + "，达到动量异常条件。"
    if anomaly_type == "orderbook_liquidity":
        cancel = measurement.get("cancel_add_ratio")
        imbalance = measurement.get("queue_imbalance_ratio")
        parts = ["盘口连续出现撤单/挂单压力或买卖盘失衡"]
        if isinstance(cancel, (int, float)):
            parts.append(f"撤挂压力 {cancel * 100:.2f}%")
        if isinstance(imbalance, (int, float)):
            parts.append(f"买卖盘失衡 {imbalance * 100:.2f}%")
        return "，".join(parts) + "。"
    return "触发已配置的异动规则。"
