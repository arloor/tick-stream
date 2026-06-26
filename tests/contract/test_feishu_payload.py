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
        symbol_names={"SHSE.600519": "贵州茅台"},
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
    assert "SHSE.600519 贵州茅台" in content
    assert "价格跳变" in content
    assert "secret" not in content


def test_feishu_momentum_payload_uses_chinese_labels_and_reason():
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
        symbol_names={"SHSE.688808": "科创材料"},
    )
    event = AnomalyEvent(
        event_id="evt",
        symbol="SHSE.688808",
        anomaly_type=AnomalyType.MOMENTUM_SPIKE,
        direction=Direction.UP,
        severity=Severity.CRITICAL,
        trigger_time=datetime.now(timezone.utc),
        trigger_price=10.5,
        measurement={
            "momentum_z": 99.0,
            "impulse_seconds": 10,
            "impulse_return_pct": 2.745098039215698,
            "velocity_pct_per_second": 0.30501089324618863,
            "nonzero_baseline_samples": 11,
            "alert_aggregation_window_seconds": 30,
        },
        reason="momentum z-score 99.00 exceeds 6.50 with 2.75% impulse return",
    )
    message = notifier.build_message([event])
    content = json.dumps(message.content, ensure_ascii=False)
    assert "SHSE.688808 科创材料" in content
    assert "动量异常" in content
    assert "动量Z分数=99.00" in content
    assert "脉冲涨跌幅=2.75%" in content
    assert "原因：10秒脉冲窗口" in content
    assert "momentum_spike" not in content
    assert "momentum z-score" not in content
