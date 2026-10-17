---
name: agent-review-loops
description: "Điều phối coding review đến APPROVED."
version: 1.2.3
metadata:
  hermes:
    tags: [orchestration, codex, claude, opencode, review-loop, preflight, live-validation]
    related_skills: [claude-code, codex, agent-model-routing, hermes-orchestration-dispatcher]
---

# Agent Review Loops

## 1. Nguyên Tắc Điều Phối & Phân Tầng
- **T1 Sửa nhỏ O(1) <= 15 dòng:** Coordinator tự sửa, verify focused test < 30s.
- **T2 Thi công lớn > 15 dòng:** Single Dispatch Gateway `dispatch_worker.py` (Haiku 5.5 CLI -> Agy CLI).
- **Thẩm định chốt phiên:** Bắt buộc chạy `closeout_gate.py`. Đạt >= 85 (hoặc Grace Band 80-84 diff <= 30) -> auto push qua `safe_push.py`.

## 2. Quy Chuẩn Strike Khắc Phục (3-Strike Reviewer Hand-off)
- **Strike 1 & 2:** Sol Repair (:20129) tạo proposal O(1) AST.
- **Strike 3:** Trượt 3 lần -> Chuyển giao quyền can thiệp cho `claude_worker.py --role worker` (Haiku 5.5) hoặc `ag_cli.py fix`.
- Bỏ qua Sol cày điểm sau khi Claude CLI sửa xong và test pass 100%.

## 3. Tài Liệu Tham Khảo (References)
- Sol Closeout Gate Lifecycle: [`references/sol-closeout-gate-lifecycle.md`](references/sol-closeout-gate-lifecycle.md)
- Anti-Premature Block: [`references/anti-premature-block-in-closeout.md`](references/anti-premature-block-in-closeout.md)
- Session Close Remediation Discipline: [`references/session-close-remediation-discipline.md`](references/session-close-remediation-discipline.md)
