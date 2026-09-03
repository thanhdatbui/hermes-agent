"""Verify picker entries stay on the 5-minute slot grid (SLOT_GRID_MINUTES).

Run after ANY change to JITTER_MINUTES / BLOCK_ANCHORS / pair-gap logic in
blocks.py (or after re-generating source config). A continuous jitter range
(range(-25, 26)) breaks is_schedulable_interval -> RESERVED_BLOCK_CONFLICT
cron failures (2026-08-20, commit 7053491).

Usage:
  python check_jitter_grid.py <source-config.json> <feed_state.json> <post_state.json> <day> <seed> [owner_id]

Defaults: owner_id=hermes-cron-kibe, worker=owner. Exit 0 = all entries
schedulable; exit 1 = off-grid/out-of-window entries printed.
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta

import os

REPO = os.environ.get("TAADAA_FEED_REPO", "D:/Taadaa/tiktok-luot nuoi acc")
sys.path.insert(0, REPO)

from python_runner.hermes_cron.picker import Picker  # noqa: E402
from python_runner.hermes_cron.models import (  # noqa: E402
    is_schedulable_interval,
    logical_day_for,
    parse_hcm_timestamp,
)
from python_runner.hermes_cron.source_config import (  # noqa: E402
    JsonFeedStateReader,
    JsonPostStateReader,
    SourceConfig,
)


def main(argv: list[str]) -> int:
    if len(argv) < 5:
        print(__doc__)
        return 2
    src, feed_p, post_p, day, seed_s = argv[0], argv[1], argv[2], argv[3], argv[4]
    owner = argv[5] if len(argv) > 5 else "hermes-cron-kibe"
    seed = int(seed_s)
    as_of = parse_hcm_timestamp(f"{day}T06:00:56+07:00")

    source = SourceConfig.from_json(src)
    feed = json.loads(open(feed_p, encoding="utf-8").read())
    post = json.loads(open(post_p, encoding="utf-8").read())
    picker = Picker(source, JsonFeedStateReader(feed), JsonPostStateReader(post))
    captured = picker._capture_snapshot(day, as_of)
    entries, skipped, blocks = picker._entries(day, seed, owner, owner, as_of, captured)
    print(f"entries={len(entries)} skipped={len(skipped)} blocks={len(blocks)}")

    bad: list[tuple] = []
    for e in entries:
        s = parse_hcm_timestamp(e["slot_time"])
        end = parse_hcm_timestamp(e["slot_end"])
        ok = (
            end == s + timedelta(hours=1)
            and logical_day_for(s) == date.fromisoformat(day)
            and is_schedulable_interval(s, end)
        )
        if not ok:
            bad.append((e["machine"], e["account"], e["slot_time"], e["slot_end"]))
    if bad:
        print(f"FAIL: {len(bad)}/{len(entries)} entries off-grid or out-of-window")
        for machine, account, slot, end in bad[:20]:
            s = parse_hcm_timestamp(slot)
            print(f"  m{machine} {account} {slot} {end} minute%5={s.minute % 5}")
        return 1
    print(f"OK: all {len(entries)} entries on 5-min grid and inside window")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
