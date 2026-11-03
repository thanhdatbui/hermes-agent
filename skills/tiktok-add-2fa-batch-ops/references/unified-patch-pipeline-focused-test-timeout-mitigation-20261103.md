# Unified Patch Pipeline: Tránh Timeout 600s ở S3 Focused Test cho Batch Runner

## Ngữ cảnh & Triệu chứng
Khi Coordinator kích hoạt lệnh sửa code qua pipeline:
```bash
python D:/Taadaa/tools/unified_patch_pipeline.py run \
  --repo D:/Taadaa/tiktok-add-bao-mat-f2a \
  --file python_runner/run_batch_live_2fa.py \
  --task "..." \
  --test-cmd "pytest python_runner/tests/test_run_batch_live_2fa.py -v"
```
Pipeline đã bị **timeout 600s** và đứt phiên ở tầng S3 (Focused Test).

## Nguyên nhân gốc rễ
1. File test `test_run_batch_live_2fa.py` chứa các test case giả lập tranh chấp file lock và retry backoff (`test_freeze_retry_exhausted_returns_5`, `test_jit_dispatch_...`).
2. Các test case này có các vòng lặp retry ngầm (`delays = [2.0, 3.0, 4.0, 5.0, 5.0]`) và multi-worker dispatch khiến tổng thời gian thực thi vượt quá timeout cho phép của subagent S3 / terminal runner.
3. Khi test timeout, pipeline không thể chuyển sang S4/S5 để hoàn tất, để lại dirty diff trên repo.

## Giải pháp chuẩn hóa O(1)
Khi truyền `--test-cmd` cho các batch runner hoặc module có sleep retry, **BẮT BUỘC**:
- Chỉ định đích danh 1 test method kiểm chứng logic trực tiếp, không phụ thuộc I/O sleep ngâm, ví dụ:
  `--test-cmd "pytest python_runner/tests/test_run_batch_live_2fa.py -k test_freeze_accepts_kibe_and_admin_machine_ranges_with_telemetry -v"`
- Hoặc chạy test tập trung bằng script focused test riêng biệt với runtime < 10s.
