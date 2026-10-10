# Missing Account Login Recovery & Kibe Version Contract (2026-10-10)

## 1. Chấn chỉnh nghiệp vụ Operator: Cấm dừng lại ở BLOCKED khi thiếu phiên login
- **Tình huống thực tế:** Khi runner đổi avatar (`run_tiktok_upload_avatar.ps1`) chạy trên Máy 44 báo lỗi:
  `[ACCOUNT_SWITCHER_FAILED] ACCOUNT_READY verify failed: ACCOUNT_VERIFY_MISMATCH: Profile did not show the expected account.`
  Coordinator kiểm tra và xác nhận trên máy đang có 7 nick khác (`maralbbct24`, `v.th.thoooo`, `ngongan1906`, `kellybxm52j`, `olinasbnetu`, `miumiu10434`, `oquangduong7604`), tài khoản đích `@annapmfdh0a` hoàn toàn chưa có trong Switcher.
- **Phản ứng sai lầm của Agent:** Dừng lại, báo cáo BLOCKED kèm ảnh và kết luận: *"Cần cho nick chạy qua luồng login trước khi runner nạp avatar"*.
- **Operator chấn chỉnh gay gắt:** *"Thì chạy tiktok login acc đó vào"*.
- **Quy tắc bắt buộc:**
  * Khi phát hiện tài khoản đích thiếu trong danh sách Switcher trên thiết bị (dưới 8 accounts), **CẤM TUYỆT ĐỐI** dừng lại chờ đợi hay đẩy việc cho User.
  * Lập tức chuyển tiếp sang luồng đăng nhập tự động (`tiktok_login_v1.py`), sau đó tái kích hoạt runner upload avatar ngay khi đăng nhập thành công.

---

## 2. Canonical Tooling Login Tài khoản cũ trên Farm
- **Script SSOT:** `D:\Taadaa\Tiktok_Reg\tiktok_login_v1.py`
- **Môi trường Python bắt buộc:** `D:\Taadaa\python-envs\automation\Scripts\python.exe`
- **Cú pháp thực thi chuẩn:**
  ```bash
  python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <username_hoac_email> --ss
  ```
- **Cơ chế hoạt động:**
  1. Đọc tự động credentials từ `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx` (Sheet `Tài Khoản`, hàng tương ứng STT).
  2. Kiểm tra ràng buộc gán máy (`assert_account_machine_binding`), kiểm tra live email/Hotmail.
  3. Mở TikTok trên thiết bị $\to$ vào Profile $\to$ mở Switcher $\to$ bấm *"Thêm tài khoản"* $\to$ *"Thêm tài khoản khác"* (bypass One-tap nếu có).
  4. Điền TikTok ID & Password, tự động xử lý Captcha, bypass 2FA và chụp ảnh màn hình nghiệm thu (`--ss`).

---

## 3. Bẫy Mismatch `TIKTOK_VIDEO_AUTOMATION_CORE_VERSION` trên Kibe Local
- **Hiện tượng:** Khi chạy wrapper gọi `run_tiktok_upload_avatar.ps1`, nếu gán:
  `os.environ["TIKTOK_VIDEO_AUTOMATION_CORE_VERSION"] = "0.4.45"`
  thì PowerShell `run_tiktok_upload_batch.ps1:127` sẽ ném ngoại lệ:
  `automation-core version mismatch: expected=0.4.45; actual=0.4.44; reason=metadata version did not match expected contract`
- **Nguyên nhân:** Môi trường `venv-core024` trên máy Kibe đang cài đặt `automation-core 0.4.44`.
- **Quy tắc:** Trên Kibe farm, luôn để mặc định hoặc gán rõ `0.4.44`. Tuyệt đối không copy cấu hình `0.4.45` từ các repo khác sang làm gián đoạn batch.

---

## 4. Xử lý Tranh chấp Device Lock Kép
- Trước khi thực thi bất kỳ lệnh can thiệp UI nào, kiểm tra lock file `~/.codex/device-locks/machine_<N>.lock.json`.
- Nếu máy đang bị giữ lock bởi các tiến trình nền của farm (như `multi-machine-feed-session` hoặc `run_batch_live_2fa.py`):
  * **CẤM** tự ý kill tiến trình nền (`kill -9`) gây hỏng dữ liệu phiên farm.
  * Sử dụng script chờ nhả lock an toàn (vòng lặp kiểm tra `os.path.exists(lock_file)` tối đa 180–300s).
  * Ngay khi lock được giải phóng (`lock_file` biến mất), lắng lại 2s rồi lập tức chiếm quyền thực thi canonical runner.
