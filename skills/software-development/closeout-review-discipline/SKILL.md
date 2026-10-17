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
  - ANTI-PHANTOM CLOSEOUT TRAP: Trước khi chạy closeout_gate.py, BẮT BUỘC kiểm tra `git status --short` và `git diff --stat origin/main..HEAD` (hoặc `origin/master..HEAD`). Nếu working tree sạch và local khớp remote (ahead 0), task ĐÃ XONG từ trước (hoặc đã push qua safe_push trong phiên), CẤM chạy gate review đè lên commit lịch sử cũ! Việc chạy gate lên commit đã push sẽ dẫn đến báo rớt điểm giả trên commit cũ khiến User bức xúc ("chưa đủ điểm sao commit push hết rồi").
  - CẤM PUSH TRƯỚC GATE (ANTI-PRE-GATE-PUSH): Tuyệt đối cấm commit & push code lên remote trước khi chạy closeout_gate.py. Mọi bản vá bắt buộc phải qua thẩm định Sol đạt APPROVED (>= 85 hoặc Grace Band 80-84) trước mới được phép push qua safe_push.py.
  - REJECTION OVERRIDES PUSH STATE (CẤM ĐÓNG PHIÊN KHI GATE RỚT KỂ CẢ ĐÃ LỠ PUSH): Kể cả khi commit đã lỡ bị push lên remote, một khi closeout_gate.py chấm REJECTED (< 85), phiên BẮT BUỘC bước vào vòng lặp Remediation. CẤM TUYỆT ĐỐI vin vào việc working tree sạch hay remote ahead 0 để tuyên bố hoàn thành hoặc đóng phiên!
  - ZERO EXCUSES & ACTION-FIRST (CHỐNG PHÂN BUA THỜI GIAN): Khi User bắt lỗi vi phạm quy trình/rớt điểm, CẤM giải thích rườm rà thứ tự thời gian, cấm thanh minh hay xin lỗi suông. BẮT BUỘC nhận lỗi trong 1 câu và lập tức thực thi hành động kỹ thuật khắc phục triệt để.
  - CHỐNG VĂN MẪU XIN LỖI ĐỐI PHÓ & VÒNG LẶP TÁI PHẠM (ANTI-APOLOGY THEATER & ZERO DRAMA - 2026-10-18):
    * CẤM TUYỆT ĐỐI văn mẫu kịch tính hóa ("cúi đầu nhận lỗi", "xin nhận lỗi nặng nhất", "nhận tội sâu sắc"). Người dùng cực kỳ dị ứng với vòng lặp: Vi phạm quy trình -> Xin lỗi thống thiết -> Tái phạm -> Lại xin lỗi tiếp ("Tóm lại là mày tiếp tục vi phạm quy trình và đòi xin lỗi tiếp?").
    * CẤM hỏi xin phép thừa thãi ("sếp có muốn em sửa không hay để vậy") đối với lỗi kỹ thuật/rớt gate hiển nhiên.
    * KỶ LUẬT THỰC THI: Thừa nhận vi phạm trong đúng 1 câu ngắn gọn không thanh minh, và LẬP TỨC THỰC THI kỹ thuật sửa triệt để trong cùng lượt, đưa ra kết quả và bằng chứng thay vì lời xin lỗi.
  - PER-COMMAND TARGET STAGING: CẤM TUYỆT ĐỐI `git commit -a`, `git add .`, `git add -A`. Bắt buộc chỉ định file đích: `git commit -m "..." -- <target_file> <target_test>`.
  - IMPLEMENTATION-TEST PAIRING (ĐỒNG BỘ TARGET FILE & TRÁNH TEST-ONLY GATE): Khi chạy `closeout_gate.py --target-file`, BẮT BUỘC truyền đồng thời cả file triển khai logic và file unit test tương ứng. Chỉ truyền file test sẽ bị Reviewer đánh rớt do thiếu bằng chứng mã nguồn (57-63đ). Cả hai file phải cùng ở trạng thái working tree dirty hoặc cùng staged (`git add <impl> <test>`). Mock file I/O trong test phải mock đúng namespace `builtins.open`.
  - HOOK PRE-COMMIT CRASH DO GIT_EXTERNAL_DIFF RỖNG (STAGED-GATE FALLBACK - 2026-10-18): Khi môi trường sandbox inject `GIT_EXTERNAL_DIFF=""`, các pre-commit hook chạy `git diff` nội bộ sẽ crash (`error: cannot spawn : No such file or directory; fatal: external diff died`). Thay vì dùng cờ cấm hoặc cố bypass hook, BẮT BUỘC dùng `git add <target_files>` đưa vào Staging Index rồi chạy `closeout_gate.py --base HEAD --json-output`; `closeout_gate.py` bóc tách staged diff với cờ `--no-ext-diff` chuẩn mực để hoàn tất thẩm định.
  - CHỐNG OVER-ENGINEERING & KHÓC LÓC: CẤM cài Windows ACLs, cấm sửa core.hooksPath toàn cục, cấm HMAC scope lock gây nghẽn runtime/cronjob farm; khi kẹt gate, chạy `git diff --stat` gọt tỉa diff <= 30 dòng để lấy Grace Band auto-push dứt điểm.
  - CẤM TUYỆT ĐỐI BẢO USER SỬA TAY (ANTI-SURRENDER): Khi gặp Guard chặn phương thức thô (như `config.yaml`), CẤM bảo User mở Notepad hay sửa thủ công. BẮT BUỘC dùng công cụ có kiểu chuẩn (`manage_hermes_config.py`) hoặc viết script có validation/atomic-write trong `D:/Taadaa/tools/` để thi công dứt điểm.
  - TỰ THẨM ĐỊNH KHI CLAUDE QUOTA CẠN (SELF-REVIEW DISCIPLINE): Khi Claude CLI chạm ngưỡng bảo vệ (85%+), CẤM gửi câu hỏi clarify xin mở quota hay ngồi chờ. Coordinator BẮT BUỘC tự đứng ra làm reviewer soi diff, fallback sang Agy CLI (`python D:/Taadaa/tools/ag_cli.py fix`) O(1) để sửa (TUYỆT ĐỐI CẤM dùng Luna hay delegate_task cho tác vụ sửa code), và tự chạy inline test / focused test kiểm chứng xanh 100%.
  - SINGLE-COMMIT PRE-PUSH SCOPE MATCHING (SQUASH TRƯỚC GATE KHI CÓ MULTI-COMMIT CHUỖI SỬA): Pre-push hook kiểm tra `diff-tree -r HEAD` của commit HEAD với `audit_binding.scope` và `scope_hash` trong `gate_audit.jsonl`. Khi phiên làm việc qua nhiều commit nhỏ (sửa impl -> sửa test -> gọt tỉa), chạy closeout_gate trên dải `--base <commit_gốc>` sẽ ghi nhận scope của toàn dải, dẫn đến pre-push hook từ chối vì `diff-tree HEAD` của commit con cuối cùng không khớp toàn bộ scope đã thẩm định. BẮT BUỘC dùng `git reset --soft <base_commit>` gom toàn bộ thay đổi hoàn chỉnh (cả implementation và unit tests) vào DUY NHẤT 1 commit trước khi chạy closeout_gate thẩm định cuối; khi đó HEAD commit_sha và diff-tree scope khớp tuyệt đối 100% với audit log, cho phép `safe_push.py` thông qua mượt mà.

