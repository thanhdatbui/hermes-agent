# Implementation Phase — CRLF-safe editing & AG audit loop detail

Session evidence: P1 feed pilot, 2026-08-12 (`tiktok-luot-nuoi-acc-recovery-adapter-p1-wt`,
commits `2c2e21d` → REJECT → `5b10635` → MINOR_FIXES → `6c52bea` → chờ verdict).

## CRLF-safe edit recipe (MANDATORY on these repos)

These repo files use CRLF (`\r\n`). Naive Python string surgery corrupts EOLs and can
duplicate dict keys. The safe pattern:

```python
from pathlib import Path
p = Path(r'D:\Taadaa\...\file.py')
raw = p.read_bytes().decode('utf-8')
# work on LF-normalized text
raw = raw.replace('\r\n', '\n')
# ... do replacements/regex on raw (LF) ...
# write back as CRLF
p.write_bytes(raw.replace('\n', '\r\n').encode('utf-8'))
```

Never hand-build replacement lists of `\r\n`-split lines containing embedded `\n` —
the `SEP.join()` step then mixes EOLs and leaves orphaned/duplicated lines (observed:
duplicate `"state"`/`"proof_backed"` keys in `classify_manual_needed_popup` return,
stray `assert` continuation from the old loop after a `for`-line replace). After any
scripted edit, verify the affected block by re-printing line numbers and check `git diff`.

## AG audit wrapper

`bash /d/Taadaa/reports/ag-audit/run-ag-audit.sh "<repo>" <commit> [model] [timeout]`

- Verdict is the LAST line: `AG_AUDIT_VERDICT=APPROVED|MINOR_FIXES|REJECT|UNPARSEABLE`.
- Human-readable findings in `<out-dir>/audit-<commit>-<stamp>-response.txt`; each MAJOR
  finding carries locator (file+line), trigger, consequence.
- Run via `background=true, notify_on_complete=true` (up to 600s; the wrapper default
  timeout is 600).

## REJECT → fix loop (observed M1–M3 pattern)

Audit REJECT on `2c2e21d` flagged (all real locators):

- M1: consumer-side registration wrapper (`register_escalation_hook`) lacked the
  `None`/callable TypeError gate that the sibling `register_feed_recovery_escalation`
  had → add the same guard in the scheduler-side wrapper. Sibling asymmetry = finding.
- M2: mixed control-plane enums in one result dict — `ExitStatus.MANUAL_NEEDED.value`
  (`"manual-needed"`) vs core `FinalResultStatus.FAILED_LOCKED.value`. Auditors treat
  a consumer string beside core enum strings as a fail-closed bypass (downstream
  `switch` on `FinalResultStatus` never matches). Normalize every value to the core
  enum; keep consumer nuance in an extra field (`"manual_needed": True`), not in the
  `status` value. Update the test assertion to the new value.
- M3: helper built a registry AND `__init__` overwrote `queue.registry` → double
  construction + silent overwrite. Single-owner: helper stops assigning; adapter is
  the only place `queue.registry` is set.

Test-side findings:
- m2: redaction assertions were vacuous — secrets never injected into evidence.
  Fix = inject real secrets (add `"serial"/"account"` from ctx into the evidence the
  adapter actually sends), assert `evidence["serial"] == "<redacted>"`, keep
  `<redacted>`-marker assertion. Don't keep asserting secrets that never enter evidence.

## MINOR_FIXES → proof-test loop (observed F1–F3 pattern)

`MINOR_FIXES` findings on `5b10635` were "confirm/justify" style, not code defects:

- F1 "redaction coverage narrowed (5→2 secrets)": satisfy by adding a direct unit test
  of core `automation_core.redaction.redact_value({"otp": ..., "token": ..., "password": ...})`
  → each `== "<redacted>"`, plus a comment explaining why the dropped literals are no
  longer reachable in evidence. Core `_SECRET_KEY` regex covers
  `password|passwd|secret|token|cookie|authorization|otp|totp`; `_IDENTIFIER_KEY`
  covers `serial|machine|workbook|account|target_id|target_ref`.
- F2 "serial/account added but redaction not visible": add exact asserts
  `evidence.get("serial") == "<redacted>"` / `evidence.get("account") == "<redacted>"`
  — proves key-based redaction without needing core diff.
- F3 "_feed_recovery_queue no longer assigns registry": add assert
  `adapter.queue.registry is adapter.registry` to the single-control-plane test (the
  assignment lives in `FeedRecoveryAdapter.__init__:356`).

Rule: MINOR_FIXES that ask for confirmation are closed with PROOF TESTS, one commit,
then re-audit. Do not add production churn to answer a "confirm" finding.

## Venv isolation (root cause of a "broken venv")

Symptom: pip install succeeds but `import automation_core.escalation` fails /
`ModuleNotFoundError`, or `pip` says "Not uninstalling ... outside environment".
Cause: inherited `PYTHONPATH` env var points at the hermes venv site-packages, so the
new venv's `python.exe` resolves `automation_core` from the hermes venv instead of its
own site-packages.

Fix checklist:
1. Create venv from a real runtime: `C:\Users\Kibe\AppData\Local\Programs\Python\Python312\python.exe -m venv <path>` (`py -3.11` launcher has NO runtime on this host; `py -0p` lists `Python312` + uv CPython 3.11.15).
2. Every run: `env -u PYTHONPATH <venv>/Scripts/python.exe ...`.
3. Verify: `sys.prefix` == venv path; `automation_core.__file__` under venv
   `Lib/site-packages`; `pip show automation-core` == pinned version; `sys.path`
   contains NO hermes-agent path.

## Pytest stale-`__pycache__` trap

After editing/renaming tests, pytest may collect and run the CACHED old test body
(e.g. old `test_mode2_missing_fails_closed` name with a `assert True is False` from
`_mode2_module_available()` still expecting False). The source file looks correct but
the run shows the old test. Delete all `__pycache__` dirs under the repo and re-run;
prefer `-p no:cacheprovider` and consider `-B` for baseline runs.