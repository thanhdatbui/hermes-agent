# Grace Band (80-84) & Anti-Score-Chasing Invariant

## 1. Bản chất cơ chế Grace Band (80-84 Điểm)
- **Cơ sở pháp lý & Codebase:**
  * `closeout_policy.json`: quy định `"threshold": 85`, `"grace_threshold": 80`.
  * `gate_common.py`: hàm `passes(score, allow_grace=True)` kiểm tra `score >= grace_threshold (80)`.
  * `closeout_gate.py`: khi điểm `80 <= total < 85`, gắn cờ `ready_to_close = True`, `grace_band = True` và trả về `Verdict: APPROVED`.
  * `safe_push.py`: cho phép push khi `passed and (score >= 85 or is_grace or score >= 80)`.
- **CẤM TUYỆT ĐỐI Sonnet / Sol cày điểm vụn vặt:**
  * Khi điểm đạt trong khoảng **80–84** và **focused unit test đã XANH 100%**: ĐÂY LÀ ĐIỀU KIỆN ĐỦ ĐỂ APPROVED VÀ PUSH.
  * CẤM tiếp tục vòng lặp sửa docstring, thêm type hint, thêm telemetry râu ria để cố kéo từ 82 lên 85.
  * Càng cày điểm vụn vặt càng làm trôi sụt điểm số (LLM jitter) và gây bẫy kẹt phiên (anti-surrender loop).

## 2. Kỷ luật Anti-Surrender (CẤM dừng lại khóc lóc)
- Khi Operator phát lệnh "Done" / "Chốt":
  * Nhiệm vụ duy nhất của Coordinator là đưa task về đích: tự sửa qua Strike 1, 2, 3 (nếu < 80) cho tới khi >= 80 (Grace Band) rồi auto-push.
  * TUYỆT ĐỐI CẤM dừng lại chat giải trình thủ tục, lôi diff hoặc commit cũ ra đọc làm phiền Operator.
