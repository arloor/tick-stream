import json
from datetime import datetime, timezone

from tick_stream.models import AnomalyEvent, AnomalyType, Direction, Severity
from tick_stream.notifier import FeishuNotifier


def test_feishu_post_payload_contract():
    notifier = FeishuNotifier(
        {
            "app_id": "cli",
            "app_secret": "secret",
            "receive_id_type": "chat_id",
            "receive_id": "oc",
            "token_refresh_margin_seconds": 300,
            "max_attempts": 3,
            "retry_backoff_seconds": [0],
        },
        http_post=lambda *a, **k: {"code": 0, "tenant_access_token": "t", "expire": 7200},
    )
    event = AnomalyEvent(
        event_id="evt",
        symbol="SHSE.600519",
        anomaly_type=AnomalyType.PRICE_JUMP,
        direction=Direction.UP,
        severity=Severity.HIGH,
        trigger_time=datetime.now(timezone.utc),
        trigger_price=101.0,
        measurement={"price_return_pct": 2.0},
        reason="test",
    )
    message = notifier.build_message([event])
    content = json.dumps(message.content, ensure_ascii=False)
    assert message.msg_type == "post"
    assert "zh_cn" in message.content
    assert "post" not in message.content
    assert "SHSE.600519" in content
    assert "secret" not in content
