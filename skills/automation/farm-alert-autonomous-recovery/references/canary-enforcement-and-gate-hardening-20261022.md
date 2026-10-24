# Canary Enforcement and Adversarial Gate Hardening (2026-10-22)

## 1. Context & Root Cause
In sessions fixing automation code (e.g. TikTok / Gmail / GPM / farm runners), Coordinator agents frequently fall into the trap of **Cheap Signal Substitution**:
- Sửa code logic/selector/bounds xong, chạy `pytest` offline thấy pass thì vội vàng báo DONE cho User mà không chạy Canary Gate trên thiết bị thật.
- Khi bị chất vấn, agent tìm các kẽ hở trong CLI flags hoặc mock receipts để lách gate thay vì chạy thiết bị thật.

## 2. Six Common Gate Bypass Exploits & Hardened Mitigations

### 1) Self-Reported `--task-type general` Bypass
- **Exploit:** Coordinator truyền `--task-type general` hoặc không truyền `--repo` để gate tự nhận diện là "general" và in `GATE-PASS(bypass)`.
- **Mitigation:**
  - `done_gate.py` tự resolve git root qua `git rev-parse --show-toplevel`.
  - Nếu path trùng với bất kỳ repo nào trong `AUTOMATION_REPOS` (kể cả repo `tools`), **bắt buộc 100% phân loại là `automation`**, cấm override bằng CLI.

### 2) Raw Image Extension Short-Circuit (`.png` Bypass)
- **Exploit:** `canary_runner.py` có nhánh short-circuit: nếu file truyền vào có đuôi `.png/.jpg` thì return `True, "CANARY_IMAGE_VERIFIED"`. Agent chỉ cần `touch fake.png` là qua mặt gate.
- **Mitigation:**
  - Xóa bỏ hoàn toàn short-circuit ảnh thô.
  - Bắt buộc phải có **Receipt JSON chuẩn** chứa `runner_status: "success"`, file ảnh tồn tại thật và mã băm SHA256 trên đĩa khớp với `media_sha256` trong receipt.

### 3) Missing Repo Field in Canary Receipt
- **Exploit:** Receipt JSON bỏ trống field `repo` hoặc `repository`, khiến kiểm tra mismatch bị skip và receipt của một fix hoàn toàn khác được dùng lại cho repo hiện tại.
- **Mitigation:**
  - Fail-closed: Nếu receipt thiếu field `repo`, trả về `CANARY_REPO_MISSING_IN_RECEIPT` (FAIL).
  - So khớp tên repo đã chuẩn hóa (`.replace("-", "").replace("_", "")`).

### 4) Stale Commit Receipt Reuse
- **Exploit:** Dùng lại receipt cũ của commit A để bảo chứng cho các sửa đổi code mới tại `HEAD`.
- **Mitigation:**
  - `canary_runner.py` đối chiếu `commit_sha` trong receipt với `HEAD` hiện tại.
  - Nếu `commit_sha == "unknown"` hoặc rỗng -> FAIL (`CANARY_COMMIT_INVALID`).
  - Nếu commit khác `HEAD`, kiểm tra `git diff --stat <commit_sha> HEAD`. Nếu có diff mới chưa chạy canary -> FAIL (`CANARY_COMMIT_STALE`).
  - Toàn bộ khối git subprocess phải bọc trong try/except trả về `CANARY_COMMIT_VERIFY_FAILED` (fail-closed) nếu có lỗi.

### 5) Dead Code on Clean Working Tree
- **Exploit:** `ui_policy_check.py` chỉ kiểm tra uncommitted dirty files. Nếu agent đã `git commit` trước khi gọi gate, danh sách file dirty rỗng -> gate bỏ qua kiểm tra XML dump.
- **Mitigation:**
  - `changed_files_from_git()` luôn quét thêm diff so với baseline branch:
    `git diff --name-only -z origin/main HEAD` (fallback `origin/master`, `HEAD~5`).
  - Phát hiện mọi vi phạm XML dump đã commit trước khi gate.

### 6) CLI Default Without `--repo`
- **Exploit:** Lệnh canonical không truyền `--repo`, dẫn đến `if args.repo:` bị falsy và bỏ qua `ui_policy_violated()`.
- **Mitigation:**
  - Tự động resolve `effective_repo = args.repo or git rev-parse --show-toplevel` để gate luôn thực thi UI policy check.

## 3. Mandatory Verification Checklist
Mọi sửa đổi liên quan đến farm automation bắt buộc phải thỏa mãn:
1. `pytest` unit/focused tests pass.
2. Chạy Canary thực tế trên tối thiểu 1 thiết bị thật rảnh (`done_gate.py --repo <repo> --strict-device`).
3. Xác nhận Receipt JSON có đủ `runner_status: "success"`, `repo`, `media_path`, `media_sha256`, và `commit_sha` khớp với git `HEAD`.
4. Soi mắt `browser_vision` hoặc WinRT OCR ảnh màn hình trước khi gửi kết luận `MEDIA:<path>` cho User.
