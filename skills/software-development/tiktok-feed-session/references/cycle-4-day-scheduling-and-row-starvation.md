# Quy Tắc Điều Phối Chu Kỳ 4 Ngày & Chống Bỏ Đói Row (Row Starvation Guard)

## 1. Chu Kỳ 4 Ngày (Modulo 4) Farm TikTok Feed / Follow
Lịch chạy chuẩn 3 ca/ngày (bỏ ca 0h đêm), chu kỳ xoay tua 4 ngày:

- **Ngày 1 (Khởi động sau ngày nghỉ):**
  - Ca 1 (06:00 & 08:00): Row 1 hoặc Row 2 (Mỗi máy chọn 1 hoặc 2, ưu tiên dàn khỏe nòng cốt đi trước sau ngày nghỉ để bảo vệ dải IP).
  - Ca 2 (12:00 & 14:00): Row 3 hoặc Row 4.
  - Ca 3 (18:00 & 20:00): Row 5 hoặc Row 6.
  - Chế độ: Cày thực tế (Follow + Upload).
- **Ngày 2 (Bù trừ):**
  - Ca 1 (Sáng): Row còn lại của {1, 2}.
  - Ca 2 (Trưa): Row còn lại của {3, 4}.
  - Ca 3 (Tối): Row còn lại của {5, 6}.
  - Chế độ: Cày thực tế (Follow + Upload). Hoàn tất trọn vẹn 100% các Row từ 1 đến 6.
- **Ngày 3 (Về đích & Xả tối):**
  - Ca 1 (Sáng): Row 7 (Cày Follow + Upload).
  - Ca 2 (Trưa): Row 8 (Cày Follow + Upload).
  - Ca 3 (Tối): Dưỡng sinh Acc Yếu / Ăn Nhả (Tắt follow, lướt feed + Upload 1 video nếu chưa có).
- **Ngày 4 (Nghỉ xả tải toàn Farm):**
  - Cả 3 Ca (Sáng, Trưa, Tối): Đều dành riêng nuôi dưỡng sinh Acc Yếu / Ăn Nhả.
  - Follow: TẮT 100% (`_follow_rate = 0`, `TAADAA_REST_DAY_NO_FOLLOW = 1`).
  - Lướt feed: Tự nhiên hồi trust.
  - Upload: VẪN MỞ ĐĂNG 1 VIDEO/NGÀY nếu nick chưa có video trong ngày.

## 2. Định Nghĩa "Acc Yếu" & Thứ Tự Bốc Dưỡng Sinh
Khi vào ca dưỡng sinh (Ca tối N3 và cả 3 ca N4), bốc theo thứ tự ưu tiên:
1. **Ưu tiên 1 (Cứu hộ khẩn cấp):** Acc ăn nhả follow (`is_follow_cooldown == True`) — **Bao gồm cả acc thuộc Row khỏe (Row 1, Row 2) nếu bị nhả**. CẤM bấm follow, chỉ lướt feed rửa trust.
2. **Ưu tiên 2 (Tân binh thiếu video):** Acc có `video_count < 10` (ưu tiên nick ít video nhất).
3. **Ưu tiên 3 (Acc đứng hình):** Acc nhiều ngày liền $\Delta \text{view} = 0, \Delta \text{heart} = 0$.

## 3. Quy Tắc Bất Biến Về Upload Video (Opportunistic Upload)
- **Luôn mở Upload Hook (`-AllowUploadHook`) ở cả Phiên 1 và Phiên 2.**
- Khóa Idempotent 1 video/ngày qua sổ cái `shift_upload_history.json`: Phiên 1 đăng thành công -> Phiên 2 tự động skip; Phiên 1 lỗi -> Phiên 2 đăng bù.
- **TÁCH BẠCH HOÀN TOÀN** Follow Cooldown / Ngày dưỡng sinh với Upload:
  - CẤM xem "ngày dưỡng sinh" hoặc "bị nhả follow" là cấm đăng video.
  - Nick bị nhả follow hay đang chạy ca dưỡng sinh lướt feed **vẫn phải đăng 1 video/ngày** để nuôi nhịp Creator tự nhiên và đạt mốc 10 video.

## 4. Cơ Chế Chống Bỏ Đói Row (Row Starvation Watchdog)
- Ngoài việc theo dõi Sức khỏe cụm máy và Sức khỏe follow, hệ thống phải theo dõi `last_nurtured_at` của từng Row từ Row 1 đến Row 8.
- **Ngưỡng Starvation Alert:** Bất kỳ Row nào quá **48 giờ** không có phiên chạy thành công nào (do script crash ngầm, lỗi mapping file Excel, kẹt lock...) phải phát cảnh báo `ROW_STARVATION_ALERT` lập tức, tránh việc 1 Row mãi không được nuôi.
