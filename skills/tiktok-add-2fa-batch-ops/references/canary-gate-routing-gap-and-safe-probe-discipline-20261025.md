# Canary Gate Multi-Repo Routing Gap & Safe Probe Discipline (2026-10-25)

## 1. Bối Cảnh & Điểm Nghẽn Kẹt Push (Canary Routing Gap)
- **Cơ chế chặn của `safe_push.py`:**
  - `safe_push.py` gọi `done_gate.detect_task_type(repo_path)`. Nếu thuộc nhóm `AUTOMATION_REPOS` (`tiktok-add-bao-mat-f2a`, `Tiktok-video`, `tiktok-log-in`, `Tiktok_Reg`, `register gmail`, `automation-core`, `GPM auto`), script bắt buộc phải kiểm tra biên nhận Canary còn hạn (`check_canary_status()`).
  - Tuy nhiên, trong `canary_runner.py` (tại thời điểm 25/10/2026), logic điều phối mới chỉ hỗ trợ 2 repo:
    1. `tiktok-follow` (chạy `follow_runner.run_follow`)
    2. `tiktok-luot nuoi acc` / `tiktok-feed` (chạy `run_tiktok.py --mode multi-machine-feed-session --recovery-test-swipes 2`)
  - Khi chạy canary cho các repo automation khác như `tiktok-add-bao-mat-f2a`, `canary_runner.py` báo lỗi:
    `[CANARY_ERROR] Chưa đăng ký routing runner cho repo: <repo_name>`
  - Kết quả: Các repo này không thể tự tạo ra `canary_receipt.json` hợp lệ, khiến `safe_push.py` chặn vô điều kiện với lỗi `BLOCKED_CANARY_REQUIRED (CANARY_FLAG_EXPIRED)`.
  - Cờ `--owner-override` trong `safe_push.py` chỉ dành cho Human Operator thực thi trực tiếp trên console máy chủ, tự động chặn Agent gọi (`BLOCKED_AGENT_OVERRIDE`).

## 2. Kỷ Luật Xử Lý Khi Kẹt Canary Gate Do Thiếu Routing
- Khi commit đã vượt qua **Closeout Gate** (Overall Score >= 85 hoặc grace band >= 80 kèm 100% unit tests passed):
  1. **CẤM TUYỆT ĐỐI fake biên nhận:** Không được tạo file `.canary_passed` hoặc `.canary_receipt.json` giả mạo sha256 ảnh.
  2. **Giải thích rõ ràng nguyên nhân:** Báo cáo User rằng commit đã được phê duyệt ở local, nhưng kẹt push do repo chưa có kịch bản Canary thực địa trong `canary_runner.py`.
  3. **Cung cấp lệnh Push trực tiếp cho User:**
     ```bash
     git -C "<repo_path>" push origin main
     ```

## 3. Thiết Kế Chuẩn "Safe Probe Canary" Khi Mở Rộng Cho Repo 2FA & Các Script Khác
- Với các repo có tính chất biến đổi dữ liệu tài khoản (2FA, Upload video, Reg nick, Login):
  - **CẤM Canary chạy kịch bản thật làm hỏng dữ liệu:** Không được tự ý gắn 2FA/đổi pass nick thật, không đăng video rác lên kênh đang nuôi, không gửi OTP bừa bãi làm cháy quota mail.
  - **BẮT BUỘC thiết kế Safe Probe Hook (Chỉ xác nhận UI/ADB):**
    - `tiktok-add-bao-mat-f2a`: Mở TikTok -> vào màn hình Switcher hoặc Cài đặt bảo mật -> chụp ảnh screencap -> WinRT OCR kiểm tra chữ -> teardown về Home.
    - `Tiktok-video`: Đẩy 1 file video probe ngắn vào `/sdcard/DCIM/Camera/` -> mở TikTok vào màn hình chọn video -> chụp ảnh xác nhận nút Đăng/Next -> xóa video probe -> teardown về Home.
    - `tiktok-log-in`: Mở Switcher -> kiểm tra nút "Thêm tài khoản" -> teardown về Home.
- **Fail-Closed khi Farm đang trong ca nuôi:**
  - Nếu tất cả các máy đều có lịch ca hoặc đang có `mCurrentFocus` là TikTok của cron nuôi acc, Canary Runner BẮT BUỘC dừng lại (`fail-closed`), tuyệt đối không cướp máy làm văng phiên nuôi của hệ thống.
