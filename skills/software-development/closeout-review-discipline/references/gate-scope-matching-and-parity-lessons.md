# Closeout Gate Hard Lessons: Scope Matching, Diff Budget, and Parity Testing

## 1. Scope Matching & "Refusing partial committed scope"
Khi chạy `closeout_gate.py --repo <path> --base <ref> --files <files...>`:
- Nếu giữa `<ref>` và `HEAD` đã có commit: gate sẽ kiểm tra danh sách file đã commit so với danh sách truyền vào `--files`.
- Nếu commit chạm 3 files nhưng `--files` chỉ truyền 2 files: Gate báo lỗi ngay lập tức:
  `refusing partial committed scope: committed [...] != --files targets [...]`
- **Cách xử lý:** Luôn đồng bộ danh sách file trong commit với danh sách `--files`, hoặc `git reset` commit về working tree và commit chính xác tập files cần audit.
- **Cô lập Scope Khi Working Tree Bị Dirty:** Nếu repo đang có các file dirty hoặc uncommitted từ task khác (ví dụ: `benign_popup_registry.py`), việc chỉ định rõ ràng `--files <file1> <file2>` giúp gate chỉ trích xuất diff của đúng các file trong scope của task hiện tại, ngăn việc reviewer chấm trượt toàn bộ phiên vì các file lạ thiếu test coverage.

## 2. DIFF_TOO_LARGE Hard Ceiling (< 30,000 bytes)
- Gate từ chối thẩm định nếu diff vượt quá 30,000 bytes:
  `[Gate Fail-Fast: DIFF_TOO_LARGE] targeted diff quá lớn (> 30000 bytes)`
- Khi test file phát triển lớn (hàng trăm dòng test cases), refactor các assertions lặp lại thành parameterized loop (`for case in cases:`) để giảm footprint diff mà vẫn giữ nguyên 100% test coverage.

## 3. Strict String Slice Parity Testing (`test_reconcile_helpers_in_sync`)
- Các test case kiểm tra parity giữa `scripts/<script>.py` và `scripts/hermes_cron/<script>.py` cắt trực tiếp substring từ `RECONCILE_METRICS` đến `def reconcile_cluster_following(`.
- Mọi ký tự (kể cả 1 dấu cách, cách import, hay inline vs multi-line) lệch nhau đều làm fail test parity.
- Khi cập nhật logic một bên, bắt buộc đồng bộ chính xác từng dòng sang file cron đối ứng.

## 4. Pre-Push Gate Audit Binding
- Script `safe_push.py <repo> origin master` giải phóng biến môi trường sandbox `GIT_ALLOW_PROTOCOL=file`.
- Pre-push hook bắt buộc tìm thấy entry `APPROVED` (score >= 85) trong `gate_audit.jsonl` khớp cả `commit_sha` và `scope_hash`.
- Cấm tự ý `git push` tay bỏ qua `closeout_gate.py` và `safe_push.py`.

## 5. Thứ Tự Audit Binding & Commit SHA Trong Strike 3 Reviewer Hand-off (17/10/2026)
- **Cạm bẫy lệch Commit SHA (Pre-commit Audit Binding Trap):**
  - Khi chạy Strike 3 Reviewer Hand-off qua Claude Reviewer (`claude_worker.py --role reviewer`), Reviewer thẩm định working tree và trả về `VERDICT: APPROVED`.
  - Nếu Coordinator gọi `closeout_gate.build_audit_binding()` và `write_gate_audit()` **TRƯỚC** khi chạy `git commit`: `audit_binding['commit_sha']` sẽ nhận SHA của commit cha (HEAD cũ).
  - Ngay sau đó, `git commit` tạo ra commit SHA mới. Khi gọi `safe_push.py`, script `.git/hooks/pre-push` duyệt `git rev-parse HEAD` (SHA mới) và đối chiếu với `gate_audit.jsonl` -> **Lập tức bị BLOCKED** với lỗi:
    `❌ [BLOCKED - PRE-PUSH HOOK]: Không tìm thấy bản ghi Closeout Gate APPROVED >= 85 cho commit hiện tại!`
- **Quy tắc Bất Biến khắc phục:**
  1. Thẩm định `VERDICT: APPROVED` và kiểm chứng 4 nấc cơ học (`py_compile`, `pytest 100%`).
  2. Stage đúng scope (`git add <files>`) và tạo commit (`git commit -m "..."`).
  3. **Ngay sau commit:** Gọi `closeout_gate.build_audit_binding(repo, scope)` để lấy đúng `commit_sha` vừa sinh, rồi ghi vào audit log qua `closeout_gate.write_gate_audit(..., audit_binding=binding)`.
  4. Sau đó mới gọi `safe_push.py <repo> <remote> <branch>` để pre-push hook đối soát thành công 100%.
- **Lưu ý Remote Upstream vs Fork:** Trên các repo clone từ nguồn cộng đồng (như `Hermes` có remote `origin` là `NousResearch/hermes-agent.git` và `fork` là repo cá nhân của User), lệnh push mặc định vào `origin` sẽ dính HTTP 403 Forbidden. Kiểm tra `git remote -v` để push đúng remote `fork`.
