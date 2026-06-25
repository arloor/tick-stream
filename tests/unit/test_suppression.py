from datetime import datetime, timezone

from tick_stream.detection.suppression import SuppressionEngine
from tick_stream.models import AnomalyEvent, AnomalyType, Direction, Severity


def event(severity=Severity.WARNING):
    return AnomalyEvent("evt", "SHSE.600519", AnomalyType.PRICE_JUMP, Direction.UP, severity, datetime.now(timezone.utc), 100, {}, "test", suppression_key="k")


def test_suppresses_duplicate_but_allows_escalation():
    engine = SuppressionEngine(cooldown_seconds=180)
    assert not engine.decide(event()).suppressed
    assert engine.decide(event()).suppressed
    assert not engine.decide(event(Severity.HIGH)).suppressed
