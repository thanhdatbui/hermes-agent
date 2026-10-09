# Vòng đời Profile GPM và Dọn dẹp Thiết bị S7 Cuốn chiếu

## 1. Bản chất Phân tách Hai Tác vụ
1. **Tạo Profile GPM trên PC**:
   - **Bản chất**: Tạo môi trường browser cô lập (User-Agent, Fingerprint) và gán proxy 4G tương ứng theo `PROXYgandienthoai.xlsx`.
   - **Điều kiện**: Chỉ cần Gmail LIVE + Proxy mapping hợp lệ + Chưa có trong GPM DB.
   - **CẢNH BÁO QUAN TRỌNG (User Correction)**: **TUYỆT ĐỐI KHÔNG kiểm tra ADB online của thiết bị S7 khi tạo profile GPM!** Tạo profile GPM chỉ là chuẩn bị môi trường trên PC, chưa tiến hành login Google hay cấp OAuth nên thiết bị S7 chưa hề bị đụng tới. Đòi hỏi S7 phải online ADB lúc tạo profile là điều kiện thừa thãi gây nghẽn toàn bộ dàn tài khoản.

2. **Dọn dẹp Tài khoản DIE trên Thiết bị S7 (Device Cleanup)**:
   - **Bản chất**: Tác động trực tiếp vào OS Android của điện thoại thật (`android.settings.SYNC_SETTINGS`) để gỡ bỏ tài khoản đã DIE / BAN / SUSPENDED.
   - **Điều kiện**: Thiết bị S7 BẮT BUỘC phải online ADB (`adb devices`) và phải vượt qua các cổng bảo vệ an toàn ca nuôi.

---

## 2. Khung Giờ Hoạt Động (Schedule Policy)
- **Buổi sáng (07:15 - 08:45 HCM)**:
  - Khung giờ DUY NHẤT cho phép chạy dọn dẹp thiết bị S7.
  - Chạy ngay sau khi cron `daily-manual-stock-checklive` (07:00) cập nhật danh sách DIE vào `master_gmail_manager.xlsx`, và TRƯỚC KHI chuỗi `post-morning-gmail-2fa-watchdog` (08:30) bắt đầu.
- **Buổi chiều & Tối**:
  - **KHÓA CHẶT**, tuyệt đối không chạy dọn dẹp thiết bị S7 vào buổi chiều/tối để tránh xung đột với chuỗi Reg Gmail chiều (14:30) và các ca nuôi TikTok.

---

## 3. Ba Tầng Tự Bảo Vệ Khi Chạm Vào Thiết Bị S7
1. **Tầng 1 - Manifest Idle Buffer (30 phút)**:
   - Kiểm tra `D:/Taadaa/runtime/kibe/cron-state/manifests/<today>/assignment-v1-*.json`.
   - Nếu máy đang trong slot nuôi hoặc sắp bắt đầu ca nuôi trong 30 phút tới -> **BỎ QUA NGAY LẬP TỨC**.
2. **Tầng 2 - Non-blocking Device Lock (`acquire_device_lock`)**:
   - Khóa máy qua `automation_core.device_lock`:
     ```python
     try:
         with acquire_device_lock(machine=str(mid), serial=serial, project="gpm-cleanup", bypass_proxy_readiness=True):
             # Gỡ tài khoản DIE trên S7
     except DeviceLockUnavailable:
         # Cron nuôi TikTok đang giữ lock -> Bỏ qua máy này, sang máy rảnh làm trước
         continue
     ```
   - Tuyệt đối không sleep chờ mù quáng (`blind wait/sleep`). Máy đang nuôi sẽ tự động được dọn ở tick 15 phút tiếp theo khi cron nuôi đã nhả lock.
3. **Tầng 3 - Post-Action Home Reset**:
   - Xong từng máy, bắt buộc bấm HOME (`adb shell input keyevent 3`) và nhả lock ngay lập tức trước khi duyệt sang máy kế tiếp.

---

## 4. Dọn dẹp Profile GPM DIE trên PC
- Quét danh sách Gmail DIE từ `master_gmail_manager.xlsx`.
- Tìm ID profile trong GPM SQLite DB `profile_data.db`.
- Gọi Local API v3: `GET http://127.0.0.1:19995/api/v3/profiles/delete/{profile_id}?mode=2` (`mode=2` để xóa sạch folder data trên ổ đĩa tránh phình dung lượng).
