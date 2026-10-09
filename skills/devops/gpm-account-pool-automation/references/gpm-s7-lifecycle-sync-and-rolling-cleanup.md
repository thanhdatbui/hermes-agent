# GPM & S7 Account Lifecycle Sync & Non-Blocking Rolling Cleanup

## 1. Bối cảnh & Mục đích
- Khi chạy tự động hóa trên Farm điện thoại Samsung S7 kết hợp GPMLogin (trình duyệt antidetect):
  - **Tránh Profile Bloat & Rác ổ cứng**: Các tài khoản Gmail bị `DIE` / `BAN` / `SUSPENDED` cần được dọn dẹp kép: xóa profile GPM và gỡ tài khoản khỏi thiết bị S7.
  - **Tránh nghẽn ứng viên (Candidate Exhaustion)**: Khi Gmail mới được cập nhật trạng thái `LIVE`, cần tự động tạo profile GPM chuẩn proxy để watchdog login nhìn thấy và vận hành.
  - **Tránh xung đột ca nuôi (Anti-Conflict)**: Tuyệt đối không can thiệp vào điện thoại S7 khi máy đang trong ca nuôi TikTok hoặc sắp nuôi.

## 2. Quy tắc Khung giờ (Morning-Only Execution)
- **Khung giờ chạy**: Chỉ chạy dọn dẹp S7 vào **buổi sáng (07:15 - 08:45 HCM)**:
  - Ngay sau khi cron `daily-manual-stock-checklive` (07:00) cập nhật trạng thái DIE vào `master_gmail_manager.xlsx`.
  - Trước khi cron `post-morning-gmail-2fa-watchdog` (08:30) bắt đầu.
- **Buổi chiều & ca tối**: Tuyệt đối KHÔNG chạy dọn thiết bị S7 để nhường hoàn toàn tài nguyên cho chuỗi Reg Gmail và các ca nuôi.
- **Cron schedule chuẩn**: `*/15 7,8 * * *`.

## 3. Kiến trúc 3 Tầng Bảo vệ & Cuốn chiếu (Non-Blocking)

```python
# Tầng 1: Kiểm tra slot nuôi trong Manifest hôm nay
if is_machine_in_feed_slot(mid):
    continue  # Đang nuôi hoặc sắp nuôi trong 30p -> Bỏ qua ngay

# Tầng 2: Thử lấy lock thiết bị Non-blocking
try:
    with acquire_device_lock(machine=str(mid), serial=serial, project="gpm-cleanup", bypass_proxy_readiness=True):
        # Tầng 3: Đối soát thực tế trên thiết bị trước khi xóa
        chk = subprocess.run([ADB_PATH, "-s", serial, "shell", "dumpsys", "account"], capture_output=True, text=True, timeout=5)
        dev_accs = [a.lower() for a in re.findall(r"Account \{name=([^,]+), type=com\.google\}", chk.stdout)]
        hit_emails = [em for em in dies if em in dev_accs]
        
        for target_email in hit_emails:
            remove_account_adb(serial, mid, target_email, dry_run=False, skip_lock=True)
            
        # Luôn đưa máy về HOME sau khi hoàn tất
        subprocess.run([ADB_PATH, "-s", serial, "shell", "input", "keyevent", "3"], capture_output=True, timeout=5)
except DeviceLockUnavailable:
    # Máy đang bị cron nuôi hoặc tiến trình khác giữ lock -> Bỏ qua để sang máy khác rảnh làm trước!
    continue
```

## 4. Dọn dẹp Profile GPM qua Local API v3
- Gọi endpoint: `GET http://127.0.0.1:19995/api/v3/profiles/delete/{profile_id}?mode=2`
- `mode=2`: Xóa sạch cả database metadata lẫn thư mục profile trên ổ cứng máy tính để giải phóng dung lượng.

## 5. Tạo Profile GPM LIVE chuẩn Farm
- Đọc proxy từ `PROXYgandienthoai.xlsx` theo `mid` để gán proxy 4G tách biệt (`test.taadaa.click:PORT:user:pass`).
- Đặt tên profile chuẩn: `{mid:02d} - {email} - {port}`.
- Gán `group_id = 1` độc lập.
