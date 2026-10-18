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
- **Hai mức phê duyệt, không nhập nhằng:**
  - **`STRICT_APPROVED`:** score là `int >= 85`; phát hành strict HMAC token.
  - **`GRACE_APPROVED`:** chỉ cho score `80–84` khi *đồng thời* focused test xanh, diff <= 30 dòng tổng cộng, <= 2 files, không chạm protected path, không có critical finding, không có reviewer handoff/strike lock. Phải phát hành grace token riêng; không được in/diễn giải thành generic `APPROVED`.
  - **`REJECTED`:** score <80 hoặc score 80–84 nhưng thiếu bất kỳ điều kiện Grace nào.
  - `gate_common.strict_passes()` và `gate_common.grace_eligible(evidence)` là hai kiểm tra độc lập. Không để `passes()` mặc định nuốt Grace; token issue/verify phải mang `approval_kind` và kiểm tra đúng policy.
  - Thiếu token hợp lệ hoặc token không khớp `approval_kind`: `safe_push.py` chặn push, output guard chặn claim DONE.
  - Mục tiêu của Grace là tránh Sol bắt bẻ lặt vặt gây vòng lặp vô hạn, không phải hạ chuẩn an toàn: Grace chỉ là closeout có điều kiện và vẫn phải có evidence đầy đủ.
  - ANTI-PHANTOM CLOSEOUT TRAP: Trước khi chạy closeout_gate.py, BẮT BUỘC kiểm tra `git status --short` và `git diff --stat origin/main..HEAD`. Nếu working tree sạch và local khớp remote (ahead 0), task ĐÃ XONG từ trước, CẤM chạy gate review đè lên commit lịch sử cũ.
  - PRE-CLOSEOUT SHORT-CIRCUIT INVARIANT: `check_pre_closeout_short_circuit(repo, targets)` tự động exit 0 với `[ALREADY_PUSHED]` khi target files đã khớp 100% remote upstream (`@{u}`).
  - PER-COMMAND TARGET STAGING: CẤM TUYỆT ĐỐI `git commit -a`, `git add .`, `git add -A`. Bắt buộc chỉ định file đích: `git commit -m "..." -- <target_file> <target_test>`.
  - IMPLEMENTATION-TEST PAIRING: Khi chạy `closeout_gate.py --target-file`, BẮT BUỘC truyền đồng thời cả file triển khai logic và file unit test tương ứng.
  - CẤM PUSH TRƯỚC GATE (ANTI-PRE-GATE-PUSH): Tuyệt đối cấm commit & push code lên remote trước khi chạy closeout_gate.py đạt APPROVED.

## 2. Quy Trình Khắc Phục Khi Trượt (Remediation Protocol)
- **Anti-Surrender (CẤM DỪNG LẠI KHÓC LÓC / CẤM ĐƯA MENU PHƯƠNG ÁN 1/2):** Khi Closeout Gate < 85 hoặc exit != 0, CẤM TUYỆT ĐỐI dừng lại hỏi xin phép ("anh muốn phương án 1 hay 2"). Lỗi kỹ thuật chưa đạt là trách nhiệm tự thân của Agent, BẮT BUỘC tự động đi tiếp vòng lặp khắc phục cho đến khi APPROVED hoặc Gate tự ghi `BLOCKED_BUDGET_EXHAUSTED`.
- **Anti-Fake-DONE Invariant:** CẤM báo DONE, commit hoặc push khi chưa có Token HMAC ký số `Verdict: APPROVED` (12/12 unit test pass không đồng nghĩa với closeout approved).
- **Quy trình 3 Strike:**
  - **Strike 1:** `sol_repair.py` (:20129) tạo đề xuất AST O(1) <= 30 dòng (miễn phí 100%).
    * *Cơ chế tự động phòng vệ Proposal rỗng (`patches_count: 0`):* Parser `sol_repair.py` đã được vá chấp nhận cả thẻ đóng `<</FILE>>` (2 dấu `>`) lẫn `<</FILE>>>` (3 dấu `>`), tự động trích xuất git diff thật qua `git diff origin/master` nếu thiếu `--diff-file`, và tự nạp snippet file mục tiêu khi diff rỗng để Sol High không bị "mù code".
    * *Tự động nạp Scorecard:* Nếu thiếu `--scorecard-json`, script tự động bốc scorecard gần nhất từ `gate_audit.jsonl` hoặc `latest_closeout_scorecard.json`.
  - **Strike 2:** `sol_worker.py` (:20129) ReAct test tích hợp kèm rollback snapshot (miễn phí 100%).
  - **Strike 3 Hand-off:** Trượt 3 lần liên tiếp -> Chuyển giao quyền can thiệp cho `claude_worker.py --role worker` (Haiku 5.5) hoặc `ag_cli.py fix`.
