# Strike 3 Quota Preservation: Haiku Worker vs Sonnet Reviewer Discipline (17/10/2026)

## Context & The "Ba Phải" Antipattern Analysis
In past sessions, over 1/3 of tasks (~35%) repeatedly failed Sol Auditor reviews (scoring in the 72-78 range due to lack of deep integration tests or telemetry). When hitting Strike 3 Hand-off (`reviewer_handoff_triggered`), Coordinators repeatedly made two severe mistakes:
1. **The Sonnet Code-Writing Quota Disaster:** Invoking `claude_worker.py --role reviewer` (or Sonnet CLI) to edit files and write regression tests. Sonnet 5.5 burns an immense amount of 5h quota per turn. Calling Sonnet across multiple review loops repeatedly depleted Operator quota.
2. **The "Ba Phải" Flip-Flop (Sol Worker vs Sol Repair):** Proposing to replace `sol_repair.py` with `sol_worker.py` in Closeout Gate. This was rightly rejected: `sol_repair.py` is an in-memory AST-validated proposal generator strictly bounded to $O(1) \le 30$ lines. Unleashing a multi-turn ReAct worker (`sol_worker.py`) inside Closeout Gate causes command loops, test sprawl, and blows the diff budget.

---

## Technical Definitions: What is a "Turn"?
- **1 Turn $\neq$ 1 Repair Session or 1 Closeout Run.**
- **1 Turn = 1 Single Action Step** inside a ReAct agent loop (e.g. `READ_FILE` $\to$ `PATCH` $\to$ `COMMAND` $\to$ `DONE`).
- A `max-turns=8` cap means the agent has at most 8 tool round-trips to achieve passing tests before failing closed with `MAX_TURNS_REACHED`.

---

## Strict 3-Tier Escalation Ladder for Closeout Remediation

```
+-----------------------------------------------------------------------------------+
| STRIKE 1 & 2: SOL REPAIR MONOPOLY (FREE & BOUNDED)                                |
| - Tool: python D:/Taadaa/tools/sol_repair.py (:20129 / gpt-web-sol)               |
| - Nature: Single-shot, in-memory AST proposal, git diff <= 30 lines O(1).         |
| - Rule: CẤM thay thế sol_repair bằng sol_worker trong Gate để tránh phình diff.   |
+-----------------------------------------------------------------------------------+
                                          |
                               (Trượt 3 lần trên cùng scope)
                                          v
+-----------------------------------------------------------------------------------+
| STRIKE 3 HAND-OFF: ROLE-SEPARATED CODE FIX & REVIEW                               |
|                                                                                   |
| 1. SỬA CODE & VIẾT TEST: CLAUDE HAIKU WORKER (RẺ & NHẸ QUOTA)                    |
|    - Command: python D:/Taadaa/tools/claude_worker.py --role worker ...           |
|    - Model: claude-haiku-5-5 (chi phí cực thấp, 10-15s, O(1)).                  |
|    - Fallback khi hết quota: ag_cli.py fix (22 acc Google Pro 4G miễn phí).       |
|    - CẤM TUYỆT ĐỐI: Dùng Sonnet 5.5 để mò mẫm viết code hay test!                 |
|                                                                                   |
| 2. THẨM ĐỊNH & PHÊ DUYỆT: CLAUDE SONNET REVIEWER (READ-ONLY, <= 1-2 TURNS)       |
|    - Command: python D:/Taadaa/tools/claude_worker.py --role reviewer ...         |
|    - Model: claude-sonnet-5-5 (chỉ đọc diff đã hoàn thành, max 4-6 turns).       |
|    - Output: In đúng `VERDICT: APPROVED` và findings súc tích.                    |
|                                                                                   |
| 3. AUTO-PUSH QUA SAFE_PUSH:                                                       |
|    - Ghi nhận Audit Binding và push thẳng qua safe_push.py.                       |
|    - CẤM quay lại Sol cày điểm lặp vô tận.                                       |
+-----------------------------------------------------------------------------------+
```

---

## Summary of Invariants
1. **`sol_repair.py` remains the exclusive First Responder for Strike 1 & 2.**
2. **`claude_worker.py --role worker` (Haiku 5.5) does all code and test writing at Strike 3.**
3. **`claude_worker.py --role reviewer` (Sonnet 5.5) is strictly restricted to read-only inspection ($\le 1-2$ turns) for final sign-off.**
