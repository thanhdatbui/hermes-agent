# Telegram Gateway Idle Blind Spot vs. OmniRoute 403 Turnstile Burst RCA (2026-11-03)

## 1. Hiện Tượng & Nghi Ngờ Ban Đầu (Symptoms & Misdiagnosis)
* **Màn hình OmniRoute Dashboard:** Đồng hồ trên điện thoại lúc 09:33 nhưng log request gần nhất dừng lại ở 09:30:55. Khoảng trống ~2-3 phút hoàn toàn không có request mới.
* **Ngay trước khoảng mù (09:30:24 – 09:30:39):** Xuất hiện chuỗi 5-8 request liên tiếp có `TI: 0 | TO: 0` và TPS `-`.
* **Phán đoán nhầm phổ biến của Agent:** Vội vàng kết luận Gateway bị sập, hoặc kết nối Telegram bị đứt ngầm do nhà mạng bóp Long-polling / Webhook.

---

## 2. Bản Chất Thực Tế Từ Đối Soát CSDL (`.omniroute/storage.sqlite`)

### A. Vệt `TI: 0 | TO: 0` là HTTP 403 Turnstile, Không Phải Mạng Đơ
Truy vấn trực tiếp bảng `call_logs` tại thời điểm đó:
```sql
SELECT timestamp, status, duration, model, tokens_in, tokens_out, error_type, error_summary 
FROM call_logs 
WHERE timestamp >= '2026-11-03T02:30:00Z' AND timestamp <= '2026-11-03T02:31:00Z';
```
* **Kết quả:** Các request này trả về `status: 403`, lỗi:
  `[403]: ChatGPT blocked the request (Sentinel/Turnstile required). Try again later or open chatgpt.com in a browser to refresh state.`
* **Cơ chế:** Khi tài khoản ChatGPT Web trong pool bị Cloudflare Turnstile chặn họng, OmniRoute kích hoạt combo fallback chuyển sang tài khoản khác liên tục 8 lần trong 45 giây. Do bị chặn ngay từ cổng vào, không có token nào được sinh ra (`TI: 0 | TO: 0`). Đến 09:30:54, fallback sang account lành lặn thành công (`Status 200`).

### B. Khoảng Mù 2-3 Phút Là Trạng Thái IDLE Của Session
* Lúc 09:30:54 và 09:30:55, cả 2 session (`conv_82a95e1...` và `conv_8ca5fd3...`) đều đã sinh phản hồi xong và trả về cho Telegram client.
* Từ 09:30:55 đến 09:33:00, người dùng đang đọc tin nhắn hoặc chưa gõ lệnh tiếp theo.
* **Quy luật:** Khi không có tin nhắn mới và không có background tool nào đang chạy, OmniRoute không nhận request là **HOÀN TOÀN ĐÚNG LOGIC VẬN HÀNH**, không phải hệ thống bị treo.

---

## 3. Lịch Sử Kiến Trúc: Webhook vs. Long-Polling trên Taadaa Farm
* **21–23/09 (Cloudflare Tunnel Webhook):** Cài `cloudflared.exe` map `bot.taadaa.click` $\to$ port 8443. Chạy mượt nhưng có tử huyệt: khi host chạy lệnh terminal nặng (như `os.walk`), tiến trình giữ GIL khiến Gateway không trả `200 OK` kịp trong 5s cho Telegram $\to$ Telegram server phạt `Read timeout expired` và ngắt đẩy webhook 5-10 phút.
* **28/09 (Chốt chuyển sang Long-Polling qua WARP SOCKS5):** Chạy `TELEGRAM_PROXY=socks5://127.0.0.1:40000`, bot chủ động kéo tin khi rảnh. Ổn định suốt tháng 10.
* **02–03/11 (Nguy cơ Flapping do Fallback Proxy):** Khi di dời sang `D:\Taadaa\Hermes\.venv`, thêm `TELEGRAM_FALLBACK_PROXY=http://192.168.110.2:10001`. Cơ chế probe ngầm 60s vội nhảy ngược về WARP khi WARP bị bóp UDP (MASQUE) gây chu kỳ gián đoạn `getUpdates`.

---

## 4. Kỷ Luật Điều Phối & Phản Biện (Devil's Advocate Protocol)
1. **Truy vấn Ground Truth trước khi phán:** CẤM nhìn vào khoảng trống dashboard rồi suy diễn mạng hỏng. Bắt buộc query SQLite `storage.sqlite` (cột `status`, `error_type`, `error_summary`) để biết request thật sự là gì.
2. **Triệu hồi Hội đồng Cố vấn (-a all):** Tuân thủ quy tắc triệu hồi song song cả Sol (:20129) và Claude CLI để có góc nhìn phản biện khách quan 2 chiều (Internal vs External).
3. **Chống Flapping Proxy:** Tuyệt đối không để 2 proxy giành giật nhau. Ưu tiên khóa cứng 1 tuyến (Viettel LAN hoặc WARP) và siết heartbeat interval = 30s.
