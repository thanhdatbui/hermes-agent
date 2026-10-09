# Kế hoạch & Phân tích Khung giờ Vàng Cron Đổi Info Hotmail (18/09/2026)

## 1. Bối cảnh & Yêu cầu Operator
- Operator yêu cầu tạo Cron đổi thông tin Hotmail (đổi pass mới + gỡ mail khôi phục bên bán + đá session mọi nơi -> ghi Cột G -> log Outlook 1 lần duy nhất).
- **Yêu cầu an toàn tối cao:**
  + Tìm khung giờ rảnh nhất của toàn Farm.
  + Kiểm tra toàn bộ 29 scripts/cronjobs khác trên hệ thống xem có bị trùng lịch hay không.
  + Đảm bảo đủ độ dài khung giờ để chạy cuốn chiếu an toàn mà không cướp máy hay đụng độ Device Lock.

---

## 2. Bản đồ Lịch trình 24h Toàn Farm (Schedule Conflict Matrix)

| Khung Giờ (HCM) | Tiến trình đang chạy | Cronjob Name | Tình trạng thiết bị Farm |
| :--- | :--- | :--- | :--- |
| **00:00 - 02:30** | Ca 4 Feed Session (Phiên 1 lúc 00:00, Phiên 2 lúc 01:30) | `phase9-runner-tiktok-feed` | BẬN (Nuôi Feed + Upload) |
| **02:30 - 03:00** | Đệm nghỉ đêm | - | Rảnh cục bộ |
| **03:00 - 05:45** | Dọn cache TikTok cuốn chiếu 40 máy | `end-of-day-clear-tiktok-cache` | BẬN ĐỊNH KỲ (Chiếm lock dọn cache) |
| **05:45 - 06:00** | Chuẩn bị Staging Picker | `phase9-staging-picker-...` | Rảnh ngắn 15 phút |
| **06:00 - 08:30** | Ca 1 Feed Session (Phiên 1 lúc 06:00, Phiên 2 lúc 08:00) | `phase9-runner-tiktok-feed` | BẬN (Nuôi Feed + Upload) |
| **08:30 - 11:30** | Chuỗi bật 2FA Gmail sau Ca 1 | `post-morning-gmail-2fa-watchdog` | BẬN (Máy dính Gmail) |
| **11:30 - 12:00** | **Khoảng đệm nghỉ trưa** | - | **RẢNH AN TOÀN (30 phút)** |
| **12:00 - 14:30** | Ca 2 Feed Session (Phiên 1 lúc 12:00, Phiên 2 lúc 14:00) | `phase9-runner-tiktok-feed` | BẬN (Nuôi Feed + Upload) |
| **14:30 - 17:30** | Chuỗi sau Ca trưa: Reg Gmail -> Add 2FA TikTok | `post-noon-chain-watchdog` | BẬN (Batch 40 máy) |
| **17:30 - 18:00** | **Khoảng đệm nghỉ chiều** | - | **RẢNH AN TOÀN TUYỆT ĐỐI (30 phút)** |
| **18:00 - 20:30** | Ca 3 Feed Session (Phiên 1 lúc 18:00, Phiên 2 lúc 20:00) | `phase9-runner-tiktok-feed` | BẬN (Nuôi Feed + Upload) |
| **20:30 - 23:45** | Upload Avatar & GPM Login sau Ca tối | `post-evening-avatar/gpm-watchdog` | BẬN (Máy dính Avatar/GPM) |
| **23:45 - 00:00** | Đệm giao ca đêm | - | Rảnh ngắn 15 phút |

---

## 3. Đánh giá Khung Giờ Khả Thi

### Lựa chọn 1: Nối đuôi Phase 3 trong Chuỗi Trưa (14:30 - 17:30) - KHUYẾN NGHỊ CAO NHẤT
- **Cơ chế:** Nằm trực tiếp trong `post_noon_chain_watchdog.py`.
- **Ưu điểm:** 
  + Không cần mở thêm cronjob mới.
  + Chạy theo sự kiện (Event-driven): Máy nào vừa hoàn tất 2FA TikTok trong Phase 2 thì nối đuôi ngay sang Phase 3 kiểm tra đổi Hotmail đủ 7 ngày.
  + Không sợ trùng lịch vì chuỗi trưa đã sở hữu cơ chế điều phối và giải phóng lock bài bản.

### Lựa chọn 2: Cronjob độc lập Khung Chiều (17:15 - 17:55)
- **Cơ chế:** Lên lịch cron `*/10 17 * * *`.
- **Ưu điểm:** Khung giờ vàng 17:15 - 17:55 là lúc Chuỗi Trưa đã kết thúc, các máy nghỉ ngơi hoàn toàn trước khi Ca 3 (Tối) bắt đầu lúc 18:00.
- **Bắt buộc:** Tích hợp `with_device_lock` và kiểm tra `is_feed_runner_active()`. Nếu máy nào đang bận hoặc chạy bù feed thì tự động skip, không cướp máy.
