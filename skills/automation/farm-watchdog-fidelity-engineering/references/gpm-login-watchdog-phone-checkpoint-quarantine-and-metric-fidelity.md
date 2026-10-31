# GPM Login Watchdog: Phone Checkpoint Quarantine & Metric Fidelity

## 1. Problem Context
In scheduled farm login watchdogs (e.g., rolling Gmail login onto GPM browser profiles across shifts: morning, afternoon, evening):
1. **The Re-login Spam Storm Trap**: When an account loses session or is picked for login and encounters Google's `challenge/iap` (Hard Phone Checkpoint / "unusual activity detected"), if the watchdog merely marks the failure as a transient `PLATFORM` error for the current run without writing to a persistent quarantine ledger (`wrong_password_or_checkpoint`), subsequent shifts will repeatedly re-select the account.
2. **Escalation to Hard Checkpoint**: Even high-trust accounts with 2FA TOTP and linked recovery emails will escalate to hard phone checkpoint if hit with repeated failed login attempts from proxy IPs. Google sends repeated security alert emails to the primary owner email ("bắn mail về mail chính") and suppresses recovery email / TOTP fallback options.
3. **Zombie Cooldown Loop**: Accounts whose 7-day cooldown expired (`retry_after <= today`) that fail upon retry must not remain in the expired state. If `retry_after` is not automatically extended (+14 to +30 days), the watchdog will pick them every single day.
4. **False Zero Metric Trap (`max_proxy 0/cổng`)**: In shift closeout handlers (`if not candidates:`), calling report formatters without passing accumulated `proxy_count` and `failed_details` causes defaults (`proxy_count=None` -> `max_p = 0`) to misreport "max_proxy 0/cổng", misleading operators into thinking proxies were exhausted when in reality accounts failed due to platform checkpoints.

## 2. Core Architecture Invariants

### A. Immediate Thread-Safe Auto-Quarantine
When a worker returns `PHONE_CHECKPOINT` (`challenge/iap` or Google Hard Phone):
- Immediately lock and write to `STATUS_JSON` under `wrong_password_or_checkpoint` with timestamp, machine ID, and explicit reason.
- Never wait for end-of-day reconciliation to exclude the account.

```python
is_checkpoint = "PHONE_CHECKPOINT" in combined
is_cooldown_retry = str(c.get("reason", "")).startswith("cooldown_expired")
if is_checkpoint or is_cooldown_retry:
    with _STATUS_LOCK:
        if STATUS_JSON.exists():
            st_data = json.loads(STATUS_JSON.read_text(encoding="utf-8"))
            if is_checkpoint:
                st_data.setdefault("wrong_password_or_checkpoint", {})[email] = {
                    "mid": mid,
                    "at": datetime.now().isoformat(),
                    "reason": "PHONE_CHECKPOINT"
                }
            if is_cooldown_retry:
                cd = st_data.setdefault("cooldown_7days", {})
                key = next((k for k in cd if k.lower() == email.lower()), email)
                entry = cd.get(key) if isinstance(cd.get(key), dict) else {}
                entry["retry_after"] = (datetime.now(HCMC) + timedelta(days=14)).strftime("%Y-%m-%d")
                entry.setdefault("machine", mid)
                cd[key] = entry
            STATUS_JSON.write_text(json.dumps(st_data, ensure_ascii=False, indent=2), encoding="utf-8")
```

### B. Summary Report Parameter Parity
All exit branches in `main()` (both mid-shift completions and forced closeouts on `not candidates` or timeout) MUST forward:
1. `proxy_count=proxy_count` (reflecting actual port utilization, never defaulting to 0).
2. `failed_details=failed_details` (listing up to 5 failed emails and their categorized fail type: `PLATFORM` vs `SCRIPT`).

### C. Cooldown Auto-Extension on Failed Retry
- Any account retried from a cooldown list (`cooldown_7days`, `cooldown_72h`) that fails again MUST have its `retry_after` bumped forward by at least 14 days.
- Prevent unquarantined zombie accounts from burning daily proxy quotas.
