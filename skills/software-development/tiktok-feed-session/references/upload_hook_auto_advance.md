# Upload Hook: Video Number Validation & Auto-Advance Gate

## Bối cảnh & Vấn đề
Trong `multi_machine_feed_session.py` (flow `_run_upload_hook`), kết quả report từ video upload runner được đọc để xác thực việc đăng video có thành công hay không.
Nếu chỉ kiểm tra điều kiện `actual_video_num >= int(next_video)`, runner sẽ chấp nhận các video number không khớp (ví dụ `actual_video_num = 999` trong khi mong đợi `next_video = 3`), dẫn đến vượt qua sai lầm khi không có auto-advance thực sự.

## Quy tắc bắt buộc
1. **Validation Logic:**
   ```python
   actual_video_num = int(rep_video_num) if rep_video_num is not None else None
   has_auto_advance = "[auto-advance]" in stdout_lower or "auto-advance" in stdout_lower
   is_video_num_valid = (
       actual_video_num is not None
       and (
           actual_video_num == int(next_video)
           or (has_auto_advance and actual_video_num > int(next_video))
       )
   )
   ```
2. **Veto Gate:**
   - Nếu `is_video_num_valid` là False, runner BẮT BUỘC phải veto (`report_veto_failed = True` và không set `verified_from_report = True`).
   - Mismatch số video khi không có auto-advance marker trong stdout phải trả về `status: failed` với reason `post_verification_failed`.

3. **Kiểm thử liên quan (`python_runner/tests/test_upload_hook.py`):**
   - Test mismatch: `test_upload_hook_fails_when_video_number_mismatch_in_report`
   - Test auto-advance: `test_upload_hook_succeeds_when_auto_advance_in_report`
