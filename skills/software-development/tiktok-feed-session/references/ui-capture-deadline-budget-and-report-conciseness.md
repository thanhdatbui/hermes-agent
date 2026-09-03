# UI Capture Deadline Budget Initialization & External Incident Reporting

## 1. UI Capture Loop Deadline Variable Initialization
- **Pitfall**: When implementing multi-attempt capture with bounded deadlines (`bounded_deadline - (time.monotonic() - loop_start)`), `loop_start = time.monotonic()` MUST be explicitly initialized immediately after `bounded_deadline` is resolved.
- **Consequence of missing `loop_start`**: ATX session dumps requiring retry will crash with `NameError: name 'loop_start' is not defined`, failing all workers on live batches (as observed in incident 2026-08-30 row-2-230003 where 46 machines crashed simultaneously).

## 2. External / Admin Error Report Conciseness
- **Rule**: When formatting an error/incident report to send to admin, third-party operators, or another bot:
  - Output **ONLY** the raw factual symptoms, target host/IP, affected port range, error signatures, and live test reproduction (e.g. TCP connection refused vs PPPoE up).
  - **DO NOT** append unsolicited solutions, advice, instructions, or speculation unless explicitly asked by the user. Keep it crisp, factual, and direct.
