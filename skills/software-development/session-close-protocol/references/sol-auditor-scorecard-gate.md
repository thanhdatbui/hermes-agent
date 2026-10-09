# Sol Auditor 100-Point Scorecard & Universal OmniRoute Resolution for Closeout Gate

## Overview
Runner `D:/Taadaa/tools/closeout_gate.py` điều phối chốt phiên và tích hợp Giám khảo chấm điểm Sol Auditor (GPT-5.6 Sol Web :20129) theo Rubric 100 điểm.

## 1. Universal OmniRoute Resolver
- **Localhost (Kibe)**: `http://localhost:20129/v1/chat/completions` (hoặc `http://127.0.0.1:20129/...`).
- **LAN Fallback (Admin / Remote Workers)**: `http://192.168.110.123:20129/v1/chat/completions`.
- **Thứ tự phân giải**:
  1. CLI `--base-url` hoặc env `OMNI_ROUTE_URL` / `OMNI_URL`.
  2. Thử socket probe localhost:20129 (timeout 0.8s - 1.0s).
  3. Nếu không truy cập được localhost, tự động fallback sang LAN URL.

## 2. Rule Engine & 100-Point Rubric
- LLM (`chatgpt-web/gpt-5.6-sol-high`) đóng vai trò Giám khảo chấm điểm độc lập, xuất JSON:
  - `logic_correctness`: 0-35đ
  - `test_evidence`: 0-25đ
  - `telemetry_observability`: 0-15đ
  - `farm_safety_regression`: 0-15đ
  - `code_architecture`: 0-10đ
  - `overall_score`: 0-100đ
- **Authority**: `closeout_gate.py` là bên quyết định kết quả dựa trên rule:
  - `overall_score >= 85` -> `APPROVED` (exit 0)
  - `overall_score < 85` -> `REJECTED` (exit 1)
- **Backward compatibility**: Nếu response là text legacy (chứa `VERDICT: APPROVED | REJECTED`), fallback về parse text truyền thống.
