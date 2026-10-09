# Vận Hành Auto Rescan Loop & Farm Progress Monitoring (Tiktok-video)

*Cập nhật: 2026-09-19*

## 1. Mục đích & Cơ chế
Script `scripts/auto_rescan_loop.py` tự động phát hiện và quét bù cho các folder chưa đạt chuẩn trong kho 640 folder (`video_count < 30` hoặc `status = 'insufficient_pool'`) từ `state.db`.

## 2. Failure Handling & Circuit Breaker
- **Exponential Backoff**: Khi subprocess `download_by_niche.py` trả về `exit_code != 0`, script áp dụng thời gian chờ giãn cách (backoff) thay vì scan mù liên tục gây nghẽn proxy hoặc spam server.
- **Max Consecutive Failures**: Tham số `--max-consecutive-failures` (mặc định 5). Nếu số lần lỗi liên tiếp chạm ngưỡng:
  - Ghi log `ALERT: Exceeded max consecutive failures (X), aborting rescan loop to protect farm.`
  - Thoát ngay với mã lỗi non-zero (1) để bảo vệ tài nguyên và proxy pool của farm.

## 3. Structured Summary Metric & Status JSON
- Mỗi round đều thu thập tóm tắt tiến độ qua `get_farm_progress_summary(state_db_path)`:
  - `total`: Tổng số folders trong DB.
  - `complete`: Số folders có `video_count >= 30`.
  - `incomplete`: Số folders còn thiếu.
  - `pct`: Tỷ lệ hoàn thành (%).
  - `incomplete_folders`: Danh sách ID các folder còn dang dở.
- **File trạng thái JSON**: Ghi ra `rescan_status.json` (mặc định tại `D:\CodexRuntime\tiktok-video\rescan_status.json`, cấu hình qua `--status-json`):
  ```json
  {
    "timestamp": "YYYY-MM-DD HH:MM:SS",
    "round": 1,
    "complete": 639,
    "total": 640,
    "pct": 99.8,
    "incomplete_folders": [613]
  }
  ```
- **Log chuẩn hóa**:
  `FARM_SWEEP_PROGRESS complete=639/640 (99.8%) remaining=1`

## 4. Lệnh chạy chuẩn & Kiểm thử
- Chạy quét bù tự động:
  ```bash
  python scripts/auto_rescan_loop.py --state-db D:\CodexRuntime\tiktok-video\state.db --interval 15 --max-consecutive-failures 5
  ```
- Chạy unit tests:
  ```bash
  python -m pytest -p no:cacheprovider tests/test_auto_rescan_loop.py
  ```
