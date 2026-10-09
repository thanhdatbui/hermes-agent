# Telegram Multi-ISP Send & Edit Path Failover

## Bối cảnh & Hiện tượng (The Asymmetric Failover Bug)
- **Triệu chứng**: Khi WARP hoặc Proxy Viettel (192.168.110.2:10001) bị chập chờn hoặc rớt mạng, Gateway Telegram có thể rơi vào trạng thái "im lặng kéo dài" (im lặng 2 tiếng).
- **Nguyên nhân gốc rễ**:
  - Cơ chế Multi-ISP failover (`TelegramMultiISPTransport`) trước đây chỉ được bọc vào `get_updates_request` (đường nhận / Long Polling).
  - Đường gửi và chỉnh sửa tin nhắn (`request` / `send_message`, `edit_message_text`) lại dùng `HTTPXRequest(proxy=proxy_url, ...)`.
  - Khi proxy chết: Polling tự động chuyển sang FPT Direct (fallback DoH IPs) nên vẫn nhận tin nhắn từ user bình thường, tạo ảo giác bot vẫn sống. Nhưng khi bot gửi trả lời, request gửi tin vẫn cắm đầu vào proxy đã chết → treo connection, kích hoạt cờ `_send_path_degraded` hoặc drop tin nhắn hoàn toàn.

## Kiến trúc Bản vá (Symmetric Bidirectional Failover)
Trong `plugins/platforms/telegram/adapter.py`, khi phát hiện có `proxy_url` và `fallback_ips` (chế độ Multi-ISP):
Bắt buộc khởi tạo thêm một instance `TelegramMultiISPTransport` độc lập cho send path:

```python
# Send/edit path must fail over too, otherwise a dead proxy
# leaves polling alive but every reply undeliverable.
_multi_transport_send = TelegramMultiISPTransport(
    fallback_ips=fallback_ips,
    stall_threshold_s=stall_s,
    recovery_probe_interval_s=probe_s,
    **_multi_kwargs,
)
request = HTTPXRequest(
    **request_kwargs,
    httpx_kwargs={"transport": _multi_transport_send},
)
get_updates_request = HTTPXRequest(
    **request_kwargs,
    httpx_kwargs={"transport": _multi_transport},
)
```

### Invariants quan trọng:
1. **Tách biệt Transport Instances**:
   - `request` và `get_updates_request` BẮT BUỘC dùng 2 instance `TelegramMultiISPTransport` khác nhau (`_multi_transport_send` vs `_multi_transport`).
   - Tuyệt đối KHÔNG dùng chung 1 transport instance, vì polling chạy long-lived streaming connection trong khi send chạy short-lived transactional requests; dùng chung sẽ gây tranh chấp `_mode_lock` và kẹt connection pool.
2. **Kế thừa giới hạn kết nối (Limits)**:
   - Các tham số pool limits (`max_connections`, `max_keepalive_connections`, `keepalive_expiry`) phải được truyền vào `_multi_kwargs` cho cả 2 transport để chống rò rỉ fd (`CLOSE_WAIT`).

## 3 Vị trí Đồng bộ trên Windows Host
Trên môi trường Windows chạy Hermes Agent, code platform plugin có thể tồn tại ở 3 nơi cần đồng bộ khi vá nóng:
1. `D:/Taadaa/Hermes/plugins/platforms/telegram/adapter.py` (Source repo Git)
2. `C:/Users/Kibe/AppData/Local/hermes/hermes-agent/plugins/platforms/telegram/adapter.py` (Local bundle)
3. `C:/Users/Kibe/AppData/Local/hermes/hermes-agent/venv/Lib/site-packages/plugins/platforms/telegram/adapter.py` (Runtime thực tế mà gateway nạp)

*Quy tắc*: Sau khi vá và test, dọn sạch tất cả file `.bak-before-*` để tránh làm bẩn git status và gây nhầm lẫn khi review.

## Quy chuẩn Unit Test & Closeout Gate
Tạo file test focused `tests/test_telegram_send_failover.py` với 2 test cases:
1. `test_telegram_multi_isp_send_and_polling_transports`:
   - Mock `Application.builder()` và `HTTPXRequest`.
   - Cung cấp `proxy_url` và `fallback_ips`.
   - Assert: Cả `request` và `get_updates_request` đều có `transport` là `TelegramMultiISPTransport`.
   - Assert: `send_transport is not poll_transport` (hai instance độc lập).
