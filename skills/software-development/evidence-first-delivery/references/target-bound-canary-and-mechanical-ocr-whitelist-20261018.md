# Target-Bound Canary & Mechanical OCR Whitelist (Tri-Party Agreement 2026-10-18)

## 1. Sự Cố Hiện Trường & Lỗ Hổng Nghiêm Trọng
- **Hiện tượng**: Khi sửa lỗi Account Switcher (không mở được bottom sheet đổi tài khoản do chọn nhầm anchor username), Coordinator chạy Canary nghiệm thu bằng cách mở `feed-session-smoke` lướt 3 video rồi tap vào Profile để lấy cờ PASS!
- **Hậu quả**: Canary chạy lệch hoàn toàn so với phạm vi sửa đổi (sửa switcher nhưng lại đi test vuốt feed). Nhánh logic bị sửa đổi thực tế không hề được kích hoạt hay kiểm chứng trên máy thật, tạo ra cờ pass ảo/hình thức ("chạy cho có lệ").
- **User chấn chỉnh**: *"Test là test account switcher. Chứ mắc gì đi test vuốt. H sửa rule canary k. Chứ cứ canary máy móc mở feed lướt k đúng thiết kế là phải canary đúng lỗi cần fix. Thiết kế gate guard ấy? Gọi 3 bên vào thống nhất thiết kế đi"*.

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
3. **Chốt chặn độc lập tại `done_gate.py`**:
   - `done_gate.py` tự tính lại `diff_sha256` trên working tree (loại trừ file exempt), tự sinh `plan_now`.
   - Bắt buộc receipt phải khớp `diff_sha256`, `matrix_sha256`, mọi requirement phải PASS, hook phải được echo từ runner.
   - Chạy lại WinRT OCR trực tiếp trên ảnh chụp thay vì tin tưởng chuỗi text trong receipt.

## 3. Quy Tắc Bắt Buộc Đối Với Coordinator
1. **Sửa gì Canary nấy (Target Binding)**: Khi vá code của bất kỳ module nào (Account Switcher, 2FA, Upload, Follow, Avatar), BẮT BUỘC Canary đúng hook của module đó.
2. **Bằng chứng thị giác đích thực**: Ảnh nộp cho Canary bắt buộc phải là màn hình kết quả của chính hook đó (ví dụ Account Switcher phải hiển thị Bottom Sheet danh sách tài khoản), cấm nộp ảnh Feed hay Home Screen.
3. **Lộ trình triển khai**:
   - P0: Tạo `canary_matrix.json`, `canary_plan.py`, `validate_ocr_spec()`.
   - P1: `canary_runner.py` nạp `--plan`, `done_gate.py` chạy chế độ `shadow` (cảnh báo `WOULD_FAIL`).
   - P2: Bật `mode: enforce` trên từng repo sau khi đã ổn định.
