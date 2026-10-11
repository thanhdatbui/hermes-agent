# Diurnal 4-Day Cycle, Permutation Scheduling, Weak Account Definition & Row Nurture Health Watchdog (2026-10-11)

## 1. Context & Operator Directives
Trong quá trình vận hành Phone Farm (160 máy, 1.280 accounts, 8 slot/máy), việc lập lịch và nuôi tài khoản đã được chuẩn hóa qua các quyết định chiến lược:
1. **Chu kỳ 4 ngày cố định (3 ngày cày + 1 ngày nghỉ):**
   - Không được để random tự do làm mất trật tự chu kỳ hoặc bỏ đói tài khoản.
   - Bắt buộc đi hết chu kỳ để mọi Row đều được phủ đều đặn.
2. **Khung giờ buổi sáng Ngày 1:**
   - Ngày đầu tiên sau ngày nghỉ: Ca sáng (06:00 & 08:00) **CHỈ ĐƯỢC CHỌN Row 1 hoặc Row 2** (hai dàn nòng cốt khỏe nhất). Tuyệt đối không đưa Row 7 vào ca sáng Ngày 1 để bảo vệ dải IP và đường truyền sau ngày nghỉ.
3. **Định nghĩa "Acc Yếu" (Weak Account):**
   - Bao gồm **CẢ ACC KHỎE (Row 1, Row 2) NẾU ĐANG BỊ NHẢ FOLLOW** (đang dính Follow Cooldown).
   - Acc khỏe ăn nhả follow cần được đưa vào các ca dưỡng sinh (Ca tối Ngày 3 và cả 3 ca Ngày 4) để lướt feed rửa trust score, tuyệt đối không bấm follow.
4. **Sức Khỏe Nuôi Acc (Row Nurture Health & Starvation Watchdog):**
   - Theo dõi thời gian nuôi gần nhất của từng Row (Row 1 -> 8).
   - Phát cảnh báo nếu một Row > 48h chưa có phiên chạy thành công (do script crash, lỗi workbook hoặc kẹt launcher).

---

## 2. Bảng Lịch Chu Kỳ 4 Ngày Hoàn Chỉnh

| Ngày | Ca 1 (Sáng: 06h & 08h) | Ca 2 (Trưa: 12h & 14h) | Ca 3 (Tối: 18h & 20h) | Chế độ Vận hành |
| :---: | :---: | :---: | :---: | :--- |
| **NGÀY 1** *(Khởi động)* | **Row 1** hoặc **Row 2** *(Mỗi máy chọn 1 hoặc 2)* | **Row 3** hoặc **Row 4** *(Mỗi máy chọn 3 hoặc 4)* | **Row 5** hoặc **Row 6** *(Mỗi máy chọn 5 hoặc 6)* | **CÀY THỰC TẾ (Follow + Up)**<br>• Ưu tiên nick khỏe chạy trước sau ngày nghỉ. |
| **NGÀY 2** *(Bù trừ)* | **Row còn lại** *(1 hoặc 2)* | **Row còn lại** *(3 hoặc 4)* | **Row còn lại** *(5 hoặc 6)* | **CÀY THỰC TẾ (Follow + Up)**<br>• Hoàn thành bù trừ 100% các Row từ 1 đến 6. |
| **NGÀY 3** *(Về đích)* | **Row 7** *(Cày)* | **Row 8** *(Cày)* | **ACC YẾU / ĂN NHẢ** *(Dưỡng sinh)* | • Sáng & Trưa: Cày dứt điểm Row 7, 8.<br>• **Ca tối:** Tắt follow, lướt feed dưỡng sinh acc yếu. |
| **NGÀY 4** *(Nghỉ xả tải)* | **ACC YẾU / ĂN NHẢ** *(Dưỡng sinh)* | **ACC YẾU / ĂN NHẢ** *(Dưỡng sinh)* | **ACC YẾU / ĂN NHẢ** *(Dưỡng sinh)* | **NGÀY NGHỈ DƯỠNG SINH TOÀN FARM**<br>• **Follow:** TẮT 100% (`_follow_rate = 0`).<br>• **Upload:** Vẫn mở 1 video/ngày. |

*(Ngày 5: Bắt đầu chu kỳ 4 ngày mới với seed ngẫu nhiên mới).*

---

## 3. Kiến Trúc Cycle Plan Bất Biến (`cycle_plan.json`)
Để chống việc máy restart làm mất dấu và chọn trùng lặp Row ở Ngày 2:
- Scheduler tạo file `cycle_plan.json` bền vững trên đĩa ngay từ đầu chu kỳ `cycle_idx`.
- Ngày 1 chọn Row nào thì Ngày 2 đọc trực tiếp phần bù trừ từ file state, đảm bảo 100% tính tất định.

---

## 4. Cơ Chế Bốc Acc Yếu & Hàng Đợi 4 Ca Dưỡng Sinh
Trong 1 chu kỳ có 4 ca dưỡng sinh (1 ca tối N3 + 3 ca N4):
1. **Thứ tự ưu tiên bốc acc:**
   - **Ưu tiên 1:** Acc đang dính Follow Cooldown (kể cả Row 1, Row 2).
   - **Ưu tiên 2:** Acc tân binh `< 10` video.
   - **Ưu tiên 3:** Acc đứng hình (0 delta view, 0 delta heart trong 7 ngày).
2. **Chống lặp (Deduplication Guard):**
   - Ca tối N3 bốc acc yếu Hạng 1.
   - Sáng N4 bốc acc yếu Hạng 2.
   - Trưa N4 bốc acc yếu Hạng 3.
   - Tối N4 bốc acc yếu Hạng 4.
   - Không để 1 acc bị chạy lặp cả 4 ca trong khi acc khác bị bỏ sót.

---

## 5. Sức Khỏe Nuôi Acc & Starvation Watchdog
Để tránh tình trạng lỗi script làm một Row mãi không được nuôi:
- **Dữ liệu giám sát:** Quét thư mục chạy thực tế `live/` trong 5 ngày gần nhất.
- **Chỉ số:** `last_nurtured_at`, `runs_48h`, `success_48h`, `fail_48h`.
- **Cảnh báo Bỏ Đói (Starvation Alert):**
  - Nếu `hours_since_last_run > 48h` mà không có lượt chạy thành công nào:
  - Bắn cảnh báo đỏ `ROW_STARVATION_ALERT` kèm danh sách Row và lần chạy thành công cuối cùng.
  - Tích hợp kiểm tra trước mỗi ca chạy trong `tiktok_runner.py` và xuất file `row_nurture_health.json`.