## 2. Quy Trình Khắc Phục Khi Trượt (Remediation Protocol)
- **Anti-Surrender (Cấm Dừng Lại Khóc Lóc):** Khi Closeout Gate < 85 hoặc exit != 0, CẤM TUYỆT ĐỐI dừng lại hỏi xin phép ("anh muốn phương án 1 hay 2"). Bắt buộc tự động đi tiếp vòng lặp khắc phục cho đến khi APPROVED hoặc Gate tự ghi BLOCKED_BUDGET_EXHAUSTED.
- **Anti-Fake-DONE Invariant:** CẤM báo DONE, commit hoặc push khi chưa có `Verdict: APPROVED` (12/12 unit test pass không đồng nghĩa với closeout approved).
- **Strike 1:** `sol_repair.py` (:20129) tạo đề xuất AST O(1) <= 30 dòng (miễn phí 100%).
- **Strike 2:** `sol_worker.py` (:20129) ReAct test tích hợp kèm rollback snapshot (miễn phí 100%).
- **Strike 3 Hand-off:** Trượt 3 lần liên tiếp -> Chuyển giao quyền can thiệp cho `claude_worker.py --role worker` (Haiku 5.5) hoặc `ag_cli.py fix`.
- Khống chế tối đa 3 vòng sửa; CẤM vòng lặp vô tận ("loop until tests pass").
- CẤM TUYỆT ĐỐI gọi Claude Sonnet 5.5 để cày điểm closeout gate hoặc sửa code tự động. Sonnet là vũ khí chiến lược đắt đỏ, chỉ chạy khi Operator (User) ra lệnh đích danh.

