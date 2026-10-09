# Chẩn đoán lỗi 'active manifest has no valid cohort' (All máy Pause / Runner Silent)

## Hiện tượng
- Toàn bộ máy điện thoại đứng yên / paused ở màn hình cá nhân TikTok hoặc home screen, không có phiên feed nào được khởi chạy.
- Cron `phase9-runner-tiktok-feed` (job `cdd43b124363`) kích hoạt định kỳ (mỗi 15 phút) nhưng log ghi nhận:
  `Status: silent (empty output)` (file output chỉ ~166 bytes).
- Khi chạy trực tiếp wrapper kiểm tra:
  ```bash
  python C:/Users/Kibe/AppData/Local/hermes/scripts/tiktok_runner.py
  ```
  Wrapper trả về mã thoát 0 nhưng bắn ra stderr:
  ```text
  tiktok_runner: active manifest has no valid cohort
  ```

## Cơ chế phát sinh
1. **Runner fail-closed khi `build_cohort_plan` văng lỗi**:
   - Trong `tiktok_runner.py`:
     ```python
     try:
         plan = build_cohort_plan(manifest, as_of=now.isoformat())
     except (ImportError, TypeError, ValueError, KeyError):
         sys.stderr.write("tiktok_runner: active manifest has no valid cohort\n")
         return 0
     ```
   - Khi `build_cohort_plan()` ném ngoại lệ (`ValueError`), runner lập tức fail-closed trả về 0 và không spawn bất kỳ worker/launcher nào.
   - Vì Hermes cron ở chế độ `no_agent: true` coi empty stdout là silent watchdog, user không nhận được alert nào từ cron nhưng thực tế toàn bộ dàn máy bị đình trệ.

2. **Root Cause: Giới hạn cứng số Block (Ca nuôi)**:
   - Trong `python_runner/hermes_cron/cohort.py`, hàm `_session_key()` kiểm tra:
     ```python
     if block not in (1, 2, 3) or session not in (1, 2, 3):
         raise ValueError("cohort entry session is invalid")
     ```
   - Thiết kế thực tế của Taadaa Farm gồm **4 Ca / ngày** (06:00, 12:00, 18:00, 00:00). Vào ngày chẵn (Row 2, 4, 6, 8) hoặc ngày lẻ (Row 1, 3, 5, 7), Ca 4 ứng với `block_index = 4`.
   - Khi manifest chứa các entry thuộc Block 4, toàn bộ quá trình parse `build_cohort_plan` bị vỡ với `ValueError("cohort entry session is invalid")`, làm tê liệt việc dispatch máy của tất cả các ca trong ngày.

## Quy trình kiểm tra nhanh
1. Kiểm tra stderr của runner:
   ```bash
   python ~/AppData/Local/hermes/scripts/tiktok_runner.py
   ```
2. Kiểm tra các block trong active manifest:
   ```bash
   grep -o '"block_index":[0-9]*' D:/Taadaa/runtime/kibe/cron-state/manifests/<YYYY-MM-DD>/ACTIVE.json | sort -u
   ```
   Nếu xuất hiện `block_index: 4`, đối chiếu với điều kiện validation trong `cohort.py`.

## Khắc phục
- Cập nhật điều kiện validation trong `python_runner/hermes_cron/cohort.py` để hỗ trợ đủ 4 block:
  ```python
  if block not in (1, 2, 3, 4) or session not in (1, 2, 3):
  ```
- Kiểm tra các hàm liên quan trong `cohort.py` và `cohort_watchdog.py` xem còn chỗ nào giả định tối đa 3 block không.
- Chạy kiểm thử:
  ```bash
  pytest python_runner/tests/test_hermes_cron_cohort*.py
  ```
- Chạy lại wrapper để xác nhận cohort đã được nhận diện hợp lệ và máy được dispatch theo đúng lịch.
