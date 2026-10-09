# TikTok Reg Execution: Direct Runner vs Batch Deferred Tracking

## 1. Hai chế độ Runner & Hành vi ghi Tracking Workbook

### A. Direct Runner (`social_reg_v1.py`)
- **Lệnh chạy:**
  ```bash
  D:/Taadaa/python-envs/automation/Scripts/python.exe D:/Taadaa/Tiktok_Reg/social_reg_v1.py <device> <stt> --ss --email <email>
  ```
- **Đặc điểm & Luồng thực thi:**
  1. Tự động kiểm tra và acquire device lock (`machine_<stt>.lock.json`).
  2. Thực hiện đăng ký tài khoản TikTok với email chỉ định.
  3. Khi **SUCCESS**:
     - Tự động gọi `upsert_tracking_account(...)` ghi trực tiếp thông tin tài khoản (handle, password, mail, dob, date) vào workbook `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx`.
     - Chạy lướt feed warmup (`run_warmup_feed`).
     - `_post_reg_cleanup` tự động force-stop TikTok và nhấn Home (`keycode 3`).
     - Giải phóng device lock (`release()`).
- **Khi nào nên dùng:** Chạy cho các máy cụ thể theo yêu cầu (1-3 máy) khi cần ghi workbook ngay lập tức mà không qua bước apply deferred.

---

### B. Batch Runner (`_run_all_targets.py`)
- **Lệnh chạy:**
  ```bash
  D:/Taadaa/python-envs/automation/Scripts/python.exe D:/Taadaa/Tiktok_Reg/_run_all_targets.py --max-workers <N>
  ```
- **Đặc điểm & Luồng thực thi:**
  1. Gọi `_detect_clean.py` để refresh target từ `_clean_targets.json`.
  2. Lọc bỏ máy đang bị lock (`filter_unlocked_targets`).
  3. Child process được gọi kèm cờ `--defer-tracking-write`.
  4. Khi thành công, kết quả được lưu dưới dạng file JSON `tracking_result_*.json` trong thư mục batch run:
     `artifact_dir/runs/social-batch-all/<timestamp>/batch_X/stt_YY/tracking_result_*.json`.
  5. **QUAN TRỌNG:** Runner này **KHÔNG** ghi trực tiếp vào workbook tracking!
- **Bắt buộc sau khi chạy batch:**
  Để merge kết quả vào `taikhoan_dat_v2_updated .xlsx` và đồng bộ sang `taikhoan_run_safe.xlsx`, phải chạy tiếp:
  ```bash
  D:/Taadaa/python-envs/automation/Scripts/python.exe D:/Taadaa/Tiktok_Reg/scripts/apply_deferred_tracking_results.py
  ```

---

## 2. Quy trình Preflight Check nhanh
1. **Kiểm tra target:** Đọc `D:\Taadaa\Tiktok_Reg\_clean_targets.json`.
2. **Kiểm tra ADB:** `adb devices` đảm bảo serial tương ứng ở trạng thái `device`.
3. **Kiểm tra Lock:** Soát trong `C:\Users\Kibe\.codex\device-locks\`:
   - `machine_<STT>.lock.json`
   - `serial_<SERIAL>.lock.json`
   Nếu file không tồn tại hoặc process cũ đã chết -> máy rảnh an toàn để chạy.

---

## 3. Tiêu chuẩn Báo cáo Farm
- Sau khi hoàn thành hoặc gặp lỗi, đối chiếu các tiêu chí:
  - **SUCCESS:** Xác nhận đã lưu tracking workbook, feed warmup đã lướt, app force-stop về Home, lock đã nhả.
  - **FAIL:** Chụp screencap, log lý do (OTP / DOB / Captcha / Proxy...), force-stop app về Home, lock xử lý theo quy định.
- Mẫu báo cáo chuẩn:
  ```text
  • Tổng máy: N
  • Success (<N>): <danh sách STT>
  • Fail (<N>): <danh sách STT kèm lý do>
  ```
