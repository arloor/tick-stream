from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .config import ConfigError, load_config
from .health import read_health
from .replay import replay_from_files
from .runner import LiveRunner
from .tick_store import partition_tick_file
from .utils import redact, stable_json


def cmd_validate_config(args: argparse.Namespace) -> int:
    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps({"status": "ok", "symbol_count": len(config.watchlist), "rule_profiles": list(config.rules)}, ensure_ascii=False))
    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    try:
        summary = replay_from_files(args.config, args.ticks, dry_run_notify=args.dry_run_notify)
    except ConfigError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 2
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(redact({"error": str(exc)})["error"])}, ensure_ascii=False))
        return 1
    print(json.dumps(summary.as_dict(), ensure_ascii=False))
    return 0


def cmd_partition_ticks(args: argparse.Namespace) -> int:
    dates = set(args.date or []) or None
    try:
        summary = partition_tick_file(args.input, args.out_dir, merged_dir=args.merged_dir, dates=dates)
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(redact({"error": str(exc)})["error"])}, ensure_ascii=False))
        return 1
    print(json.dumps(summary.as_dict(), ensure_ascii=False))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    try:
        config = load_config(args.config)
        runner = LiveRunner(config)
        if args.blocking:
            runner.run_forever()
            return 0
        status = runner.start()
    except ConfigError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 2
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 4
    print(json.dumps(status, ensure_ascii=False))
    return 0


def cmd_health(args: argparse.Namespace) -> int:
    print(json.dumps(read_health(Path(args.audit_dir)), ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tick-stream")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate-config")
    validate.add_argument("--config", required=True)
    validate.set_defaults(func=cmd_validate_config)
    replay = sub.add_parser("replay")
    replay.add_argument("--config", required=True)
    replay.add_argument("--ticks", required=True)
    replay.add_argument("--dry-run-notify", action="store_true")
    replay.set_defaults(func=cmd_replay)
    partition = sub.add_parser("partition-ticks")
    partition.add_argument("--input", required=True, help="source JSONL tick file")
    partition.add_argument("--out-dir", default="var/replay/ticks", help="partitioned tick output root")
    partition.add_argument("--merged-dir", default="var/replay/merged", help="optional merged daily JSONL output root")
    partition.add_argument("--date", action="append", help="optional trading date filter, repeatable, e.g. 2026-06-25")
    partition.set_defaults(func=cmd_partition_ticks)
    run = sub.add_parser("run")
    run.add_argument("--config", required=True)
    run.add_argument("--blocking", action="store_true", help="enter GM SDK event loop and process live ticks")
    run.set_defaults(func=cmd_run)
    health = sub.add_parser("health")
    health.add_argument("--audit-dir", required=True)
    health.set_defaults(func=cmd_health)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
