# GPM Profile Lifecycle & S7 Rolling Cleanup Protocol

## 1. Bản chất và Mục tiêu
- **2 Chiều đồng bộ (Two-way Lifecycle Sync)**:
  1. **Tạo Profile LIVE**: Duy trì đủ profile GPM chuẩn cho các Gmail LIVE trên máy S7 online ADB nhằm mở rộng tối đa tài nguyên IP cho các ca chạy (không để bị nghẽn candidates do thiếu profile GPM).
  2. **Dọn dẹp DIE kép (Two-fold DIE Cleanup)**: Khi Gmail bị `DIE` / `BAN` / `SUSPENDED`, bắt buộc phải dọn cả 2 đầu:
     - **GPM PC**: Gọi GPM API `/api/v3/profiles/delete/{id}?mode=2` (xóa sạch thư mục trên đĩa để chống phình ổ cứng).
     - **Samsung S7**: Dùng ADB/UI Settings gỡ bỏ tài khoản khỏi thiết bị thật để tránh kẹt slot tối đa (4-5 acc/máy) và tránh Google Play Services hiện popup lỗi che khuất màn hình.

---

## 2. Khung giờ vàng (Gold Windows)
Theo lịch vận hành Farm, dọn dẹp cuốn chiếu trên thiết bị S7 chỉ được kích hoạt vào 2 khung giờ:
1. **Sáng: `07:15 - 08:15`**:
   - Chạy ngay sau khi cron `daily-manual-stock-checklive` (07:00) cập nhật trạng thái DIE vào `master_gmail_manager.xlsx`.
   - Hoàn tất trước khi cron `post-morning-gmail-2fa-watchdog` (08:30) bắt đầu ca làm việc.
2. **Trưa: `13:30 - 14:25`**:
   - Chạy trước khi cron chuỗi chiều `post-noon-chain-watchdog` (14:30) bắt đầu Phase 1 Reg Gmail mới (đảm bảo máy có slot trống để đăng ký tài khoản mới).

---

## 3. Quy tắc an toàn & Cơ chế cuốn chiếu (Non-blocking Device Lock)
Tuyệt đối tuân thủ 3 tầng bảo vệ để không bao giờ xung đột với ca nuôi TikTok:
1. **Tầng 1 - Manifest Idle Window**:
   - Đọc `manifests/assignment-v1-*.json` của ngày hôm nay.
   - Nếu máy $N$ đang trong slot nuôi hoặc sắp bắt đầu nuôi trong vòng 30 phút tới -> **Bỏ qua máy $N$ ngay lập tức**.
2. **Tầng 2 - Non-blocking Device Lock**:
   - Sử dụng `automation_core.device_lock.acquire_device_lock(machine=str(mid), serial=serial, project="gpm-cleanup", bypass_proxy_readiness=True)`.
   - Bắt ngoại lệ `DeviceLockUnavailable`: nếu máy đang bị cron nuôi hoặc tiến trình khác giữ lock -> **Bỏ qua máy đó để sang máy khác rảnh làm trước**, cấm ngủ/chờ mù quáng (`blind wait`). Ở tick 15 phút tiếp theo khi máy nhả lock, cron sẽ tự động quay lại dọn.
3. **Tầng 3 - Thao tác gọn & Nhả lock ngay**:
   - Kiểm tra `dumpsys account` xác nhận tài khoản DIE thực sự còn trên máy.
   - Mở Cài đặt gỡ tài khoản (`android.settings.SYNC_SETTINGS`), xác nhận popup xóa.
   - BẮT BUỘC bấm phím HOME (`input keyevent 3`) đưa máy về màn hình chính trước khi kết thúc khối `with acquire_device_lock`, đảm bảo nhả lock an toàn.

---

## 4. Lệnh kiểm tra & Cron chuẩn
- Script thực thi: `D:\Taadaa\GPM auto\scripts\sync_gpm_lifecycle.py`
- Lịch cronjob: `*/15 7,8,13,14 * * *` (Job: `gpm-lifecycle-sync-watchdog`)
- Chạy thử nghiệm:
  ```bash
  python "D:/Taadaa/GPM auto/scripts/sync_gpm_lifecycle.py" --dry-run --force-s7
  ```
