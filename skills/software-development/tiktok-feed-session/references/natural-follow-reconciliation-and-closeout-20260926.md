# Natural Follow Reconciliation & Closeout

## Contract
Natural/organic follows must enter Web reconciliation even when cross-follow success is empty. Target the union of cross-follow machines and machines with `natural_follows > 0`.

For each target:

```text
expected_delta = cross_follow_count + natural_follow_count
web_delta      = latest_following - baseline_following
difference     = web_delta - expected_delta
```

- `difference == 0`: report `KHỚP`.
- Nonzero: report signed `Lệch ±N`.
- Missing baseline or latest snapshot: report `thiếu baseline/latest snapshot | UNPROVEN`.
- Never fabricate `web +0` or call the automation failed without valid snapshots.
- Keep cross and natural counts separately labeled.

## Regression minimum
Use offline mocked tests covering:
1. natural-only targets when cross-follow success is empty;
2. baseline 100 → latest 101 with natural +1 reports `KHỚP`;
3. missing baseline/latest reports `UNPROVEN`, not `Lệch -1`.

## Closeout
A focused test is not the final closeout gate. After the patch and focused verification, run:

```text
python D:/Taadaa/tools/closeout_gate.py --repo <repo> --base HEAD~1 --json-output
```

Only treat the change as closeout-approved when the reviewer returns `Verdict: APPROVED` and score >=85. Pre-existing unrelated working-tree changes are scope evidence; do not blindly revert them.
