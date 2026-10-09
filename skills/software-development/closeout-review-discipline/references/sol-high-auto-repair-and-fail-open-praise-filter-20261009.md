# Sol High Auto-Repair Architecture & Fail-Open Praise Filter (2026-10-09)

## Context & User Mandate
When Closeout Gate rejects code, the legacy workflow allowed Gemini to loop for 3 guessing rounds ("3 vòng đoán mò"), often resulting in:
1. Gemini overfitting on reviewer prompts (superficial patch, hack test, spaghetti if-else).
2. Coordinator stopping at round 3 and reporting "BLOCKED khóc lóc" to the user.
3. User explicit invariant (2026-10-09):
   - **"K đc gắn claude cli vào trừ khi t cho phép, gọi claude lung tung v tốn token lắm."**
   - **"Ủa khi sửa thì chạy qua closeout gate đã gửi đúng mỗi cái diff vs scope, thì sol sửa đc chứ. Chứ chạy 3 vòng r dừng lại thì dẹp mẹ đi tao đéo chấp nhận blocked khóc lóc."**
   - **"Ủa v từ h ném mẹ luôn cho sol high review xong tự sol high sửa đc m. Khỏi cần gemini tự sửa 3 vòng."**

To fulfill this mandate without consuming Claude quota, the **Sol High Auto-Repair module (`sol_repair.py`)** was developed, audited by Claude CLI, and approved with **86/100 (56/56 tests passing)**.

---

## 1. Sol High Auto-Repair Architecture (`sol_repair.py`)

### Core Principles
1. **Strict Read-Only Proposal Generation:**
   Sol High operates strictly as an advisory repair engine. It emits structured JSON patch proposals (`old_snippet`, `new_snippet`, `file_path`, `addressed_findings`). It NEVER directly writes or mutates files on disk. The Coordinator/Caller applies the patch via explicit tools (`patch`), followed by local `pytest` verification.
2. **Deterministic Context Packaging:**
   Because Closeout Gate isolates the diff to `<= 2` files and `<= 30KB`, `build_repair_prompt` packages the exact failing functions/files and reviewer findings without blowing the web endpoint buffer ceiling (~35KB).
3. **Cumulative In-Memory Patch Simulation:**
   When multiple patches apply to the same target file, `sol_repair.py` simulates them cumulatively in RAM using a canonical path key (`(repo_p / fpath).resolve().relative_to(repo_p.resolve()).as_posix().lower()`). This ensures path variants like `pkg/./mod.py` and `pkg/mod.py` accumulate on the exact same working copy.
4. **Whole-File Cumulative AST Syntax Validation:**
   After all in-memory patches are applied, the entire resulting file is verified with `ast.parse()`. If syntax regressions occur (e.g. unclosed parenthesis, indentation mismatch), the proposal fails closed (`syntax_ok=False`), and the error is pinned directly to the offending patch.
5. **No-Op Patch Rejection:**
   Patches where `old_snippet == new_snippet` are strictly rejected as invalid no-op attempts.

---

## 2. Fail-Open Praise Filter vs Substring Trap

### The Substring Matching Vulnerability
A common pattern in scorecard parsers is checking whether a finding starts with or contains praise words (`pass`, `tốt`, `clean code`, `test coverage`):
```python
# VULNERABLE: Substring matching drops real security defects!
if any(p in body.lower() for p in ("pass", "tốt", "clean code")):
    continue
```
**Consequences:**
- Finding `"Pass: validation is missing in parse()"` was silently dropped because of `"pass"`.
- Finding `"Hoàn thành: đã fix lỗi A nhưng lỗi B (race condition) vẫn còn"` was dropped because of `"hoàn thành"`.
- Finding `"Pass: SQL injection possible"` was dropped because of `"pass"`.
- Finding `"Password stored in plaintext in log"` was dropped because `startswith("pass")` matched `Password`!

### The Fail-Open Exact Match Solution
The filter must be strictly **fail-open**: only drop a line if it is a bare header (no text after `:`) or matches an exact entry in a strictly curated allowlist of pure praise phrases:

