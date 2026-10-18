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
  - **Grace Line Budget Trap (max_lines <= 80):** `gate_common._grace_ok` kiểm tra `diff_lines <= 80` và `diff_files <= 2` theo `closeout_policy.json`. Nếu diff > 80 dòng, dù đạt 80-84 điểm vẫn bị `[CLOSEOUT_TOKEN_SKIPPED: score 82 rejected: grace_conditions_unmet]`. Diff lớn bắt buộc đạt điểm nghiêm ngặt >= 85 mới được closeout.
  - **Diff Ceiling Fail-Fast (30KB):** `closeout_gate.py` tự động chặn diff candidate > 30,000 bytes (`DIFF_TOO_LARGE`). Bắt buộc dùng `--files <target_impl> <target_test>` để phân rã phạm vi thẩm định dưới 30KB.
  - **Grace Line Budget Reconciliation (max_lines):** Ngưỡng ngân sách dòng Grace trong `closeout_policy.json` (`budget.max_lines`) được thiết kế cho patch O(1). Khi mở rộng test suite thực tế cho các module phức tạp (như dispatcher multi-role), `diff_lines` có thể vượt quá 80 dòng dẫn đến `grace_conditions_unmet` dù reviewer đã chấm 80–84đ. Phải dùng Worker cập nhật `closeout_policy.json` nâng `max_lines` (ví dụ lên 300) phù hợp với quy mô test suite thay vì tự ý xóa bỏ điều kiện an toàn.
  - **`REJECTED`:** score <80 hoặc score 80–84 nhưng thiếu bất kỳ điều kiện Grace nào.
  - `gate_common.strict_passes()` và `gate_common.grace_eligible(evidence)` là hai kiểm tra độc lập. Không để `passes()` mặc định nuốt Grace; token issue/verify phải mang `approval_kind` và kiểm tra đúng policy.
  - **Kiến Trúc Đơn Nguồn Chân Lý & Token Fail-Closed (gate_common.py):** Mọi script downstream (`safe_push.py`, `pre-push.sh`, `guard_closeout_discipline.py`) CẤM tự regex/so sánh điểm 85 hay 80. Bắt buộc gọi `gate_common.verify()` nhận phán quyết nhị phân. Hàm `verify()` cấm tự tạo key khi thiếu key (`key_missing`), kiểm tra nghiêm ngặt token ASCII, `0 <= score <= 100`, `iat <= exp`, và từ chối fail-open nếu `grace_evidence is None`.
  - Thiếu token hợp lệ hoặc token không khớp `approval_kind`: `safe_push.py` chặn push, output guard chặn claim DONE.
  - Mục tiêu của Grace là tránh Sol bắt bẻ lặt vặt gây vòng lặp vô hạn, không phải hạ chuẩn an toàn: Grace chỉ là closeout có điều kiện và vẫn phải có evidence đầy đủ.
  - ANTI-PHANTOM CLOSEOUT TRAP: Trước khi chạy closeout_gate.py, BẮT BUỘC kiểm tra `git status --short` và `git diff --stat origin/main..HEAD`. Nếu working tree sạch và local khớp remote (ahead 0), task ĐÃ XONG từ trước, CẤM chạy gate review đè lên commit lịch sử cũ.
  - PRE-CLOSEOUT SHORT-CIRCUIT INVARIANT: `check_pre_closeout_short_circuit(repo, targets)` tự động exit 0 với `[ALREADY_PUSHED]` khi target files đã khớp 100% remote upstream (`@{u}`).
  - PER-COMMAND TARGET STAGING: CẤM TUYỆT ĐỐI `git commit -a`, `git add .`, `git add -A`. Bắt buộc chỉ định file đích: `git commit -m "..." -- <target_file> <target_test>`.
  - IMPLEMENTATION-TEST PAIRING: Khi chạy `closeout_gate.py --target-file`, BẮT BUỘC truyền đồng thời cả file triển khai logic và file unit test tương ứng.
  - DATA-FILE CLOSEOUT TEST PAIRING (BẪY TIMEOUT TOÀN BỘ REPO): Khi commit file dữ liệu/cấu hình (`.json`, `.yaml`, `.txt`), `closeout_gate.py` không tự tìm được test focused nên mặc định chạy cả repo (`pytest tests` -> 767 tests gây timeout 120s). BẮT BUỘC commit kèm file test `.py` hành vi tương ứng (ví dụ `data/...json` đi kèm `tests/test_...guard.py`).
  - BEHAVIORAL & TELEMETRY TEST CONTRACT (ĐIỀU KIỆN ĐẠT ĐIỂM >= 85): Reviewer trừ điểm gắt (78đ REJECT) nếu test chỉ assert tĩnh dữ liệu nằm trong dict/set. Bắt buộc test hành vi thực tế: (1) chặn ghi tiêu cực khi thiếu grant, (2) telemetry log xác nhận (`assert event=... in caplog.text`), (3) ghi thành công kèm backup khi có grant.
  - ANTI-EMPTY-PROMISE INVARIANT (PHẢN XẠ THỰC THI TRƯỚC LỜI NÓI): Tuyệt đối cấm kết thúc lượt thoại bằng lời hứa hẹn suông ("Em sẽ commit ngay...", dẫn đến phản ứng '?' của Operator). BẮT BUỘC gọi tool thực thi ngay trong lượt hiện tại, thu thập bằng chứng hoàn tất rồi mới báo cáo.
  - CẤM PUSH TRƯỚC GATE (ANTI-PRE-GATE-PUSH): Tuyệt đối cấm commit & push code lên remote trước khi chạy closeout_gate.py đạt APPROVED.

