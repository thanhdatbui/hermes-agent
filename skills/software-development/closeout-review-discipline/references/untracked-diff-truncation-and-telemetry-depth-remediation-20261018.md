# Untracked Diff Truncation & Telemetry Depth Remediation in Closeout Gate (2026-10-18)

## 1. Hiện tượng & Vấn đề Phát sinh
- **Bối cảnh:** Khi thực hiện Closeout Gate (`closeout_gate.py`) cho các file mới tạo hoặc sửa đổi nhưng chưa được commit (`--files guard_media_vision_gate.py tests/test_guard_media_vision_gate.py`).
- **Điểm số Reviewer Sol:** Bị chấm **74/100 (REJECTED)**.
- **Hai nguyên nhân chính khiến Reviewer trừ điểm gắt:**
  1. *Truncation Manifest Trap:* Do file mới hoàn toàn chưa được theo dõi trong git, công cụ extract diff bốc toàn bộ nội dung file (~25KB). Khối lượng này vượt quá ngưỡng context an toàn, kích hoạt `TRUNCATION_MANIFEST`. Reviewer ghi chú rõ: *"Các đoạn bị lược không được coi là đã review; do đó chưa đủ căn cứ để xác nhận toàn bộ luồng..."*.
  2. *Thiếu Telemetry Quan sát Vận hành (Telemetry & Observability: 7/15đ):* Code security gate chỉ trả về boolean `(passed, message)` mà không có log có cấu trúc (logger, severity levels, extra payload chứa verdict, reason, timestamp) và không có unit test kiểm thử hành vi ghi log qua `caplog`.

## 2. Quy tắc Khắc phục Chuẩn (Remediation Protocol)
1. **Bổ sung Telemetry có cấu trúc:**
   - Trong các hàm quyết định an toàn (như `transform_llm_output_check`), bắt buộc dùng `logger = logging.getLogger(...)`.
   - Khi BLOCKED: Ghi log `logger.warning(...)` kèm `extra={"verdict": ..., "reason": ...}`.
   - Khi PASSED: Ghi log `logger.info(...)` kèm metadata kiểm chứng.
2. **Kiểm thử Telemetry Hành vi (Behavioral Telemetry Test):**
   - Không chỉ assert kết quả trả về `passed is False`, mà bắt buộc dùng fixture `caplog` để assert thông điệp log đã được kích hoạt:
     ```python
     def test_transform_llm_output_check_telemetry(caplog):
         with caplog.at_level(logging.INFO):
             passed, _ = transform_llm_output_check("Báo cáo: đã đổi tên")
             assert not passed
             assert any("transform_llm_output_check_blocked" in r.message for r in caplog.records)
     ```
3. **Phân rã Scope để tránh Truncation:**
   - Với file monolith hoặc file mới, chỉ định danh sách file mục tiêu hẹp (`--files <impl> <test>`).
   - Nếu diff vẫn vượt 30KB (`DIFF_TOO_LARGE`), bắt buộc cam kết một phần (partial commit/stage) trước khi chạy review, giúp git diff chỉ thể hiện delta thay đổi thực sự thay vì toàn bộ mã nguồn.
