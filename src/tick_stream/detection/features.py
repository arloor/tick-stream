from __future__ import annotations

from statistics import mean, pstdev

from tick_stream.models import AnomalyRuleSet, FeatureSnapshot, TickRecord
from tick_stream.utils import pct_change


def compute_features(ticks: list[TickRecord], rule: AnomalyRuleSet) -> FeatureSnapshot | None:
    if not ticks or ticks[-1].event_time is None:
        return None
    latest = ticks[-1]
    short = [t for t in ticks if latest.event_time and t.event_time and (latest.event_time - t.event_time).total_seconds() <= rule.price_window_seconds]
    prices = [t.last_price for t in short if t.last_price is not None]
    availability: dict[str, str] = {}
    price_return = pct_change(prices[0], prices[-1]) if len(prices) >= 2 else 0.0
    returns = [pct_change(prices[i - 1], prices[i]) for i in range(1, len(prices)) if prices[i - 1]]
    vol = pstdev(returns) if len(returns) >= 2 else 0.0
    base_returns = [pct_change(ticks[i - 1].last_price or 0, ticks[i].last_price or 0) for i in range(1, len(ticks)) if ticks[i - 1].last_price]
    base_vol = pstdev(base_returns) if len(base_returns) >= 2 else 0.0
    realized_vol_ratio = vol / base_vol if base_vol > 0 else (1.0 if vol == 0 else 99.0)

    volumes = [t.volume or 0.0 for t in short]
    all_volumes = [t.volume or 0.0 for t in ticks]
    volume_burst = (sum(volumes) / max(mean(all_volumes), 1.0)) if all_volumes else 0.0
    book = latest.order_book
    if book and book.depth_available:
        total_add = book.bid_added_quantity + book.ask_added_quantity
        total_cancel = book.bid_cancelled_quantity + book.ask_cancelled_quantity
        order_flow = (book.bid_added_quantity + book.ask_cancelled_quantity) - (book.ask_added_quantity + book.bid_cancelled_quantity)
        cancel_add = total_cancel / max(total_add + total_cancel, 1.0)
        spread = book.ask_levels[0].price - book.bid_levels[0].price if book.ask_levels and book.bid_levels else 0.0
        depth = book.total_bid_quantity + book.total_ask_quantity
        all_depths = [(t.order_book.total_bid_quantity + t.order_book.total_ask_quantity) for t in ticks if t.order_book]
        avg_depth = mean(all_depths) if all_depths else depth
        depth_collapse = max((avg_depth - depth) / avg_depth, 0.0) if avg_depth > 0 else 0.0
        availability.update({k: "available" for k in ("order_flow_imbalance", "queue_imbalance_ratio", "spread_ratio", "depth_collapse_ratio", "cancel_add_ratio")})
    else:
        order_flow = 0.0
        cancel_add = 0.0
        spread = 0.0
        depth_collapse = 0.0
        availability.update({k: "missing_data" for k in ("order_flow_imbalance", "queue_imbalance_ratio", "spread_ratio", "depth_collapse_ratio", "cancel_add_ratio")})
    return FeatureSnapshot(
        symbol=latest.symbol,
        event_time=latest.event_time,
        price_return_short_pct=price_return,
        realized_volatility_ratio=realized_vol_ratio,
        volume_burst_ratio=volume_burst,
        order_flow_imbalance=order_flow,
        queue_imbalance_ratio=book.imbalance_ratio if book else 0.0,
        spread_ratio=spread / latest.last_price if latest.last_price else 0.0,
        depth_collapse_ratio=depth_collapse,
        cancel_add_ratio=cancel_add,
        feature_availability=availability,
    )
