# Pure Sol Discipline & Clean-Fail Policy (2026-10-10)

## 1. Bối cảnh & Operator Chấn Chỉnh
Khi Operator hỏi nguyên nhân hoặc kiến trúc và yêu cầu gọi Advisor, Coordinator từng xây dựng fallback 3 tầng nhảy sang Gemini và 9Router. Operator phản ứng gay gắt:
> *"Sol gemini high là cái đéo gì v? R còn 9router nữa. Advisor thất bại thì cho fail luôn lấy info coordinator đủ r. Nhưnh time wait advisor phải tăng lên"*

## 2. Quy tắc cốt lõi (Core Principles)
1. **Advisor Sol là Duy Nhất (No Hybrid Fallbacks):**
   - Khi gọi Advisor Sol, CHỈ ĐƯỢC PHÉP gọi đúng endpoint `:20129 route review` (Sol Web High / `gpt-5.6-sol`).
   - Tuyệt đối CẤM tự ý fallback sang Gemini hay 9Router rồi ghép tên lai tạp ("Sol Gemini High", "Sol Backup 9Router"). Điều này làm sai lệch danh tính model và gây ức chế cho Operator.
2. **Fail Cleanly (Thất bại thì báo Fail luôn):**
   - Nếu Sol bị rate limit, cạn pool web hoặc timeout: Báo ngay `Advisor: unavailable (Sol / review timeout hoặc pool limit; chỉ hiển thị câu trả lời Coordinator)`.
   - Thông tin hiện trường và phân tích từ Coordinator là đủ thực chiến để ra quyết định. Không cần cố nhồi nhét model phụ vào làm loãng góc nhìn.
3. **Tăng thời gian chờ cho Reasoning Model (Timeout >= 45s):**
   - Sol Web High (`gpt-5.6-sol`) là reasoning model chuyên sâu, TTFT (Time To First Token) có thể mất 25–40s.
   - Cấm đặt timeout quá ngắn (4s–10s) dẫn đến false-negative timeout liên tục. Bắt buộc đặt `timeout_sec = 45.0s`.

## 3. Kiến trúc triển khai trong `advisor_consult.py`
```python
def consult_advisor(prompt: str, context: str = "", timeout_sec: float = 45.0) -> dict[str, Any]:
    # 1. Redact secrets (sk-*, Bearer, passwords, JSON quoted keys, basic auth)
    # 2. Call directly to OmniRoute :20129 review
    # 3. Stream SSE, verify [DONE] marker, filter pseudo-200 '[Error:'
    # 4. If failed/timed out -> return 'Advisor: unavailable' immediately.
```
