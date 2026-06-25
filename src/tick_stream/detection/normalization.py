from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from tick_stream.models import OrderBookLevel, OrderBookSnapshot, QualityStatus, TickRecord
from tick_stream.utils import parse_dt, to_float


def _levels(raw: dict[str, Any], side: str) -> list[OrderBookLevel]:
    levels: list[OrderBookLevel] = []
    quote_key_price = "bid_p" if side == "bid" else "ask_p"
    quote_key_volume = "bid_v" if side == "bid" else "ask_v"
    quotes = raw.get("quotes")
    if isinstance(quotes, list):
        for quote in quotes[:5]:
            if not isinstance(quote, dict):
                continue
            price = to_float(quote.get(quote_key_price))
            qty = to_float(quote.get(quote_key_volume))
            if price is not None and price > 0 and qty is not None and qty >= 0:
                levels.append(OrderBookLevel(price=price, quantity=qty))
        if levels:
            return levels
    for i in range(1, 6):
        price = to_float(raw.get(f"{side}_px{i}") or raw.get(f"{side}{i}_price"))
        qty = to_float(raw.get(f"{side}_vol{i}") or raw.get(f"{side}{i}_volume") or raw.get(f"{side}{i}_qty"))
        if price is not None and qty is not None and qty >= 0:
            levels.append(OrderBookLevel(price=price, quantity=qty))
    return levels


def normalize_order_book(raw: dict[str, Any], previous: OrderBookSnapshot | None = None) -> OrderBookSnapshot | None:
    bids = _levels(raw, "bid")
    asks = _levels(raw, "ask")
    if not bids or not asks:
        return None
    total_bid = sum(level.quantity for level in bids)
    total_ask = sum(level.quantity for level in asks)

    def delta(current: list[OrderBookLevel], prior: list[OrderBookLevel]) -> tuple[float, float]:
        curr_qty = sum(level.quantity for level in current)
        prior_qty = sum(level.quantity for level in prior)
        diff = curr_qty - prior_qty
        return (max(diff, 0.0), max(-diff, 0.0))

    bid_added = bid_cancelled = ask_added = ask_cancelled = 0.0
    if previous and previous.depth_available:
        bid_added, bid_cancelled = delta(bids, previous.bid_levels)
        ask_added, ask_cancelled = delta(asks, previous.ask_levels)

    denom = total_bid + total_ask
    imbalance = abs(total_bid - total_ask) / denom if denom > 0 else 0.0
    return OrderBookSnapshot(
        bid_levels=bids,
        ask_levels=asks,
        total_bid_quantity=total_bid,
        total_ask_quantity=total_ask,
        bid_added_quantity=bid_added,
        bid_cancelled_quantity=bid_cancelled,
        ask_added_quantity=ask_added,
        ask_cancelled_quantity=ask_cancelled,
        imbalance_ratio=imbalance,
        depth_available=True,
    )


def normalize_tick(
    raw: dict[str, Any],
    watchlist_symbols: set[str],
    latest_times: dict[str, datetime],
    previous_books: dict[str, OrderBookSnapshot],
) -> TickRecord:
    now = datetime.now(timezone.utc)
    symbol = str(raw.get("symbol") or "").strip()
    event_time = parse_dt(raw.get("event_time") or raw.get("created_at") or raw.get("time"))
    price = to_float(raw.get("last_price") or raw.get("price") or raw.get("current"))
    volume = to_float(raw.get("volume"))
    turnover = to_float(raw.get("turnover"))

    base = {
        "symbol": symbol,
        "event_time": event_time,
        "received_time": now,
        "last_price": price,
        "volume": volume,
        "turnover": turnover,
        "source_sequence": str(raw.get("source_sequence")) if raw.get("source_sequence") is not None else None,
        "raw": raw,
    }
    if not symbol or event_time is None or price is None or price <= 0:
        return TickRecord(**base, quality_status=QualityStatus.MALFORMED, quality_reason="missing symbol, event_time, or positive price")
    if symbol not in watchlist_symbols:
        return TickRecord(**base, quality_status=QualityStatus.IGNORED, quality_reason="symbol outside active watchlist")
    latest = latest_times.get(symbol)
    if latest is not None:
        if event_time < latest:
            return TickRecord(**base, quality_status=QualityStatus.OUT_OF_ORDER, quality_reason="event_time older than latest accepted tick")
        if event_time == latest:
            return TickRecord(**base, quality_status=QualityStatus.DUPLICATE, quality_reason="duplicate event_time for symbol")

    order_book = normalize_order_book(raw, previous_books.get(symbol))
    tick = TickRecord(**base, order_book=order_book, quality_status=QualityStatus.ACCEPTED)
    latest_times[symbol] = event_time
    if order_book is not None:
        previous_books[symbol] = order_book
    return tick
