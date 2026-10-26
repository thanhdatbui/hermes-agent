# Cron Report Observability & Anti-Blindspot Patterns (Taadaa Farm)

## Ngữ cảnh & Vấn đề gốc
Các cronjob báo cáo định kỳ (report / watchdog) trên Phone Farm và GPM Cluster nếu chỉ báo con số tổng hợp (aggregate counts như `✓ 34 | ✗ 7` hoặc `Đã hoàn tất: 78 máy`) thường che giấu các điểm mù nghiêm trọng khiến sự cố kéo dài mà operator không hay biết.

## 4 Bẫy Điểm Mù Điển Hình & Cách Khắc Phục

### 1. Bẫy Gom Trạng Thái Hỏng Vào Trạng Thái Chờ (Soaking Trap)
* **Hiện tượng:** Trong `cron_gmail_gpm_2fa_6h_report.py`, mọi tài khoản chưa đủ điều kiện bật 2FA bị gom chung vào `soaking` ("Đang ngâm an toàn"). Trong đó các acc bị văng cookie Google (`status == 'NEEDS_LOGIN'`) cũng bị tính là đang ngâm.
* **Hậu quả:** Operator nhìn báo cáo tưởng 18 acc đang ngâm sắp đủ ngày bật 2FA, nhưng thực tế 4 acc đã chết session và sẽ không bao giờ được nuôi hay bật 2FA.
* **Chuẩn xử lý:** Tách độc lập `NEEDS_LOGIN` thành một danh mục cảnh báo riêng, in rõ số lượng và top email bị văng cookie để đẩy sang queue re-login.

### 2. Bẫy Bỏ Rơi Thiết Bị Offline (Offline Device Blindspot)
* **Hiện tượng:** Trong `cron_clear_tiktok_cache.py`, script lấy danh sách thiết bị từ `adb devices` rồi lọc các máy online. Các máy trong danh sách fleet (`Tik1.xlsx`) nhưng bị tuột cáp USB hoặc mất kết nối ADB hoàn toàn biến mất khỏi báo cáo. Báo cáo ghi `Đã hoàn tất: 78 máy`, còn 2 máy offline không xuất hiện ở cả mục Thành công lẫn Thất bại.
* **Chuẩn xử lý:** Luôn đối soát `machines = load_machine_serials()` với `connected_devices`. Máy nào thuộc fleet nhưng không online ADB BẮT BUỘC phải xuất hiện ở dòng:
  `• Mất kết nối ADB (OFFLINE): 2 máy (M10, M30) - Cần cắm lại cáp/khởi động lại ADB`.

### 3. Bẫy Báo Cáo Không Kèm Danh Tánh (Anonymous Failure Trap)
* **Hiện tượng:** Watchdog Login (`post_evening_gpm_login_watchdog.py`) chỉ báo `• Kết quả ca: ✓ 34 | ✗ 7`, không in email nào bị fail, không in loại lỗi (`PLATFORM` vs `SCRIPT`).
* **Chuẩn xử lý:** Bắt buộc lưu mảng `failed_details` vào state file khi worker fail. Hàm format báo cáo phải trích xuất tối thiểu top 5 acc thất bại kèm loại lỗi:
  ```text
  ⚠️ Chi tiết 2 acc thất bại:
    - example1@gmail.com (PLATFORM)
    - example2@gmail.com (SCRIPT)
  ```

### 4. Bẫy Đọc Sai Cache Thống Kê Ngày (Stale Cache Daily Limit Trap)
* **Hiện tượng:** `cron_gpm_gmail_nurture_6h_report.py` đọc key `_daily_stats` (key này không được runner ghi vào state), báo cáo `Tiến độ trần an toàn: 0/30` trong khi runner đã nuôi đủ 30/30 profile hôm nay.
* **Chuẩn xử lý:** Bổ sung hàm fallback `count_nurtured_today(state, now_ts)` đọc trực tiếp timestamp `last_nurtured` của từng profile thuộc ngày hiện tại để đếm chính xác số lượt nuôi thực tế.

## Kỷ luật Điều phối khi User giục "Làm đi"
* Khi user phát lệnh "Làm đi", cấm Coordinator hỏi lại, phân trần hoặc xin phép thêm.
* Do Dispatch Gate chặn `delegate_task` cho tác vụ sửa code, BẮT BUỘC sử dụng Worker CLI: `python D:/Taadaa/tools/dispatch_worker.py --workdir <repo> --file <target> "<contract>"`.
