# Khắc Phục Lỗi Timeout 45s Đa Tầng Của Advisor Sol (2026-10-19)

## 1. Hiện Tượng & Câu Hỏi Của Operator
Operator đã thiết lập tăng timeout trong script tư vấn (`consult_advisor.py`) lên 80s – 150s nhưng hệ thống vẫn liên tục báo lỗi timeout hoặc ngắt kết nối tại mốc 40s – 45s:
> *"Tại sao advisor sol t set tăng timeout r cứ bị báo quá 45s?"*

---

## 2. Bản Đồ 4 Tầng Timeout Gây Nghẽn (Multi-Layer Timeout Mismatch)

Khi gọi Advisor Sol qua cụm ChatGPT-Web Pool, request phải đi qua 4 tầng kiểm soát:

```
[Client / Coordinator CLI]
       │
       ▼ (Tầng 1: Script & Skill)
  consult_advisor.py (80s / 140s / 150s)
  scripts/advisor_consult.py (vẫn kẹt first_token_timeout = 45.0s)
       │
       ▼ (Tầng 2: OmniRoute Proxy :20129)
  ACCOUNT_SEMAPHORE_TIMEOUT_MS = 45000 (45s)
  STREAM_READINESS_TIMEOUT_MS  = 40000 (40s)
       │
       ▼ (Tầng 3: Hermes Tool)
  advisor_tool.py: DEFAULT_TIMEOUT = 55s
       │
       ▼ (Tầng 4: Windows Host Terminal Guard)
  GUARD_FOREGROUND_TIMEOUT_EXCEEDED = 60s
```

### Chi tiết từng tầng gây ngắt:

### Tầng 1: Lệch file thực thi giữa production script và skill
- `D:/Taadaa/tools/consult_advisor.py` đã nâng `first_token_timeout = 80.0s`, `idle_token_timeout = 20.0s`, `max_total_timeout = 140.0s`.
- Nhưng bản lưu trong Skill `advisor-dual-answer-orchestration/scripts/advisor_consult.py` vẫn giữ nguyên `first_token_timeout = 45.0s`.
- Khi hàm `_call_stream_chat` kiểm tra `if now - t_start > first_token_timeout: return False, f"First token deadline exceeded ({first_token_timeout}s)"`, nó ném thẳng chuỗi lỗi: `First token deadline exceeded (45.0s)`.

### Tầng 2: OmniRoute Proxy (:20129) bóp nghẹt tại `.env`
Dù client có chờ 150s, OmniRoute vẫn hủy kết nối ở 2 chốt chặn:
1. `ACCOUNT_SEMAPHORE_TIMEOUT_MS=45000` (45 giây): Hàng đợi giữ slot tài khoản ChatGPT-Web pool. Khi pool bận hoặc đang xoay tua, request chờ quá 45s sẽ nhận lỗi:
   `Error: Account semaphore acquire timeout after 45000ms`.
2. `STREAM_READINESS_TIMEOUT_MS=40000` (40 giây): Thời gian OmniRoute chờ byte stream đầu tiên từ OpenAI. Với reasoning model như Sol Web (`gpt-web-sol`), thời gian suy luận ngầm (thinking) thường tốn 20s–35s. Chỉ cần gặp mạng trễ hoặc OpenAI delay chạm 40s, OmniRoute tự hủy kết nối và ném lỗi `[499] Request aborted` (ghi nhận trong `call_logs` SQLite ở mốc ~40.028ms và 48.582ms).

### Tầng 3: `advisor_tool.py` trong Hermes Core
File `D:/Taadaa/Hermes/tools/advisor_tool.py`:
`DEFAULT_TIMEOUT = 55` và `b_to = min(max(float(timeout), 0.0), DEFAULT_TIMEOUT)`.
Hàm `min(..., 55)` bóp trần mọi request ở 55 giây.

### Tầng 4: Windows Host Terminal Guard
Nếu gọi script Sol qua terminal foreground, Windows Host Guard cưỡng chế `GUARD_FOREGROUND_TIMEOUT_EXCEEDED (60s)`. Quá 60s lệnh bị ngắt với `Exit 124`.

---

## 3. Quy Trình Khắc Phục Toàn Diện

1. **Đồng bộ mã nguồn Skill:**
   Cập nhật `scripts/advisor_consult.py` đồng bộ với `consult_advisor.py`:
   - `first_token_timeout = 80.0s`
   - `idle_token_timeout = 20.0s`
   - `max_total_timeout = 140.0s`
   - `timeout_sec = 150.0s`
2. **Nâng cấu hình OmniRoute (`C:/Users/Kibe/OmniRoute/.env`):**
   - Đặt `ACCOUNT_SEMAPHORE_TIMEOUT_MS=90000` (90s).
   - Đặt `STREAM_READINESS_TIMEOUT_MS=80000` (80s).
3. **Kỷ luật gọi qua Terminal CLI:**
   - Khi gọi qua terminal foreground, luôn kèm yêu cầu prompt cô đọng (<150 từ, yêu cầu trả lời thẳng 3 gạch đầu dòng không dẫn nhập) để Sol hoàn thành suy luận trong 15s–30s, không đụng trần 60s của Host Guard.
