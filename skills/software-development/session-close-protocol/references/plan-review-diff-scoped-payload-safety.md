# Plan-Review Diff-Scoped Payload and Socket Timeout Safety

## Problem & Pitfall
When closing a session and sending the candidate diff to 9Router (`:20128`) for Gate 1 Plan-Review (`plan-review` or `plan-review-hard`):
1. **Full Repo Diff Context Exhaustion & Timeout**:
   Using `git diff <base>` across a large multi-commit range or including thousands of lines of unrelated mock/fixture boilerplate (`test_*.py` fixture files with massive XML dumps) overwhelms model context windows (100k+ tokens) or causes proxy/upstream socket timeouts (`timed out` after 60s/120s).
2. **Socket Layer Timeout Safety**:
   Python `urllib.request.urlopen` or `requests` calls without an explicit bounded socket timeout (`timeout=45` / `timeout=60`) can hang the terminal execution indefinitely if 9Router or the upstream provider stalls.

## Canonical Fix Pattern
1. **Diff-Scoped Allowlist**:
   Always scope the `git diff` to the exact modified production files, case documentation, and relevant new/modified test files:
   ```bash
   git diff <base> -- <production_files> <docs/farm-automation-cases.md> <test_files>
   ```
2. **Strict Socket Timeout**:
   Enforce `timeout=60` on the HTTP request.
3. **OmniRoute / Fallback Priority**:
   If 9Router (`:20128`) experiences high load or stalls, OmniRoute (`:20129`) provides Ordered Concurrency Spillover across accounts.
