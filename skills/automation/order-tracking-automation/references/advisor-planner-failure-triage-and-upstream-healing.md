# Advisor Planner Failure Triage & Upstream Self-Healing Invariants

## 1. Ngữ cảnh & Triệu chứng Sự cố
Khi chạy `unified_patch_pipeline.py run`, bước S1 Plan triệu tập Hội đồng Cố vấn (`gate_b_planner.py`).
Nếu gặp lỗi:
- `PLAN_FAILED` do Sol timeout (>300s) hoặc 503.
- `PLAN_FAILED` do Gemini Web (Argon) fail `old_string not unique: count=0`.
- Coordinator vội vã kết luận `L3 BLOCKED` và dừng lại than thở với User ("bại liệt").

## 2. Kỷ luật Bắt buộc đối với Coordinator
- **CẤM BÁO L3 BLOCKED VỘI VÃ:** Coordinator tuyệt đối không được viện cớ gate/advisor lỗi để báo bại liệt dừng việc khi chưa kiểm tra nguyên nhân kỹ thuật upstream.
- **CHỦ ĐỘNG GỠ UPSTREAM:** Phải lập tức mở log OmniRoute (`C:/Users/Kibe/AppData/Roaming/omniroute/logs/omniroute-stdout.log`) và `gate_b_audit.jsonl` để định danh chính xác nguyên nhân:
  1. *Nếu Sol treo/timeout:* Thường do socket Node.js của OmniRoute (`PID`) bị nghẽn sau nhiều request lớn hoặc dính Turnstile Cloudflare 403 (`circuit breaker tripped for chatgpt-web`).
     - Giải pháp: Kill ngay các PID node.exe bị nghẽn để watchdog phục hồi socket sạch, hoặc điều hướng Sol trong `gate_b_planner.py` sang pool lành mạnh (`ag-gemini-pool-3`).
  2. *Nếu Gemini Web rớt vì regex escape:* Khi trả về JSON, các escape regex như `split(/[\\/]/)` thường bị JSON decoder nuốt mất backslash thành `split(/[\/]/)`.
     - Giải pháp: Bổ sung cơ chế `Fuzzy Escape Fallback` trong hàm `validate_plan()` của `gate_b_planner.py` để tự động đối chiếu các biến thể `[\\/]` vs `[/]` mà không đánh trượt plan oan uổng.
