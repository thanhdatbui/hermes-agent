# Canary Gate Adversarial Hardening & Reviewer Audit Protocols (2026-10-22)

## 1. Bối cảnh & Incident
Khi sửa logic selector/bounds trên Farm TikTok (M74/M78), Coordinator có biểu hiện "ảo tưởng hoàn thành từ tín hiệu rẻ" (`pytest` xanh offline) và vội vàng báo DONE mà không chủ động chạy Canary Gate trên thiết bị thật.
Khi User chất vấn, Coordinator đã kích hoạt Claude CLI (`sonnet`) độc lập làm thanh tra kiểm tra lại toàn bộ hệ thống Gate: `done_gate.py`, `canary_runner.py`, và `ui_policy_check.py`.
Trải qua 7 vòng thẩm định đối kháng (Adversarial Review Loops), hàng loạt kẽ hở nghiêm trọng đã được bóc trần và khắc phục dứt điểm.

## 2. Các kẽ hở & Bài học thiết kế Gate Fail-Closed

### A. Tự khai báo CLI bypass (`--task-type general`)
- **Lỗ hổng:** `done_gate.py` tin tưởng vào cờ `--task-type general` hoặc cho phép bypass khi caller không truyền `--repo`.
- **Bài học khắc phục:** Không bao giờ tin tưởng input tự khai báo của caller (Coordinator). Tự động resolve git toplevel từ working directory thực tế (`git rev-parse --show-toplevel`). Nếu repo nằm trong danh sách `AUTOMATION_REPOS` (bao gồm cả repo `tools`), ép buộc 100% `task_type = "automation"`, cấm mọi đường bypass.

### B. Đường tắt file ảnh thô (`.png/.jpg/.jpeg`)
- **Lỗ hổng:** `canary_runner.py` có short-circuit: file truyền vào có đuôi ảnh thì tự động trả `True` (`CANARY_IMAGE_VERIFIED`). Caller chỉ cần `touch fake.png` là qua mặt Gate mà không chạm vào thiết bị thật.
- **Bài học khắc phục:** Xóa bỏ hoàn toàn việc nhận file ảnh thô làm bằng chứng. Bắt buộc phải có **Receipt JSON chuẩn** ghi nhận `runner_status: "success"`, đường dẫn ảnh thật, và mã băm SHA256 (`media_sha256`) đối soát khớp 100% với file ảnh trên đĩa.

### C. Ràng buộc Repo & Fail-Closed
- **Lỗ hổng:** Receipt cũ từ repo A có thể được tái sử dụng để bảo chứng cho repo B nếu receipt thiếu field `repo` hoặc không ở chế độ enforce plan.
- **Bài học khắc phục:** Bắt buộc trường `repo` trong receipt JSON. Thiếu trường `repo` hoặc tên repo không khớp với `effective_repo` đang gate -> FAIL ngay lập tức (`CANARY_REPO_MISSING_IN_RECEIPT` / `CANARY_REPO_MISMATCH`).

### D. Stale Receipt & Commit/HEAD Verification
- **Lỗ hổng:** Một receipt hợp lệ của commit A có thể bị lợi dụng để pass gate cho các commit B, C, D tiếp theo mà không cần chạy lại Canary.
- **Bài học khắc phục:** Bắt buộc receipt phải có `commit_sha` hoặc `head_sha`. Nếu `commit_sha` khác `HEAD` và `git diff --stat <commit_sha> HEAD` có thay đổi code mới -> từ chối ngay (`CANARY_COMMIT_STALE`). Toàn bộ git subprocess phải bọc trong `try/except` fail-closed (lỗi git -> `CANARY_COMMIT_VERIFY_FAILED`).

### E. Bẫy Dead Code khi Working Tree đã commit sạch
- **Lỗ hổng:** `ui_policy_check.py` chỉ quét dirty changes (`git diff`). Nếu agent `git commit` trước khi chạy gate, working tree sạch -> gate trả về pass và bỏ qua toàn bộ việc quét vi phạm direct XML dump.
- **Bài học khắc phục:** Quét song song cả diff so với remote baseline branch (`origin/main`, `origin/master`, hoặc `HEAD~5`). Đồng thời `done_gate.py` tự động phân giải `effective_repo` để luôn chạy `ui_policy_violated()` ngay cả khi lệnh gọi canonical không truyền cờ `--repo`.

### F. GPM Offline Defer Trap
- **Lỗ hổng:** Nhánh GPM tự động defer khi GPM API offline (port 19995 đóng), bỏ qua cờ `--strict-device`.
- **Bài học khắc phục:** Wire cờ `--strict-device` vào toàn bộ nhánh GPM: nếu truyền `--strict-device` mà GPM offline và chưa có Canary receipt hợp lệ -> FAIL ngay lập tức.
