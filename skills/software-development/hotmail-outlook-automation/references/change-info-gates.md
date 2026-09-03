# change-info pipeline gates (live snapshot 2026-08-05)

## Gate flow in `load_hotmail_targets()` (flows/hotmail_change_info.py)

For each Hotmail-domain row in `gmail_clean_v2.xlsx` sheet `Gmail Accounts`:

1. `MACHINE_MISSING` — no `số máy`
2. `PASSWORD_MISSING` — no `pass mail`
3. `DUPLICATE_EMAIL` — same email appears in >1 row
4. `LOGIN_DATE_MISSING_OR_INVALID` — `ngày tạo`/created cell empty or unparseable
5. `LOGIN_DATE_IN_FUTURE` — created date > today
6. `LOGIN_TOO_RECENT` — age < `MIN_LOGIN_AGE_DAYS` (7, constant at line 92)
7. `LOGIN_DATE_UNVERIFIED` — no login-evidence artifact for email+machine in `.ai-runs`
8. `LOGIN_DATE_CONFLICT` — latest evidence date != workbook created date

Eligible only when gate_failure is None. Then `select_targets()` filters by
`email`, `machine`, or `all_eligible`.

## Evidence collection

`collect_login_evidence(root=.ai-runs)` scans `.ai-runs/**` for JSON records
with email + machine + a login date, where status ∈ success/already_signed_in/
recovered_success/verified_success AND (verified=True OR exact_mailbox+inbox_marker).
Records under paths containing `hotmail-change-info` or `security` are excluded
(not login provenance).

## Farm snapshot 2026-08-05

```
total hotmail rows: 31
gate breakdown: {LOGIN_DATE_UNVERIFIED: 24, LOGIN_DATE_MISSING_OR_INVALID: 4,
                 LOGIN_TOO_RECENT: 2, PASSWORD_MISSING: 1}
```

Machine 1 example:
- row 3 `lipseybaroua@hotmail.com` login_date=2026-02-27 age=159 → LOGIN_DATE_UNVERIFIED (evidence=0)
- row 4 `GinnyHanstein8045@hotmail.com` login_date=2026-08-02 age=3 → LOGIN_TOO_RECENT (evidence=0)

→ No Hotmail row could run change-password/logout live without first creating
login evidence or relaxing `MIN_LOGIN_AGE_DAYS`. Always re-run the gate check
before promising a live run — the workbook and evidence set change daily.

## CLI

```
python scripts/change_info_hotmail.py <serial> --machine <N> --target <safe-label> --live
  [--steps change-password,setup-2fa,logout-devices,remove-getnada] [--recovery-email ...]
```

- `--live` required (else parser.error)
- `--target` is a safe label, never a password
- Pipeline stops at first step whose status is not SUCCESS/RECOVERED_SUCCESS;
  exit 0 only if ALL steps succeeded.
