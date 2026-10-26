# Downstream Schema Semantics & False-Negative Flagging Case Study

## 1. Incident Context & Symptoms
In the 6-hour farm lifecycle report (`cron_hotmail_gpm_lifecycle_6h_report.py`):
```text
🔐 TIẾN ĐỘ CHANGE HOTMAIL & BẢO MẬT:
  • Đã Hoàn Tất Đổi Pass (DONE) : 269/1040 (25.9%)
  • Hàng đợi đổi pass (CHANGE_INFO): 2 (Kibe: 0 | Admin: 2)
  • Đang ngâm 7 ngày chờ đổi (WAIT_7D): 425 (Kibe: 51 | Admin: 374)
    - Đã đủ 7 ngày ngâm: 286 (Kibe: 0 | Admin: 286)
    - Thiếu thông tin TikTok: 225 (Kibe: 3 | Admin: 222)
```

**Observation:**
- 286 accounts on Admin cluster had completed the required 7-day soaking period (`WAIT_7D`).
- 225 accounts were blocked from advancing to `CHANGE_INFO` because the aggregator reported `Thiếu thông tin TikTok: 225`.
- As a result, the password change pipeline stalled indefinitely with 0 new throughput.

---

## 2. Root Cause Analysis

### A. The Upstream Intentional Empty Password Pattern
Under the canonical registration skill `tiktok-reg-hotmail-outlook-flow`:
- TikTok accounts registered on physical devices via email OTP / Outlook do not pass through a password entry screen during signup.
- Farm policy strictly prohibits generating or recording fake/speculative passwords into tracking workbooks.
- Therefore, in `taikhoan_dat_v2_updated .xlsx`, Column 3 (`ID` / username) contains valid handles (e.g. `phamphuc19462`, `bobo861293`), while Column 4 (`PASS`) is intentionally `None` / empty.

### B. The Compound Credential Assertion Trap
Downstream components across three separate repositories evaluated platform readiness using:
```python
# batch_gpm_5profiles_supervisor.py (GPM auto)
"has_tiktok": bool(u_name and p_word)
has_tik = bool(info.get("has_tiktok") or (info.get("username") and info.get("password")))

# gpm_change_hotmail_security.py (Hotmail)
has_tiktok = bool(user_val and len(row) > 3 and row[3])

# cron_hotmail_gpm_lifecycle_6h_report.py (Hermes)
has_tiktok = bool(raw.get("has_tiktok") or (raw.get("username") and raw.get("password")))
```

Because `row[3]` / `password` was empty, all 225 accounts evaluated to `has_tiktok = False`.

### C. Ground Truth Verification
Checking the execution source of truth:
```python
wb_safe = openpyxl.load_workbook('taikhoan_run_safe.xlsx')
safe_users = {r[2].lower() for r in wb_safe.active.iter_rows(values_only=True) if r[2]}
# Result: 270/270 accounts without passwords in the master workbook were PRESENT and actively running feed/upload tasks in taikhoan_run_safe.xlsx!
```
The accounts were 100% active and registered; the missing password was an artifact of the OTP signup method.

### D. The Exit Code 0 Silent Skip Trap in Security Runner
In `gpm_change_hotmail_security.py`:
When invoked with `--email <target_email>`, if `find_target_accounts()` rejected the row (due to missing password or missing Column 12 in 10-column Admin workbooks):
```python
if not targets:
    log("[-] Không tìm thấy tài khoản Hotmail mục tiêu phù hợp.")
    return 0  # BUG: Exit code 0 mistaken for successful password change!
```
The supervisor saw exit code 0 and falsely stamped accounts as `DONE` without performing any password reset.

---

## 3. The Multi-Repo Remediation Contract

1. **Uniform Identifier Validation Across 3 Repos:**
   - `batch_gpm_5profiles_supervisor.py`:
     Change to `bool(u_name)` and `bool(info.get("has_tiktok") or info.get("username"))`.
   - `gpm_change_hotmail_security.py`:
     Change filter to `bool(user_val)`.
   - `cron_hotmail_gpm_lifecycle_6h_report.py`:
     Change filter to `bool(raw.get("has_tiktok") or raw.get("username"))`.

2. **Strict Non-Zero Exit on Target Missing:**
   - In `gpm_change_hotmail_security.py`:
     ```python
     if not targets:
         log("[-] Không tìm thấy tài khoản Hotmail mục tiêu phù hợp.")
         return 1 if args.email else 0
     ```

3. **Verification & Sync:**
   - Run focused pytests on all 3 repos.
   - Force sync to runtime: `python -m cron_sync_watchdog --force`.
   - Re-run 6h report live: `Thiếu thông tin TikTok` drops from 225 to 0, and eligible accounts immediately advance to `CHANGE_INFO`.
