# Upload Hook Concurrency, Follow Lock Inheritance, and Windows Background Process Flags

## 1. Upload Hook Concurrency & Queue Timeout (Session 3)
- **Vấn đề:** Ở Phiên 3 (phiên cuối ca), 60+ máy hoàn tất lướt feed gần như đồng thời và cùng kích hoạt Upload Hook sang repo `Tiktok-video`.
- **Thiết kế chuẩn:**
  - `DEFAULT_UPLOAD_MAX_CONCURRENCY = 20` (20 worker upload song song) kèm 20 disk slot leases (`slot-0.lock` đến `slot-19.lock`).
  - `DEFAULT_UPLOAD_HOOK_TIMEOUT_SECONDS = 2700.0` (45 phút, nâng từ 1200.0s / 1800.0s) để máy xếp cuối hàng đợi không bị `upload-timeout` do chờ giải phóng slot.
  - Hard deadline cho worker phiên 3: `feed_timeout (2100) + follow_budget (900) + upload_budget (2700) + 300 = 6000s` (100 phút / 1h40m).
  - Khung giờ Watchdog Phiên 3: Ca 1 (09:30 – 12:00), Ca 2 (15:30 – 18:30), Ca 3 (22:00 – 23:59).

## 2. Follow Hook Device Lock Inheritance (`--skip-identity-verify`)
- **Vấn đề:** Tiến trình cha `multi_machine_feed_session.py` (`tiktok-luot nuoi acc`) chiếm giữ `device_lock` trên máy. Khi lướt feed xong, nó gọi hook `run_follow.py`. Trước đây `run_follow.py` kiểm tra `acquire_device_lock(user_authorized=False)` và thấy lock của chính tiến trình cha nên tự chặn (`DeviceLockNeedsUserDecision`, exit 2) -> Toàn bộ follow bị fail 100%.
- **Quy chuẩn xử lý:**
  - Khi `args.skip_identity_verify` được truyền (dấu hiệu được gọi từ feed hook), `run_follow.py` kiểm tra: nếu `exc.owner.get("project") in ("tiktok-luot nuoi acc", "tiktok-feed", "multi-machine-feed-session")` thì cho phép chạy tiếp, kế thừa quyền lock của cha.

## 3. Windows Subprocess Popen Creation Flags
- **Vấn đề:** Khi `tiktok_runner.py` spawn background process cho `powershell run-feed-session.ps1`:
  - `0x00000208` (`CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS`): Trên Windows, `DETACHED_PROCESS` khi redirect stdio sang `DEVNULL` có thể khiến process con kết thúc ngay lập tức hoặc không khởi động được.
  - **Flag chuẩn:** Bắt buộc dùng `0x08000200` (`CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW`). Process con chạy ổn định ngầm, độc lập và không bị tắt khi script launcher thoát.

## 4. Định Dạng Báo Cáo Chuẩn 4 Nhóm của Watchdog (Đăng Video)
- Cấu trúc chuẩn cho phần Đăng Video:
```text
• Đăng Video (Phiên 3 - N video đã đăng):
  + Success (A): 1, 2, 3...
  + Timeout/Quá giờ (B): M4, M5...
  + Lỗi script/xác minh (C): M6, M7...
  + Bỏ qua (D): M8, M9...
```
- Danh sách máy luôn là chuỗi số gọn gàng (`1, 2, 3` hoặc `M1, M2`), không lặp lại chuỗi chi tiết như `(upload-timeout)` trên từng máy.

## 5. Cohort Target Identity Mismatch (`missing:tik`)
- Trong `_apply_cohort_identity`: Chỉ đối soát `tik` khi cohort manifest có khai báo key `"tik"` (`if "tik" in expected:`). Tuyệt đối không bắt buộc cứng `tik` khi cohort không yêu cầu, tránh sinh ra lock `blocked` giả làm treo toàn bộ ca.

## 6. Follow Hook Gating Rules, Allowlist & Watchdog Atomic Fencing
- **Cơ chế Gating theo Primary Status:**
  - `primary_status` ưu tiên `final_status` làm nguồn quyết định duy nhất (chỉ fallback sang `status` khi `final_status` rỗng).
  - **Strict Allowlist:** Follow hook CHỈ được phép chạy khi:
    1. `primary_status in {"success", "degraded"}` (trừ khi stop reason dính sensitive stop words).
    2. HOẶC `primary_status == "failed"` VÀ lý do dừng `norm_stop_reason` nằm chính xác trong `_ALLOWED_FEED_FAIL_REASONS = {"feed_swipe_limit_reached", "swipe_timeout", "feed_session_limit_reached", "max_swipes_completed", "swipe_limit", "feed_swipe_limit"}`.
  - **Fail-Closed Safe Skip:** Trạng thái rỗng hoặc bất kỳ trạng thái nhạy cảm nào (`manual_needed`, `blocked`, `config_error`, `captcha`, `otp`, `2fa`, `security_check`, `password_prompt`, `account_locked`, `banned`, `suspended`, `account_blocked`, `login`, `account_mismatch`, `profile_mismatch`, `wrong_account`, `unauthorized`, `swipe_recovery_exhausted`, `recovery_exhausted`) đều tự động Safe-Skip follow (`sensitive-skip`).
- **Atomic Watchdog Fencing:**
  - Để ngăn ngừa race TOCTOU khi watchdog terminalize tiến trình trong lúc chuẩn bị gọi hook, quyền công bố `_worker_publication_allowed()` bắt buộc phải được kiểm tra ngay trước khi spawn tiến trình `subprocess.Popen` / `subprocess.run` và phải bảo vệ việc ghi đè artifact `follow_result.json` / `upload_result.json`.
