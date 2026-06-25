from datetime import datetime, timezone

from tick_stream.models import AnomalyEvent, AnomalyType, Direction, Severity
from tick_stream.notifier import FeishuNotifier


def test_notification_retries_after_token_error():
    calls = []

    def post(url, **kwargs):
        calls.append(url)
        if "tenant_access_token" in url:
            return {"code": 0, "tenant_access_token": "token", "expire": 7200}
        if len([u for u in calls if "messages" in u]) == 1:
            return {"code": 99991663, "msg": "tenant access token invalid"}
        return {"code": 0, "msg": "success", "data": {"message_id": "om"}}

    notifier = FeishuNotifier({"app_id": "cli", "app_secret": "secret", "receive_id_type": "chat_id", "receive_id": "oc", "token_refresh_margin_seconds": 300, "max_attempts": 3, "retry_backoff_seconds": [0, 0, 0]}, http_post=post)
    event = AnomalyEvent("evt", "SHSE.600519", AnomalyType.PRICE_JUMP, Direction.UP, Severity.HIGH, datetime.now(timezone.utc), 100, {}, "test")
    sent = notifier.send(notifier.build_message([event]))
    assert sent.delivery_status.value == "sent"
    assert sent.feishu_message_id == "om"
