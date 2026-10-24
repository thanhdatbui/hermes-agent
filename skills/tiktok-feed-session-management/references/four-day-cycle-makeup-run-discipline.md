# Kỷ Luật Xử Lý Khi Row Bị Văng & Quy Tắc An Toàn Chu Kỳ Nuôi 4 Ngày (Lessons Learned 24/10/2026)

## 1. Chu Kỳ Cố Định 4 Ngày x 3 Ca (Bỏ Hoàn Toàn Ca 0h Đêm)
- **Base Date:** `2026-10-11` (Parity 96h).
- **Công thức tính ngày chu kỳ:**
  ```python
  import datetime
  base_date = datetime.date(2026, 10, 11)
  cycle_day = (current_date.toordinal() - base_date.toordinal()) % 4
  ```
- **Phân bổ lịch chạy:**
  - **Day 0 (cycle_day = 0):** Ca 1 (Row 1) – Ca 2 (Row 3) – Ca 3 (Row 5).
  - **Day 1 (cycle_day = 1):** Ca 1 (Row 2) – Ca 2 (Row 4) – Ca 3 (Row 6).
  - **Day 2 (cycle_day = 2):** Ca 1 (Row 7) – Ca 2 (Row 8) – Ca 3 (Dưỡng sinh tối / Row 3-4 pure feed).
  - **Day 3 (cycle_day = 3):** Dưỡng sinh xả tải toàn farm (3 ca pure feed).
- **Khung giờ 3 Ca cố định:**
  - **Ca 1 (Sáng):** Phiên 1 lúc `06:00` (Feed only), Phiên 2 lúc `08:00` (+ Upload/Follow).
  - **Ca 2 (Trưa):** Phiên 1 lúc `12:00` (Feed only), Phiên 2 lúc `14:00` (+ Upload/Follow).
  - **Ca 3 (Tối):** Phiên 1 lúc `18:00` (Feed only), Phiên 2 lúc `20:00` (+ Upload/Follow).
- **Dead Zone ban đêm (21:30 -> 05:59):**
  - Đêm nghỉ hoàn toàn, làm mát 80 máy Samsung S7.
  - Khung `03:00 - 04:30`: Cron dọn dẹp cache TikTok (`end-of-day-clear-tiktok-cache`).
  - **TUYỆT ĐỐI KHÔNG CÓ CA 4 HAY CA 0H ĐÊM.**

## 2. Kỷ Luật Make-Up Run (Cấm Tự Ý Chạy Bù Vào Dead Zone)
Khi một hàng (ví dụ Row 1) gặp sự cố mạng/Hub USB/Proxy khiến nhiều máy bị văng hoặc fail:
1. **CẤM chạy bù vào ban đêm rạng sáng (00:00 - 05:00):**
   - Lướt feed ban đêm bị thuật toán TikTok phạt Trust Penalty nặng vì hành vi bot bất thường.
   - Nguy cơ xung đột trực tiếp với cron dọn cache (03:00) hoặc đè lock lên Ca 1 sáng hôm sau (06:00).
2. **Cơ chế Starve Parity bảo vệ tài khoản:**
   - Chu kỳ 4 ngày có độ giãn cách starve an toàn lên tới 96h–108h. Hụt 1 phiên không làm hỏng nick.
   - Hàng bị lỡ sẽ quay lại chu kỳ ở vòng luân chuyển tiếp theo. CẤM hoảng loạn chạy bù phá vỡ nhịp Parity toàn farm.
