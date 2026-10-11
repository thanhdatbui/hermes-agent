# Anti-Starvation & 8-Row Nurture Health Monitoring (User Mandate 2026-10-11)

## 🛑 BẮT BUỘC: QUY TẮC ĐỒNG BỘ NGƯỠNG STARVATION THEO CHU KỲ

1. **Ngưỡng Starvation BẮT BUỘC bằng đúng Chu Kỳ Điều Phối (Cycle Length):**
   - **Lỗi chí mạng (User chỉnh 2026-10-11):** Gán ngưỡng starvation 48h trong khi farm chạy chu kỳ 4 ngày (96 giờ). Hậu quả: Các Row đang nằm chờ lượt tự nhiên (ví dụ Row 1 chạy Ngày 1 thì Ngày 5 mới chạy lại) bị hệ thống báo động đỏ giả liên tục!
   - **Quy tắc chuẩn:** Khi farm chạy chu kỳ $N$ ngày, ngưỡng phát hiện bỏ đói (Starvation Alert) BẮT BUỘC là $N \times 24\text{h}$ (ví dụ: chu kỳ 4 ngày $\rightarrow$ ngưỡng $96\text{h}$, cho phép buffer tối đa $100\text{h}$ để bù độ lệch giữa các ca sáng/trưa/tối).
   - CẤM TUYỆT ĐỐI gán cứng các ngưỡng tuỳ tiện ngắn hơn chu kỳ (như 24h, 36h, 48h).

2. **Phân Loại Trạng Thái Nuôi 8 Row (Thang Đo 96h):**
   - 🟢 **Bình thường / Đúng chu kỳ:** $\le 72\text{h}$ kể từ ca chạy gần nhất.
   - 🟡 **Cuối chu kỳ / Sắp đến lượt:** $72\text{h} < t \le 96\text{h}$ (đang nằm trong ngày 3 hoặc ngày 4 chờ xoay vòng).
   - 🔴 **BÁO ĐỘNG BỎ ĐÓI (STARVED):** $> 96\text{h}$ không có bất kỳ phiên chạy thành công nào $\rightarrow$ Kích hoạt chuông báo động đỏ đích danh kèm số Row để kỹ thuật kiểm tra ngay lỗi kịch bản, file workbook hoặc launcher kẹt ngầm.

3. **Cơ Chế Quét Thực Địa O(1) (CẤM Quét Đĩa Diện Rộng):**
   - Không được dùng `os.walk` hay `glob(recursive=True)` quét toàn bộ ổ `D:/Taadaa`.
   - Chỉ quét thư mục live 7 ngày gần nhất trong `runtime/kibe/live` và `runtime/admin/live` theo pattern `2026-MM-DD/row-<id>-<hhmmss>`.

4. **Đấu Nối Trực Tiếp Vào Báo Cáo Ca Telegram (`feed_session_watchdog.py`):**
   - Mỗi ca nuôi, watchdog tự động đính kèm khối:
     ```text
     🌾 【SỨC KHỎE NUÔI 8 ROW (CHU KỲ 4 NGÀY)】
     • Tiến độ: R1:🟢3h | R2:🟢27h | R3:🟢45h | R4:🟢21h | R5:🟢39h | R6:🟢15h | R7:🟢58h | R8:🟢34h
     ```
   - Khi có Row $> 96\text{h}$, watchdog tự động chèn thêm:
     `🚨 CẢNH BÁO BỎ ĐÓI: Row [X] > 96h chưa nuôi thành công!`

5. **Opportunistic Upload (Đăng Video 1 Video/Ngày Mọi Ca):**
   - Upload Hook luôn mở `-AllowUploadHook` ở cả Phiên 1 & 2 bất kể ca cày hay ca dưỡng sinh.
   - Sổ cái `shift_upload_history.json` đảm bảo đúng 1 video/ngày cho từng nick.
   - Khi dính án nhả follow (`follow_cooldown == True`), nick chỉ bị khóa bấm follow (`_follow_rate = 0`), TUYỆT ĐỐI KHÔNG khóa upload video.
