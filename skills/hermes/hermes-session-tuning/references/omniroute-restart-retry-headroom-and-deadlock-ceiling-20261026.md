# Khoảng Treo OmniRoute Restart, Bẫy "The model provider failed after retries" & Đồng Bộ Retry Headroom (26/10/2026)

## 1. Triệu Chứng & Trải Nghiệm Tiêu Cực Của User
- Dashboard OmniRoute (`:20129`) ghi nhận khoảng trống dài ~20 phút không có call log nào.
- Khi người dùng gửi tin nhắn trên Telegram qua nhiều topics/sessions song song, đồng loạt nhận phản hồi lỗi:
  > *"⚠️ The model provider failed after retries. I kept raw provider details out of chat; check gateway logs for diagnostics."*
- Người dùng bức xúc vì turn bị hủy ngang, phải vào từng topic/session gõ lại câu lệnh từ đầu và nghi ngờ có ai đó tự ý hạ timeout hệ thống.

---

## 2. Nguyên Nhân Gốc Rễ Đã Xác Minh (4 Tầng Lệch Pha)

### Tầng 1: Bão rớt proxy mobile & Khóa cứng Event Loop (16:58)
- Hàng loạt proxy `test.taadaa.click:51xx` (5103, 5111, 5113, 5114, 5115) bị ngắt kết nối (`PROXY_UNREACHABLE`, `ECONNRESET`).
- Đồng thời các session dồn context payload lớn (~405k tokens) stream kéo dài gần 50s khiến luồng Node.js của OmniRoute bị deadlock hoàn toàn.

### Tầng 2: Trần phát hiện Deadlock của Watchdog quá dài (6 phút)
- Trong `C:\Users\Kibe\AppData\Roaming\omniroute\omniroute_watchdog.ps1`:
  `$MaxDeadlockFailures = 12`
- Mỗi chu kỳ kiểm tra `/api/health` tốn 15s timeout + 15s sleep = ~31s.
- 12 chu kỳ thất bại liên tiếp = $12 \times 31\text{s} = 372\text{s}$ (**hơn 6 phút**).
- OmniRoute bị đơ cứng suốt 6 phút (16:59:52 đến 17:05:32) Watchdog mới nhận định là deadlock và kích hoạt force-restart.

### Tầng 3: Tử huyệt Retry Headroom của Hermes quá ngắn (18s vs 30s restart)
- Trong cấu hình Hermes: `agent.api_max_retries` trước đó được đặt là `3` (nhằm giảm tải retry storm ở đợt 02/10).
- Với `max_retries = 3` và backoff cấp số nhân (~2s, ~4s, ~8s):
  **Tổng thời gian kiên nhẫn chờ đợi của Hermes chỉ kéo dài ~15 – 18 giây**.
- Trong khi đó, OmniRoute khi bị kill cần **25 – 30 giây** để compile runtime, load SQLite `storage.sqlite` và bind lại cổng 20129.
- **Hệ quả chết người:** Cổng 20129 chưa kịp mở thì Hermes đã đốt sạch 3 lượt retry $\rightarrow$ Hermes phán quyết provider chết hẳn $\rightarrow$ ngắt turn và gửi thông báo lỗi ra Telegram.

### Tầng 4: Fallback Provider tự trỏ vào chính mình
- Cấu hình `fallback_providers` trong config trỏ vào `http://192.168.110.123:20129/v1`.
- Cả primary (`127.0.0.1:20129`) và fallback (`192.168.110.123:20129`) đều là **cùng một tiến trình OmniRoute** trên máy Kibe. Khi OmniRoute sập, fallback sang chính nó vẫn vấp `Connection Refused` $\rightarrow$ cơ chế failover hoàn toàn vô hiệu.

---

## 3. Bản Vá Kỹ Thuật Đã Áp Dụng & Chuẩn Hóa

### A. Nâng Retry Headroom Cho Hermes
Đã cập nhật cấu hình Hermes qua công cụ chuẩn:
```bash
python D:/Taadaa/tools/manage_hermes_config.py set agent.api_max_retries 6 --type int
```
- Chuỗi retry với 6 lượt: `2s → 4s → 8s → 16s → 32s → 60s` $\rightarrow$ **Tổng thời gian chờ đạt ~122 giây (hơn 2 phút)**.
- Khi OmniRoute restart xong ở giây thứ 25–30, lượt retry thứ 4 hoặc 5 của Hermes gửi sang sẽ kết nối thành công ngay khi cổng 20129 vừa mở.
- **Hiệu quả:** Bot tự động tiếp tục xử lý và trả lời bình thường, không hủy turn, không văng tin nhắn lỗi ra chat, triệt tiêu hoàn toàn việc user phải chat lại.

### B. Hạ Trần Deadlock Của Watchdog OmniRoute (Khuyến nghị 4 lần / ~2 phút)
- Trong `omniroute_watchdog.ps1`, hạ `$MaxDeadlockFailures` từ `12` xuống `4`.
- Thời gian phát hiện deadlock giảm từ 6 phút xuống còn **~2 phút**, vừa khít với cửa sổ kiên nhẫn 2 phút của Hermes.

### C. Độc Lập Hóa Fallback Provider
- Trỏ `fallback_providers` sang một endpoint độc lập thực sự (ví dụ 9Router `http://127.0.0.1:20128/v1` hoặc upstream direct có credential riêng) thay vì trỏ lại cổng 20129.
