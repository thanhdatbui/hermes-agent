# Sol Auditor 100-Point Scorecard & Universal Closeout Gate Architecture

## 1. Nguyên nhân gốc rễ mất Scorecard khi chốt phiên (17/09 - 18/09/2026)
- **Sự cố:** Cả Kibe lẫn Admin khi chạy `closeout_gate.py` đều mất bảng chấm điểm Scorecard 5 tiêu chí thang điểm 100, chỉ hiển thị dòng nhị phân thô sơ `Verdict: APPROVED (PASS)`.
- **Nguyên nhân kỹ thuật:**
  1. `closeout_gate.py` phiên bản đầu dùng `DEFAULT_SYSTEM_PROMPT` kiểu nhị phân, ép LLM chỉ trả về `VERDICT: APPROVED` hoặc `VERDICT: REJECTED`.
  2. Bị hardcode URL `http://localhost:20129/v1/chat/completions` khiến máy Admin không thể gọi sang OmniRoute của Kibe (connection refused).
  3. `_detect_test_command` gọi `python` trần, trên Windows dễ bị nuốt vào python uv/system thiếu `pytest`.
  4. Pytest không chỉ định thư mục `tests/` nên scan toàn bộ repo, collect nhầm các script phụ kết thúc bằng `_test.py` (như `judge_per_test.py`) gây timeout/lỗi collect.
  5. Module-level network probe `OMNI_ROUTE_URL = resolve_omni_url()` gây side-effect probe mạng chậm khi vừa import module.

## 2. Kiến trúc chuẩn: Rule Engine + AI Auditor
- **LLM không được tự quyết định PASS/FAIL:** LLM đóng vai trò thẩm định viên phân tích và chấm điểm theo Rubric 5 tiêu chí.
- **Rule Engine là nơi quyết định:** `_parse_scorecard_and_verdict` trong `closeout_gate.py` parse JSON Scorecard và so sánh:
  - `overall_score >= 85` -> `APPROVED`
  - `overall_score < 85` -> `REJECTED`
- **Rubric 5 tiêu chí (100đ):**
  1. `logic_correctness`: Đúng đắn logic & Chống phát hiện (tối đa 35đ)
  2. `test_evidence`: Độ phủ & Kết quả test thực tế (tối đa 25đ)
  3. `telemetry_observability`: Telemetry & Khả năng quan sát (tối đa 15đ)
  4. `farm_safety_regression`: An toàn Farm & Chống Regression (tối đa 15đ)
  5. `code_architecture`: Chất lượng mã nguồn & Kiến trúc (tối đa 10đ)
- **Calculated Total Tracking:** Tự động đối soát tổng điểm từ `score_breakdown` (`calculated_total`) so với `overall_score` để phát hiện lệch điểm ảo giác.

## 3. Universal Network Resolver (`resolve_omni_url`)
Thứ tự ưu tiên resolve endpoint:
1. Tham số `custom_url` truyền vào CLI `--base-url`.
2. Biến môi trường `OMNI_ROUTE_URL`.
3. Biến môi trường `OMNI_URL`.
4. Tự động probe sức khỏe endpoint `/api/health` qua danh sách:
   - `http://localhost:20129/v1/chat/completions` (Kibe local)
   - `http://127.0.0.1:20129/v1/chat/completions`
   - `http://192.168.110.123:20129/v1/chat/completions` (Admin LAN IP gọi sang Kibe)
5. Fallback mặc định: `http://192.168.110.123:20129/v1/chat/completions`.
- **Lazy Loading**: Resolver chỉ được gọi trong `OmniRouteClient.__init__` khi thực sự gọi review, tránh network probe ở cấp module scope.

## 4. Bảo vệ thực thi Pytest trong Gate Runner
- Luôn dùng `sys.executable` thay vì `"python"`.
- Luôn chỉ định đích danh thư mục test:
  ```python
  if (repo_path / "tests").is_dir():
      return [sys.executable, "-m", "pytest", "tests", "--tb=short", "-q"]
  ```
- Tuyệt đối không chạy `pytest` trọc không đối số trên root directory để tránh dính file benchmark hay tool phụ.

## 5. Kinh nghiệm tối ưu payload để đạt điểm chuẩn (>= 85đ) trên Sol Scorecard
- **Tránh gửi Diff trần đơn độc qua `--input` / `--text`:**
  - Nếu chỉ gửi raw `git diff`, Sol Auditor sẽ trừ nặng điểm `test_evidence` (thường chỉ 10/25) và `telemetry_observability` do thiếu bằng chứng chạy thực tế, khiến tổng điểm tụt xuống ~76 - 82đ (Verdict: REJECTED).
- **Cấu trúc Payload 3 phần bắt buộc khi review focused scope:**
  ```markdown
  # TASK: <Mô tả mục tiêu ngắn gọn>

  ## 1. GIT DIFF:
  <diff từ git diff các file can thiệp>

  ## 2. TEST EXECUTION EVIDENCE:
  <output stdout/stderr từ lệnh chạy pytest thực tế>

  ## 3. TELEMETRY & OBSERVABILITY:
  <số liệu đo đạc thực tế trước/sau thay đổi từ log hoặc API, chứng minh giảm lỗi/false-positive>
  ```
- **Bắt buộc Unit Test kiểm tra giá trị biên (Boundary Tests):**
  - Khi thay đổi logic so sánh/threshold (`>= N`, `> X`), Sol Auditor luôn đòi hỏi test tại điểm biên liền kề (ví dụ: `N-1` vs `N`). Cần bổ sung test biên này vào test suite trước khi gọi closeout gate.

