# TikTok Login v1 (Tiktok_Reg) Device Lock Conflict và Active Feed Session Gate

## 1. Ngữ cảnh & Triệu chứng (Context & Symptom)
Khi thực hiện đăng nhập on-demand cho một máy cụ thể bằng script `tiktok_login_v1.py` thuộc repo `D:\Taadaa\Tiktok_Reg`:
```bash
cd /d/Taadaa/Tiktok_Reg && python tiktok_login_v1.py <stt> --email <email> --ss
```

Script lập tức dừng và in thông báo lỗi exit code = 2:
```text
[device-lock] NEEDS_USER_DECISION: device lock active: path=C:\Users\Kibe\.codex\device-locks\machine_<stt>.lock.json pid=<pid> host=<host> project=tiktok-luot nuoi acc machine=<stt> serial=<serial> started_at=... command=run_tiktok.py --mode multi-machine-feed-session reservation
```

---

## 2. Phân tích nguyên nhân gốc (Root Cause)
1. **Hardcoded `user_authorized=False`:**
   Trong `tiktok_login_v1.py`:
   ```python
   device_lock = acquire_device_lock(
       machine=args.stt,
       serial=device_id,
       project="Tiktok_Reg",
       command=sys.argv,
       user_authorized=False,
   )
   ```
   Khác với `reconcile_tiktok_accounts.py`, `tiktok_login_v1.py` chưa hỗ trợ các CLI flag như `--allow-parent-lock` hay `--user-authorized`.
2. **Xung đột phiên Feed đa máy (Active Cohort):**
   Tiến trình `run_tiktok.py --mode multi-machine-feed-session` (thường quản lý dải máy lớn, ví dụ máy 1..80) đang giữ active reservation lock cho máy mục tiêu. Ngay cả khi status trong file lock là `"blocked"` với `owner_active: false` và `handoff_at`, `acquire_device_lock` với `user_authorized=False` vẫn ném `DeviceLockNeedsUserDecision` để bảo vệ tài nguyên đang chạy.

---

## 3. Kỷ luật vận hành & Xử lý sự cố (Enforcement Protocol)
- **CẤM TUYỆT ĐỐI:**
  - CẤM dùng `taskkill` hoặc `kill` tiến trình cha (`pid` của feed session) vì sẽ làm sập phiên nuôi của toàn bộ các máy khác trong cohort.
  - CẤM xóa hoặc sửa đè file lock `machine_<stt>.lock.json` thủ công khi owner process còn đang active.
  - CẤM gửi lệnh ADB chạm vào màn hình thiết bị khi chưa lấy được lock thành công.
- **Quy trình kiểm tra an toàn (Read-only Inspection):**
  1. Kiểm tra tiến trình sở hữu lock:
     ```bash
     wmic process where "ProcessId=<pid>" get CommandLine,CreationDate
     ```
  2. Đọc file lock (kiểm tra cả hai dạng tên `machine_<stt>.lock.json` và `serial_<serial>.lock.json` tại `C:\Users\Kibe\.codex\device-locks\`) để xác định `status`, `owner_active`, `project`, `handoff_at`.
  3. Nếu tiến trình owner còn đang sống (`wmic` trả về tiến trình):
     - Dừng fail-closed ngay lập tức và báo cáo chi tiết cho Coordinator/User:
       - PID và Command line đang giữ máy.
       - Thời gian bắt đầu và trạng thái lock.
       - Đề xuất: Chờ phiên feed hoàn tất hoặc đợi Coordinator chủ động nhả lock slot máy đó.
  4. Nếu tiến trình owner đã kết thúc (`No Instance(s) Available`) VÀ file lock thể hiện `owner_active: false` / `status: "blocked"` / `handoff_at`:
     - File lock này là stale lock còn sót lại sau khi cohort hoàn tất handoff.
     - Do `tiktok_login_v1.py` hardcode `user_authorized=False` và chỉ kiểm tra `path.exists()`, script sẽ luôn ném ngoại lệ `DeviceLockNeedsUserDecision` nếu file lock còn tồn tại trên đĩa.
     - Sau khi đã xác minh PID không còn tồn tại, tiến hành xóa file lock stale:
       ```bash
       rm "C:/Users/Kibe/.codex/device-locks/<lock_file_name>.lock.json"
       ```
     - Sau đó tiến hành chạy lại lệnh login ở Mục 4.

---

## 4. Quy trình tiếp tục sau khi giải phóng Lock
Khi máy đã rảnh (file lock cleared hoặc phiên feed kết thúc):
1. Chạy lại lệnh login:
   ```bash
   cd /d/Taadaa/Tiktok_Reg && python tiktok_login_v1.py <stt> --email <email> --ss
   ```
2. Sau khi script đưa nick vào trang Profile (`com.ss.android.ugc.trill/com.ss.android.ugc.aweme.splash.SplashActivity`):
   - Mở Account Switcher: tap vào display name ở header (toạ độ tham khảo `x=350, y=150` hoặc resource-id `id/su7`).
   - Chụp ảnh nghiệm thu tại Account Switcher lưu vào: `D:/Taadaa/reports/stt<stt>_reconcile_proof.png`.
   - Dump UI XML để đối soát danh sách tài khoản active.
   - Trả thiết bị về màn hình Home an toàn (`adb shell input keyevent 3`).
   - Báo cáo kết quả và đính kèm link `MEDIA:D:/Taadaa/reports/stt<stt>_reconcile_proof.png`.
