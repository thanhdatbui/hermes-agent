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
  - Grace Band (80-84 điểm): Diff <= 30 dòng (O(1)), 100% test PASS (>= 1 test, 0 fail/err) -> APPROVED và Auto-Push qua `safe_push.py`.
  - ĐỒNG BỘ PRE-PUSH HOOK (THRESHOLD=80): File `.git/hooks/pre-push` và script mẫu `hooks/pre-push.sh` ở các repo (tools, hermes, luotnuoi) bắt buộc đồng bộ `THRESHOLD=80` để khớp tuyệt đối với Grace Band của `closeout_gate.py`, cấm để lệch 85 gây lỗi giả `Gate check FAILED` khi push.
  - CẤM TUYỆT ĐỐI tư duy "WIP branch parking": patch không vào `main` nghĩa là farm không có bản vá, task bắt buộc phải thi công dứt điểm vào `main`.
  - ANTI-PHANTOM CLOSEOUT TRAP: Trước khi chạy closeout_gate.py, BẮT BUỘC kiểm tra `git status --short` và `git diff --stat origin/master..HEAD`. Nếu working tree sạch và local khớp remote (ahead 0), task ĐÃ XONG từ trước, CẤM chạy gate review đè lên commit lịch sử cũ!
  - PER-COMMAND TARGET STAGING: CẤM TUYỆT ĐỐI `git commit -a`, `git add .`, `git add -A`. Bắt buộc chỉ định file đích: `git commit -m "..." -- <target_file> <target_test>`.
  - CHỐNG OVER-ENGINEERING & KHÓC LÓC: CẤM cài Windows ACLs, cấm sửa core.hooksPath toàn cục, cấm HMAC scope lock gây nghẽn runtime/cronjob farm; khi kẹt gate, chạy `git diff --stat` gọt tỉa diff <= 30 dòng để lấy Grace Band auto-push dứt điểm.

## 2. Quy Trình Khắc Phục Khi Trượt (Remediation Protocol)
- **Strike 1:** `sol_repair.py` (:20129) tạo đề xuất AST O(1) <= 30 dòng (miễn phí 100%).
- **Strike 2:** `sol_worker.py` (:20129) ReAct test tích hợp kèm rollback snapshot (miễn phí 100%).
- **Strike 3 Hand-off:** Trượt 3 lần liên tiếp -> Chuyển giao quyền can thiệp cho `claude_worker.py --role worker` (Haiku 5.5) hoặc `ag_cli.py fix`.
- Khống chế tối đa 3 vòng sửa; CẤM vòng lặp vô tận ("loop until tests pass").
- CẤM TUYỆT ĐỐI gọi Claude Sonnet 5.5 để cày điểm closeout gate hoặc sửa code tự động. Sonnet là vũ khí chiến lược đắt đỏ, chỉ chạy khi Operator (User) ra lệnh đích danh.

## 3. Tài Liệu Tham Khảo (References)
- Sol High Scoring Rubric & Diff Budget: [`references/sol-high-scoring-rubric-and-diff-budget.md`](references/sol-high-scoring-rubric-and-diff-budget.md)
- Diff Too Large & Reviewer Handoff: [`references/diff-too-large-and-reviewer-handoff-remediation.md`](references/diff-too-large-and-reviewer-handoff-remediation.md)
- Strike 3 Failure Protocol: [`references/sol-worker-guardrails-and-strike-3-failure-protocol-20261017.md`](references/sol-worker-guardrails-and-strike-3-failure-protocol-20261017.md)
- Pragmatic Alignment & Anti-Phantom Closeout: [`references/pragmatic-alignment-and-phantom-closeout-prevention-20261017.md`](references/pragmatic-alignment-and-phantom-closeout-prevention-20261017.md)
- Call-Site Safety Helper Enforcement & Negative Test Evidence: [`references/callsite-safety-helper-enforcement-and-test-evidence-20261017.md`](references/callsite-safety-helper-enforcement-and-test-evidence-20261017.md)
