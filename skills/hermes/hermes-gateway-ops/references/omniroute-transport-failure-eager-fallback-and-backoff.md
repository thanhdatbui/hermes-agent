# OmniRoute Transport Failure, Eager Fallback & Retry Backoff Architecture

## Bối cảnh & Hiện tượng (Sự cố Hermes báo sập trong khi OmniRoute bình thường)
- **Hiện tượng**: Khi đường truyền mạng ngoại vi (Viettel) chập chờn hoặc chuyển mạng sang FPT Direct, socket TCP tới OmniRoute (`192.168.110.123:20129`) bị reset (`APIConnectionError: Connection error`).
- **Nghịch lý**: Dù OmniRoute `:20129` trên LAN vẫn sống 100% và chỉ mất kết nối trong vài giây, Hermes Gateway chỉ sau 2–3 giây đã bỏ cuộc và văng cảnh báo:
  `"⚠️ The model provider failed after retries. I kept raw provider details out of chat; check gateway logs for diagnostics."`
  Đồng thời phiên chat bị treo cứng suốt 7 phút (từ 10:23 đến 10:30).

## Nguyên nhân gốc rễ: Cái bẫy Eager Fallback & Lệch pha Retry Policy

### 1. Bẫy Fast Failover (`_is_transport_failure and retry_count >= 2`)
Trong `agent/conversation_loop.py`, lỗi kết nối transport (`APIConnectionError`, `timeout`, `overloaded`) bị áp quy tắc ngắt sớm:
```python
_should_fallback = (
    is_rate_limited
    or (_is_transport_failure and retry_count >= 2)
)
```
- Lần 1: Gặp `Connection error` $\to$ `retry_count = 1`, Hermes chờ `_DEFAULT_RETRY_BASE_DELAY` (mặc định là `2.0s`).
- Lần 2: Thử lại ở giây thứ 2, mạng chưa ổn định hoàn toàn $\to$ `retry_count = 2`.
- `retry_count >= 2` lập tức kích hoạt `_should_fallback = True` $\to$ Hermes kích hoạt fallback ngay tức khắc mà không cho primary provider cơ hội tự phục hồi khi mạng ổn định lại sau 5–10s.

### 2. Tử huyệt trong chuỗi `fallback_providers`
Khi bị đẩy ra khỏi `:20129`, Hermes đi theo cấu hình `fallback_providers` trong `config.yaml`:
1. **Nấc 1 - Cockpit `:60818`**: Trả về `503` (`auth_not_found: No active session/cookie`).
2. **Nấc 2 - 9Router `:20128`**: Trả về `404` (`No active credentials for provider: antigravity`).
3. Tại 9Router `:20128`, do lỗi là HTTP 404 (Application error chứ không phải Transport failure), Hermes **không** kích hoạt Fast Failover mà lại áp dụng retry thông thường:
   - Thử lại đủ **10 lần retry** (`api_max_retries = 10`).
   - Thời gian backoff tăng dần: 2s $\to$ 4s $\to$ 11s $\to$ 17s $\to$ 35s $\to$ 60s $\to$ 86s!
   - Kết quả: Phiên làm việc bị giam luồng suốt 7 phút trong khi OmniRoute `:20129` vẫn khỏe mạnh.

## Giải pháp Chuẩn hóa Kiến trúc

### 1. Tăng độ lì lỗi mạng trong `conversation_loop.py`
Thay vì mới fail 2 lần đã bỏ chạy, cho phép Hermes kiên trì giữ kết nối với primary provider ít nhất 5 lần:
```python
_should_fallback = (
    is_rate_limited
    or (_is_transport_failure and retry_count >= 5)
)
```

### 2. Giãn khoảng nghỉ Retry Base Delay trong `retry_utils.py`
Nâng thời gian chờ tối thiểu giữa các lần retry để vượt qua cửa sổ chập chờn mạng (ISP failover Viettel $\leftrightarrow$ FPT kéo dài 5–15s):
```python
_DEFAULT_RETRY_BASE_DELAY = 5.0    # Tăng từ 2.0s -> 5.0s
_OVERLOAD_RETRY_BASE_DELAY = 15.0  # Tăng từ 10.0s -> 15.0s
```

### 3. Cấu hình Fallback Nội bộ OmniRoute & Cắt ngắn Trần Retry (`config.yaml`)
- **Fallback ưu tiên #1**: Giữ nguyên trên OmniRoute `:20129` bằng cách trỏ sang pool dự phòng (`ag-gemini-pool-3`), không nhảy ra cổng ngoài `:20128` hay `:60818`:
  ```yaml
  fallback_providers:
    - provider: omni
      model: ag-gemini-pool-3
      base_url: http://192.168.110.123:20129/v1
      key_env: OMNIROUTE_API_KEY
    - provider: 9router
      model: omni-worker
      base_url: http://192.168.110.123:20128/v1
      key_env: NINEROUTER_API_KEY
  ```
- **Hạ trần `api_max_retries`**: Đặt `agent.api_max_retries: 6` (thay vì 10) để khi một provider thực sự chết, hệ thống fail-fast hoặc chuyển fallback dứt khoát trong vòng 30–45s, không ngâm luồng 7 phút.