```python
PURE_PRAISE_BODIES = {
    "ok",
    "pass",
    "passed",
    "clean",
    "clean code",
    "tốt",
    "đạt",
    "đạt chuẩn",
    "đã xong",
    "hoàn thành",
    "all tests pass",
    "all passed",
    "test coverage đạt 100%",
    "code sạch",
    "cấu trúc code sạch",
    "không có lỗi",
    "không có vấn đề",
    "all errors handled",
    "đã fix lỗi",
}

PRAISE_HEADER_REGEX = re.compile(
    r"^(?:điểm\s+mạnh|ưu\s+điểm|strengths?|tốt|hoàn\s+thành|đã\s+xử\s+lý|pass)\b",
    re.IGNORECASE,
)

def is_praise_finding(text: str) -> bool:
    if not text:
        return False
    cleaned = re.sub(r"^(?:[-*•#_`]+|\d+\.)\s*", "", text.strip()).strip()
    cleaned = re.sub(r"[*_`]", "", cleaned).strip()
    m = PRAISE_HEADER_REGEX.match(cleaned)
    if not m:
        return False
    after = cleaned[m.end():].strip()
    if not after or after in (":", "-"):
        return True  # Bare header like "Điểm mạnh:" -> drop
    if after.startswith(":") or after.startswith("-"):
        body = after[1:].strip().lower().rstrip(".!: ")
        return body in PURE_PRAISE_BODIES  # Exact match ONLY
    return False
```
**Guarantees:**
- Substantive defects like `"Pass: validation is missing"` or `"Tốt: tuy nhiên có race condition"` do not match `PURE_PRAISE_BODIES` and are **100% preserved**.
- Plain praise like `"**Pass**: ok"` or `"Điểm mạnh: test coverage đạt 100%"` matches and is cleanly dropped.

---

## 3. Windows Denylist & Path Traversal Hardening

When scanning and accepting file paths for repair:
1. **Windows Stream & Trailing Dot Tricks:**
   Reject paths containing `::` (alternate data streams) or components ending with trailing dots (`foo.`) or spaces (`foo `). Allow legitimate single-dot current-directory components (`.`).
2. **Canonical Component Resolution:**
   Resolve relative to repo root: `(repo_p / rel_path).resolve().relative_to(repo_p.resolve())`.
   Check each component in `parts`:
   - Must not be in `FORBIDDEN_REPAIR_PATHS` (`.git`, `.github`, `.claude`, `closeout_gate.py`, `farm_policy.py`, `SOUL.md`, `AGENTS.md`, `config.yaml`, `.env*`).
   - Must not contain `hooks`, `credentials`, `password`, `secret`, `*.pem`, `*.key`, `id_rsa`.
   This blocks sneaky variants like `./hooks/guard.py`, `tools/./hooks/x.py`, or `hooks /guard.py`.

---

## 4. Streaming & Non-Streaming Endpoint Resilience

In `call_sol_repair`:
- OmniRoute / local endpoints may return SSE streams (`data: {"choices": [{"delta": ...}]}`) or standard JSON (`{"choices": [{"message": ...}]}`).
- Maintain `non_stream_buffer` for any lines without `data: `.
- If `full_chunks` is empty after response iteration, fallback to parsing `"\n".join(non_stream_buffer)` via `json.loads()`. This prevents empty response errors when streaming is disabled by the proxy.

---

## 5. Audit Chain Fail-Closed Integrity

In `closeout_gate.py`:
- `_read_last_chain_hash`: Raises `RuntimeError` if the last line of `gate_audit.jsonl` is corrupted or missing `self_hash`. Never silently reset to `"GENESIS"`.
- `get_latest_gate_result`: Returns `None` immediately upon encountering a corrupted JSON line, preventing older `APPROVED` records from masking recent rejections.
- `count_consecutive_rejections`: Returns `limit` (triggering handoff) when log parsing fails.
- Proposal storage: Saved under `D:/Taadaa/logs/repair_proposals/proposal_<repo>_<ts>.json` with `out_p.parent.mkdir(parents=True, exist_ok=True)`. Never pollute repo working tree.
- Deadline budget: Skips auto-repair if `global_deadline - time.monotonic() < 5.0s`.
