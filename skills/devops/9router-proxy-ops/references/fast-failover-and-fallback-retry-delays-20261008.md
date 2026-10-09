# Fast Failover & Fallback Retries Analysis: OmniRoute (:20129) vs 9Router (:20128)

## 1. Hiện Tượng & Câu Hỏi Cốt Lõi (Sự Cố 10h30 Ngày 08/10/2026)
- **Hiện tượng:** Người dùng quan sát thấy Hermes báo sập gateway với thông báo:
  `"⚠️ The model provider failed after retries. I kept raw provider details out of chat; check gateway logs for diagnostics."`
  trong khi cổng chính OmniRoute (`:20129`) vẫn hoạt động bình thường, không hề chết.
- **Thắc mắc:** 
  1. Tại sao Hermes lại chuyển hướng gọi nhầm sang cổng `:20128` (9Router)?
  2. Tại sao thời gian retry trên cổng `:20129` lại diễn ra quá nhanh (chưa tới vài giây đã nhảy fallback)?

---

## 2. Giải Mã Kiến Trúc Retry Của Hermes Core (`agent/conversation_loop.py`)

### A. Cơ Chế "Eager Fallback" Đối Với Lỗi Mạng Transport
Trong mã nguồn `conversation_loop.py`, Hermes có cơ chế phân loại lỗi đặc thù:
- Khi gặp lỗi đứt socket / rớt mạng (`APIConnectionError: Connection error`), biến cờ `_is_transport_failure = True` được kích hoạt.
- Luật kích hoạt fallback sớm:
  ```python
  _should_fallback = (
      is_rate_limited
      or (_is_transport_failure and retry_count >= 2)
  )
  if _should_fallback and agent._fallback_index < len(agent._fallback_chain):
      # KÍCH HOẠT NHẢY FALLBACK NGAY LẬP TỨC!
  ```
- **Hệ quả:** Đối với lỗi transport/socket trên primary provider (`:20129`), Hermes **chỉ cho phép retry đúng 2 lần** thay vì chờ đủ 10 lần.
- Công thức backoff mặc định: `wait = min(base_delay * 2^(attempt-1), max_delay) + jitter` với `base_delay = 2.0s`.
  - Lần 1: Chờ ~1s.
  - Lần 2: Chờ ~1s $\to$ Đạt điều kiện `retry_count >= 2`.
  - $\to$ **Tổng thời gian retry trên `:20129` chỉ mất từ 1 đến 2 giây** trước khi Hermes chuyển sang fallback tiếp theo.

---

## 3. Tại Sao Luồng Bị Trôi Sang Cổng `:20128` (9Router)?

### A. Chuỗi Cấu Hình Fallback Trong `config.yaml`
```yaml
fallback_providers:
  - provider: cockpit      # Nấc 1: :60818 (gpt-6-luna)
  - provider: 9router      # Nấc 2: :20128 (omni-worker)
```

### B. Hiệu Ứng Đổ Domino Lúc 10:23:00
1. **Mạng Viettel chập chờn:** Multi-ISP failover của plugin Telegram kích hoạt chuyển interface sang FPT Direct, làm đứt các socket TCP đang mở tới loopback `:20129`.
2. **Hermes fast-failover khỏi `:20129`:** Sau 2 nhịp transport error (~2s), Hermes chuyển sang **Cockpit `:60818`**.
3. **Cockpit `:60818` trả về lỗi 503:**
   ```text
   503 - auth_not_found: No active session/cookie
   ```
4. **Hermes trôi tiếp sang Nấc 2 - 9Router `:20128`:**
   Tại 9Router, model `omni-worker` gọi provider `antigravity`, nhưng provider này không có credential hợp lệ:
   ```text
   404 - No active credentials for provider: antigravity
   ```
5. **Cái Bẫy 404:** Khác với lỗi mạng (Transport error chỉ retry 2 lần), lỗi HTTP 404 là Application error. Hermes **không kích hoạt Fast Failover**, mà kiên nhẫn retry đủ 10 lần với thời gian backoff tăng dần lên tới **80 giây/lần**.
6. **Kết cục:** Hermes bị giam chân tại 9Router suốt 7 phút (từ 10:23 đến 10:30), cuối cùng kiệt sức văng thông báo *"⚠️ The model provider failed after retries"* lên Telegram.

---

## 4. Bài Học Vận Hành & Khắc Phục Phòng Ngừa (Best Practices)
1. **Dọn sạch Provider Mất Credential Khỏi Fallback Chain:**
   Tuyệt đối không để một gateway/proxy thiếu active accounts/credentials (như 9Router `:20128` khi rỗng pool) nằm trong `fallback_providers`. Khi primary chớp tắt 2s, luồng sẽ bị hút vào "hố đen" retry 7 phút.
2. **Khôi Phục Primary Tức Thì Khi Có Tin Nhắn Mới:**
   Hermes tự động gọi `restore_primary_runtime()` khi bắt đầu một turn trò chuyện mới (`inbound message`). Do đó, chỉ cần user gửi một tin nhắn mới, Hermes sẽ lập tức hồi phục kết nối về `:20129`.
3. **Ưu Tiên Fallback Nội Bộ Cùng Cổng (OmniRoute Combo):**
   Thay vì fallback chéo cổng (`:20129` $\to$ `:60818` $\to$ `:20128`), nên cấu hình combo model trên chính `:20129` để OmniRoute tự động đổi pool ngầm (ví dụ Gemini $\to$ Opus) mà không làm rách socket ở tầng client Hermes.
