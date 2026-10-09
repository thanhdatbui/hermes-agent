# Cluster-first canary, immediate login recovery, and supervisor lessons

## Canary policy

Classify alerts by failure signature/root cause before live runs. Select one representative per cluster. Run independent clusters in parallel when locks permit; a failed representative blocks only its cluster. Requiring every machine in one cluster is explicit coverage work, not the default canary gate. Canonical policy: `D:\Taadaa\HERMES_SUBAGENT_RULES.md`, `CANARY_CLUSTER_FIRST_RULE_2026_09_26`.

## Immediate login recovery

`ACCOUNT_MISSING` and `manual-needed:login` must converge on the existing canonical `D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py` path immediately, then perform exactly one post-login verification retry with `allow_auto_reconcile=False`. Preserve fail-closed behavior when login or postcondition fails. Never create an ad-hoc login script, manually tap, or use `pm clear`.

Trace every early-return path: `identity_manual_row`, `switcher_manual_row`, and the later `last_reason` recovery block. A patch in the later block can pass offline while runtime returns earlier.

Prove invocation from the fresh target log: require `tiktok_login_v1.py`/`start_fast_login` plus subprocess result before diagnosing Gmail, credentials, or parent-lock failure. `manual-needed` alone is not proof that login ran.

Bind artifacts to exact serial/account/source row. Reject a merely newest artifact if target identity does not match; reconcile opaque runner IDs through manifest, workbook, and DB.

## Persistent orchestration

`delegate_task` children do not guarantee automatic phase continuation. Multi-phase incidents need a persistent ledger/supervisor with explicit `DONE`, `CHECKPOINT`, `FAILED_RETRYABLE`, `FAILED_FINAL`, `NEEDS_DECISION`, `resume_token`, and `next_action`. Never make an LLM child wait on a device lock; use a bounded monitor/checkpoint or detached job runner.
