# Lessons Learned & Quirks: Closeout Gate Sol High Payload Truncation & Remediation

## 1. Cơ chế Truncation & Ngân sách Payload (sol_payload_guard)
- `SOL_TARGET_BYTES = 32768` (32 KB payload tổng gửi tới OmniRoute :20129).
- Phân bổ ngân sách theo `split_budget`:
  * **Diff budget**: 65% (~21,299 bytes).
  * **Log budget**: 25% (~8,192 bytes).
  * **Wrapper / Manifest reserve**: 10%.
- Khi tổng kích thước diff của các target files vượt quá ~21KB, `sol_payload_guard` kích hoạt `_render_file` cắt xén theo từng hunk (`L4`, `omitted: [file(partial)]`).
- **Hệ quả với Sol Reviewer:** Bất kỳ file production code nào bị đánh dấu `(partial)` trong `[TRUNCATION_MANIFEST]` sẽ lập tức bị trừ điểm nặng ở tiêu chí `logic_correctness` và `farm_safety_regression` (thường trần điểm bị khóa ở mức 76-78/100, không thể đạt ngưỡng 85 để APPROVED).

## 2. Kỹ thuật đưa Diff về `level=L0` (0 Truncation)
- Không cố gắng viết test suite đồ sộ hàng trăm dòng lặp đi lặp lại các kịch bản tương tự.
- **Loại bỏ test thừa (Redundancy Pruning):**
  * Không mock lại những gì đã được bao phủ bởi real integration test (ví dụ: mock `GetLastInputInfo` khi đã có test thật trên Windows).
  * Gom các patch context lồng nhau vào một context manager duy nhất hoặc parametrize gọn gàng.
  * Giữ tổng dung lượng diff của toàn bộ package (code + test) dưới **20.5 KB** để `sol_payload_guard` giữ nguyên mức `level=L0`, `omitted=[]`.

## 3. Các yêu cầu bất biến từ Sol Reviewer cho Watchdog / Farm Automation
- **Fail-Closed Tri-State Pattern:** Khi hàm kiểm tra tiến trình (`tasklist` / `powershell`) gặp exception hoặc `returncode != 0`, phải phân biệt giữa "chắc chắn tắt" (`False`), "đang chạy" (`True`), và "không thể xác định" (`None`). Mặc định luôn an toàn (không bao giờ kill khi trạng thái là `None`).
- **Atomic Pre/Post-Condition Binding:**
  * Cleanup chỉ kích hoạt khi ứng dụng chính chắc chắn đã tắt.
  * Cleanup chỉ báo thành công khi đã verify tiến trình mục tiêu thực sự biến mất (không dựa vào return code đơn thuần).
  * Đính kèm trạng thái `adb_cleaned` trực tiếp vào telemetry của action chính (`XIAOWEI_CLOSE_OK` / `XIAOWEI_CLOSE_FAILED`).
- **Telemetry Observability:**
  * Bắt buộc có structured JSON (`ts`, `level`, `event`).
  * Bổ sung `correlation_id` / `run_id` tự sinh để log harvester liên kết các sự kiện trong cùng một chu kỳ chạy.
  * Bổ sung sự kiện tổng hợp (`WATCHDOG_SUMMARY`) chứa snapshot metrics khi kết thúc.
- **Safety Clamping & Regression Guard:**
  * Mọi tham số timeout đọc từ biến môi trường phải có range clamping an toàn (ví dụ: `max(5, min(60, timeout))`).
  * Test suite phải có assertion bảo vệ các hằng số vận hành then chốt (ví dụ: `IDLE_THRESHOLD_SECONDS == 1200`) chống sửa đổi ngoài ý muốn.
