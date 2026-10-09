# Triage & Fix Bẫy VETO Video Auto-Advance trong Upload Hook (2026-09-16)

## 1. Hiện tượng & Triệu chứng
- Khi chạy xong Phiên nuôi acc có hook upload video (ví dụ Ca 1 Row 2 - 80 máy), Watchdog phát báo cáo tỷ lệ lỗi upload cao bất thường (ví dụ: `Success (3), Lỗi script/xác minh (74)`).
- Tuy nhiên, kiểm tra đối soát ground truth (file `report.json` trên đĩa `D:/CodexRuntime/tiktok-video/runs/` và cột `Video Đã Đăng` trong `TikN.xlsx`) thì thực tế **72/80 máy đã upload thành công 100%** (`post_verified = True`, `status = SUCCESS`, video đã hiển thị trên trang cá nhân TikTok).
- File `upload_result.json` của từng máy bị ghi nhận:
  ```json
  {
    "status": "failed",
    "exit_code": 0,
    "returncode": 0,
    "reason": "post_verification_failed"
  }
  ```

## 2. Nguyên nhân gốc rễ (Root Cause)
1. **Cơ chế Auto-Advance của upload workflow (`state_machine.py`):**
   - Trước khi upload, feed session đọc workbook tính toán `next_video` cần đăng (ví dụ M12 cần đăng video 7).
   - Khi tiến trình `tiktok_workflow` khởi chạy, nó kiểm tra MediaFingerprintLedger và phát hiện video 7, 8, 9 đã từng được đăng trên kênh này trước đó.
   - Script tự động kích hoạt tính năng **Auto-Advance**:
     `[AUTO-ADVANCE] Skipped 3 verified video(s); new_video_number=10 (was 7)`
   - Script hoàn tất upload video 10, verify thành công (`status = SUCCESS`, `video_number = 10`).
2. **Bẫy so khớp cứng (Rigid Equality Check) & Quyền phủ quyết (VETO) trong feed runner:**
   - Trong `python_runner/flows/multi_machine_feed_session.py`, hàm `_run_upload_hook()` kiểm tra:
     ```python
     if (
         rep_status == "SUCCESS"
         and rep_post_verified
         and int(rep_video_num) == int(next_video)  # <--- BẪY: 10 == 7 -> False!
     ):
         verified_from_report = True
         report_veto_failed = False
     ```
   - Khi điều kiện `int(rep_video_num) == int(next_video)` bị `False`, cờ `report_veto_failed = True` kích hoạt quyền phủ quyết.
   - Dù tiến trình con exit code 0 và có chuỗi `Workflow completed successfully`, quyền VETO vẫn ép `is_success = False` và gán nhãn `final_reason = "post_verification_failed"`.
   - Kết quả: Toàn bộ các máy được auto-advance thành công bị biến thành lỗi kịch bản trên báo cáo của Watchdog.

## 3. Bài học OmniRoute Reviewer (Trust Boundary & Structured Marker)
- Khi nới lỏng điều kiện kiểm tra, OmniRoute Reviewer từ chối (REJECTED) nếu chỉ dùng substring lỏng lẻo:
  `has_auto_advance = "[auto-advance]" in stdout_lower or "auto-advance" in stdout_lower`
  vì một dòng log ngẫu nhiên hoặc output tùy ý có thể làm bypass kiểm tra `actual_video_num > next_video`.
- **Giải pháp chuẩn hóa (Fail-closed Structured Regex):**
  Trích xuất chính xác cấu trúc log do `state_machine.py` phát ra và xác minh cả 2 chiều:
  ```python
  actual_video_num = int(rep_video_num) if rep_video_num is not None else None
  auto_advance_matched = False
  if actual_video_num is not None and actual_video_num > int(next_video):
      aa_match = re.search(
          r"\[AUTO-ADVANCE\]\s+Skipped\s+\d+\s+verified\s+video\(s\);\s+new_video_number=(\d+)\s+\(was\s+(\d+)\)",
          stdout,
      )
      if aa_match:
          aa_new, aa_was = int(aa_match.group(1)), int(aa_match.group(2))
          if aa_new == actual_video_num and aa_was == int(next_video):
              auto_advance_matched = True

  is_video_num_valid = (
      actual_video_num is not None
      and (
          actual_video_num == int(next_video)
          or auto_advance_matched
      )
  )
  ```
- **Đồng bộ Ledger:**
  Khi ghi nhận `_ShiftUploadLedger.complete_success()`, phải truyền `video_number = effective_video_number` (chính là `actual_video_num`) thay vì `next_video` cũ để ledger không bị lệch số video so với thực tế.

## 4. Khôi phục dữ liệu khi gặp báo cáo ảo (Backfill Procedure)
- Khi gặp sự cố báo cáo ảo do lỗi VETO, chạy script Python đọc trực tiếp `D:/CodexRuntime/tiktok-video/runs/` đối soát theo `account` và `2026MMDD`.
- Tìm các entry trong `C:/ProgramData/Taadaa/tiktok-upload-concurrency-v1/shift_upload_history.json` đang kẹt ở trạng thái `"launched"`.
- Cập nhật lại `"status": "success"`, `"video_number": rd["video_number"]` và `"run_id": rd["run_id"]`.
- Sau khi cập nhật ledger, Watchdog ở các đợt chạy tiếp theo sẽ tự động đối soát ledger cache và hiển thị tỷ lệ thành công thực tế chính xác.
