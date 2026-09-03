# Upload Hook Post-Verification Contract & False-Positive Elimination

## 1. Bản chất sự cố False-Positive Upload Video hàng loạt
- **Hiện tượng:** Ở Phiên 3 (phiên cuối ca nuôi acc có hook upload video), cron runner báo cáo toàn bộ 58–59 máy bị `failed` với mã lỗi `post_verification_failed`, dù thực tế trên điện thoại video đã đăng thành công 100% và file `report.json` đã lưu `SUCCESS`.
- **Nguyên nhân gốc rễ (Root Cause):**
  - Subprocess `Tiktok-video` (`scripts/tiktok_workflow/run_post.py`) khi đăng thành công sẽ trả `exit_code: 0`, ghi `D:\CodexRuntime\tiktok-video\runs\<run_id>\report.json` (`status: "SUCCESS"`, `post_verified: true`), và in ra stdout:
    `[INFO] scripts.tiktok_workflow.run_post: Workflow completed successfully`
  - Tuy nhiên, trong `multi_machine_feed_session.py` (`_run_upload_hook`), biến `is_success` yêu cầu cứng:
    ```python
    is_success = (
        proc.returncode == 0
        and verified_from_report
        and (
            "post verification passed" in stdout_lower
            or "upload video success" in stdout_lower
            or "upload completed" in stdout_lower
        )
    )
    ```
  - Cả 3 chuỗi trên đều KHÔNG tồn tại trong codebase của `Tiktok-video` → Điều kiện thứ 3 luôn `False` → Runner gán nhầm `reason: "post_verification_failed"` cho tất cả máy.

## 2. Quy chuẩn Hợp đồng Xác minh Upload (Verification Contract)
1. **Ưu tiên Ground Truth từ `report.json`:**
   - Đọc exact `run_id` từ `stdout` (`run_id=(run_[a-zA-Z0-9_]+)` hoặc đường dẫn `report.json`).
   - File `report.json` phải có `status == "SUCCESS"`, `post_verified is True`, và `video_number` khớp với video dự kiến (`next_video`).
2. **Khớp chuỗi stdout chuẩn của `Tiktok-video`:**
   - Chuỗi log chuẩn thành công của `run_post.py` là `"workflow completed successfully"`.
   - Bắt buộc bổ sung `"workflow completed successfully" in stdout_lower` vào danh sách string match hoặc cho phép `verified_from_report` là căn cứ xác thực chính khi `proc.returncode == 0`.
3. **Phân biệt rạch ròi giữa Lỗi thật và Báo cáo nhầm:**
   - Khi điều tra sự cố upload cron, luôn kiểm tra trực tiếp các file `report.json` trong `D:\CodexRuntime\tiktok-video\runs\` của ngày hiện tại để đối chiếu `post_verified` thật trước khi can thiệp vào thiết bị hay restart luồng.

## 3. Hệ quả của False-Positive (Upload lặp nhiều video trong một ca)
- **Cơ chế lặp:** Khi Phiên 3 bị đánh dấu `failed` do lỗi chuỗi stdout, scheduler/watchdog ghi nhận ca chưa hoàn thành mục tiêu. Nếu scheduler re-run hoặc retry phiên, máy sẽ tiếp tục gọi lại Hook Upload ở các slot tiếp theo, dẫn tới việc đăng 2–3 video trong cùng 1 ca (`video N`, `video N+1`, `video N+2`).
- **Khắc phục triệt để:** Patch chuẩn `is_success` chấp nhận `verified_from_report` hoặc `"workflow completed successfully"` giúp Phiên 3 chốt `SUCCESS` ngay lần đầu, bảo đảm nghiêm ngặt quy tắc **chỉ upload đúng 1 video ở phiên cuối cùng của ca**.
