# Account-ready-only verify mode + canonical 3-API switcher (2026-08-14, tiktok-follow)

## Canonical account-switcher flow (core ≥ 0.4.44)

The old consumer pattern was 2 calls (`open_profile_root` + `open_switcher`) and
then a **consumer-side identity tap** (`_identity_matches` opened Profile and
compared handles). Core ≥ 0.4.44 added a complete switch+verify flow; the
consumer default must be exactly:

```python
from automation_core.tiktok.account_switcher import (
    open_account_switcher, select_exact_account, verify_selected_account)

open_account_switcher(adapter)                       # profile root + switcher, one flow
post_xml = select_exact_account(adapter, expected)   # taps the exact account row; returns post-select XML
verify_selected_account(adapter, expected, xml_text=post_xml)  # raises AccountSwitcherError on mismatch
```

Key facts (verified by reading the 0.4.44 wheel source, not docs):

- `select_exact_account` returns the post-selection UI XML; if the sheet is
  still open after selection it backs out and re-dumps. It does NOT verify the
  selected account — that is `verify_selected_account`'s job.
- `verify_selected_account(adapter, account, *, xml_text=None)` accepts the
  post-select XML, so the consumer needs **no second dump and no second tap**.
  It raises `AccountSwitcherError` (`SWITCHER_STILL_OPEN` / `ACCOUNT_VERIFY_MISMATCH`)
  when verification fails — the consumer just catches and maps to failure.
- `open_account_switcher(adapter, *, profile_attempts=3, switcher_attempts=2,
  load_attempts=3, settle_seconds=0.35)` is the single entrypoint; it already
  handles subpage exit + profile confirmation.
- Expected handle is normalized `.lstrip("@")`; `select_exact_account` /
  `verify_selected_account` strip `@` internally, so pass the bare workbook ID.
- Do not monkeypatch-in fake `open_account_switcher`/`select_exact_account`
  that return XML without ALSO honoring the real `verify_selected_account` —
  the test then never proves the selection produced a verifiable profile.

### RED test design (real verify, fake open/select)

Monkeypatch only the navigation entrypoints; let the REAL `verify_selected_account`
run against a fake post-select XML that passes core's own checks:

```python
real_verify = as_module.verify_selected_account
monkeypatch.setattr(as_module, "open_account_switcher", fake_open)   # returns switcher XML
monkeypatch.setattr(as_module, "select_exact_account", fake_select)  # returns profile XML
monkeypatch.setattr(as_module, "verify_selected_account",
                    lambda ad, acc, *, xml_text=None: real_verify(ad, acc, xml_text=xml_text))
```

A minimal passable profile XML needs: a selected bottom Profile tab
(`content_desc="Hồ sơ" selected="true"` with bottom-of-screen bounds), the
handle (`text="@user_01"`), and an "edit profile" marker
(`text="Sửa hồ sơ"`) — mirror what a real profile dump shows. Also
monkeypatch `open_profile_root`/`open_switcher` to raise AssertionError so the
test proves the legacy 2-call path is NOT used, and assert `adapter.taps == []`
to prove no legacy identity tap.

## Device-only verify modes: `--startup-only` vs `--account-ready-only`

Both are **device-only** modes: acquire the device lease only (NO workbook
lock), never construct `FollowState`, never read a follow list, zero
search/follow actions, and release the device lease with a distinct audit
reason on verified success (handoff/retained on failure via the shared
`_release_device_only` helper). They differ only in how far they go:

| | `--startup-only` | `--account-ready-only` |
|---|---|---|
| mapping source | `--serial` CLI arg (no workbook read) | safe workbook `load_mapping` (normal) |
| flow | prepare → open_tiktok → verified-feed artifacts | prepare → open_tiktok → popups → **canonical switch+verify** → popups → profile-XML artifacts |
| evidence.json | `final_feed_verification` | `account_ready_verification` + `zero_business_actions: {search: false, follow: false}` |
| artifact dir | `runs/startup-only/<run_id>/` | `runs/account-ready/<run_id>/` (config key `account_ready_artifact_dir`) |
| release reason | `verified startup-only success` | `verified account-ready success` |

### Pitfalls (all hit in the wild)

1. **`load_config(startup_only=...)` must also skip business validation for
   account-ready.** The business config (`mode`, `budget_*`,
   `follow_list_file` existence) is validated unless a no-business flag is
   passed. Adding a second no-business mode but only forwarding
   `startup_only=args.startup_only` makes the new mode fail at config load
   with `mode sai / budget phải > 0 / follow_list_file không tồn tại`. Thread
   `account_ready_only=args.account_ready_only` into `load_config` and have it
   treat either flag as no-business.
2. **CLI plan keys must be nulled for both no-business modes** (`tik_id`,
   `mode`, `budget_per_day`, `budget_per_session`, `follow_list_file`); keep
   `serial` present. Add `account_ready_only` to the plan payload so the
   operator can tell modes apart.
3. **Mutual exclusion**: `--account-ready-only` + `--startup-only` → stderr
   `CONFIG_ERROR` + exit 2 before any load/mapping/device work.
4. **Shared release helper needs a reason parameter.** If `--startup-only` and
   `--account-ready-only` share `_release_device_only(leases, res)`, the
   release audit reason is hardcoded to the first mode. Add a
   `success_reason=` keyword (default keeps the existing string → no existing
   test breaks) and pass the mode-specific reason. Assert the exact reason in
   the fake lease's `release_calls`.
5. **Device-busy guard test must assert zero side effects**: no lease acquire,
   no prepare, no popup dismiss, no screencap, no tap — the busy check fires
   before ANY device work.
6. **Account-ready artifact writing still requires the exact foreground
   check** (`focused_activity()` package match) like startup-only, but the
   XML written is the **verified post-select profile XML** (from
   `select_exact_account`), not a fresh dump — writing a fresh dump would lose
   the "this exact XML was verified" provenance.
7. **Evidence must stay privacy-safe**: never include the expected handle in
   evidence.json (`expected_handle` absent); the handle is a credential-like
   identifier.
8. **`_release_device_only` monkeypatch trap**: when the engine's release
   helper has `success_reason=` as a keyword default, the fake lease records
   `release_with_audit(reason=...)` — assert the reason string, not just that
   release was called.

## Session status

RED→GREEN for the canonical switcher rewire and `run_account_ready_only`
engine path completed (engine suite 29 passed). CLI wiring RED→GREEN was in
progress: `--account-ready-only` parser/plan/dispatch landed and the
mutual-exclusion + safe-mapping tests passed; the final
`no_business_config` test still needed `load_config` to forward
`account_ready_only` (the fix was identified but the session ended before the
GREEN rerun). Verify with:

```bash
cd /d/taadaa/tiktok-follow
PYTHONPATH="D:/Taadaa/automation-core/dist/automation_core-0.4.44-py3-none-any.whl" \
  D:/Taadaa/python-envs/automation/Scripts/python.exe -m pytest follow_runner/tests/test_cli.py -q
```
