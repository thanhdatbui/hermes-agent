---
name: mechanical-guidance-gate-design
description: "Use when designing mechanical gates to prevent agent loops."
---

# Mechanical Guidance Gate Design (Anti-Whining & Action Mandate)

## 1. When to Use
Use when creating, modifying, or reviewing mechanical enforcement gates (pre-tool hooks, git hooks, closeout gates, or runtime fences). Enforces that every gate provides deterministic, actionable unblocking paths rather than passive denials.

## 2. Core Standards (Tri-Party Consensus)

### Rule 1: No Silent Veto Gates (Cấm Veto Gate Câm)
- **Violation:** A gate checks a condition, fails, prints a static error (e.g. `[DENY] Policy violated`), and executes `sys.exit(1)` without providing executable next steps. This leaves an LLM agent in a cognitive void, triggering apologetic loops or bureaucratic helplessness.
- **Requirement:** Every non-zero exit from a gate MUST provide a machine-readable `REQUIRED_ACTION_O1` block with copy-pasteable commands and a domain-specific `guidance` string explaining the architectural invariant.

```json
{
  "gate": "<gate_name>",
  "verdict": "BLOCKED",
  "reason": "<1-line failure summary>",
  "guidance": "<architectural rationale and invariant>",
  "REQUIRED_ACTION_O1": {
    "command": "<concrete_executable_command_with_resolved_paths>",
    "expected_effect": "<what running this command achieves>",
    "fallback_if_fails": "<alternative command if primary fails>"
  },
  "evidence_path": "<audit_log_or_diff_path>"
}
```

### Rule 2: Anti-Bypass Whitelist (Chống Self-Bypass)
- The command provided in `REQUIRED_ACTION_O1` MUST NEVER be a bypass flag (`--force`, `--no-verify`, `--skip-test`, `--allow`).
- Permitted action types:
  1. Scope reduction (narrowing diff to $\le 30$ lines on target file).
  2. Evidence generation (focused test, targeted log inspection).
  3. Canonical fast-path redirection (e.g., using `lookup_channel.py` instead of broad disk scans).

### Rule 3: Reversibility & Auto-Quarantine O(1)
- When a gate intercepts invalid code or staged artifacts, it should automatically quarantine the offending hunk (e.g., via `git stash push --keep-index -m "quarantine-<rule>-<ts>" -- <file>`) to restore a clean working tree.
- The agent is informed of the quarantine reference and can proceed without fear of a dirty workspace.

### Rule 4: Strike 3 Guidance Gap & Cryptographic Hash-Isolated Self-Update
- If an agent fails the same invariant 3 consecutive times (`STRIKE-3-GUIDANCE-GAP`), do NOT allow bureaucratic idling (such as creating a ticket JSON and freezing).
- **Core Distinction:** Separate Enforcement (predicates, min/max values, target files) from Guidance (architectural explanation text).
- **Enforcement Invariant (Cấm Tự Sửa Logic Chặn):** LLM MUST NEVER have write permission to the enforcement schema or be able to self-approve a blocked diff.
- **Safe Self-Update via Hash-Isolation Tool (O(1)):**
  1. The LLM can invoke a dedicated atomic tool:
     `python D:/Taadaa/tools/guardgate/update_guidance.py --rule-id "<rule_id>" --guidance "<bài học kiến trúc>"`
  2. The tool computes `hash_enforcement` on an independent pre-mutation snapshot, updates only `guidance`, and computes `hash_enforcement` post-mutation.
  3. Strict invariant: `assert hash_before == hash_after`. If any enforcement field (`match`, `require_all`, `params`, `on_deny`, `vectors`) is touched, it fails fast with `AssertionError`.
  4. Write safety: Atomic replace (`_atomic_write_json` via tempfile + `fsync` + `os.replace`) with automatic rollback of `rules.json` if audit logging fails.
  5. **No Self-Bypass:** Updating guidance serves future sessions, but the violating diff of the current session remains REJECTED/QUARANTINED. The agent reports the updated guidance and pivots to an independent task.

## 3. Pitfalls & Anti-Paralysis Principles (Chống Khóc Lóc Bại Liệt)
- **Cấm Nhãn BLOCKED Để Hợp Pháp Hóa Bỏ Dở:** Một failure mode phổ biến của Agent là "khóc lóc quan liêu" — tự dán nhãn `BLOCKED`, ghi ticket vào file JSON rồi tắt máy dừng việc. Gate chặn là lan can bảo vệ chỉ ra hướng đi sai, BẮT BUỘC Agent phải bẻ lái (Pivot) tìm nguyên nhân gốc hoặc tự động cập nhật guidance để thi công tiếp, tuyệt đối không được viện cớ an toàn để đóng băng phiên.
- **Tự Động Hóa Không Cần Human Duyệt Proposal:** Tránh bẫy "bình mới rượu cũ" khi Strike 3 bắt Agent tạo file proposal rồi đứng chờ User duyệt. Phải dùng tool tự động `update_guidance.py` với cryptographic hash-isolation để nạp guidance tự động, auto-quarantine hunk lỗi và làm tiếp ngay.
- **Xử Lý Khi User Trực Tiếp Ra Lệnh:** Khi User xuất hiện chỉ đạo "tìm cách sửa guard / nới lỏng rule", Agent phải hiểu đó là lệnh thẩm quyền tối cao từ Operator để cập nhật lại cấu hình/guidance của Gate, không được máy móc viện cớ "em bị cấm sửa guard" rồi ngồi im bất động.
- **Hardcoding Dead Metadata:** Writing `"on_deny": {"redirect": "sol_repair"}` in JSON without runtime execution logic renders the redirect useless. The gate must output the exact CLI invocation.
- **Broad Scanning Fallback:** Blocking disk scans without providing a canonical lookup tool (such as `lookup_channel.py`) forces agents to invent 30+ tool call workarounds.

## 4. References
- Bi Kịch 37 Tool Calls & Tiêu Chuẩn Action Mandate O(1): [`references/anti-whining-guidance-gate-and-o1-lookup.md`](references/anti-whining-guidance-gate-and-o1-lookup.md)
