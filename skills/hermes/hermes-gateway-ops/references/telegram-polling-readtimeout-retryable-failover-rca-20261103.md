# Telegram Polling ReadTimeout & Multi-ISP Failover RCA (2026-11-03)

## 1. Triệu Chứng Sự Cố (Incident Forensic)
- User gửi tin nhắn trên Telegram lúc **09:33:57** (`timestamp: 1793673237`).
- Telegram client hiện 2 dấu tick `✓✓` (tin nhắn đã lên máy chủ Telegram an toàn).
- Tuy nhiên suốt từ **09:30:55 đến 09:37:22 (hơn 6 phút)**, Dashboard OmniRoute (`:20129`) hoàn toàn **không nhận được bất kỳ request nào** (0 requests).
- Bot im lặng hoàn toàn, không typing, không trả lời cho đến **09:37:29** mới phát tin nhắn phản hồi đầu tiên.
- Hiện tượng lặp lại ngắt quãng nhiều lần trong ngày, mỗi lần đơ từ 3 đến 5 phút.

## 2. Bản Chất Kỹ Thuật & Root Cause (Smoking Gun)

### A. Tử huyệt `_is_retryable_connect_error` bỏ sót `httpx.ReadTimeout`
- Trong `plugins/platforms/telegram/telegram_network.py`, hàm phân loại lỗi:
  ```python
  # Code cũ:
  def _is_retryable_connect_error(exc: Exception) -> bool:
      return isinstance(exc, (httpx.ConnectTimeout, httpx.ConnectError, httpx.ProxyError))
  ```
- **Bản chất của Long-Polling:** Khi kết nối ngâm (`getUpdates`) gặp sự cố rớt gói ngầm từ nhà mạng (Silent TCP Stall), socket không sinh lỗi `ConnectTimeout` (vì kết nối đã thành công từ trước). Sau khi hết `HERMES_TELEGRAM_HTTP_READ_TIMEOUT=45.0`, `httpx` ném ra ngoại lệ **`httpx.ReadTimeout`**.
- Vì `ReadTimeout` không nằm trong danh sách retryable, `TelegramMultiISPTransport.handle_async_request()` **không kích hoạt failover sang Fallback Proxy (WARP `:40000`)**, mà ném thẳng ngoại lệ ra ngoài luồng `network_retry_loop` của PTB (Python-Telegram-Bot).

### B. Bẫy đụng độ giữa PTB Backoff và Watchdog Wedged Queue
1. PTB nhận `ReadTimeout`, ghi nhận lỗi mạng và phạt backoff: ngủ 5s $\to$ thử lại trên cùng Proxy Viettel đang ngập $\to$ ngâm tiếp 45s $\to$ văng `ReadTimeout` lần 2 $\to$ ngủ 10s.
2. Trong lúc đó, hàm `_probe_pending_updates` trong `adapter.py` (dòng 2465) thăm dò qua `get_webhook_info()` trên luồng general path (vẫn sống), phát hiện `pending_update_count > 0` tồn tại liên tiếp 2 chu kỳ thăm dò ($30\text{s} \times 2 = 60\text{s}$).
3. Watchdog đánh giá luồng tiêu thụ update bị kẹt cứng:
   `getUpdates consumer appears wedged (queue not draining); triggering polling restart`
4. Watchdog cưỡng chế **STOP toàn bộ tiến trình Polling, reset httpx connection pool và start_polling() lại từ đầu** (tiêu tốn thêm 45s–60s).
5. Đến khi updater khởi động lại xong hoàn toàn, toàn bộ tin nhắn tồn đọng mới ùa về, gây ra khoảng chết đúng **3m32s**.

## 3. Bản Vá Chuẩn Hóa O(1)
Mở rộng toàn diện các ngoại lệ timeout và socket network trong `plugins/platforms/telegram/telegram_network.py`:
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
            httpx.NetworkError,
        ),
    )
```

## 4. Kiểm Thử & Nghiệm Thu
- Khi gặp `ReadTimeout` trên Primary Proxy, `TelegramMultiISPTransport` lập tức nhận diện là lỗi có thể retry và **failover chuyển sang Fallback Proxy trong vòng 0.1s**, không ném exception làm sập updater PTB và không kích hoạt án phạt restart của watchdog.
- Unit test bắt buộc xác thực 8/8 assertions ngoại lệ (`ConnectTimeout`, `ConnectError`, `ProxyError`, `ReadTimeout`, `WriteTimeout`, `TimeoutException`, `NetworkError` $\rightarrow$ `True`; `ValueError` $\rightarrow$ `False`).
