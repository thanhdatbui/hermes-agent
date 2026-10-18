# Zero-Conflict Gate Common & Fail-Closed Token Architecture (2026-10-18)

## 1. Bối Cảnh & Vấn Đề
- Khi khôi phục cơ chế Grace Band 80–84 để chống việc Sol Auditor bắt bẻ vụn vặt, nguy cơ nảy sinh xung đột giữa các thành phần kiểm soát:
  - `closeout_gate.py` cho pass Grace, nhưng `safe_push.py` hoặc `pre-push.sh` lại kiểm tra cứng `threshold >= 85` bằng regex riêng $\rightarrow$ gây nghẽn push.
  - Phán quyết generic `APPROVED` khiến Coordinator ngộ nhận là Strict Pass và báo DONE toàn diện mà không kiểm tra diff budget.
  - Hàm `verify()` tự động tạo key mới khi key bị mất hoặc lệch thư mục $\rightarrow$ che giấu lỗi cấu hình và tạo cửa sổ fail-open.

## 2. Kiến Trúc "Đơn Nguồn Chân Lý" (Single Source of Truth)
- **Cấu hình duy nhất:** `closeout_policy.json` định nghĩa:
  - `strict_threshold: 85`
  - `grace_threshold: 80`
  - `budget: {"max_files": 2, "max_lines": 80}` (hoặc O(1) 30 dòng cho task nhỏ)
- **Bộ phân xử duy nhất:** `gate_common.py`:
  - Mọi script downstream (`safe_push.py`, `pre-push.sh`, `guard_closeout_discipline.py`) CẤM so sánh điểm số hay regex `85`/`80` độc lập.
  - Bắt buộc kiểm tra qua CLI hoặc API chuẩn: `gate_common.verify(change_id, head=head)`. Mã thoát chuẩn: `0` (VERIFIED), `10` (DENIED), `20` (INTEGRITY_ERROR).

## 3. Ba Trạng Thái Phán Quyết Bất Biến
1. **`PASS` (`tier: "strict"`):** Score $\ge 85$ $\rightarrow$ Cấp strict HMAC token, Coordinator được báo `DONE`.
2. **`CONDITIONAL_PASS` (`tier: "grace"`):** $80 \le \text{Score} < 85$ $\rightarrow$ BẮT BUỘC kiểm tra 5 điều kiện cơ học cứng:
   - Focused test **100% PASS**.
   - `diff_files <= budget["max_files"]` và `diff_lines <= budget["max_lines"]`.
   - Bằng chứng `grace_evidence` tồn tại và hợp lệ (`tests_passed is True`). Nếu `grace_evidence is None` $\rightarrow$ trả về `FAIL` (`grace_conditions_unmet`), tuyệt đối cấm fail-open.
   - Cấp grace HMAC token, Coordinator chỉ được báo `DONE_WITH_GRACE`.
3. **`FAIL`:** Score $< 80$ hoặc 80–84 nhưng trượt điều kiện Grace $\rightarrow$ Từ chối cấp token, bắt buộc tiếp tục vòng lặp remediation.

## 4. Kỷ Luật Bảo Mật Khóa & Token HMAC-SHA256
- **Khởi tạo khóa bất đối xứng (Asymmetric Key Discipline):**
  - Chỉ hàm `issue()` mới được phép gọi `_key(gate_dir, create=True)` kèm ghi nguyên tử qua file tạm (`os.replace`).
  - Hàm `verify()` BẮT BUỘC gọi `_key(gate_dir, create=False)`. Nếu file key thiếu, raise `FileNotFoundError` hoặc trả về `(False, "key_missing")`. CẤM TUYỆT ĐỐI tự tạo key trong luồng verify!
- **Kiểm soát Schema & Input Encoding:**
  - Token và signature bắt buộc là chuỗi thuần ASCII (`body.isascii() and sig.isascii()`).
  - So sánh chữ ký HMAC bằng `hmac.compare_digest` chống timing attacks.
  - Bắt buộc kiểm tra miền dữ liệu payload: `_is_int(score)`, `0 <= score <= 100`, `_is_int(iat)`, `_is_int(exp)`, `iat <= exp`. Token có điểm âm hoặc điểm > 100 bị từ chối `malformed_payload` ngay lập tức.
