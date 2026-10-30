# Unified Pipeline (Gate 1 to 6) & Mechanical Enforcement Architecture (2026-10-30)

## 1. Bản chất kiến trúc xâu chuỗi (Unified Pipeline)
- Khi xâu chuỗi từ Gate 1 đến Gate 6 trong một lệnh tự động `unified_patch_pipeline.py`:
  * **S0 (Precheck):** Gate 1 (chặn batch-job) & Gate 5 (khóa scope target files, kiểm tra clean working tree).
  * **S1 (Plan):** Gate A & Gate B (Thang Planner: Gemini Web 120s -> Claude CLI 150s -> Sol 120s). Timeout tổng >= 420s để Sol luôn có slot cứu hộ.
  * **S2 (Patch):** Gate C (Thang Worker: Qoder T0 -> Sol T1 -> Agy T2 -> Haiku T3).
    - Hậu kiểm độc lập: Không tin mồm Worker; snapshot `pre_content` trước khi sửa; kiểm tra `post_content == pre_content.replace(old, new, 1)` để tránh false-reject khi thêm dòng.
  * **S3 (Verify):** Chạy focused test command < 30s.
  * **S4 (Canary Gate 6):** Tự động phát hiện task chạm vào farm device -> chạy `canary_runner.py` trên 1 máy thật, chụp ảnh screencap, OCR verify, trích xuất `MEDIA:<path>`.
  * **S5 (Hold):** Xuất báo cáo, in `MEDIA:<path>`, ghi `state.json` với `status=AWAITING_USER` kèm `diff_hash_at_hold` và THOÁT TIẾN TRÌNH.

## 2. Cơ chế Confirm Chốt Phiên (Anti-Bypass & Fail-Closed)
- Pipeline chỉ chốt khi User gõ đúng từ khóa:
  - Regex chính xác: `^(done|chốt|chốt phiên|đóng phiên|xong phiên|wrap up)$`.
  - Cấm substring matching để tránh lọt "not done", "chưa chốt".
  - Kiểm tra tính toàn vẹn: `diff_hash_current == diff_hash_at_hold` (chứng minh không ai lén sửa code sau lưng User).
  - Sau khi xác thực hợp lệ mới kích hoạt `closeout_gate.py` cho Reviewer chấm điểm >= 85 để chính thức đóng phiên.