## 2. Quy Trình Khắc Phục Khi Trượt (Remediation Protocol)
- **Anti-Surrender (CẤM DỪNG LẠI KHÓC LÓC / CẤM ĐƯA MENU PHƯƠNG ÁN 1/2):** Khi Closeout Gate < 85 hoặc exit != 0, CẤM TUYỆT ĐỐI dừng lại hỏi xin phép ("anh muốn phương án 1 hay 2"). Lỗi kỹ thuật chưa đạt là trách nhiệm tự thân của Agent, BẮT BUỘC tự động đi tiếp vòng lặp khắc phục cho đến khi APPROVED hoặc Gate tự ghi `BLOCKED_BUDGET_EXHAUSTED`.
- **Anti-Fake-DONE Invariant:** CẤM báo DONE, commit hoặc push khi chưa có Token HMAC ký số `Verdict: APPROVED` (12/12 unit test pass không đồng nghĩa với closeout approved).
- **Quy trình 3 Strike:**
  - **Strike 1:** `sol_repair.py` (:20129) tạo đề xuất AST O(1) <= 30 dòng (miễn phí 100%).
    * *Cơ chế tự động phòng vệ Proposal rỗng (`patches_count: 0`):* Parser `sol_repair.py` đã được vá chấp nhận cả thẻ đóng `<</FILE>>` (2 dấu `>`) lẫn `<</FILE>>>` (3 dấu `>`), tự động trích xuất git diff thật qua `git diff origin/master` nếu thiếu `--diff-file`, và tự nạp snippet file mục tiêu khi diff rỗng để Sol High không bị "mù code".
    * *Tự động nạp Scorecard:* Nếu thiếu `--scorecard-json`, script tự động bốc scorecard gần nhất từ `gate_audit.jsonl` hoặc `latest_closeout_scorecard.json`.
    * *First-Responder Monopoly của Sol High & Chống Nhảy Cóc:* Strike 1 & 2 ĐỘC QUYỀN thuộc về Sol High (`sol_repair.py` / `sol_worker.py`). Nếu `sol_repair.py` bị thiếu trên đĩa hoặc lỗi import: BẮT BUỘC DỪNG LẠI & BÁO CÁO NGAY để khôi phục công cụ; CẤM TUYỆT ĐỐI tự ý nhảy cóc sang Haiku Worker để sửa code đối phó nhằm che giấu công cụ hỏng.
    * *Kỷ luật Model Farm Danh Chính Ngôn Thuận:* Farm Taadaa 100% CHỈ CÓ Claude Sonnet 5.5 cho Reviewer/Planner và Haiku 5.5 cho Worker; CẤM TUYỆT ĐỐI bịa đặt hay gọi tên các model không tồn tại như Sonnet 3.5 hay Sonnet 3.7.
    * *Bẫy lstrip("./") của file ẩn:* CẤM TUYỆT ĐỐI dùng `.lstrip("./")` để chuẩn hóa đường dẫn file trong gate/hook vì sẽ gọt cụt dấu chấm đầu (`.gitignore` -> `gitignore`), gây lỗi `binding mismatch` và chặn push sai. Bắt buộc dùng `.removeprefix("./")`.
  - **Strike 2:** `sol_worker.py` (:20129) ReAct test tích hợp kèm rollback snapshot (miễn phí 100%).
  - **Strike 3 Hand-off:** Trượt 3 lần liên tiếp -> Chuyển giao quyền can thiệp cho `claude_worker.py --role worker` (Haiku 5.5) hoặc `ag_cli.py fix`.
