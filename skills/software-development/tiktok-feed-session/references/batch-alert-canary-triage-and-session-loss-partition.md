# Batch alert canary triage and session-loss partition

## Scope
Use for wide TikTok feed-session alerts (especially 1–80 machines) with P0 login/account-switcher messages. This is a historical-artifact workflow; it does not authorize fleet-wide intervention.

## Evidence sequence
1. Run the mandatory canary inspection first: `python D:/Taadaa/tools/inspect_machine.py <N>` for the named canary. Treat its output as current physical state only; a later `LauncherActivity`/Sleep state may be teardown residue, not the batch root cause.
2. Resolve the exact run artifact and read its `run_manifest.json`. `multi_machine_summary` is a `list[dict]`; select records by `item["machine"]`. Prefer manifest counts and per-machine `stop_reason` over alert prose when they differ.
3. For each P0 machine, read the machine `summary.txt` and `log.jsonl` around the decision, then open the exact same-attempt `ui.xml` and `screen.png`. Missing/mismatched artifacts are `UNPROVEN`.
4. Reconcile expected usernames/slots against `D:/Taadaa/data/tiktok_tracker.db` (`farm_account_info`, keyed by `may` and `tik`) before any login, logout, or account mutation. Never treat an account-switcher failure alone as proof that an existing nick was logged out.

## Partition rules
- **Session-lost/login:** UI evidence contains login/account markers at the identity guard (for example `Đăng nhập`, `Tạo tài khoản`, phone/email login), and the exact run records `manual-needed:login`. Report the target account and stop for bounded recovery.
- **Slot-fill/expected missing:** Switcher sheet is genuinely open and lists existing accounts plus `Thêm tài khoản`, but the expected target is absent. Existing accounts are preserved; this is a missing target slot, not proof of session loss.
- **Anchor/layout drift:** Profile XML proves an active username/profile, but switcher sheet never opens after the known anchor tap and retries. Classify as selector/navigation/layout incompatibility, not account loss. Prefer a semantic menu/settings fallback in code; do not hand-tap as the completion.

## Reporting
Always separate `Confirmed`, `Excluded`, and `Unproven`. Include exact artifact paths, serial, expected username/slot, verbatim UI/log evidence, and a cache-busted copy of any screenshot sent to the user. Do not claim a canary or fleet reopen succeeded without a fresh post-action artifact.