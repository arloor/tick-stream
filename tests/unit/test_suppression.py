from datetime import datetime, timedelta, timezone

from tick_stream.detection.suppression import SuppressionEngine
from tick_stream.models import AnomalyEvent, AnomalyType, Direction, Severity


def event(severity=Severity.WARNING, direction=Direction.UP, trigger_time=None, key=None):
    trigger_time = trigger_time or datetime.now(timezone.utc)
    key = key or f"SHSE.600519:alert:momentum_spike:{direction.value}"
    return AnomalyEvent("evt", "SHSE.600519", AnomalyType.MOMENTUM_SPIKE, direction, severity, trigger_time, 100, {}, "test", suppression_key=key)


def test_suppresses_duplicate_but_allows_escalation():
    engine = SuppressionEngine(cooldown_seconds=180)
    assert not engine.decide(event()).suppressed
    assert engine.decide(event()).suppressed
    assert not engine.decide(event(Severity.HIGH)).suppressed


def test_suppresses_opposite_direction_inside_guard_window():
    engine = SuppressionEngine()
    now = datetime.now(timezone.utc)
    assert not engine.decide(event(direction=Direction.DOWN, trigger_time=now), cooldown_seconds=180, opposite_direction_guard_seconds=90).suppressed
    decision = engine.decide(event(direction=Direction.UP, trigger_time=now + timedelta(seconds=30)), cooldown_seconds=180, opposite_direction_guard_seconds=90)
    assert decision.suppressed
    assert decision.reason == "opposite direction whipsaw guard"


def test_allows_opposite_direction_after_guard_window():
    engine = SuppressionEngine()
    now = datetime.now(timezone.utc)
    assert not engine.decide(event(direction=Direction.DOWN, trigger_time=now), cooldown_seconds=180, opposite_direction_guard_seconds=90).suppressed
    decision = engine.decide(event(direction=Direction.UP, trigger_time=now + timedelta(seconds=91)), cooldown_seconds=180, opposite_direction_guard_seconds=90)
    assert not decision.suppressed
