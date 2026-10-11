# Chu Kỳ 4 Ngày & Hệ Thống Giám Sát Sức Khỏe Nuôi Acc 8 Row (Anti-Starvation 96H)

## 1. Chu Kỳ Điều Phối 4 Ngày (Modulo 4) trong `tiktok_runner.py`
- **Cấu trúc chu kỳ:**
  - **Ngày 1 (Day 0):** Sáng Row 1, Trưa Row 3, Tối Row 5.
  - **Ngày 2 (Day 1):** Sáng Row 2, Trưa Row 4, Tối Row 6.
  - **Ngày 3 (Day 2):** Sáng Row 7, Trưa Row 8, Tối dưỡng sinh (Row 3 / Row 4 luân phiên, 0 follow).
  - **Ngày 4 (Day 3):** Nghỉ dưỡng sinh toàn farm cả 3 ca (Sáng Row 3, Trưa Row 4, Tối Row 5/6, 0 follow, `is_rest_day = True`).
- **Upload Hook Invariant:**
  - Cờ `-AllowUploadHook` luôn được mở ở cả Phiên 1 & Phiên 2 cho mọi ca chạy (kể cả ca dưỡng sinh hay nick dính án nhả follow).
  - Đảm bảo mỗi nick đăng đúng 1 video/ngày qua sổ cái `shift_upload_history.json`.

## 2. Kỷ Luật Ngưỡng Bỏ Đói (Anti-Starvation Watchdog 96H)
- **User Correction Invariant:** 
  - Ngưỡng phát hiện Row bị bỏ đói (Starvation) **BẮT BUỘC PHẢI BẰNG CHU KỲ (4 NGÀY = 96 GIỜ)**.
  - **CẤM TUYỆT ĐỐI** gán ngưỡng 48h vì trong chu kỳ 4 ngày, một Row nòng cốt (như Row 1) sau khi chạy Ngày 1 phải đến Ngày 5 (96h sau) mới quay lại lượt. Gán 48h sẽ gây báo động giả liên tục.
- **3 Trụ Cột Giám Sát Sức Khỏe Toàn Farm:**
  1. `🏥 Sức Khỏe Cụm Máy (Fleet Health)`: Phần cứng, USB, ADB, IP, kết nối mạng.
  2. `🩺 Sức Khỏe Follow (Follow Health)`: Trạng thái nick (Khỏe, Hồi phục, Cooldown nhả follow).
  3. `🌾 Sức Khỏe Nuôi Acc (8 Row Nurture Health)`: Lịch sử và độ trễ chạy thực tế của 8 Row.
- **Phân Loại Ngưỡng 96H:**
  - 🟢 **Bình thường:** Nuôi thành công gần nhất $\le 72\text{h}$.
  - 🟡 **Cuối chu kỳ:** $72\text{h} - 96\text{h}$ (đang chuẩn bị đến lượt xoay tua).
  - 🔴 **BÁO ĐỘNG BỎ ĐÓI (STARVED):** $> 96\text{h}$ không có phiên nuôi nào thành công $\rightarrow$ Watchdog lập tức phát cảnh báo đỏ đích danh lên Telegram kèm số Row bị kẹt để can thiệp lỗi script/workbook.

## 3. Khắc Phục Lỗi Runtime & Watchdog Hygiene
- Khi quét thư mục live: dùng glob `????-??-??` thay vì hardcode năm để tránh lỗi sang năm mới.
- Không nuốt exception im lặng (`except Exception: pass`); phải bắt đúng exception hoặc log warning đầy đủ.
- Gửi Telegram đa kênh: bọc `try/except` độc lập theo từng chat ID để lỗi một kênh (ví dụ Follow) không chặn kênh khác (Upload).
