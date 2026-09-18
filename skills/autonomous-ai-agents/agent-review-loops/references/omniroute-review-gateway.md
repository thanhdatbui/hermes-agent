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
1. **Model Specification Discipline & Root Cause Anti-Insanity (Bắt buộc dùng `review` hoặc `chatgpt-web/gpt-5.6-sol-high`):**
   - TUYỆT ĐỐI CẤM caller / script / subagent tự ý gửi trực tiếp `chatgpt-web/gpt-5.6-sol-pro` hoặc fallback hạ cấp sang `chatgpt-web/gpt-5.6-sol-instant`.
   - **Bẫy Agent Over-engineering / CLI Speculation (Root Cause 18/09/2026):** Subagent sau khi inspect `/v1/models` thấy danh sách model alias trả về có `sol-pro`, tự suy diễn "phải gọi bản Pro cho xịn nhất" rồi tự gõ `--model "chatgpt-web/gpt-5.6-sol-pro"` vào CLI `closeout_gate.py`.
   - Hậu quả: `sol-pro` trên ChatGPT Web backend có quota cực kỳ ngặt nghèo (vài requests / 3-5h). Bắn vào acc sẽ ăn ngay `[502]: You've hit your limit. Please try again later.`. Khi dính 502, agent lại tự chữa cháy nhảy sang `sol-instant` (0 thinking / không suy luận), phá hỏng toàn bộ chuẩn review khắt khe của Farm.
   - **Quy tắc điều phối & thực thi:**
     * BẮT BUỘC giữ nguyên default `--model review` khi gọi `closeout_gate.py` (hoặc chỉ định đích danh `chatgpt-web/gpt-5.6-sol-high`).
     * Combo `review` đã cấu hình Tier 0 là `chatgpt-web-pool` xoay vòng đều 16 accounts qua Round-Robin chạy `gpt-5.6-sol-high`, tự động failover sang account kế tiếp khi gặp 429/502 mà bảo toàn 100% lane Sol High.
     * CẤM Coordinator và Worker dispatch các lệnh gọi review có cờ model can thiệp sang Pro/Instant.
     * **Cơ chế Khóa cứng Đa tầng (Hard Gate Enforcements):**
       - *Tầng 1 (Core Gate):* `closeout_gate.py` whitelist cứng `ALLOWED_REVIEW_MODELS = {"review", "chatgpt-web/gpt-5.6-sol-high"}` và blacklist `FORBIDDEN_MODEL_PATTERNS = ["sol-pro", "sol-instant", "gpt-5.6-sol-pro", "gpt-5.6-sol-instant"]`. Chặn ngay tại `main()` với exit code `2` kèm structured JSON log vào stderr (`{"event": "MODEL_DRIFT_BLOCKED", ...}`) và raise `ValueError` tại `run_gate_pipeline()`.
       - *Tầng 2 (Pre-tool Hook Hermes):* Hook `guard_model_drift.py` chặn lệnh terminal gọi `--model` chứa các pattern cấm (`sol-pro`, `sol-instant`) trước khi tool kịp thực thi.
       - *Tầng 3 (Unit Tests Regression):* Khóa test suite `test_closeout_gate_scorecard.py` kiểm thử fail-closed mọi flag vi phạm, test pre-tool hook stdin/stdout block & allow, test argument parsing chấp nhận các flag hợp lệ, và không hardcode absolute paths (dùng `Path(__file__)`).

2. **Lazy URL Resolution (Tránh import side-effect):**
   - Không gọi `resolve_omni_url()` tại cấp module (`OMNI_ROUTE_URL = resolve_omni_url()` -> ANTI-PATTERN).
   - Đặt hằng số tĩnh mặc định `OMNI_ROUTE_URL = "http://localhost:20129/v1/chat/completions"`.
   - Chỉ resolve URL động (probe network) lười (lazy) bên trong `OmniRouteClient.__init__` hoặc khi runner thực sự chạy review để tránh làm chậm unit test và các tác vụ import module.
3. **Scorecard Validation & Telemetry:**
   - Khi parse scorecard JSON từ Sol/Reviewer, kiểm tra tính nhất quán giữa `overall_score` và tổng `score_breakdown`:
     `calc_total = sum(scorecard["score_breakdown"].values())`.
   - Nếu có chênh lệch (`calc_total != total`), ghi nhận vào telemetry của scorecard: `scorecard["calculated_total"] = calc_total`.
   - Kết quả pipeline trả về trường telemetry giàu dữ liệu:
     `result["telemetry"] = {"resolved_url": client.base_url, "duration_s": elapsed, "has_scorecard": bool(scorecard), "model_locked": True, "enforced_model": model}`.

