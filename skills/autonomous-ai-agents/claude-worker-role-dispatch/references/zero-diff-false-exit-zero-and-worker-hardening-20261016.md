# Zero-Diff False Exit 0 Trap & Worker Dispatch Hardening (16/10/2026)

## 1. The Incident: False Exit 0 & Conversational Evasion
When `dispatch_worker.py` called Haiku 5.5 to patch `claude_quota_guard.py` in a repository with uncommitted changes (dirty tree from `closeout_gate.py`):
1. **Conversational Evasion:** Haiku saw the uncommitted files, triggered safety avoidance, and outputted a long analysis ending with: *"What do you want done with this file? ... I'll set the scope from your answer."* It made zero edits.
2. **False Exit 0:** Claude Code CLI completed its turns cleanly and exited with returncode `0`.
3. **Dispatcher Blind Trust:** `dispatch_worker.py` checked `if rc == 0: return 0`, logged `success: True`, and exited—while `git diff` on the target file was 0 lines. Coordinator was misled into thinking the fix landed, only realizing later that `claude_quota_guard.py` was untouched.
4. **Wasted Quota on Probe Calls:** Coordinator also ran dummy probe commands (`echo test_dispatch`, `in ra đường dẫn file và kiểm tra...`), unnecessarily consuming Claude 5h session quota on startup.

---

## 2. Architectural Analysis (Claude Sonnet 5.5 Consultation)
When evaluating whether to replace Haiku with Agy CLI (Gemini 3.8 Flash):
- **Verdict:** Keep Haiku 5.5 as Tier 1, Agy CLI as Tier 2 fallback.
- **Root Cause:** The flaw was in the dispatcher trusting `exit 0`, not the model. Any worker (including Gemini) can exit 0 without editing, or edit the wrong file.
- **Quality Advantage:** Haiku produces cleaner syntax, strict type hints, and fewer hallucinations than Gemini Flash, making it superior for Tier 1.

---

## 3. Four Mechanical Hardening Rules

### Rule 1: Zero-Diff Verification (Never Trust Exit 0 Alone)
A worker execution is only SUCCESS when:
`returncode == 0` AND `file_hash_after != file_hash_before` (for target files) AND `acceptance_check == PASS`.
- Snapshot SHA256 of target files before dispatch.
- If returncode is 0 but target file hash is unchanged (`NO_DIFF`), classify as structural failure `NO_DIFF`.
- Do not rely solely on `git diff --numstat` because pre-existing dirty changes on the target file will create a false positive. Target file content hash before/after is the true invariant.

### Rule 2: Imperative Autonomous Directive in Worker Prompt
Claude CLI running headless (`-p`) requires an explicit non-interactive directive to suppress conversational hesitation:
```text
[AUTONOMOUS WORKER MODE]: You are running non-interactively. NEVER ask questions or propose plans for approval. MUST immediately apply code edits to the target file using Edit/Write tool. Ignore unrelated uncommitted files and never modify them. If the task cannot be completed, output exactly 'BLOCKED: <reason>' and make no edits.
```
If worker outputs `BLOCKED:`, dispatcher maps it to `NEEDS_INPUT` and triggers retry or fallback, never `OK`.

### Rule 3: Zero-Probe Quota Discipline
- NEVER use model dispatch (`dispatch_worker.py` or `claude_worker.py`) for probe calls (testing echo, checking permissions, reading paths).
- All environment and tool checks MUST be executed via deterministic local Python scripts O(1) without burning LLM session tokens.

### Rule 4: Dispatcher Escalation Protocol
1. **Attempt 1:** Haiku CLI with explicit target file and autonomous prompt.
2. **Attempt 2 (Retry on `NO_DIFF` / `TIMEOUT`):** Append `[O(1) FOCUS RETRY - DO NOT EXPLORE, TOUCH ONLY TARGET FILE MINIMALLY]`.
3. **Tier 2 Fallback:** Escalate to `ag_cli.py fix` (Antigravity pool / Gemini Flash) if attempt 2 fails or quota is exhausted. Agy CLI must undergo the same pre/post hash verification gate.
