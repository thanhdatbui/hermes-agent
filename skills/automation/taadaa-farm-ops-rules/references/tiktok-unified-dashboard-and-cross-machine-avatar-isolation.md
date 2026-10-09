# TikTok Unified Dashboard & Cross-Machine Avatar Watchdog Isolation

## 1. NGUYÊN TẮC HỢP NHẤT DASHBOARD (SINGLE SOURCE OF TRUTH)
- Cơ sở dữ liệu SQLite `D:/Taadaa/data/tiktok_tracker.db` (bảng `snapshots` và `farm_account_info`) là nguồn sự thật duy nhất về trạng thái nick toàn farm (LIVE, DIE, follower, tim, video, avatar, trending).
- **Hợp nhất đa host**: Lưu kèm cột `host_id` ('kibe' cho máy 1..80, 'admin' cho máy 201..280).
- Nguồn nạp ID tài khoản:
  * Kibe: Quét từ `D:/OneDrive/TaadaaData/kibe/Tik*.xlsx`.
  * Admin: Quét trực tiếp từ file tổng `D:/OneDrive/TaadaaData/admin/taikhoan_dat_v2_updated .xlsx` (sheet `Tài Khoản`).
- Loại bỏ hoàn toàn sự phụ thuộc vào cột "Avatar" trong các file Excel khi vận hành cronjob (Excel hay ghi sai 'OK' dù nick thật chưa up).

## 2. QUY TẮC PHÂN VÙNG PHẦN CỨNG & TỰ ĐỐI CHIẾU SỐ MÁY (MACHINE BOUNDARY)
Khi cronjob upload avatar (`post_evening_avatar_watchdog.py`) chạy ca tối:
- **Tự động đối chiếu số máy (Auto-resolve Machine ID)**:
  * Mỗi nick chưa có avatar (`has_avatar == 0`) được map với số máy `may` tương ứng.
  * **Kibe host**: CHỈ nhận các máy `1 <= may <= 80`. TỰ ĐỘNG BỎ QUA toàn bộ các máy `may >= 200` (máy Admin). Tuyệt đối không gửi lệnh ADB/PowerShell chạm vào phần cứng của Admin.
  * **Admin host**: CHỈ nhận các máy `may >= 200` (201..280). TỰ ĐỘNG BỎ QUA toàn bộ các máy `may <= 80` của Kibe.
- Đảm bảo 2 host chạy độc lập, không giẫm chân lên nhau, nhưng cùng nhìn chung 1 database báo cáo kết quả.

## 3. NHẬN DIỆN AVATAR MẶC ĐỊNH TIKTOK
- URL avatar mặc định của TikTok chứa pattern:
  * `musically-maliva-obj`
  * ID ảnh hệ thống: `1594805258216454`
  * Hoặc rỗng / `None`.
- Helper chuẩn:
  ```python
  def is_default_avatar(avatar_url: str) -> bool:
      if not avatar_url:
          return True
      u = avatar_url.lower()
      return 'musically-maliva-obj' in u or '1594805258216454' in u
  ```
- Trạng thái `has_avatar`:
  * `0` (False) ➔ Gắn cờ `⚠️ NO AVATAR`, kích hoạt watchdog ca tối up ảnh.
  * `1` (True) ➔ Đã đổi avatar tùy chỉnh.

## 4. QUY TẮC TRENDING (CẮN ĐỀ XUẤT)
- Ngưỡng chuẩn hóa cho farm: `delta_follower >= 20` HOẶC `delta_heart >= 50` (hoặc `follower >= 1000 and status == 'LIVE'`).
- Tuyệt đối không dùng ngưỡng `> 0` tránh gây bão false positive trên 600-880 nick.
