# Gate Compliance & Hook Guard Friction Rollup

## 1. Problem Statement
When a compliance watchdog only tracks downstream CI/CD gates (Canary, Model Review, Commit Scope, Push Verified, Closeout Score), most of the time it returns `NO_EVIDENCE`. Meanwhile, the real friction causing agents to fumble, retry blindly, and burn thousands of tokens is pre-execution hook guards (`GUARD_SEARCH_FILES_ROOT`, `GUARD_FOREGROUND_TIMEOUT_MISSING`, `GUARD_DANGEROUS_ROOT`) and dispatch route blocks (`subagent_edit_blocked`, unbudgeted `investigate`).

## 2. Invariant Rules
1. **Full-Spectrum Telemetry Rollup:** Compliance watchdogs must ingest pre-tool hook audits (`guard_scan_audit.jsonl`) and dispatch audits (`dispatch_audit.jsonl`), extracting `rule_id` and `route` to compute frequency and violation percentages.
2. **Guidance Feedback Loop:** Top blocked rules must be displayed in the periodic report with actionable reasons, allowing the operator/agent to inject targeted guidance O(1) via `update_guidance.py`.