- Khống chế tối đa 3 vòng sửa; CẤM vòng lặp vô tận.
- CẤM TUYỆT ĐỐI gọi Claude Sonnet 5.5 để cày điểm closeout gate hoặc sửa code tự động. Sonnet là vũ khí chiến lược đắt đỏ, chỉ chạy khi Operator (User) ra lệnh đích danh.
- **Anti-Stalling / Anti-Bureaucracy Invariant:** Khi Operator hỏi "xong hết chưa", cấm viện cớ quan liêu về trạng thái dirty hay chưa closeout để thoái thác. Bắt buộc xác nhận ngay code đã active trên đĩa hay chưa, báo cáo kết quả kiểm chứng cụ thể và lập tức kích hoạt Closeout Gate.

## 3. Tài Liệu Tham Khảo (References)
- Grace Band (80-84) & Chống Cày Điểm Vụn Vặt (2026-10-18): [`references/grace-band-80-84-and-anti-score-chasing-20261018.md`](references/grace-band-80-84-and-anti-score-chasing-20261018.md)
- Sol Repair Empty Proposal & Closing Tag Invariant (2026-10-18): [`references/sol-repair-empty-proposal-and-closing-tag-patch-20261018.md`](references/sol-repair-empty-proposal-and-closing-tag-patch-20261018.md)
- Sol Repair Empty Proposal Pitfall & Pytest PYTHONPATH: [`references/sol-repair-empty-proposal-and-pytest-pythonpath-pitfalls-20261018.md`](references/sol-repair-empty-proposal-and-pytest-pythonpath-pitfalls-20261018.md)
- Pytest PYTHONPATH & Direct Test Pairing trong Closeout Gate: [`references/closeout-gate-pytest-pythonpath-and-direct-test-pairing-20261018.md`](references/closeout-gate-pytest-pythonpath-and-direct-test-pairing-20261018.md)
- Xóa Bỏ Grace Band & HMAC Token-Gated Closeout: [`references/grace-band-elimination-and-hmac-token-gated-closeout-20261018.md`](references/grace-band-elimination-and-hmac-token-gated-closeout-20261018.md)
- Anti-Surrender Remediation & Fake-DONE Invariant: [`references/anti-surrender-closeout-remediation-and-fake-done-invariant.md`](references/anti-surrender-closeout-remediation-and-fake-done-invariant.md)
- Pre-Closeout Short-Circuit & Chống Cày Điểm Commit Session Khác: [`references/pre-closeout-short-circuit-and-anti-score-chasing-20261018.md`](references/pre-closeout-short-circuit-and-anti-score-chasing-20261018.md)
- Anti-Apology Theater & Action-First Discipline: [`references/anti-apology-theater-and-action-first-discipline-20261018.md`](references/anti-apology-theater-and-action-first-discipline-20261018.md)
- Single-Commit Pre-Push Scope Matching & Squash Gate: [`references/single-commit-pre-push-scope-matching-and-squash-gate-20261018.md`](references/single-commit-pre-push-scope-matching-and-squash-gate-20261018.md)
- Sol High Scoring Rubric & Diff Budget: [`references/sol-high-scoring-rubric-and-diff-budget.md`](references/sol-high-scoring-rubric-and-diff-budget.md)
- Strike 3 Failure Protocol: [`references/sol-worker-guardrails-and-strike-3-failure-protocol-20261017.md`](references/sol-worker-guardrails-and-strike-3-failure-protocol-20261017.md)