## 3. Tài Liệu Tham Khảo (References)
- Anti-Surrender Remediation & Fake-DONE Invariant: [`references/anti-surrender-closeout-remediation-and-fake-done-invariant.md`](references/anti-surrender-closeout-remediation-and-fake-done-invariant.md)
- Single-Commit Pre-Push Scope Matching & Squash Gate: [`references/single-commit-pre-push-scope-matching-and-squash-gate-20261018.md`](references/single-commit-pre-push-scope-matching-and-squash-gate-20261018.md)
- Target Scope Cohesion & Implementation-Test Pairing: [`references/target-scope-cohesion-and-implementation-test-pairing-20261018.md`](references/target-scope-cohesion-and-implementation-test-pairing-20261018.md)
- Staged-Gate Fallback & Git External Diff Environment Sanitization: [`references/staged-gate-fallback-and-git-external-diff-crash-20261018.md`](references/staged-gate-fallback-and-git-external-diff-crash-20261018.md)
- Anti-Apology Theater & Action-First Discipline: [`references/anti-apology-theater-and-action-first-discipline-20261018.md`](references/anti-apology-theater-and-action-first-discipline-20261018.md)
- Rejection Overrides Push State & Zero-Excuses Invariant: [`references/rejection-overrides-push-state-and-zero-excuses-invariant-20261018.md`](references/rejection-overrides-push-state-and-zero-excuses-invariant-20261018.md)
- Anti-Pre-Gate-Push & Phantom Closeout Trap: [`references/anti-pre-gate-push-and-phantom-closeout-trap-20261018.md`](references/anti-pre-gate-push-and-phantom-closeout-trap-20261018.md)
- Sol High Scoring Rubric & Diff Budget: [`references/sol-high-scoring-rubric-and-diff-budget.md`](references/sol-high-scoring-rubric-and-diff-budget.md)
- Diff Too Large & Reviewer Handoff: [`references/diff-too-large-and-reviewer-handoff-remediation.md`](references/diff-too-large-and-reviewer-handoff-remediation.md)
- Strike 3 Failure Protocol: [`references/sol-worker-guardrails-and-strike-3-failure-protocol-20261017.md`](references/sol-worker-guardrails-and-strike-3-failure-protocol-20261017.md)
- Pragmatic Alignment & Anti-Phantom Closeout: [`references/pragmatic-alignment-and-phantom-closeout-prevention-20261017.md`](references/pragmatic-alignment-and-phantom-closeout-prevention-20261017.md)
- Anti-Surrender Guard Failure & Capability Tools: [`references/anti-surrender-guard-and-capability-config-tools-20261017.md`](references/anti-surrender-guard-and-capability-config-tools-20261017.md)
- Call-Site Safety Helper Enforcement & Negative Test Evidence: [`references/callsite-safety-helper-enforcement-and-test-evidence-20261017.md`](references/callsite-safety-helper-enforcement-and-test-evidence-20261017.md)
- Header Normalization Consumer Drift & Slot Scrambling: [`references/header-normalization-consumer-drift-and-slot-scrambling-20261017.md`](references/header-normalization-consumer-drift-and-slot-scrambling-20261017.md)
