# Target-Bound Canary & Mechanical OCR Whitelist (Tri-Party Agreement 2026-10-18)

## 1. Sự Cố Hiện Trường & Lỗ Hổng Nghiêm Trọng
- **Hiện tượng**: Khi sửa lỗi Account Switcher (không mở được bottom sheet đổi tài khoản do chọn nhầm anchor username), Coordinator chạy Canary nghiệm thu bằng cách mở `feed-session-smoke` lướt 3 video rồi tap vào Profile để lấy cờ PASS!
- **Hậu quả**: Canary chạy lệch hoàn toàn so với phạm vi sửa đổi (sửa switcher nhưng lại đi test vuốt feed). Nhánh logic bị sửa đổi thực tế không hề được kích hoạt hay kiểm chứng trên máy thật, tạo ra cờ pass ảo/hình thức ("chạy cho có lệ").
- **User chấn chỉnh**:
  - *"Test là test account switcher. Chứ mắc gì đi test vuốt. H sửa rule canary k. Chứ cứ canary máy móc mở feed lướt k đúng thiết kế là phải canary đúng lỗi cần fix. Thiết kế gate guard ấy? Gọi 3 bên vào thống nhất thiết kế đi"*
  - *"Done_gate.py là clgt? Làm đi đừng có dừng lại hỏi"*

## 2. Kết Quả Hội Chẩn 3 Bên (Sol High Auditor + Claude Planner + Coordinator)

### A. Sol High Auditor (:20129) — CONDITIONAL APPROVE
1. **Target-bound Canary**: Phải suy ra module/hàm bị sửa từ git diff để bắt buộc chạy Canary đúng hook/module đó. Nếu diff không map được vào rule nào hoặc thiếu hook bắt buộc ➔ **FAIL-CLOSED (BLOCK)**, tuyệt đối cấm tự động fallback về feed swipe để lấy cờ pass đối phó.
2. **Mechanical OCR Whitelist**: WinRT OCR phải kiểm tra tổ hợp: **Từ khóa bắt buộc của màn hình đích + Từ khóa cấm (launcher/home) + Độ dài tối thiểu (min chars)**. OCR rỗng hoặc không tin cậy ➔ FAIL ngay. CẤM dùng ảnh feed/launcher làm bằng chứng pass cho các module khác.
3. **Fast O(1) Hook $\le$ 20s**: Hook chạy tập trung vào đúng hành vi cần test; hard deadline $\le$ 20s, timeout = FAIL ngay, không retry mù biến FAIL thành PASS.

### B. Claude Planner — Bản Thiết Kế Kiến Trúc 3 Tầng
1. **Cấu hình Declarative `tools/canary_matrix.json`**:
   - Khai báo theo từng repo với các chế độ: `off`, `shadow`, `enforce`.
   - Mỗi rule định nghĩa: `id`, `path_globs`, `hunk_regex`, `hook`, `scope` (`single` vs `wide`), và `ocr` (`required_all`, `forbidden_extra`, `min_chars`).
2. **Hợp đồng Luồng Dữ liệu (Pipeline Contract)**:
   ```
   Git Diff ──▶ canary_plan.py ──▶ canary_runner.py ──▶ validate_evidence_screen.py ──▶ done_gate.py
                  (plan.json)      (hook execution       (validate_ocr_spec)             (plan-check &
                                    & hook-echo)                                          diff-sha match)
   ```
3. **Chốt chặn độc lập tại `canary_runner.py` & `done_gate.py`**:
   - `canary_runner.check_canary_status()` là **Single Source of Truth** xác thực cờ canary (TTL 2h, media file $\ge 40KB$, sha256 match, plan alignment).
   - `done_gate.py` là wrapper mỏng gọi trực tiếp `canary_runner.check_canary_status()`, loại bỏ hoàn toàn cơ chế kiểm tra file rỗng/stale cũ.
   - Hỗ trợ CLI kiểm tra nhanh: `python canary_runner.py --check`.

## 3. Quy Tắc Bắt Buộc Đối Với Coordinator
1. **Sửa gì Canary nấy (Target Binding)**: Khi vá code của bất kỳ module nào (Account Switcher, 2FA, Upload, Follow, Avatar), BẮT BUỘC Canary đúng hook của module đó.
2. **Bằng chứng thị giác đích thực**: Ảnh nộp cho Canary bắt buộc phải là màn hình kết quả của chính hook đó (ví dụ Account Switcher phải hiển thị Bottom Sheet danh sách tài khoản), cấm nộp ảnh Feed hay Home Screen.
3. **Kỷ luật thực thi dứt điểm ("Làm đi đừng có dừng lại hỏi")**: Khi lệnh của Operator đã rõ ràng và có căn cứ kỹ thuật, Coordinator phải chủ động triển khai, tự chạy test nghiệm thu và chỉ báo cáo kết quả cuối cùng kèm bằng chứng, cấm dừng lại hỏi xin phép kiểu thủ tục.

## 4. Hiện Trạng Triển Khai (Đã Hoàn Thành 18/10/2026)
- Đã tạo: `tools/canary_matrix.json`, `tools/canary_plan.py`, hàm `validate_ocr_spec()` trong `tools/validate_evidence_screen.py`.
- Đã nâng cấp: `tools/canary_runner.py` hỗ trợ `--plan`, `--check`, Receipt v2 (`diff_sha256`, `plan_sha256`).
- Đã đồng bộ: `tools/done_gate.py` ủy quyền trực tiếp cho `canary_runner.check_canary_status()`.
- Test suite: 21/21 test passed (`test_canary_runner.py`, `test_canary_plan.py`, `test_done_gate.py`).
