# Sol Auditor Scorecard & Universal OmniRoute Resolution in Closeout Gate

## Bối cảnh sự cố kiến trúc (17-18/09/2026)
Khi đưa `closeout_gate.py` vào vận hành trên repo `taadaa-farm-tools`, xuất hiện hiện tượng cả máy Kibe và Admin đều mất bảng chấm điểm Scorecard 100 điểm, chỉ còn dòng `Verdict: APPROVED (PASS)` nhị phân. Đồng thời Admin bị lỗi kết nối mạng sang OmniRoute do hardcode `localhost:20129`.

## Nguyên tắc cốt lõi từ Sol Auditor (GPT-5.6 Sol High)
1. **Phân tách trách nhiệm (Separation of Concerns)**:
   - `closeout_gate.py` là **Orchestrator** điều phối Gate 1 (Review) và Gate 2 (Test).
   - Sol Auditor (hoặc prompt Rubric 100đ tương đương) là **Scoring Authority**.
   - **LLM KHÔNG ĐƯỢC TỰ QUYẾT ĐỊNH APPROVED/REJECTED**. LLM chỉ đánh giá 5 tiêu chí và trả về JSON Scorecard. Rule Engine trong code là nơi kiểm tra `overall_score >= 85` để đưa ra phán quyết cuối cùng.
2. **Rubric 5 tiêu chí 100 điểm**:
   - `logic_correctness`: Đúng đắn logic & Chống phát hiện (tối đa 35đ)
   - `test_evidence`: Độ phủ & Kết quả test thực tế (tối đa 25đ)
   - `telemetry_observability`: Telemetry & Khả năng quan sát (tối đa 15đ)
   - `farm_safety_regression`: An toàn Farm & Chống Regression (tối đa 15đ)
   - `code_architecture`: Chất lượng mã nguồn & Kiến trúc (tối đa 10đ)
   - **Ngưỡng PASS**: `overall_score >= 85` và `ready_to_close: true`.
3. **Universal Network Resolver (`resolve_omni_url`)**:
   - Thứ tự ưu tiên: `custom_url` -> `os.environ["OMNI_ROUTE_URL"]` -> `os.environ["OMNI_URL"]`.
   - Fallback probe: kiểm tra endpoint `/api/health` lần lượt qua:
     1. `http://localhost:20129/v1/chat/completions` (Kibe host)
     2. `http://127.0.0.1:20129/v1/chat/completions`
     3. `http://192.168.110.123:20129/v1/chat/completions` (IP LAN Kibe dành cho Admin)
   - Đảm bảo một codebase `closeout_gate.py` duy nhất chạy thông suốt trên cả Kibe và Admin.
