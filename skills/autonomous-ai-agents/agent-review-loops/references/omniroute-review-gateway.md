# OmniRoute Review Gateway (:20129)

## Overview
OmniRoute chạy tại `http://localhost:20129` (song song với 9Router tại `:20128`), cung cấp các route chuyên biệt cho code review và agent execution.

## Endpoints & Models
- Endpoint: `POST http://localhost:20129/v1/chat/completions`
- Headers: `{"Content-Type": "application/json", "Authorization": "Bearer sk-antigravity"}`.
- Review models:
  - `review`: Combo đa tầng bảo vệ toàn diện (cập nhật 09/2026):
    * **Tier 0 (Primary):** `chatgpt-web/gpt-5.6-sol-high` qua pool 5 accounts ChatGPT-Web sống khỏe — reasoning cao cấp nhất (Sol), zero token cost, bắt bẫy invariant và bẫy speculative architecture cực kỳ xuất sắc. Tự động xoay acc khi gặp rate limit 429.
    * **Tier 1:** `gpt-5.6-terra-high` (Codex Farm pool).
    * **Tier 2:** `ag-opus-pool` (Claude Opus 4.6 Thinking trên pool 78 Google accounts).
    * **Tier 3-6:** `oc/nemotron-3.5-lightning-free` -> `openrouter/nvidia/nemotron-3-super-120b-a12b:free` -> `oc/muse-spark-1.3-contributor-free` -> `oc/muse-spark-1.2-contributor-free`.
    * **Tier 7:** `ag-gemini-pool-3` (Lưới an toàn cuối cùng).
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

## Closeout Gate Tooling Best Practices (`closeout_gate.py`)
1. **Lazy URL Resolution (Tránh import side-effect):**
   - Không gọi `resolve_omni_url()` tại cấp module (`OMNI_ROUTE_URL = resolve_omni_url()` -> ANTI-PATTERN).
   - Đặt hằng số tĩnh mặc định `OMNI_ROUTE_URL = "http://localhost:20129/v1/chat/completions"`.
   - Chỉ resolve URL động (probe network) lười (lazy) bên trong `OmniRouteClient.__init__` hoặc khi runner thực sự chạy review để tránh làm chậm unit test và các tác vụ import module.
2. **Scorecard Validation & Telemetry:**
   - Khi parse scorecard JSON từ Sol/Reviewer, kiểm tra tính nhất quán giữa `overall_score` và tổng `score_breakdown`:
     `calc_total = sum(scorecard["score_breakdown"].values())`.
   - Nếu có chênh lệch (`calc_total != total`), ghi nhận vào telemetry của scorecard: `scorecard["calculated_total"] = calc_total`.
   - Kết quả pipeline trả về trường telemetry:
     `result["telemetry"] = {"resolved_url": client.base_url, "duration_s": elapsed, "has_scorecard": bool(scorecard)}`.

