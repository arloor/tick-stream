from pathlib import Path

from tick_stream.tick_store import partition_tick_file, read_tick_rows


def test_partition_tick_file_writes_date_symbol_partitions_and_merged_file(tmp_path):
    input_path = "tests/fixtures/ticks/sample.jsonl"
    out_dir = tmp_path / "ticks"
    merged_dir = tmp_path / "merged"

    summary = partition_tick_file(input_path, out_dir, merged_dir=merged_dir)

    assert summary.ticks_read == 12
    assert summary.ticks_written == 12
    date_summary = summary.dates["2026-06-25"]
    assert date_summary.symbol_count == 2
    assert (out_dir / "trading_date=2026-06-25" / "SHSE.600519.jsonl").exists()
    assert (out_dir / "trading_date=2026-06-25" / "SZSE.000001.jsonl").exists()
    assert (out_dir / "trading_date=2026-06-25" / "manifest.json").exists()
    assert (merged_dir / "watchlist_2026-06-25.jsonl").exists()


def test_read_tick_rows_accepts_partition_directory(tmp_path):
    partition_tick_file("tests/fixtures/ticks/sample.jsonl", tmp_path / "ticks")

    rows = read_tick_rows(tmp_path / "ticks" / "trading_date=2026-06-25")

    assert len(rows) == 12
    assert rows[0]["event_time"] == "2026-06-25T09:59:59+08:00"
