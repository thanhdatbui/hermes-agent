# Intelligent Failure Classification & Haiku Retry Ladder (16/10/2026)

## Context & Operator Directive

During farm operations, when running routine code-fix tasks through `dispatch_worker.py`, a naive fallback mechanism that immediately dumps any failure to Agy CLI (Gemini Pro) is inefficient and misdiagnoses the failure mode.

The Operator asked:
> *"Haiku thất bại là khi hết quota thôi chứ? Nếu cấp tool cho nó đủ có phân rã task ra làm tiếp không hay fallback qua Agy CLI luôn?"*

---

## 1. Why Haiku Must NEVER Decompose Tasks

1. **Haiku is an $O(1)$ Fast Worker (10–15s):**
   Haiku excels at high-speed, localized edits when given a concrete, exact contract: *"Edit file X, replace line A with B, run test Y"*.
2. **Decomposition Burns the Turns Budget:**
   Task decomposition requires reading architecture, codebase mapping, and multi-step reasoning. With a strict budget of `--max-turns 8` (hard cap 15), giving Haiku an open-ended goal causes it to spend all its turns exploring and reading files without writing a single line of code, triggering `error_max_turns`.
3. **Strict Division of Roles:**
   - **Task Decomposition is the COORDINATOR's Duty:** Coordinator has global context and MUST break tasks into minimal $O(1)$ contracts before dispatching.
   - **Haiku is Strictly an Execution Worker:** Receives $O(1)$ contract $\to$ edits target file $\to$ runs focused test $\to$ returns.

---

## 2. Failure Classification Matrix (`classify_failure`)

Failures in `claude_worker.py` belong to three distinct categories:

| Category | Detection Criteria | Root Cause | Action |
| :--- | :--- | :--- | :--- |
| **`QUOTA`** | rc == 127, output contains `"hit your session limit"`, `"quota_gate_triggered"`, `"rate_limit"`, `"429"` | Claude 5h session limit reached or quota unreadable | **Immediate Fallback to Agy CLI fix** (reason: `quota_exhausted`). No Haiku retry. |
| **`ENV`** | rc == 126, output contains `"no such file or directory"`, `"cant open file"`, `"is not recognized as an internal"` | File path wrong, tool binary missing, OS path syntax error | **HALT IMMEDIATELY.** Do NOT fallback to Agy CLI. Fix environment first. |
| **`MAX_TURNS` / `TIMEOUT` / `TASK_FAIL`** | Output contains `"error_max_turns"`, `"reached max turns"`, rc == 124 (timeout), or test fail | Contract too broad, subtle logic bug, test assertion mismatch. **Haiku still has quota!** | **HAIKU RETRY (Attempt 2)** with O(1) focus contract. |

---

## 3. The Intelligent 2-Attempt Haiku Ladder

Instead of blindly dumping to Agy CLI on the first failure:

```text
                  [dispatch_worker.py "<contract>"]
                                 │
                                 ▼
                     [Haiku CLI - Attempt 1]
                                 │
         ┌───────────────────────┼───────────────────────┐
         ▼ (rc == 0)             ▼                       ▼
    [THÀNH CÔNG]           [LỖI ENV]               [HẾT QUOTA]
         │                 (Sai path, tool)        (Session limit)
         │                       │                       │
         │                       ▼                       ▼
         │                 [DỪNG NGAY]             [AGY CLI FIX]
         │                 (Cấm gọi Agy)           (Audit: quota_exhausted)
         │
         ▼
[MAX_TURNS / TIMEOUT / TASK_FAIL] (Haiku còn Quota!)
         │
         ▼
[Haiku Attempt 2 - Injected O(1) Focus Prefix]
Prompt = "[O(1) FOCUS RETRY - DO NOT EXPLORE, TOUCH ONLY TARGET FILE MINIMALLY]\n" + prompt
         │
         ├───────────────────────┐
         ▼ (rc2 == 0)            ▼ (Vẫn fail lần 2)
    [THÀNH CÔNG]           [ESCALATE SANG AGY CLI FIX]
                           (Audit: haiku_exhausted_contract)
                           (Cụm 7 acc Gemini Pro giải quyết dứt điểm)
```

---

## 4. Audit Log Verification (`D:/Taadaa/logs/dispatch.jsonl`)

Every dispatch execution records transparent metrics:
```json
{
  "ts": "2026-10-16T06:30:00+00:00",
  "tier": "haiku",
  "attempt": 1,
  "category": "TASK_FAIL",
  "reason": "retry_needed",
  "workdir": "D:/Taadaa/Hermes",
  "file": "deploy/hermes-home/scripts/watchdog.py",
  "exit_code": 1,
  "success": false
}
```
If Attempt 2 succeeds, token consumption on Agy CLI is 0. If Attempt 2 fails, Agy CLI takes over with verifiable failure evidence.