2. `test_telegram_failover_disabled_uses_plain_proxy`:
   - Set `HERMES_TELEGRAM_DISABLE_FALLBACK_IPS=true`.
   - Assert: `send_req_kw.get("proxy") == proxy_url` và không inject custom transport.

Kiểm tra test chạy dưới 3s:
```bash
python -m pytest tests/test_telegram_send_failover.py --tb=short -q
```
Commit isolated candidate diff vào Git (`HEAD~1..HEAD`), sau đó chạy `closeout_gate.py` với `background=True, notify_on_complete=True`.

---

## Cạm bẫy SOCKS5/WARP Proxy: `httpx.ProxyError` trong `_is_retryable_connect_error`
- **Hiện tượng**: Khi WARP (`127.0.0.1:40000`) hoặc upstream proxy bị nghẽn/rớt kết nối tới CDN Telegram, Gateway văng lỗi:
  `httpx.ProxyError: Proxy Server could not connect: Host unreachable.`
  dẫn tới bot không nhận/tải được media (`⚠️ Couldn't download your photo (NetworkError)`), hoặc stall tin nhắn gửi đi.
- **Nguyên nhân cốt lõi trong `plugins/platforms/telegram/telegram_network.py`**:
  Hàm kiểm tra lỗi retryable ban đầu chỉ định nghĩa:
  ```python
  def _is_retryable_connect_error(exc: Exception) -> bool:
      return isinstance(exc, (httpx.ConnectTimeout, httpx.ConnectError))
  ```
  Trong HTTPX/HTTPCore, `httpx.ProxyError` **KHÔNG** kế thừa từ `ConnectError` hay `ConnectTimeout` (mà kế thừa trực tiếp từ `TransportError`).
  Hệ quả: Khi proxy chết trả về `Proxy Server could not connect: Host unreachable`, `_is_retryable_connect_error` trả về `False`!
  Cơ chế Multi-ISP failover (`_switch_to_fallback()`) bị **bỏ qua hoàn toàn**, không thể kích hoạt fallback sang FPT Direct, re-raise `ProxyError` ngay lập tức khiến toàn bộ retry tải ảnh / gửi tin đều chết theo proxy.
- **Giải pháp chuẩn hóa**:
  Bổ sung `httpx.ProxyError` vào bộ lọc retryable connect error trong `telegram_network.py`:
  ```python
  def _is_retryable_connect_error(exc: Exception) -> bool:
      return isinstance(exc, (httpx.ConnectTimeout, httpx.ConnectError, httpx.ProxyError))
  ```
  Nhờ đó, khi SOCKS5/WARP proxy rớt mạng, `TelegramMultiISPTransport` sẽ nhận diện đúng lỗi kết nối proxy và lập tức tự động switch sang FPT Direct (`_TelegramDirectFallbackTransport`) mà không làm đứt luồng của bot.

### Cạm bẫy Lệch Version giữa Git Repo và Venv Site-Packages (The Venv Drift Trap)
- **Rủi ro**: `hermes-agent` trên Windows khi chạy dưới dạng service / background gateway nạp trực tiếp module từ `.../hermes-agent/venv/Lib/site-packages/plugins/platforms/telegram/telegram_network.py`.
- **Hiện tượng**: Git repo nguồn (`hermes-agent/plugins/...`) đã có bản vá `httpx.ProxyError`, nhưng file trong `venv/Lib/site-packages/...` vẫn là code cũ chưa được copy sang. Kết quả: bot vẫn tiếp tục văng lỗi `⚠️ Couldn't download your photo (NetworkError)` và crash failover khi proxy chập chờn.
- **Quy tắc bắt buộc khi vá platform plugin**:
  1. Luôn kiểm tra diff giữa source và runtime: `diff -u <venv_path>/telegram_network.py <repo_path>/telegram_network.py`.
  2. Đồng bộ đúp vào cả file runtime trong `venv/Lib/site-packages` và source trong repo.
  3. Chạy `pytest tests/test_telegram_send_failover.py` với python của chính venv để bảo đảm runtime nạp đúng code mới.
