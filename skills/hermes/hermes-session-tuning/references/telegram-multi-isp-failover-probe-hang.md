# Telegram Multi-ISP Failover Flapping, Unbounded Probe Hang & 10-Minute Omni Silence

## Incident Summary (26/10/2026)
- **Triệu chứng**: Dashboard OmniRoute (`:20129`) hoàn toàn trống trơn 0 request suốt 10 phút 15 giây (từ `13:10:49` đến `13:21:04`), trong khi user liên tục nhắn tin trên Telegram nhưng bot im bặt không typing, không xử lý.
- Đến đúng `13:20:26`, hệ thống bất ngờ xả dồn đồng loạt 7 tin nhắn cùng một giây, làm bùng nổ requests token lớn (250k–470k tokens) sang OmniRoute.

## Cơ chế lỗi gốc rễ (Root Cause Analysis)

### 1. `_probe_primary_recovery` thiếu timeout cứng trên `handle_async_request`
Trong `TelegramMultiISPTransport` (`plugins/platforms/telegram/telegram_network.py`):
```python
async def _probe_primary_recovery(self) -> None:
    while True:
        await asyncio.sleep(self._recovery_probe_interval_s)
        if self._current_mode != "fallback":
            return
        try:
            req = httpx.Request("GET", f"https://{_TELEGRAM_API_HOST}/")
            resp = await self._get_primary().handle_async_request(req)
            if 200 <= resp.status_code < 500: ...
```
- Khi gọi trực tiếp `handle_async_request(req)` trên `httpx.AsyncHTTPTransport` (thay vì qua `httpx.AsyncClient`), httpx **không áp dụng request/read timeout**.
- Khi WARP proxy (`127.0.0.1:40000`) vấp mạng hoặc ngâm socket, lệnh probe bị treo vĩnh viễn ở mức TCP/socket Windows (lên tới 10 phút chờ TCP keepalive/RST).
- Hệ quả: Luồng `_probe_primary_recovery` bị đóng băng, không bao giờ hoàn thành lần probe 2 để gọi `_switch_to_primary()`.

### 2. Mắc kẹt tại `FALLBACK (FPT Direct)`
- Trong suốt thời gian probe bị treo, `self._current_mode` bị khóa chặt ở `"fallback"`.
- Tại Việt Nam, ISP FPT Direct chặn/bóp kết nối long-poll `getUpdates` của `api.telegram.org`.
- Không một tin nhắn nào từ Telegram Server kéo được về máy Kibe $\rightarrow$ Gateway không có tin nhắn để dispatch $\rightarrow$ Agent hoàn toàn idle $\rightarrow$ OmniRoute 0 request trong 10 phút.

### 3. Khớp nối watchdog trễ (`HERMES_TELEGRAM_HEARTBEAT_INTERVAL=180`)
- Cấu hình trong `.env` đặt interval heartbeat lên tới 180s (3 phút).
- Hàm `_probe_pending_updates` trong `adapter.py` yêu cầu 2 lần probe liên tiếp phát hiện `pending_update_count > 0` mới kích hoạt recovery:
  $$3\text{ phút} \times 2 = 6\text{–}10\text{ phút}$$
- Watchdog phát hiện kẹt hàng đợi quá chậm, khuếch đại thời gian chết của hệ thống.

## Biện pháp khắc phục chuẩn hóa

1. **Bọc `asyncio.wait_for` trên Probe Call (`telegram_network.py`)**:
   ```python
   resp = await asyncio.wait_for(
       self._get_primary().handle_async_request(req),
       timeout=5.0
   )
   ```
   Nếu primary proxy không phản hồi trong 5 giây, probe coi như fail ngay lập tức, giải phóng coroutine cho vòng lặp tiếp theo.

2. **Hạ Heartbeat Interval về chuẩn (`.env`)**:
   - Đặt `HERMES_TELEGRAM_HEARTBEAT_INTERVAL=30` (30 giây).
   - Watchdog phát hiện `pending_update_count` kẹt và restart polling chỉ trong tối đa 60 giây.
