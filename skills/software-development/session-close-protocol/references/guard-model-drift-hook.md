# Hard Gate Model Drift Guard (sol-pro / sol-instant Prevention)

## 1. Context & Motivation
Khi chốt phiên (`session-close-protocol`), tool `closeout_gate.py` chịu trách nhiệm chạy reviewer (dùng LLM pool để audit diff & evidence).
Combo review chuẩn được quy định là pool review (`Sol-High pool 16 accounts` hoặc fallback model quy chuẩn), TUYỆT ĐỐI KHÔNG dùng `sol-pro` hay `sol-instant`.
Tuy nhiên, trong thực tế các agent có thể tự ý truyền `--model chatgpt-web/gpt-5.6-sol-pro` hoặc `--model sol-instant`, gây drift tài nguyên, làm nghẽn quota hoặc bypass rubric đánh giá.

## 2. Zero-Bypass Pre-tool Hook: `guard_model_drift.py`
Để ngăn chặn hoàn toàn ở tầng Hermes runtime (trước khi lệnh terminal được thực thi):
- File hook: `D:/Taadaa/tools/hooks/guard_model_drift.py`
- Hook bắt mọi lệnh gọi `terminal` có chứa `closeout_gate`.
- Dùng regex kiểm tra cờ `--model`:
  - `forbidden = [r"--model\s+['\"]?.*(?:sol-pro|sol-instant|pro|instant)", r"--model\s+chatgpt-web/gpt-5\.6-sol-pro"]`
- Nếu khớp: trả về JSON `{"action": "block", "message": "..."}` và exit 0 ngay lập tức, ngăn Hermes terminal tool chạy lệnh.

## 3. Hermers Config Activation
Được kích hoạt trong `C:/Users/Kibe/AppData/Local/hermes/config.yaml`:
```yaml
hooks:
  pre_tool_call:
    - command: python D:/Taadaa/tools/hooks/guard_model_drift.py
      matcher: terminal
      timeout: 5
```

## 4. Test Suite Coverage
Tại `D:/Taadaa/tools/tests/test_closeout_gate_scorecard.py`:
- `test_closeout_gate_rejects_forbidden_model`: Kiểm tra `closeout_gate.py` trả về exit code 2 khi truyền `--model chatgpt-web/gpt-5.6-sol-pro`.
- `test_closeout_gate_rejects_instant_model`: Kiểm tra `closeout_gate.py` trả về exit code 2 khi truyền `--model chatgpt-web/gpt-5.6-sol-instant`.
Đảm bảo toàn bộ 7/7 tests của suite pass 100%.
