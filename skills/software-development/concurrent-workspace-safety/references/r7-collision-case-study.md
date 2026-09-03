# R7 Scope-Collision Case Study (P1 hermes_cron, 2026-08-10)

Real collision during an audit-remediation round: a parallel writer implemented the
exact task (3 P1 findings) in the exact scoped files while the session was mid-read.

## Timeline (all times +07:00, repo D:\Taadaa\tiktok-luot nuoi acc)

| Time | Event |
|------|-------|
| ~12:5x | Session starts. Baseline reads: watcher.py 327 lines, journal.py 520 lines — pre-fix (no artifact binding, no handler registry, no value validation). 4 test files read; test_hermes_cron_p1_r2.py = 601 lines, no `test_r7_*`. |
| ~12:59 | Baseline suite: `70 passed` (contract 20 + p1_r2 30 + regressions 12 + watcher 8). |
| 13:01–13:05 | Foreign writer edits scoped files: test_hermes_cron_watcher.py 13:01, test_hermes_cron_regressions.py 13:03, journal.py 13:03, test_hermes_cron_p1_r2.py 13:04 (732 lines), watcher.py 13:05 (391 lines). |
| 13:06 | Detection: `grep -n "Watcher("` returned lines with `registered_handlers=` that my earlier read did NOT contain (line numbers shifted 67→70). `stat` showed mtimes minutes old vs `date`. |
| 13:06–13:07 | Assessment: `ps aux | grep python` empty (writer finished), full suite `75 passed` (70 + 5 new `test_r7_*`), py_compile OK, files all LF. Foreign work COMPLETE. |
| 13:08+ | Pivot to verification: replicated the audit's 3 probes against the fixed tree; zero files written by me; probe script placed outside repo and deleted. |

## Detection signals that fired (in order)

1. **Re-grep mismatch**: `grep -n "Watcher("` showed `registered_handlers={"fake-v1": bridge}` at lines 70/84/97/130 and `RecoveryRequest(...)` at line 646 — none existed in my earlier reads (line 67 had no `registered_handlers`; p1_r2 was 601 lines).
2. **mtimes vs date**: all scoped files 13:01–13:05, `date` = 13:06 — writes occurred mid-session.
3. **Process check**: `ps aux | grep python` empty → writer was not mid-flight; safe to inspect but not to co-edit.
4. **git status delta**: no new entries; `__pycache__` gitignored (`git check-ignore` confirmed) — repo pollution risk low.

## Decision

Do NOT re-implement, do NOT revert. Foreign work was complete and green → independent verification + collision report. Kept my own writes to zero repo files (probe script at `C:\Users\Kibe\r7_probe.py`, deleted after).

## Probe replication results (audit attack shapes vs fixed code)

| Probe | Attack shape | Result |
|-------|-------------|--------|
| 1a | Old result schema: digest ONLY on recapture, retry/proof arbitrary files, no bindings | `REJECTED: RECOVERY_RESULT_INVALID` |
| 1c | Binding with forged `entry_id` | `REJECTED: RECOVERY_RESULT_INVALID` |
| 1d | End-to-end: bridge returns unbound result | `HANDOFF` (no VERIFIED_SUCCESS); events `[DETECTED, CLASSIFIED, RECOVERY_RESERVED, HANDOFF]` |
| 2a | CLASSIFIED(outcome="BOGUS", lock_safe="not-a-bool", reason="", evidence={}) | `REJECTED: invalid journal value` |
| 2b | FAILED(retryable="yes", next_attempt=99) | `REJECTED: invalid boolean journal value` |
| 2c | FAILED(retryable=True, next_attempt=99) | `REJECTED: invalid next_attempt` |
| 3 | Callable bridge + handler_id="totally-unregistered-handler", registered_handlers={} | `NO_HANDLER_IMPLEMENTED`, bridge_calls=0, events `[DETECTED, CLASSIFIED, NO_HANDLER_IMPLEMENTED]` (isolated root) |
| 1b | Fully consistent result (bindings present, digests correct) | `ACCEPTED` — by design; flag as residual note |

**Probe pollution bug caught in my own run**: probe 3 initially reused the temp root from
probe 1d → journal already contained HANDOFF for the same entry+signature → process_failure
short-circuited to `HANDOFF` and events showed a stale RECOVERY_RESERVED. Fixed by
`tempfile.mkdtemp()` per probe. This is the strongest argument for the fresh-root-per-probe rule.

## RED evidence sourcing (since I did not write the tests)

- Pre-fix documented probes (audit transcript of the REJECT verdict): `arbitrary_unhashed_proof_and_invocation: "ACCEPTED"`, `bogus_classified_values: "ACCEPTED"`, `bogus_failed_values: "ACCEPTED"`, `unregistered_callable_handler: ["AUTO_RECOVERY_PENDING", ...]`.
- My baseline snapshot: pre-fix watcher/journal content (327/520 lines), 70 tests, zero `test_r7_*`.

## Residual gaps flagged to coordinator (design notes, not failures)

- Artifact binding record lives in the RESULT dict, not inside the artifact file — a bridge can point at arbitrary existing files as long as its binding digests match.
- Invocation_id is bridge-supplied and journaled as-is (consistent by construction), NOT anchored to reservation_id — different reading of "invocation nhất quán" than the audit suggested.
- Binding reference_time = clock.reference_time() while reserved_at = as_of — two timestamps in one flow; journal only checks non-empty + parseable.
- `_populate_artifact_bindings` retro-fills missing bindings on append (legacy-tolerant path, slightly softer than fail-closed).
