# Telegram Multi-ISP Flapping Trap & Dual-Proxy Failover Architecture

## Bối cảnh sự cố (26/10/2026)
User phản ánh: "Cứ thỉnh thoảng treo cụ 5-10ph" và "Sao nay lại gặp tình trạng gateway hermes treo k gửi request tới omni nữa. Bữa t fix đc r mà, h lại bị lại".
Ảnh chụp Dashboard OmniRoute cho thấy khoảng trống 13:10:49 đến 13:20:26 (gần 10 phút) hoàn toàn 0 request tới OmniRoute, bot Telegram không nhận tin nhắn và không typing.

## 1. Cơ chế lỗi gốc rễ (Root Cause)

### A. Bẫy Flapping không Debounce trong `telegram_network.py`
- Gateway sử dụng Cloudflare WARP local làm Primary: `TELEGRAM_PROXY=socks5://127.0.0.1:40000`.
- Trong `TelegramMultiISPTransport.handle_async_request`:
  ```python
  try:
      return await self._get_primary().handle_async_request(request)
  except Exception as exc:
      if not _is_retryable_connect_error(exc):
          raise
      await self._switch_to_fallback()
      self._ensure_recovery_probe()
      return await self._get_fallback().handle_async_request(request)
  ```
- **Tử huyệt**: Không có debounce! Chỉ cần WARP local vấp nhẹ 1 gói tin (Windows tái chế ephemeral port hoặc WARP reconnect 100ms), Multi-ISP lập tức chuyển chế độ sang `FALLBACK (FPT Direct)`.
- Ghi nhận thực tế trong `gateway.log`: Hiện tượng này xảy ra tới **55 lần trong 1 ngày**!

### B. Mạng FPT Direct tại Việt Nam chặn/bóp Telegram Long-polling
- Tại Việt Nam (FPT, Viettel, VNPT), các dải IP máy chủ Telegram DC5 Singapore (`149.154.166.0/20`) bị nhà mạng bóp băng thông, drop gói hoặc chặn ngầm (Silent TCP Stall).
- Khi Gateway bị bẻ sang `FPT Direct`, kết nối `getUpdates` ngâm liên tục bị tường lửa FPT bóp nghẹt $\rightarrow$ Bot bị "điếc" tin nhắn, không thể kéo update mới từ Telegram về Gateway.
- Vì không có tin nhắn Telegram chuyển sang Agent $\rightarrow$ Agent không gọi OmniRoute $\rightarrow$ Dashboard OmniRoute đứng im 0 request.

### C. Luồng Probe hồi phục không có Timeout (`asyncio.wait_for`)
- Trong `_probe_primary_recovery`:
  ```python
  req = httpx.Request("GET", f"https://{_TELEGRAM_API_HOST}/")
  resp = await self._get_primary().handle_async_request(req)
  ```
- Lệnh gọi trực tiếp transport không có timeout bọc ngoài. Khi socket cổng 40000 bị ngậm TCP handshake, luồng probe bị đóng băng cứng ngắc suốt **590 giây (~10 phút)**!
- Trong 10 phút đó, Gateway bị giam chặt ở FPT Direct. Chỉ khi socket probe hết hạn lúc 13:20:26, probe thành công và giật ngược về WARP thì 7 tin nhắn dồn ứ mới ùa về máy:
  `Telegram polling heartbeat: 7 update(s) queued but not consumed`.

---

## 2. Bài học chống Regression: Vì sao KHÔNG ĐƯỢC hạ `HERMES_TELEGRAM_HEARTBEAT_INTERVAL`?

- **Bẫy tư duy nông cạn**: Khi thấy log báo `polling heartbeat ... update(s) queued`, phản xạ vội vàng là muốn hạ `HERMES_TELEGRAM_HEARTBEAT_INTERVAL` từ 180s xuống 30s để "phát hiện nhanh hơn".
- **Sự thật lịch sử (Fix ngày 28/09/2026)**:
  - Trước đây để interval 15s–30s không có debounce. Mỗi khi WARP lag 1s là probe `get_me()` tạch $\rightarrow$ adapter tự kill polling để reconnect $\rightarrow$ dính chuỗi phạt Exponential Backoff (5s $\rightarrow$ 10s $\rightarrow$ 20s $\rightarrow$ 40s $\rightarrow$ 60s) làm bot đơ 5–10 phút liên tục.
  - Phải nâng lên `180s` để khử độ nhạy, chống tự sát khi mạng vấp nhẹ.
- **Kết luận**: Hạ heartbeat interval sẽ gây **regression 100%** với bản fix 28/09. Heartbeat không phải nguyên nhân gây đơ trưa nay.

---

## 3. Kiến trúc chuẩn: Dual-Proxy Failover (WARP ↔ Viettel Proxy)

Thay vì fallback ra mạng trực tiếp FPT Direct (vốn bị ISP chặn), Gateway phải cấu hình 2 tầng Proxy độc lập:

| Tuyến | Endpoint | Bản chất |
|---|---|---|
| **PRIMARY** | `socks5://127.0.0.1:40000` (Cloudflare WARP) | Tuyến chính, cực nhanh, trễ 0.8s, chạy local |
| **FALLBACK** | `http://192.168.110.2:10001` (Router Viettel Farm) | Tuyến dự phòng, trễ 0.9s, mạng Viettel độc lập, không bị chặn |

### Nguyên tắc triển khai an toàn:
1. **Debounce 2 nhịp trước khi Failover**: Bắt buộc Primary phải fail liên tiếp 2–3 lần mới chuyển sang Fallback, triệt tiêu 100% tình trạng vấp 1 gói là nhảy tuyến.
2. **Hard Timeout cho Probe**: Bọc `asyncio.wait_for(self._get_primary().handle_async_request(req), timeout=5.0)` để probe không bao giờ ngậm socket quá 5s.
3. **Cấu hình `TELEGRAM_FALLBACK_PROXY`**: Cho phép khai báo proxy fallback riêng trong `.env`, nếu không khai báo mới dùng Direct DoH fallback.
