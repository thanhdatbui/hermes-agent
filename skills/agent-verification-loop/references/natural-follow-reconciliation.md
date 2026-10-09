# Snapshot-based natural-follow reconciliation

## Contract

For each crawled account, keep cross-follow and natural-follow counts distinct:

```text
expected_delta = cross_follow_count + natural_follow_count
web_delta      = latest_following - baseline_following
difference     = web_delta - expected_delta
```

Use the newest snapshot at or before `session_start_iso` as the baseline when
that session timestamp is supplied. Do not silently replace a missing session
baseline with an unrelated recent pair. If the function's established rule is
explicitly a different baseline rule, preserve that rule and document it in the
test.

A valid comparison must show an explicit zero-difference `KHỚP` result or a
signed `Lệch <difference>` result. If baseline or latest is missing, emit:

```text
thiếu baseline/latest snapshot | UNPROVEN
```

Do not emit a fabricated `web +0`, a first-snapshot pseudo-comparison, or a
negative mismatch caused only by missing evidence.

## Focused offline regression recipe

- Mock the workbook reader so machine slots resolve to deterministic usernames.
- Mock the tracker subprocess and assert its `--usernames` argv includes
  natural-only machines; this verifies crawling, not server success.
- Use a temporary SQLite database with a `snapshots` table.
- Give one natural-only account a baseline of 100 before the session and latest
  101 after it, with natural count +1; assert the line contains separate
  `chéo 0, tự nhiên 1` labels and `KHỚP`.
- Give another target a latest snapshot but no valid baseline; assert
  `UNPROVEN`/`thiếu baseline` and assert the complete output does not contain
  `Lệch -1`.
- Keep the test under the user's time budget and run only the changed focused
  test node.

## Review pitfalls

- A natural-only target is easy to omit if the target set is derived only from
  cross-follow success. Build the target set as cross-follow successes union
  machines with positive natural-follow counts.
- Summing natural counts into a generic `script báo` label hides the contract.
  Preserve both category labels even when one count is zero.
- A tracker subprocess returning normally is not proof that TikTok/server state
  changed; only valid snapshots support a reconciliation claim.
- A missing baseline is unknown evidence, not a zero baseline and not a
  mismatch. Keep aggregate “valid comparison” counters from treating UNPROVEN
  rows as valid deltas.