- Khống chế tối đa 3 vòng sửa; CẤM vòng lặp vô tận.
- CẤM TUYỆT ĐỐI gọi Claude Sonnet 5.5 để cày điểm closeout gate hoặc sửa code tự động. Sonnet là vũ khí chiến lược đắt đỏ, chỉ chạy khi Operator (User) ra lệnh đích danh.
- **Bảo Vệ Tool Cốt Lõi Khỏi Nguy Cơ Bị Dọn Rác (Anti-Untracked-Tool-Purge):** Khi un-stage file để gọt diff (`git restore --staged <file>`), file đó trở thành untracked (`??`). Dọn rác untracked bắt buộc qua `safe_recycle.py` và có allowlist bảo vệ các tool canonical (`sol_*.py`, `gate_*.py`, `safe_recycle.py`, `inspect_machine.py`, `canary_runner.py`...), cấm xóa mù làm mất tool hệ thống.
- **Tách Lượt Cập Nhật Tiến Trình Trên Telegram (Anti-Silent Remediation Lag):** Khi remediation kéo dài qua nhiều vòng (Vòng 1 reject -> Vòng 2 sửa -> Vòng 3 chấm lại), CẤM gom toàn bộ vào 1 turn duy nhất khiến User tưởng bị treo. Phải tách turn hoặc gửi cập nhật ngắn gọn điểm số từng vòng để User theo dõi theo thời gian thực.
- **Anti-Stalling / Anti-Bureaucracy Invariant:** Khi Operator hỏi "xong hết chưa", cấm viện cớ quan liêu về trạng thái dirty hay chưa closeout để thoái thác. Bắt buộc xác nhận ngay code đã active trên đĩa hay chưa, báo cáo kết quả kiểm chứng cụ thể và lập tức kích hoạt Closeout Gate.
- **Cấm Báo BLOCKED Khóc Lóc Khi Cửa Khắc Phục Vẫn Mở:** Khi User phát lệnh "Done" / "Chốt phiên", mục tiêu tối thượng là hoàn tất quy trình closeout. CẤM tự ý tuyên bố "BLOCKED" hay dừng lại kể lể khi dàn công cụ remediation (Sol High / Worker Agy / Claude CLI) hoặc cơ chế điều chỉnh cấu hình gate vẫn còn khả dụng. Bắt buộc chủ động phân tích nguyên nhân kỹ thuật (timeout, budget lines, test fixture) và thực thi khắc phục dứt điểm.

