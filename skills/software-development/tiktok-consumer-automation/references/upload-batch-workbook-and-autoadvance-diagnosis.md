# Chẩn đoán Lỗi Đăng Video Diện Rộng: [READ_WORKBOOK_ERROR] & Lệch Auto-Advance (Case 177)

## Bối cảnh Sự cố (Incident Analysis)
Khi chạy ca nuôi acc kết hợp upload video (ví dụ Ca 3 - Row 5), watchdog báo cáo có thể xuất hiện hàng loạt máy báo:
`[READ_WORKBOOK_ERROR] Missing required fields: ID TikTok` hoặc `post_verification_failed`.

---

## 1. Cơ chế lỗi [READ_WORKBOOK_ERROR] Missing required fields
- **Root Cause**: Trong `scripts/tiktok_workflow/account_source.py`, hàm `validate_row(row)` kiểm tra 4 trường bắt buộc:
  ```python
  required = ["device ID", "ID TikTok", "Folder Video", "Hashtag Pool"]
  ```
- **Kịch bản tranh chấp ghi/đọc hoặc Sync OneDrive**:
  Khi cron đồng bộ (`sync_tik_workbooks.py` hoặc OneDrive sync) đang ghi lại file `TikN.xlsx` hoặc file vừa được lưu trong tích tắc mà cột `ID` bị rỗng tạm thời:
  - Tất cả các tiến trình upload con (`run_post.py`) spawn đồng loạt trong cùng 1-2 phút sẽ đọc trúng lúc cell ID TikTok bị `None`/rỗng.
  - Vòng lặp retry 5 lần (backoff 0.5s -> 2.0s) trong `AccountSource.read_row()` nếu file trên đĩa vẫn chưa hoàn tất ghi xong dữ liệu cột ID thì cả 5 lần đều fail với `Missing required fields: ID TikTok`.
  - Kết quả: 15-20 máy cùng ca đều văng lỗi `[READ_WORKBOOK_ERROR]` mặc dù khi vào inspect thủ công sau đó thì file Excel đã đầy đủ 100%.

- **Cách chẩn đoán O(1)**:
  - Kiểm tra `report.json` và `execution.log` trong `D:\CodexRuntime\tiktok-video\runs\run_<serial>_<timestamp>\`.
  - Nếu tất cả các máy fail cùng một `timestamp` (trong vòng vài giây đến 1 phút) và cùng lỗi `Missing required fields: ID TikTok`, hãy kiểm tra mtime của file `TikN.xlsx` xem có vừa bị ghi đè/sync vào đúng thời điểm đó hay không.
  - Chạy probe nhanh 1 dòng kiểm tra xem hiện tại `read_row()` của `AccountSource` đã đọc bình thường chưa:
    ```python
    asrc = AccountSource(r"D:\OneDrive\TaadaaData\kibe\Tik5.xlsx", device_id="<serial>", dry_run=True)
    row = asrc.read_row()
    ```

---

## 2. Cơ chế lỗi Lệch Số Đếm Video (Auto-Advance Veto)
- **Root Cause**:
  Trong `python_runner/flows/multi_machine_feed_session.py` (hàm `_run_upload_hook`):
  - Runner gọi lệnh upload với `--video-number 1` (do lấy từ cột Video Đã Đăng = 0 trong Excel safe/ledger).
  - Tuy nhiên, trong runtime của `run_post.py`, state machine phát hiện video 1 đã được đăng trước đó (qua fingerprint SHA-256 hoặc profile grid), script kích hoạt cơ chế `[AUTO-ADVANCE]`:
    ```text
    [AUTO-ADVANCE] Skipped 1 verified video(s); new_video_number=2 (was 1)
    ```
    và thực tế đã đăng thành công video số 2 lên TikTok (`post_verified = True`, `status = SUCCESS`).
  - Khi tiến trình con kết thúc, `_run_upload_hook` kiểm tra:
    ```python
    is_video_num_valid = (
        actual_video_num == int(next_video)
        or auto_advance_matched
    )
    ```
  - Nếu regex parse stdout không bắt được chuỗi `[AUTO-ADVANCE]` (ví dụ stdout bị cắt ngắn hoặc format chuỗi log thay đổi nhẹ), hook sẽ VETO kết quả thành công và gán:
    ```python
    final_reason = "post_verification_failed"
    ```
  - Dù thực tế video đã được đăng thành công lên TikTok và workbook `TikN.xlsx` đã cập nhật Video Đã Đăng = 2!

- **Cách chẩn đoán O(1)**:
  - Đọc trực tiếp `report.json` của run:
    Nếu `status == "SUCCESS"` và `post_verified == true` và `video_number > 1`, nhưng `upload_result.json` ghi `post_verification_failed` -> Đây chính là hiện tượng Veto lệch số đếm Auto-Advance, không phải lỗi thiết bị hay lỗi TikTok.
