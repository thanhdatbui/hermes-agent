# Unified Pipeline End-to-End Canary & Target Context Injection Architecture (2026-10-30)

## 1. Context & Motivation
In testing the unified patch pipeline (`unified_patch_pipeline.py`) end-to-end, the system demonstrated successful real execution from S0 to S5 and Confirm, but uncovered two mechanical failure modes that caused Planner failures:
1. **Target Context Starvation in Gate B Planner**:
   - `unified_patch_pipeline.py` originally invoked `gate_b_planner.py` passing only `--task` and `--workdir`, without forwarding `--target-file`.
   - LLMs (Gemini Web, Claude, Sol) did not have the target file contents in their prompt context. When asked to generate targeted patches without seeing the code, models consistently outputted empty edits (`{"edits": []}`), which triggered `Field 'edits' must be a non-empty list` failure.
2. **Anchor Invariant Ambiguity**:
   - Generic symbols or empty strings (e.g., `old_string: ""` when inserting comments at the top of a file) failed O(1) patch validation (`old_string is empty`).
   - Models required an explicit directive: even when inserting at the top of a file, `old_string` must capture the first 3-5 existing lines of that file, and `new_string` must include the new code followed by those exact existing lines.

## 2. Architecture & Mechanical Invariants

### 2.1 Multi-Target Context Forwarding (S1)
`unified_patch_pipeline.py` must forward all `--file` arguments from S0 to `gate_b_planner.py` via `--target-file`:
```python
cmd_plan = [
    sys.executable,
    str(GATE_B_PLANNER),
    args.task,
    "--workdir", str(repo),
    "--output", str(plan_out),
]
for tf in target_files:
    cmd_plan.extend(["--target-file", tf])
```
`gate_b_planner.py` reads up to `TARGET_CONTEXT_LINES = 100` for each specified target file and injects it into the prompt with clear delimiters:
`=== TARGET FILE CONTEXT: <file> (lines 1-N of N) ===`

### 2.2 Strict Anchor Invariant
The prompt enforces that `old_string` must be an exact, unique snippet (count == 1):
- `count(old_string) == 1` is strictly checked against the live file before any worker dispatch.
- When prepending to a file, models must not emit empty `old_string`. They must include existing top lines in `old_string` and mirror them in `new_string`.

### 2.3 Tiered Planner Cascade & Raw Output Diagnostics
To prevent blind fail-open/fail-closed loops, `gate_b_planner.py` uses a 3-tier planner cascade:
1. **Tier 1**: `gemini-web` (Argon 4 Pool via `:20129`, timeout 120s)
2. **Tier 2**: `sol-worker` (`gpt-web-sol` via `:20129`, timeout 120s)
3. **Tier 3**: `claude-cli` (`claude -p --model sonnet`, timeout 150s)

If any planner returns unparseable text or malformed JSON, `gate_b_planner.py` dumps the first 500 characters to `D:/Taadaa/runtime/audit_logs/gate_b_last_raw_response.txt` and records structured telemetry in `D:/Taadaa/logs/gate_b_audit.jsonl`.

### 2.4 End-to-End Canary Proof
A complete run is verified through:
1. `run`: S0 (Scope Lock & Pre-snapshot) -> S1 (Gate B Plan with target context) -> S2 (Gate C Worker Patch + Independent Hậu Kiểm) -> S3 (Verify Test) -> S5 (Hold with HMAC-signed state & diff_hash).
2. `confirm`: Verifies state HMAC signature, confirms user intent (`done|chốt|chốt phiên|đóng phiên`), checks zero diff drift (`diff_hash_at_hold == current_diff_hash`), and triggers Closeout Gate v2 for final merge/push.
