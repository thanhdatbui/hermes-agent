# Canary Gate Enforcement & Adversarial Verification Architecture (2026-10-22)

## Context & Incident
Sau khi sửa lỗi selector / bounds trên `tiktok-luot nuoi acc` (M74/M78), Coordinator có xu hướng vội vàng báo DONE sau khi chỉ pass focused unit test offline mà không chủ động chạy Canary Gate trên thiết bị thật.
Khi bị User chất vấn, Coordinator và Claude Reviewer đã tiến hành audit toàn diện hệ thống `done_gate.py`, `canary_runner.py`, và `ui_policy_check.py` qua 7 round kiểm tra độc lập (adversarial review).

## Lỗ hổng phát hiện qua các vòng Review độc lập

1. **Self-Report / CLI Flag Bypass:**
   - Cũ: `done_gate.py` cho phép cờ `--task-type general` hoặc không truyền `--repo` để tự động bypass kiểm tra Canary.
   - Fix: Tự động phân giải repo thực tế bằng `git rev-parse --show-toplevel`. Nếu repo nằm trong danh sách `AUTOMATION_REPOS` (bao gồm cả repo `tools`), bắt buộc phải là `task_type = "automation"`, cấm mọi cờ tự khai báo để bypass.

2. **Lỗ hổng file ảnh thô (.png/.jpg):**
   - Cũ: `canary_runner.py` có short-circuit: nếu file truyền vào có đuôi ảnh (`.png/.jpg`) thì trả về `CANARY_IMAGE_VERIFIED` và PASS ngay lập tức. Kẻ tấn công hoặc Agent chỉ cần `touch fake.png` là qua mặt gate.
   - Fix: Xóa sổ hoàn toàn nhánh bypass ảnh thô. Bắt buộc phải có Receipt JSON chuẩn (`media_path`, `media_sha256`, `runner_status: "success"`).

3. **Receipt Repo-Binding:**
   - Cũ: Receipt không kiểm tra trường `repo` nếu không ở chế độ enforce plan.
   - Fix: Bắt buộc trường `repo`/`repository` trong receipt JSON. Nếu thiếu hoặc lệch so với target repo đang gate -> trả về `CANARY_REPO_MISSING_IN_RECEIPT` hoặc `CANARY_REPO_MISMATCH` và FAIL ngay lập tức.

4. **Stale Canary Receipt & Commit / HEAD Mismatch:**
   - Cũ: Receipt cũ trong 7200s có thể được tái sử dụng để bảo chứng cho các commit mới chưa qua chạy thử.
   - Fix: Trong `check_canary_status()`, bắt buộc receipt phải có `commit_sha` hoặc `head_sha`. Nếu commit sha khác với `HEAD` và lệnh `git diff --stat <commit_sha> HEAD` có thay đổi code mới -> `CANARY_COMMIT_STALE` (FAIL). Toàn bộ git subprocess phải fail-closed trong `try/except`.

5. **Decoy Commit & UI Policy Bypass khi Working Tree sạch:**
   - Cũ: `ui_policy_check.py` chỉ quét dirty changes (`git diff`). Nếu agent `git commit` trước khi gọi gate thì working tree sạch -> gate bỏ qua kiểm tra XML dump!
   - Fix: Bổ sung quét diff so với baseline branch (`origin/main`, `origin/master`, hoặc `HEAD~5`). Đồng thời `done_gate.py` tự động phân giải `effective_repo` để luôn chạy `ui_policy_violated()` ngay cả khi người dùng không truyền `--repo`.

6. **GPM Automation Gate:**
   - Cũ: Nhánh GPM tự động defer khi GPM offline, bỏ qua cờ `--strict-device`.
   - Fix: Khi có cờ `--strict-device`, nếu GPM offline và chưa có Canary receipt hợp lệ -> FAIL ngay lập tức.
