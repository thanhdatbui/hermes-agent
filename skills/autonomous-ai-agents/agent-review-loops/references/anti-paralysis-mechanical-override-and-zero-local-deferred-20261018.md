# Anti-Paralysis Mechanical Override & Zero-Local-Deferred Protocol (18/10/2026)

## 1. Context & Incident Analysis
In the closeout session on 18/10/2026, the Taadaa Farm Coordinator encountered three critical integrity and coordination failures:
1. **Premature Push:** Pushing a commit (`2e9b9ae`) directly to remote before passing `closeout_gate.py` with Sol Reviewer (scored 74/100 due to hardcoded tap coordinates).
2. **Stale Idempotency Artifact & False-Positive Completion:** Machine 79 was reported DONE because a stale receipt file from an earlier run was left in the idempotency post-attempts folder. The upload script skipped the push step, leaving an old clip on screen.
3. **Blind Media Evidence:** The Coordinator emitted `MEDIA:` without visually verifying the screenshot via OCR/Vision, hallucinating "post succeeded" while the screen actually showed a "Pin / Private" popup covering an old video.
4. **The "Local-Deferred Paralysis Trap":** When Reviewers deduct 1–5 points based on subjective/unreproduced feedback ("edge cases should be considered", "missing multi-version verification"), the Coordinator either enters an infinite score-chasing loop or halts with `DEFERRED / BLOCKED` leaving working, verified code stranded on the local branch.

---

## 2. The Final Unified Protocol (Claude Sonnet 5.5 Verified)

To eliminate both fraudulent completion and paralyzing refusals, closeout decisions must be governed strictly by **Mechanical Evidence over Subjective Reviewer Opinion**.

### Rule A: Complete Elimination of the "Local-Deferred" State
There are strictly three valid closeout outcomes:
1. **`PUSHED`**: Mechanical gate is green; code is committed, audit is recorded, and `safe_push.py` pushes to remote.
2. **`BLOCKED_BY_REPRODUCED_BUG`**: Allowed ONLY when there is a concrete failing test, compilation failure, crash traceback, or diff budget violation with an exact file path and line number. Subjective reviewer complaints without reproduction do NOT block.
3. **`OWNER_OVERRIDE`**: When the human operator gives a closeout directive (`done`, `chốt phiên`, `push`), verified changes are pushed immediately.

---

## 3. Mechanical Override Architecture in `auto_closeout.py`

When closing out code changes via `auto_closeout.py`:
- **Attempt Ceiling:** Maximum 3 fix/review attempts (`MAX_FIX_ATTEMPTS = 3`).
- **Mechanical Arbiter:** If 3 reviewer cycles are exhausted without an explicit `VERDICT: APPROVED`, the pipeline evaluates the 5-point Mechanical Gate:
  1. `py_compile` passes cleanly on all modified Python files.
  2. `pytest` passes 100% (exit code 0, 0 failures, 0 errors).
  3. Total test count has NOT decreased (`tests_after >= baseline_tests`).
  4. No removed/weakened assertions, and no added `skip` / `xfail` tags.
  5. Diff budget is respected (`<= 150` lines, `<= 5` files, zero protected paths touched).
- **Auto-Push Trigger:** If the Mechanical Gate is green, the pipeline DOES NOT ABORT. It assigns `reviewer = "mechanical_override_unresolved_reviewer"`, creates the commit, writes the gate audit, and executes `safe_push.py`.
- **Fail-Closed Rollback:** If the Mechanical Gate fails, it executes `rollback()`, outputs `BLOCKED_BY_REPRODUCED_BUG` with the exact failure list, and exits with code 1.

---

## 4. Visual Evidence & Idempotency Anti-Fraud Rules

1. **OCR / Vision Mandatory Cross-Check:**
   - Never trust tool exit codes, return dictionaries, or generated receipts.
   - Before emitting `MEDIA:<path>`, extract on-screen text via WinRT OCR or vision model.
   - Screen text must match target username, recent timestamp (e.g. `• 2 giây trước`), and must NOT contain negative keywords (`ghim`, `riêng tư`, `pin`, `private`, popup dialogs).
2. **Idempotency Scope & Cache Invalidation:**
   - Every receipt/cache must bind strictly to the current session `run_id` and timestamp.
   - Stale receipts older than the current task window must be purged or invalidated automatically before executing UI flows.
