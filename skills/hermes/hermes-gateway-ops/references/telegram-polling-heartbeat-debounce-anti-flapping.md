# Chẩn đoán & Xử lý Telegram Polling Heartbeat Degradation (Anti-Flapping & Adaptive Cadence)

## 1. Triệu chứng & Hiện trường
- Bot Telegram đột ngột im lặng từ 5 đến 10 phút, không kéo thêm tin nhắn mới.
- Dashboard LLM (OmniRoute / 9Router) hoàn toàn không nhận được request nào trong suốt khoảng thời gian đó.
- Trong `gateway.log` xuất hiện các dòng lặp liên tiếp:
  ```text
  WARNING hermes_plugins.telegram_platform.adapter: [Telegram] Telegram polling degraded (heartbeat probe); gateway stays alive and will retry. Error: httpx.ProxyError: Proxy Server could not connect: Host unreachable.
  WARNING hermes_plugins.telegram_platform.adapter: [Telegram] Telegram network error (attempt 1/10), reconnecting in 5s.
  ...
  WARNING hermes_plugins.telegram_platform.adapter: [Telegram] Telegram network error (attempt 2/10), reconnecting in 10s.
  ```

## 2. Nguyên nhân gốc rễ (Root Cause)
1. **Probe quá gắt**: Mặc định cũ trong `.env`:
   - `HERMES_TELEGRAM_HEARTBEAT_INTERVAL=15` (cứ 15s gọi `bot.get_me()` một lần).
   - `HERMES_TELEGRAM_HEARTBEAT_TIMEOUT=10.0` (chỉ cho phép timeout 10 giây).
   Khi mạng quốc tế hoặc WARP SOCKS5 bị micro-jitter (nghẽn gói 1-2 giây), probe bị timeout ngay lập tức.
2. **Thiếu cơ chế Debounce trong code**:
   - Trong `adapter.py` cũ (`_polling_heartbeat_loop`), chỉ cần probe fail **1 lần duy nhất**, adapter đã lập tức ra lệnh **STOP toàn bộ tiến trình Polling** và rơi vào thang phạt exponential backoff (5s -> 10s -> 20s -> 40s -> 60s).
   - Cứ vừa gượng dậy được 30s lại bị probe fail tiếp, dẫn đến hiện tượng flapping và tê liệt bot kéo dài 10-15 phút.
3. **Phân loại thiếu lỗi Proxy**:
   - Trong `telegram_network.py`, hàm `_is_retryable_connect_error(exc)` chỉ kiểm tra `ConnectTimeout` và `ConnectError`, bỏ sót `httpx.ProxyError` khiến proxy lỗi không kích hoạt được cơ chế retry failover đúng cách.

## 3. Giải pháp chuẩn hóa (3 lớp)

### Lớp 1: Cấu hình runtime giãn tần suất (`.env`)
```env
HERMES_TELEGRAM_HEARTBEAT_INTERVAL=180
HERMES_TELEGRAM_HEARTBEAT_TIMEOUT=45.0
HERMES_TELEGRAM_HTTP_READ_TIMEOUT=45.0
```

### Lớp 2: Code Debounce 3 lần + Adaptive Fast-Retry (`adapter.py`)
Trong `_polling_heartbeat_loop`:
```python
while True:
    try:
        # Nếu đang có lỗi dở (fail_count > 0), probe lại nhanh sau 15s thay vì 180s
        sleep_s = 15 if getattr(self, "_polling_heartbeat_fail_count", 0) > 0 else HEARTBEAT_INTERVAL
        await asyncio.sleep(sleep_s)
        ...
        await asyncio.wait_for(bot.get_me(), PROBE_TIMEOUT)
        self._polling_heartbeat_fail_count = 0  # Reset khi thành công
        ...
    except (asyncio.TimeoutError, OSError) as probe_err:
        self._polling_heartbeat_fail_count = getattr(self, "_polling_heartbeat_fail_count", 0) + 1
        if self._polling_heartbeat_fail_count >= 3:
            self._polling_heartbeat_fail_count = 0
            self._schedule_polling_recovery(probe_err, reason="heartbeat probe (3 consecutive failures)")
        else:
            logger.warning("[%s] Telegram heartbeat probe transient failure (%d/3): %s", self.name, self._polling_heartbeat_fail_count, probe_err)
    except Exception as probe_err:
        if self._looks_like_network_error(probe_err):
            self._polling_heartbeat_fail_count = getattr(self, "_polling_heartbeat_fail_count", 0) + 1
            if self._polling_heartbeat_fail_count >= 3:
                self._polling_heartbeat_fail_count = 0
                self._schedule_polling_recovery(probe_err, reason="heartbeat probe (3 consecutive failures)")
            else:
                logger.warning("[%s] Telegram heartbeat probe transient failure (%d/3): %s", self.name, self._polling_heartbeat_fail_count, probe_err)
            continue
```

### Lớp 3: Mở rộng Retryable Proxy Error (`telegram_network.py`)
```python
def _is_retryable_connect_error(exc: Exception) -> bool:
    return isinstance(exc, (httpx.ConnectTimeout, httpx.ConnectError, httpx.ProxyError))
```

## 4. Kỷ luật kiểm thử & Thẩm định
- Chạy unit test mô phỏng cả 2 kịch bản: transient fail 2 lần reset về 0, và fail liên tiếp 3 lần kích hoạt `_schedule_polling_recovery`.
- Thẩm định độc lập bằng Claude CLI hoặc Closeout Gate trước khi triển khai production.
