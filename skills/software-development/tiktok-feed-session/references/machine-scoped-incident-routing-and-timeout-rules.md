# Machine-Scoped Incident Routing & Test Timeout Rules (TikTok Feed Session)

## 1. Machine-Scoped Incident Investigation
- Khi nhận screenshot có banner đỏ `[MAY <N>]` hoặc alert chỉ định Máy N:
  - Tra serial từ `D:\Taadaa\machine-config\kibe.yaml`.
  - Đọc log/artifact trực tiếp tại `D:\Taadaa\runtime\kibe\live\<ngày>\*\machines\machine_<N>\` hoặc `alert_machine_<N>.png`.
  - Cấm chạy `grep -rn` / `find` đệ quy trên `.ai-runs/` hoặc `runtime/`.

## 2. Test Execution Policy
- Chạy focused test theo file sửa: `pytest python_runner/tests/test_<module>.py -k "<test_name>" -v`.
- Cấm chạy `pytest python_runner/tests/` (1800+ test) trong các chu kỳ fix lỗi hoặc chốt phiên.
- Bắt buộc đặt timeout terminal 30-60s.
