# Watchdog Cron Registration & Upload SLA Monitoring Discipline

## 1. The "Orphaned Script" Trap (Code Committed But Scheduler Omitted)
When a user requests a watchdog, alert filter, or recurring audit (e.g. "cần có 1 cơ chế đối soát nick lâu ngày k đăng video"):
- Developers and agents frequently build the audit script (`audit_stale_upload_accounts.py`), write unit tests, pass closeout gate, and commit to Git.
- **The Pitfall:** The task is marked "done" without registering the script into the scheduler (`cronjob action=create`). Weeks later, the user finds out the alert never ran ("sao đéo thấy chạy").
- **Rule:** A watchdog or audit mechanism is **INCOMPLETE** until it is registered in `hermes cronjob`, verified in `cronjob action=list`, and validated via a test tick.

### Complete Watchdog Delivery Checklist:
1. **Core Logic:** Standalone Python script with clear CLI options (`--days`, `--critical-days`, `--dry-run`, `--json`).
2. **Headless Cron Wrapper:** A dedicated wrapper or entrypoint that respects Hermes `no_agent=True` stdout semantics:
   - Output 100% empty (`0 bytes`) when fleet is healthy or eligible count is 0.
   - Output concise Telegram Markdown summary only when anomalies/stale items occur.
   - Cleanly exit with code `0` when delivering report text (do NOT use `sys.exit(1)` for business alerts, as non-zero exit codes trigger scheduler crash errors instead of clean message delivery).
3. **Scheduler Registration:** Call `cronjob(action='create', name=..., schedule=..., script=..., deliver=...)`.
4. **Verification:** Inspect `next_run_at` via `cronjob action=list` and test run with `cronjob action=run`.

---

## 2. Inventory Depletion vs. Account Activity SLA (Distinct Watchdog Scopes)
Do NOT confuse or conflate the two distinct monitoring scopes:

| Monitoring Scope | What It Measures | Target Entity | Mechanism / Script |
| :--- | :--- | :--- | :--- |
| **Media / Render Inventory** | Does file `{N+1}.mp4` exist in folder? | Video folder / render pipeline | Checked during feed session preflight (`feed_session_watchdog.py`: "Hết video / Cần cào"). |
| **Upload Freshness SLA** | Has account posted a new video within SLA ($\le 7$d / $\le 14$d)? | Account / device / physical phone | Checked against snapshot history & workbook drift (`audit_stale_upload_accounts.py`). |

When user asks "tại sao nick dừng đăng video", checking render folders alone is insufficient. An account may have 40+ rendered videos in its folder, but still be stalled due to:
- Physical phone disconnection (`device not found` / USB drop / offline ADB).
- Account drift / desynchronization (nick died and was replaced on device but workbook still mapped to old username, or vice-versa).
- Schedule starve (machine prioritizes Slot 1/Row 1, while secondary slots Tik 2..8 are starved).
- Silent skip anti-patterns in upload runner.

---

## 3. Audit Script Exit Code Invariant for Hermes Cron (`no_agent=True`)
- `sys.exit(0)` with **non-empty stdout**: Delivered to Telegram as a regular message (standard alert report).
- `sys.exit(0)` with **empty stdout**: Completely silent tick (normal watchdog heartbeat, no spam).
- `sys.exit(non-zero)`: Triggers Hermes failure handler (`⚠️ Cron '<name>' failed: exit code N`), prepending an error header and treating the execution as a software crash.
- **Invariant:** Reserve non-zero exit codes strictly for unhandled infrastructure crashes (e.g. database file corrupt, unexpected unhandled exception). Any formatted report of stale accounts or anomalies must exit `0` so the payload delivers cleanly as intended.
