# Advisor Sol Idle Streaming Timeout Resolution (2026-10-18)

## 1. Bối cảnh & Thắc mắc của Operator
Trong phiên làm việc ngày 18/10/2026, Operator đã trực tiếp chất vấn:
> *"Tại sao gọi sol advisor chỉ để có 45s v?"*
Và khi được giải thích về sự cố chém ngang luồng streaming, Operator chỉ đạo dứt khoát:
> *"Sửa đi"*

---

## 2. Gốc rễ của con số 45s trước đây
1. **Host Terminal Foreground Guard (Trần 60s):**
   Trên môi trường Windows của farm, Coordinator chạy dưới sự giám sát của `GUARD_FOREGROUND_TIMEOUT_EXCEEDED` với trần cứng **60s**. Bất kỳ lệnh terminal foreground nào chạy quá 60s đều bị kill với mã lỗi `Exit 124`.
2. **Thời gian suy luận (Reasoning TTFT) của Sol Web:**
   Sol (`gpt-web-sol` qua cổng `:20129`) là reasoning model chạy trên cụm ChatGPT-Web Pool (115 accounts). Thời gian suy nghĩ ẩn (Time To First Token) trung bình mất **15s – 35s**, sau đó stream nội dung ra mất thêm **10s – 20s**.
3. **Chống nghẽn xoay vòng Pool (Waterfall Lockup):**
   Khi các account trong pool dính rate-limit hoặc captcha, OmniRoute sẽ thử rotate sang account kế tiếp. Nếu không có deadline cứng, lệnh sẽ bị kẹt xoay vòng nhiều account mất 2–3 phút, làm đóng băng phiên chat của Coordinator.
4. **Nhược điểm nghiêm trọng của trần cứng (Wall-Clock Dead Cut):**
   Trước đây `advisor_consult.py` dùng trần cứng tổng thời gian:
   ```python
   # LỖI CŨ:
   if time.monotonic() - start_time > timeout_sec: # 45s
       return False, f"Stream timeout exceeded {timeout_sec}s"
   ```
   Nếu Sol suy luận sâu mất 30s mới bắt đầu stream, đến giây thứ 45 trần cứng sẽ chém đứt ngang kết nối dù text đang được nhả ra ầm ầm!

---

## 3. Kiến trúc Đã Sửa Đổi: Idle Streaming Timeout 3 Tầng
Trong `scripts/advisor_consult.py`, cơ chế timeout đã được thiết kế lại hoàn toàn:

```python
def _call_stream_chat(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    first_token_timeout: float = 45.0,
    idle_token_timeout: float = 15.0,
    max_total_timeout: float = 90.0,
) -> Tuple[bool, str]:
    t_start = time.time()
    t_last_activity = t_start
    has_started_streaming = False
    ...
    with urllib.request.urlopen(req, timeout=first_token_timeout) as resp:
        for line in resp:
            now = time.time()
            if not has_started_streaming:
                if now - t_start > first_token_timeout:
                    return False, f"First token deadline exceeded ({first_token_timeout}s)"
            else:
                if now - t_last_activity > idle_token_timeout:
                    return False, f"Stream idle timeout exceeded ({idle_token_timeout}s)"

            if now - t_start > max_total_timeout:
                return False, f"Total stream timeout exceeded ({max_total_timeout}s)"

            # Nhận chunk thành công -> reset timer hoạt động
            if delta:
                has_started_streaming = True
                t_last_activity = now
```

### Các thông số chuẩn hóa:
1. **`first_token_timeout = 45.0s` (Thinking Allowance):** Cho phép Sol Web trọn vẹn 45s để suy luận ngầm và sinh token đầu tiên.
2. **`idle_token_timeout = 15.0s` (Chunk Keepalive):** Một khi đã bắt đầu stream chữ, đồng hồ đếm ngược được **reset liên tục sau mỗi chunk**. Miễn là model vẫn đang nhả chữ, stream sẽ không bao giờ bị cắt ngang câu. Chỉ khi đường truyền im lặng hoàn toàn quá 15s mới tính là rớt mạng.
3. **`max_total_timeout = 90.0s`:** Trần bảo vệ toàn cục chống treo socket vô hạn.
4. **`consult_advisor(timeout_sec=95.0)`:** Khống chế luồng ThreadPool với `wait=False, cancel_futures=True` đồng bộ với trần 90s của stream.
