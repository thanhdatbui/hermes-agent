# Telegram Multi-ISP Failover: ReadTimeout Omission & Wedged getUpdates Queue RCA (2026-11-03)

## 1. Hiện tượng & Triệu chứng (Symptoms)
- Bot Telegram đột ngột bị "điếc" tin nhắn từng chặng 3–5 phút ở nhiều khung giờ khác nhau trong ngày.
- Tin nhắn gửi từ Telegram client hiện 2 dấu tick (`✓✓`), nhưng bot không typing, không phản hồi.
- Trên OmniRoute Dashboard ghi nhận khoảng mù 3–7 phút hoàn toàn không có request nào từ Telegram.
- **Bằng chứng timestamp O(1):**
  - User bấm gửi lúc `09:33:57` (timestamp Telegram: `1793673237`).
  - Session Hermes mãi đến `09:36:56` mới khởi tạo (`started_at: 1793673416`).
  - Bot phản hồi câu đầu tiên lúc `09:37:29` (ngâm tổng cộng 3 phút 32 giây).

---

## 2. Nguyên nhân gốc rễ (Root Cause Analysis)

### A. Tử huyệt trong `_is_retryable_connect_error` (`telegram_network.py`)
Trong `TelegramMultiISPTransport`:
```python
def _is_retryable_connect_error(exc: Exception) -> bool:
    return isinstance(exc, (httpx.ConnectTimeout, httpx.ConnectError, httpx.ProxyError))
```
- **Bản chất của Long-Polling (`getUpdates`):** Kết nối TCP giữa Gateway và Telegram Bot API qua proxy (Viettel `:10001` hoặc WARP `:40000`) đã được thiết lập từ trước. Khi nhà mạng hoặc proxy bị silent drop / rớt gói quốc tế, kết nối không bao giờ ném `ConnectTimeout`.
- Thay vào đó, sau khi hết `HERMES_TELEGRAM_HTTP_READ_TIMEOUT` (mặc định 45s), HTTP client văng ra **`httpx.ReadTimeout`**.
- Do `ReadTimeout` **không nằm trong danh sách retryable**, `TelegramMultiISPTransport.handle_async_request`:
  ```python
  except Exception as exc:
      if not _is_retryable_connect_error(exc):
          raise  # Không failover sang fallback proxy, vứt lỗi thẳng lên PTB!
  ```
  Hệ thống hoàn toàn **không kích hoạt failover sang fallback proxy** (WARP SOCKS5), mà để mặc lỗi ném lên `Application` của Python-Telegram-Bot (PTB).

### B. Bẫy Deadlock giữa PTB Backoff và Watchdog `_probe_pending_updates`
1. Khi PTB nhận `ReadTimeout`, vòng lặp nội bộ rơi vào thang phạt retry: ngủ 5s $\to$ thử lại trên cùng proxy bị ngâm $\to$ ngâm tiếp 45s $\to$ phạt ngủ 10s.
2. Trong lúc đó, hàm watchdog `_probe_pending_updates` trong `adapter.py` (dòng 2552) thăm dò qua `get_webhook_info()` (chạy trên luồng HTTP riêng) và phát hiện tin nhắn bị dồn ứ:
   ```text
   [Telegram] Telegram polling heartbeat: 1 update(s) queued but not consumed (stuck probe 1/2)
   ... (30s sau)
   [Telegram] getUpdates consumer appears wedged (queue not draining); triggering polling restart
   ```
3. Watchdog buộc phải kích hoạt quy trình cứu hộ cưỡng chế: **Hủy task polling, reset toàn bộ httpx connection pool và restart lại updater**.
4. Quá trình teardown + setup lại consumer ngốn thêm 45s–60s. Sau khi updater mới online, toàn bộ tin nhắn tồn đọng mới được kéo về dồn toa cùng một lúc.

### C. Dead-code `_stall_threshold_s`
- Tham số `TELEGRAM_FAILOVER_STALL_THRESHOLD` (mặc định 20s) được truyền vào `TelegramMultiISPTransport(stall_threshold_s=stall_s)`, nhưng bên trong transport biến này chỉ được gán vào `self._stall_threshold_s` mà **không hề được dùng ở bất kỳ logic nào**. Luồng request vẫn bị ngâm đủ 45s–60s theo socket timeout thay vì failover sau 20s.

---

## 3. Quy chuẩn Khắc phục Triệt để (Fix Specifications)

### 1. Mở rộng Retryable Timeout trong `telegram_network.py`
Bắt buộc bao gồm toàn bộ các họ timeout mạng của `httpx`:
```python
def _is_retryable_connect_error(exc: Exception) -> bool:
    return isinstance(
        exc,
        (
            httpx.ConnectTimeout,
            httpx.ConnectError,
            httpx.ProxyError,
            httpx.ReadTimeout,
            httpx.WriteTimeout,
            httpx.TimeoutException,
        ),
    )
```

### 2. Tận dụng `_stall_threshold_s` cho luồng `getUpdates`
Bọc request của Primary Transport với `asyncio.wait_for(..., timeout=self._stall_threshold_s)` hoặc hạ `HERMES_TELEGRAM_HTTP_READ_TIMEOUT=20.0` để chuyển ngay sang fallback proxy trong vòng $\le 20\text{s}$, không ngâm luồng 45s và không để watchdog phải restart updater.

### 3. Kỷ luật Phân biệt Long-Polling vs. Webhook
- **Webhook qua Cloudflare Tunnel:** Tránh dùng nếu local có nhiều tác vụ terminal/subagent nặng vì Tornado handler không kịp trả HTTP 200 $\to$ Telegram server phạt `Read timeout expired` giam tin 5–10 phút.
- **Long-Polling đa proxy:** Là phương án ổn định nhất trên mạng VN, nhưng BẮT BUỘC phải có failover `ReadTimeout` tức thời như trên.
