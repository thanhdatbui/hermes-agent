# Hermes Transport Eager Fallback & Retry Resilience (OmniRoute :20129 vs 9Router :20128 vs Cockpit :60818)

## 1. Hiện Tượng & Nguyên Nhân Gốc Rễ Sự Cố 10h30 (08/10/2026)
- **Triệu chứng:** OmniRoute (`:20129`) vẫn hoạt động 100% bình thường, nhưng Hermes lại báo sập với cảnh báo:
  `"⚠️ The model provider failed after retries. I kept raw provider details out of chat; check gateway logs for diagnostics."`
- **Nguyên nhân kép (Cascading Failover Trap):**
  1. **Đứt kết nối tạm thời do chuyển mạng (ISP Failover):**
     Khi đường truyền mạng (Viettel) bị drop gói tin, plugin Telegram chuyển interface sang FPT Direct $\to$ Đứt socket TCP đang giữ tới `:20129` $\to$ Hermes bắt gặp `APIConnectionError: Connection error`.
  2. **Bẫy Eager Fallback với Transport Error trong Hermes (`agent/conversation_loop.py`):**
     Hermes phân loại lỗi mạng là `_is_transport_failure = classified.reason in {FailoverReason.timeout, FailoverReason.overloaded}`.
     Code mặc định kích hoạt fallback sớm:
     ```python
     _should_fallback = (
         is_rate_limited
         or (_is_transport_failure and retry_count >= 2)
     )
     ```
     Với `_DEFAULT_RETRY_BASE_DELAY = 2.0s`, chỉ sau đúng 2 lần retry (chưa đầy 2-3 giây), Hermes vội vàng bỏ `:20129` và nhảy fallback!
  3. **Chuỗi Fallback rách nát kích hoạt kẹt luồng 7 phút:**
     - Nấc 1: Cockpit (`:60818`) trả về `503 upstream_error auth_not_found` (mất session/cookie).
     - Nấc 2: 9Router (`:20128`) trả về `404 No active credentials for provider: antigravity`.
     - Vì 404 là lỗi HTTP application (không phải transport error), cơ chế Eager Fallback không kích hoạt, buộc Hermes phải retry đủ `api_max_retries = 10` với exponential backoff tăng dần lên tới 86s $\to$ Giam chết phiên trong 7 phút rồi văng lỗi sập.

---

## 2. Các Biện Pháp Khắc Phục Triệt Để

### A. Tinh chỉnh độ lì retry mạng của Hermes (`agent/retry_utils.py` & `conversation_loop.py`)
1. **Tăng ngưỡng chịu đựng lỗi mạng trước khi nhảy Fallback:**
   Trong `agent/conversation_loop.py`, nâng điều kiện nhảy fallback từ 2 lần lên 5 lần:
   ```python
   _should_fallback = (
       is_rate_limited
       or (_is_transport_failure and retry_count >= 5)
   )
   ```
   Giúp Hermes kiên trì giữ kết nối với OmniRoute `:20129` khi mạng chập chờn thay vì mới thử 2 lần (2s) đã hoảng loạn nhảy fallback.
2. **Tăng Base Delay khi gặp lỗi mạng/socket:**
   Trong `agent/retry_utils.py`:
   - `_DEFAULT_RETRY_BASE_DELAY`: Nâng từ `2.0s` $\to$ `5.0s`.
   - `_OVERLOAD_RETRY_BASE_DELAY`: Nâng từ `10.0s` $\to$ `15.0s`.
   Khoảng nghỉ giãn ra 5s, 10s, 20s... kèm jitter để cho mạng ISP kịp hồi phục.
3. **Giảm trần retry tối đa để chống kẹt luồng dài:**
   Đặt `agent.api_max_retries = 6` (qua `hermes config set agent.api_max_retries 6`). Tạo ra cửa sổ tự hồi phục 30–60s đủ dài mà không bị kẹt tới 7-10 phút khi upstream thực sự chết.

### B. Cấu hình Fallback an toàn cùng Host (`config.yaml`)
Không để fallback trỏ sang các port ngoài (`:60818`, `:20128`) khi chưa kiểm chứng credential. Thay vào đó, ưu tiên fallback sang **pool dự phòng của OmniRoute ngay trên `:20129`**:
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
Khi `omni-worker` gặp trục trặc, Hermes tự động chuyển sang pool `ag-gemini-pool-3` trên cùng endpoint `:20129` một cách mượt mà.