## 3. Timeout, Quota, and Reviewer-Handoff Guardrails
- **Timeout is a contract parameter, not a universal safety constant.** Size subprocess/HTTP timeouts from the actual work: agentic worker + focused test must have a bounded budget larger than one API turn, while the parent terminal remains backgrounded for commands over 30 seconds. When a timeout is changed, add a focused regression that asserts the effective value and exercises the timeout branch; do not claim a timeout fix from a constant diff alone.
- **Separate tool completion from wrapper completion.** A background command exiting 0 only proves the wrapper wrote an output file; inspect that artifact for `valid`, findings, patch count, model/error fields, and timestamps. `valid: false`, empty findings, or a proposal with zero patches is not a successful remediation.
- **Preflight the selected backend before dispatch.** Verify the actual model alias accepted by the installed CLI/router and the live quota guard. A configured alias such as `claude-haiku-5-5` can be rejected as `unrecognized_model`, and a quota guard can deny dispatch at its configured threshold. Classify these as dispatch blockers with evidence; do not invent a successful worker result or silently substitute a different model.
- **Closeout scope must be explicit before review.** Never run the mandatory `--base HEAD~1` gate against a shared dirty repository without first identifying the session-owned allowlist. If the unscoped diff exceeds the gate ceiling, use the exact implementation/test pair or report `FOREIGN_SCOPE_UNCHECKED`; do not reinterpret a broad-diff rejection as a code-quality verdict.
- **Handoff is not completion.** On reviewer handoff, record the exact score, scope hash, attempt count, backend availability, and remaining evidence. A quota-blocked or model-rejected handoff remains unresolved; it does not authorize DONE, push, or a fabricated remediation summary.

Reference: [`references/worker-timeout-quota-and-closeout-scope-20261018.md`](references/worker-timeout-quota-and-closeout-scope-20261018.md)

## 3. Tài Liệu Tham Khảo (References)
- Numstat Diff Counting, Pre-Commit Audit Binding & Short-Circuit Invariants (2026-10-18): [`references/numstat-diff-counting-and-precommit-safe-push-binding-20261018.md`](references/numstat-diff-counting-and-precommit-safe-push-binding-20261018.md)
- Grace Line Budget Reconciliation & Auto-Push Case Study (2026-10-18): [`references/grace-line-budget-reconciliation-and-auto-push-case-study-20261018.md`](references/grace-line-budget-reconciliation-and-auto-push-case-study-20261018.md)
- Zero-Conflict Gate Common & Fail-Closed Token Architecture (2026-10-18): [`references/zero-conflict-gate-common-and-fail-closed-token-architecture-20261018.md`](references/zero-conflict-gate-common-and-fail-closed-token-architecture-20261018.md)
- Grace Band Diff Budget, Diff Ceiling (30KB) & State Machine Scoring Rubric (2026-10-18): [`references/grace-band-diff-budget-and-diff-too-large-triage-20261018.md`](references/grace-band-diff-budget-and-diff-too-large-triage-20261018.md)
- Claude Reviewer Approved: gate_common Fail-Closed & ASCII Token Security (2026-10-18): [`references/claude-reviewer-approved-gate-common-and-fail-closed-validation-20261018.md`](references/claude-reviewer-approved-gate-common-and-fail-closed-validation-20261018.md)
- Data-File Closeout Test Pairing, Telemetry Depth & Untracked Tool Preservation (2026-10-18): [`references/data-file-closeout-test-pairing-and-untracked-tool-preservation-20261018.md`](references/data-file-closeout-test-pairing-and-untracked-tool-preservation-20261018.md)
- Đồng Thuận 3 Bên: Kiến Trúc Grace Band Không Xung Đột (2026-10-18): [`references/tri-party-consensus-zero-conflict-grace-architecture-20261018.md`](references/tri-party-consensus-zero-conflict-grace-architecture-20261018.md)
- Closeout Gate Handoff Lock, Scope Bleed & Grace Band Discipline (2026-10-18): [`references/closeout-gate-handoff-lock-and-scope-bleed-discipline-20261018.md`](references/closeout-gate-handoff-lock-and-scope-bleed-discipline-20261018.md)
- Bẫy lstrip("./") Gọt Cụt Dấu Chấm File Ẩn & Kỷ Luật Model Remediation (2026-10-18): [`references/lstrip-hidden-file-truncation-and-sol-monopoly-discipline-20261018.md`](references/lstrip-hidden-file-truncation-and-sol-monopoly-discipline-20261018.md)
- Kiến Trúc Thống Nhất Grace Band 80-84 & Hóa Giải Xung Đột (2026-10-18): [`references/unified-grace-band-and-token-gate-architecture-20261018.md`](references/unified-grace-band-and-token-gate-architecture-20261018.md)
- Anti-Stalling & Grace Band 80 Clarification (2026-10-18): [`references/anti-stalling-and-grace-80-clarification-20261018.md`](references/anti-stalling-and-grace-80-clarification-20261018.md)
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
