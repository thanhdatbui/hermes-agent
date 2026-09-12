# OmniRoute Review Gateway (:20129)

## Overview
OmniRoute chạy tại `http://localhost:20129` (song song với 9Router tại `:20128`), cung cấp các route chuyên biệt cho code review và agent execution.

## Endpoints & Models
- Endpoint: `POST http://localhost:20129/v1/chat/completions`
- Headers: `{"Content-Type": "application/json", "Authorization": "Bearer sk-antigravity"}`.
- Review models:
  - `review`: Cấu hình combo luân phiên qua pool tài khoản Google Gemini (`ag-gemini-pool-3` gồm >70 accounts active, dồi dào quota, cơ chế failover tự động bỏ qua account lỗi/bận). Chuyên dùng cho audit logic, review an toàn fail-closed, phản hồi siêu nhanh 8-15s, loại bỏ triệt để nghẽn Semaphore Timeout 429.
  - `ag-worker`: Route tới `gemini-3.8-flash-tiered` (200k context, max_output 131k). Phù hợp cho quick check, second opinion hoặc review nhẹ.

## Invocation Protocol
1. **Lấy exact diff:** Dùng `git diff <file1> <file2>` hoặc `git diff --cached`. Tuyệt đối không tóm tắt hay đưa văn bản mô tả thay thế git diff thực tế.
2. **Prompt chuẩn hoá:**
   - Khai báo role: Reviewer độc lập, read-only.
   - Bối cảnh thay đổi & task description.
   - Bắt buộc dòng đầu tiên của response phải là `VERDICT: APPROVED` hoặc `VERDICT: REJECT`.
   - Nếu `REJECT`: Liệt kê rõ file, dòng code, lỗi logic, vi phạm fail-closed, hoặc thiếu test.
   - Nếu `APPROVED`: Nhận xét ngắn gọn về độ an toàn, fail-closed, test coverage.
3. **Payload mẫu:**
```python
payload = {
    "model": "review",  # hoặc "ag-worker"
    "messages": [
        {"role": "user", "content": prompt}
    ],
    "stream": False,
    "max_tokens": 4096,
}
```

## Khác biệt giữa 9Router (:20128) và OmniRoute (:20129)
| Tiêu chí | 9Router (:20128) | OmniRoute (:20129) |
|---|---|---|
| Model review | `plan-review`, `plan-review-hard`, `gpt-5.6-terra`, `gpt-5.6-sol` | `review` (Claude Opus Thinking), `ag-worker` (Gemini Flash Tiered) |
| Auth key | Bắt buộc `NINEROUTER_API_KEY` | Không yêu cầu auth key cục bộ |
| Tool chuẩn | `invoke-plan-review.py` | Python HTTP script tới port 20129 |
