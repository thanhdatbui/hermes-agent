# Sol Reviewer Gate Payload Truncation, L0 Ceilings & Remediation Protocol (2026-10-16)

## 1. Bản chất cơ chế Payload Truncation của Sol Reviewer
- Trong `closeout_gate.py` phối hợp với `sol_payload_guard.py`:
  - Payload gửi tới Sol Reviewer (:20129) được tính toán qua `fit_and_enforce` với ngân sách mục tiêu `SOL_TARGET_BYTES` (32,768 bytes) hoặc `CALCULATED_MAX_ALLOWED` (37,952 bytes).
  - Ngân sách diff (`diff_b`) chiếm 65% của payload (`~21,299` đến `24,668` bytes).
  - Nếu tổng dung lượng diff của các files được audit vượt quá `diff_b`, guard sẽ tự động kích hoạt `digest_diff` ở cấp độ `L4` và lược bớt các hunk/file bằng `_render_file`, đánh dấu `(partial)` hoặc `TRUNCATION_MANIFEST`.
  - **Hậu quả trực tiếp trên Score:** Khi Sol Reviewer phát hiện `TRUNCATION_MANIFEST` hoặc `(partial)`, các tiêu chí `logic_correctness` và `farm_safety_regression` sẽ bị trừ điểm nặng nề (thường bị kẹp ở mức 76-82/100, không bao giờ đạt ngưỡng >= 85), bởi vì Reviewer từ chối xác nhận an toàn cho code bị che khuất.

## 2. Công thức duy trì Diff ở Trạng thái L0 (Zero Truncation)
- **Quy tắc trần kích thước Diff:**
  - Tổng dung lượng raw git diff (`git diff --no-ext-diff HEAD -- <files>`) BẮT BUỘC phải nằm dưới **21.0 KB** (`~21,000 bytes`).
  - Khi có file code chính và file test:
    * File code chính: Giữ gọn gàng, súc tích (<= 12 KB raw diff).
    * File test suite: Tuyệt đối không viết lan man redundant test cases. Tinh gọn, gộp context managers và assert súc tích (giữ file test raw diff <= 8.5 KB).
  - Khi raw diff <= 21.0 KB, `digest_diff` trả về `level=L0` với `omitted=[]`, đảm bảo Sol Reviewer nhìn thấy 100% từng dòng code và nâng điểm lên vùng phê duyệt.

## 3. Các yêu cầu thiết kế sống còn cho Watchdog Farm Daemon
1. **PEP 257 & Shebang Order:**
   - Dòng 1: Shebang tuyệt đối `#!/usr/bin/env python3`.
   - Dòng 2+: Module Docstring (`"""..."""`).
   - Sau Docstring: `from __future__ import annotations` (nếu dùng union syntax `bool | None` cho Python <3.10) và các import khác.
   - *Vi phạm:* Đặt `from __future__` trước shebang làm vô hiệu hóa shebang; đặt trước docstring làm hỏng module docstring.
2. **Single Responsibility cho Synchronization Locks:**
   - Tuyệt đối không dùng chung 1 Lock cho cả Metrics và Cache (`lock abuse`).
   - Tách riêng:
     * `_METRICS_LOCK = threading.Lock()` cho `WATCHDOG_METRICS`.
     * `_CACHE_LOCK = threading.Lock()` cho `_XIAOWEI_RUNNING_CACHE`.
3. **Fail-Closed Semantics & TOCTOU Prevention:**
   - Khi kiểm tra trạng thái tiến trình gặp lỗi (subprocess exit != 0 hoặc exception): BẮT BUỘC fail-closed trả về `True` (coi như tiến trình đang chạy để không bao giờ kill nhầm).
   - Trước mỗi bước can thiệp phá hủy (Kill-server, CIM terminate): BẮT BUỘC kiểm tra hàm guard `_xiaowei_started_before` và chặn đứng ngay lập tức nếu tiến trình vừa khởi động lại.
4. **Emergency Kill-Switch (Dry-Run Mode):**
   - Hỗ trợ biến môi trường `WATCHDOG_DRY_RUN` (`1`, `true`, `yes`).
   - Khi bật: phát `log_event("DRY_RUN_ENABLED", level="WARNING")` và thoát ngay ở đầu `main()`, cho phép dừng can thiệp khẩn cấp trên farm mà không cần sửa code.
5. **Zombie Process Detection:**
   - Khi lệnh kill (như `taskkill`) trả về mã 0 nhưng kiểm tra lại tiến trình vẫn còn chạy (zombie state), phải ghi nhận `log_event("XIAOWEI_ZOMBIE_DETECTED", level="WARNING")` trước khi chuyển sang tầng fallback mạnh hơn (CIM / WMI Terminate).
