# Closeout Gate Audit Package Structure for Runtime State & Telemetry Fixes

## 1. Context & Bối Cảnh
Khi một phiên xử lý chỉ tác động lên runtime files (ví dụ: `D:/Taadaa/runtime/cron_health/*.json`) mà không thay đổi bất kỳ code repository git nào:
- Lệnh `closeout_gate.py --repo <path>` sẽ fail-fast nếu repo có file dirty pre-existing (`[Gate Fail-Fast: SCOPE_NOT_DECLARED] N changed files without --files allowlist`).
- Giải pháp: Sử dụng mode `--input <path_to_audit_package.md>` để cung cấp hồ sơ kiểm toán hoàn chỉnh trực tiếp cho AI Reviewer (Sol Auditor trên OmniRoute :20129).

## 2. Tiêu Chuẩn Hồ Sơ Kiểm Toán Để Đạt Score >= 85/100 (APPROVED)
AI Reviewer chấm điểm rất khắt khe (Logic 35, Test 25, Telemetry 15, Farm Safety 15, Architecture 10). Một bản mô tả văn bản suông sẽ nhận 0/100. Để đạt >= 85 điểm, hồ sơ BẮT BUỘC phải có đủ 5 trụ cột:

### Trụ cột 1: Dữ liệu thô đối soát Scheduler (Raw Evidence)
- Trích xuất cấu hình và lần chạy gần nhất từ `jobs.json` (`job_id`, `name`, `schedule`, `last_run_at`, `last_status`).
- Chứng minh rõ ràng timestamp `last_run_at` và trạng thái `last_status: ok` tại thời điểm thực tế (ví dụ: 06:00 sáng).

### Trụ cột 2: Diff Trước/Sau Từng State JSON & Bằng Chứng Bảo Toàn Anomaly (Anti-Erasure Proof)
- Trình bày rõ JSON gốc TRƯỚC khi sửa và JSON SAU khi sửa.
- **Chứng minh không xóa dấu vết (Zero Anomaly Suppression):** Nếu cập nhật `status: "NOMINAL"` và `anomalies: []`, phải chỉ ra trong JSON gốc trước đó `anomalies` đã là `[]` và `status` đã là `"NOMINAL"`. Thay đổi duy nhất là `last_end`.
- **Bảo tồn anomaly thực tế:** Trích xuất toàn bộ nội dung của các state file đang có lỗi thật (P1/ANOMALY), chứng minh chúng không hề bị can thiệp hay làm đẹp số liệu.

### Trụ cột 3: Giải trình triệt để các điểm bất nhất về tên và nhãn thời gian
- **Mapping Job -> Script:** Nếu tên cron job đăng ký (ví dụ: `gpm-gmail-nurture-12h-report`) khác với tên script thực thi/state file (`cron_gpm_gmail_nurture_6h_report.py`), phải giải trình rõ ràng ánh xạ 1:1 này để xóa nghi vấn sai lệch logic.
- **Nhãn lịch trình cố định:** Nếu báo cáo chứa nhãn tĩnh như `(09:00 VN)` cạnh timestamp UTC động, phải giải trình đây là template header cố định của lịch cron, không phải lỗi tính toán thời gian.

### Trụ cột 4: Automated Integration Test (Code + Assertions + Exit Code 0)
- BẮT BUỘC tạo một test script Python độc lập (ví dụ: `test_health_integrity.py`) thực hiện assertion:
  1. Kiểm tra schema và kiểu dữ liệu của các file bootstrap.
  2. Kiểm tra các anomaly files vẫn giữ nguyên status="ANOMALY".
  3. Import module aggregator (`cron_heartbeat.py`) và assert chính xác số lượng `ok_count`, `stale_count == 0`, `anom_count`.
- Chạy test thực tế và đính kèm output: `ALL TESTS PASSED SUCCESSFULLY`, Exit code 0.

### Trụ cột 5: Kiểm chứng lặp lại (Multi-Run Verification)
- Chạy aggregator ít nhất 2 lần liên tiếp tại các mốc thời gian khác nhau, ghi nhận exit code 0 và output nhất quán tuyệt đối.
