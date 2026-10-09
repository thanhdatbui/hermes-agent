# Upload Hook Auto-Advance Gate & Video Number Validation

## Vấn đề & Quy tắc kiểm tra Video Number trong Upload Hook

Khi chạy upload hook trong `multi_machine_feed_session.py`:
1. Runner đọc kết quả từ `report.json` và log `stdout` của tiến trình upload con (`run_tiktok.py` / `upload_hook`).
2. **Nguyên tắc đối chiếu `actual_video_num` với `next_video` (kế hoạch):**
   - Không được dùng điều kiện lỏng lẻo `actual_video_num >= int(next_video)` vô điều kiện, vì nếu upload runner bị bug hoặc nhầm lẫn báo `video_number: 999` (so với `next_video: 3`), hook sẽ pass sai và ghi nhận sai vào shift ledger.
   - Nhận diện định dạng Auto-Advance: Regex hỗ trợ cả 2 định dạng log (có khoảng trắng hoặc dấu gạch dưới):
     ```python
     aa_match = re.search(
         r"\[AUTO-ADVANCE\]\s+Skipped\s+\d+\s+verified\s+video\(s\);\s+new[ _]?video_number=(\d+)\s+\(was\s+(\d+)\)",
         stdout,
     )
     if aa_match:
         aa_new, aa_was = int(aa_match.group(1)), int(aa_match.group(2))
         if aa_new == actual_video_num and aa_was == int(next_video):
             auto_advance_matched = True
     ```
   - Ràng buộc hợp lệ:
     ```python
     actual_video_num = int(rep_video_num) if rep_video_num is not None else None
     is_video_num_valid = (
         actual_video_num is not None
         and (
             actual_video_num == int(next_video)
             or auto_advance_matched
         )
     )
     ```
3. **Quy tắc VETO và Fail-Closed:**
   - Nếu `is_video_num_valid` là False, `report_veto_failed = True` và tiến trình bị đánh dấu thất bại với `reason = "post_verification_failed"`.
   - Chỉ khi nào có marker Auto-Advance hợp lệ (`aa_new == actual_video_num` và `aa_was == next_video`) thì mới cho phép `actual_video_num > next_video` và cập nhật `effective_video_number = actual_video_num` cho ledger.

## Cạm bẫy khi viết Unit Test (`python_runner/tests/test_upload_hook.py`)
- **Nguy cơ Flaky do `_is_organic_rest`:**
  - Trong `_run_upload_hook`, hàm sẽ kiểm tra `child_cfg.get("_is_organic_rest")`. Nếu không được set (hoặc là `None`), hệ thống sẽ gọi `_is_account_organic_rest_day(machine, row)` dựa trên lịch/ngày hiện tại.
  - Nếu ngày chạy test trùng vào chu kỳ organic rest của `(machine, row)`, hook sẽ tự động bỏ qua upload và trả về:
    `status: "skipped"`, `reason: "organic-rest-day-no-upload"`.
  - Kết quả là các test assertion kỳ vọng `res["status"] == "success"` hoặc `"failed"` sẽ vấp phải assertion error: `assert 'skipped' == 'success'`.
  - **BẮT BUỘC:** Trong mọi test fixture/function kiểm thử `_run_upload_hook` cho auto-advance hay video verification, phải set rõ:
    ```python
    child_ctx.config["_is_organic_rest"] = False
    ```

## Regression Test Coverage
- `test_upload_hook_fails_when_video_number_mismatch_in_report`: Mock `video_number: 999` không có chuỗi auto-advance -> BẮT BUỘC trả về `res["status"] == "failed"` và `res["reason"] == "post_verification_failed"`.
- `test_upload_hook_succeeds_when_auto_advance_in_report`: Mock `video_number: 10` với stdout chứa `[AUTO-ADVANCE] Skipped 7 verified video(s); new_video_number=10 (was 3)` (hoặc `new video_number=10 (was 3)`) và report status SUCCESS -> `res["status"] == "success"` và ledger nhận `video_number: 10`.
- `test_upload_hook_fails_when_untrusted_auto_advance_in_stdout`: Mock marker auto advance với số `was` không khớp -> fail với `post_verification_failed`.
