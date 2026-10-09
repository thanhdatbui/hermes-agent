# Triage & Fix: Upload Hook False-Failure do VETO Auto-Advance Video Number (2026-09-16)

## 1. Hiện tượng (Symptom)
- Watchdog `feed_session_watchdog.py` báo cáo hàng loạt máy bị lỗi đăng video: `• Đăng Video (1/2 - 3 video đã đăng): Success (3) ... Lỗi script/xác minh (73 máy)`.
- Trong khi đó, kiểm tra thực tế (Ground Truth) trong `D:\CodexRuntime\tiktok-video\runs`:
  - 72/80 máy chạy hoàn tất thành công (`exit_code = 0`, `status: SUCCESS`, `post_verified: True`).
  - Video đã đăng lên kênh TikTok và cột `Video Đã Đăng` trong file Excel (`Tik2.xlsx`) đã nhảy số tăng bình thường.
  - File `upload_result.json` tại từng máy trong runtime ghi nhận: `"status": "failed", "reason": "post_verification_failed"`.

## 2. Nguyên nhân gốc rễ (Root Cause)
- **Tính năng Auto-Advance của upload runner (`tiktok_workflow`):**
  - Khi runner được gọi với `--video-number N` (dự đoán từ Excel), runner đối soát SHA-256 fingerprint. Nếu video $N$ đã từng được đăng trên kênh/máy trước đó, runner tự động nhảy cóc qua các video đã đăng:
    `[AUTO-ADVANCE] Skipped X verified video(s); new video_number=M (was N)`
  - Script đăng thành công video $M$ ($M > N$), lưu `report.json` với `video_number: M`, `status: SUCCESS`.
- **Bẫy kiểm tra cứng nhắc (Strict Equality Check) trong feed session upload hook:**
  - Tại `multi_machine_feed_session.py` (dòng 4159), điều kiện kiểm tra kết quả `report.json` yêu cầu:
    ```python
    if (
        rep_status == "SUCCESS"
        and rep_post_verified
        and int(rep_video_num) == int(next_video)  # <--- BẪY: M == N là False!
        and ...
    ):
    ```
  - Khi $M \ne N$, điều kiện `False` khiến cờ `report_veto_failed = True` kích hoạt quyền phủ quyết (VETO).
  - Khối VETO ép `is_success = False` và gán nhãn `reason: "post_verification_failed"`, hủy bỏ toàn bộ kết quả thành công thực tế và không cập nhật ledger `shift_upload_history.json`.

## 3. Giải pháp chuẩn (Fix Pattern)
Trong `D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/multi_machine_feed_session.py`:
1. Nhận diện tín hiệu Auto-Advance từ output tiến trình con:
   ```python
   has_auto_advance = "[auto-advance]" in stdout_lower or "auto-advance" in stdout_lower
   ```
2. Cho phép số video trong `report.json` lớn hơn `next_video` nếu có tín hiệu Auto-Advance:
   ```python
   actual_video_num = int(rep_video_num) if rep_video_num is not None else None
   is_video_num_valid = (
       actual_video_num is not None
       and (
           actual_video_num == int(next_video)
           or (has_auto_advance and actual_video_num > int(next_video))
       )
   )
   ```
3. Đồng bộ `effective_video_number = actual_video_num` khi gọi `_ShiftUploadLedger.complete_success()` để ghi nhận đúng số video thực tế vào ledger ca/phiên.

## 4. Kiểm chứng (Verification)
- Chạy test suite focused:
  ```bash
  pytest "D:\Taadaa\tiktok-luot nuoi acc\python_runner\tests\test_upload_hook.py"
  ```
- Xác nhận:
  - Test mismatch ngẫu nhiên không có auto-advance (`video_number: 999`) vẫn fail-closed an toàn (`assert res["status"] == "failed"`).
  - Test auto-advance (`video_number: 10` với expected `3` kèm `[AUTO-ADVANCE]` trong stdout) pass thành công (`assert res["status"] == "success"`).
- Đối soát lại ledger `shift_upload_history.json` và chạy lại watchdog xác nhận báo cáo số liệu chính xác.
