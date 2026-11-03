# Chẩn Đoán Treo Session Sau Khi Reset PC & Kỷ Luật Không Xúi User Bấm /new Khi Đang Làm Dở

## 1. Bối Cảnh & Phản Ứng Thực Tế Của User
- **Tình huống:** Sau khi máy tính vừa restart/reset, người dùng thấy bot/session im lặng >10 phút, kiểm tra Dashboard OmniRoute thấy vệt request đứng im hoặc dính `TI: 0 | TO: 0`.
- **Mục tiêu thực sự của User:** Kiểm tra xem **hệ thống có bị lỗi cấu hình (config), đứt cổng hay chết gateway không**, hay chỉ là độ trễ bình thường sau khi reboot PC.
- **TỬ HUYỆT CẦN TRÁNH (GÂY ỨC CHẾ TỘT ĐỘ CHO USER):**
  * Vội vàng khuyên User gõ `/new` hoặc `/reset`!
  * User đang chạy task dở, nhiều context. Gõ `/new` làm mất sạch tiến trình và công sức của phiên làm việc.
  * Việc xúi `/new` khi chưa kiểm chứng thể hiện sự lười biếng, trốn tránh trách nhiệm chẩn đoán kỹ thuật.

## 2. Quy Trình Kiểm Tra Kỹ Thuật (Read-Only Chẩn Đoán Config & Runtime)
1. **Kiểm tra Gateway có sống không sau khi reboot:**
   - Quét tiến trình `pythonw.exe -m hermes_cli.main gateway run`. Sau khi PC bật lại, Scheduled Task hoặc Service VBS thường khởi động Gateway ngay.
2. **Kiểm tra cổng upstream (OmniRoute :20129, 9Router :20128):**
   - Probe `HTTP GET /api/health` hoặc `/` để xác nhận proxy cục bộ đã up chưa.
   - Thử gửi 1 completion test nhỏ (ping) tới pool model đang active (`ag-gemini-pool-3`, `ag-sonnet`, `gemini-web`) để đo latency.
3. **Giải mã vệt `TI: 0 | TO: 0` trên OmniRoute Dashboard:**
   - **Bằng chứng:** Request đã lên tới Dashboard OmniRoute chứng tỏ **Gateway và kết nối Telegram -> Hermes -> OmniRoute hoàn toàn thông suốt**, không hề lỗi config hay chết mạng.
   - **Bản chất vệt `TI: 0 | TO: 0`:** Request gọi vào model/combo upstream (ví dụ ChatGPT Web / Codex) nhưng bị Cloudflare Turnstile Captcha chặn (`HTTP 403`). Không có token nào được sinh ra, OmniRoute fallback liên tục qua các tài khoản khác trong pool khiến bảng log xuất hiện một chuỗi `TI: 0 | TO: 0`.
   - **Khoảng mù sau đó:** Khi fallback kết thúc hoặc session đang chờ người dùng/chờ background task chạy xong, hệ thống ở trạng thái IDLE, không có request mới là hoàn toàn đúng logic.

## 3. Kỷ Luật Trả Lời User
- **Khẳng định ngay tình trạng config:** Nêu rõ "Cấu hình Gateway và Proxy hoàn toàn bình thường, không bị lỗi config".
- **Giải thích nguyên nhân độ trễ:** Do máy vừa reset, cơ chế auto-resume nạp lại các session nền + upstream combo dính nhịp fallback/Turnstile.
- **TUYỆT ĐỐI KHÔNG xúi giục bấm `/new`:** Để nguyên session cho hệ thống tiếp tục xử lý hoặc để User tự quyết định.
