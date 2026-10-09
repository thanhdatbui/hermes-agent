# Parasite Account Guard & Anti-Hijack Policy (Taadaa Farm)

## 1. What is a "Parasite Account" (Nick Ký Sinh)?
On the Taadaa phone farm, accounts are assigned to specific physical devices / machine indices (`stt`) as tracked in canonical Excel workbooks:
- `D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx` (Sheet: `Tài Khoản`, Column 0: STT, Column 2: TikTok ID, Column 5: Gmail)
- `D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx` & `admin/taikhoan_run_safe.xlsx` (Sheet: `Accounts`, Column 0: STT, Column 2: TikTok ID)

A **parasite account** violation occurs when a consumer runner on machine $X$ (e.g. STT 201) operates on, logs into, or registers an account that is already owned by machine $Y$ (e.g. STT 22).

## 2. Enforcement Mechanism (`parasite_guard.py`)
`parasite_guard.py` enforces machine-account binding before state-mutating actions (login, registration):

```python
from parasite_guard import assert_account_machine_binding, ParasiteAccountViolation

try:
    assert_account_machine_binding(target_stt, account_identifier, allow_override=False, operator_reason="")
except ParasiteAccountViolation as pv:
    # Fail-closed: do not continue operation on the foreign account
    ...
```

### Audit & Telemetry Persistence
Every check generates structured telemetry:
`[telemetry:parasite-guard] action={action} target_stt={target_stt} account={account} owner_stt={owner_stt} status={status} reason={reason}`
and persists a JSONL entry to `D:/Taadaa/runtime/audit/parasite_guard_audit.jsonl` (or an injected `audit_file` path for isolated testing).

## 3. Anti-Hijack in Registration Flow (`social_reg_v1.py`)
In registration (`fill_email_and_next`):
- When an email returns `registered` or `registered_otp` (already has a TikTok account):
  - **ABORT** this candidate email immediately (`continue`), emit UI XML diagnostic, and press Back (`keyevent 4`).
  - **DO NOT** fall through to the login flow on the current machine! Hijacking into login on an arbitrary registered email risks attaching another machine's account onto the current device.
