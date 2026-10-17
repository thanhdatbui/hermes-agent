---
name: closeout-review-discipline
description: "Use for code closeout review loops."
version: 1.0.0
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [closeout, review, evidence, staging, truncation, orchestration]
    related_skills: [requesting-code-review, session-close-protocol, agent-model-routing]
---

# Closeout Review Discipline

## 1. Cơ Chế Thẩm Định & Ngưỡng Điểm
- **Lệnh thực thi duy nhất:**
  `python D:/Taadaa/tools/closeout_gate.py --repo <đường_dẫn_repo> --base origin/main --json-output`
- **Ngưỡng phê duyệt (Verdict APPROVED):**
  - Điểm >= 85/100: APPROVED -> Tiến hành Push.
  - Grace Band (80-84 điểm): Diff <= 30 dòng, 100% test PASS (>= 1 test, 0 fail/err) -> Auto-Push qua `safe_push.py`.
  - Hook `.git/hooks/pre-push` đã ép cứng chặn đứng mọi commit có điểm < 80 hoặc test trượt.

## 2. Quy Trình Khắc Phục Khi Trượt (Remediation Protocol)
- **Strike 1:** `sol_repair.py` (:20129) tạo đề xuất AST O(1) <= 30 dòng (miễn phí 100%).
- **Strike 2:** `sol_worker.py` (:20129) ReAct test tích hợp kèm rollback snapshot.
- **Strike 3 Hand-off:** Trượt 3 lần liên tiếp -> Chuyển giao quyền can thiệp cho `claude_worker.py --role worker` (Haiku 5.5) hoặc `ag_cli.py fix`.
- CẤM TUYỆT ĐỐI gọi Claude Sonnet 5.5 để cày điểm closeout gate.

## 3. Tài Liệu Tham Khảo (References)
- Sol High Scoring Rubric & Diff Budget: [`references/sol-high-scoring-rubric-and-diff-budget.md`](references/sol-high-scoring-rubric-and-diff-budget.md)
- Diff Too Large & Reviewer Handoff: [`references/diff-too-large-and-reviewer-handoff-remediation.md`](references/diff-too-large-and-reviewer-handoff-remediation.md)
- Strike 3 Failure Protocol: [`references/sol-worker-guardrails-and-strike-3-failure-protocol-20261017.md`](references/sol-worker-guardrails-and-strike-3-failure-protocol-20261017.md)
