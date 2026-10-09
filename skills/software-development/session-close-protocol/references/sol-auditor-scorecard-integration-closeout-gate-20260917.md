# Sol Auditor Scorecard Integration in closeout_gate.py & Universal Network Resolution

## 1. Context & Problem History (17/09/2026)
- Ban đầu, `sol_auditor.py` (cổng :20129) được xây dựng để thẩm định chốt phiên theo Rubric 5 tiêu chí thang điểm 100 (Logic 35đ, Test 25đ, Telemetry 15đ, Safety 15đ, Architecture 10đ), yêu cầu `overall_score >= 85` mới cho phép đóng phiên.
- Khi init repo `taadaa-farm-tools`, script `closeout_gate.py` được mang ra làm runner tự động hóa Gate 1 + Gate 2. Tuy nhiên, `DEFAULT_SYSTEM_PROMPT` của nó lại chỉ yêu cầu trả về nhị phân: `VERDICT: APPROVED` hoặc `VERDICT: REJECTED`, và URL bị hardcode `http://localhost:20129/v1/chat/completions`.
- Kết quả: Cả máy Kibe lẫn máy Admin khi chốt phiên bị "APPROVED mù" — mất hoàn toàn bảng điểm Scorecard, và máy Admin khi gọi `localhost:20129` bị lỗi mạng `Connection Refused`.

## 2. Kiến trúc Giải pháp Chuẩn (Phân tích từ Sol Auditor)
- **Tách bạch vai trò:**
  - `closeout_gate.py`: Orchestrator điều phối toàn bộ pipeline Gate 1 (Review) + Gate 2 (Pytest).
  - `sol_auditor.py` (hoặc engine scoring Rubric 100đ): Scoring Authority.
  - **Quy tắc bất biến:** LLM KHÔNG được tự quyền quyết định `APPROVED/REJECTED`. LLM chỉ phân tích và chấm điểm chi tiết 5 tiêu chí trả về qua JSON Scorecard. Rule engine của `closeout_gate.py` dựa trên điểm tổng `overall_score >= 85` mới là nơi quyết định `APPROVED`.

## 3. Universal Network Resolution Pattern
Cả 2 cụm máy Kibe và Admin dùng chung mã nguồn tại `D:/Taadaa/tools/closeout_gate.py`. Cơ chế resolve URL cho OmniRoute `:20129` phải tuân theo thứ tự:
1. `os.environ.get("OMNI_ROUTE_URL")` (nếu có cấu hình riêng trong `.env`).
2. Thử `http://localhost:20129/v1/chat/completions` (nếu chạy trực tiếp trên Kibe host).
3. Fallback sang IP LAN `http://192.168.110.123:20129/v1/chat/completions` (cho máy Admin hoặc CI).

```python
def resolve_omniroute_url() -> str:
    env_url = os.environ.get("OMNI_ROUTE_URL")
    if env_url:
        return env_url
    # Candidates check
    candidates = [
        "http://localhost:20129/v1/chat/completions",
        "http://192.168.110.123:20129/v1/chat/completions"
    ]
    # Default fallback to LAN IP for cross-machine parity
    return "http://192.168.110.123:20129/v1/chat/completions"
```

## 4. Contract Schema Bắt Buộc của Scorecard JSON
`closeout_gate.py` parse response JSON từ model review:
```json
{
  "overall_score": 90,
  "verdict": "APPROVED",
  "score_breakdown": {
    "logic_correctness": 32,
    "test_evidence": 22,
    "telemetry_observability": 15,
    "farm_safety_regression": 14,
    "code_architecture": 9
  },
  "key_findings": [
    "Test coverage xanh 100%",
    "Đảm bảo an toàn không tranh chấp lock"
  ],
  "judge_notes": "Đánh giá chi tiết...",
  "ready_to_close": true
}
```
- Rule: Nếu `overall_score >= 85` và focused pytest PASS -> Gate PASS (`exit 0`).
- Nếu `overall_score < 85` hoặc thiếu trường điểm -> Gate REJECT (`exit 1`), CẤM đóng phiên.
