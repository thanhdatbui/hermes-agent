# Quy Tắc Đánh Dấu Kho Mail Clean V2 & Xử Lý Gmail App Popups (2026-08-31)

## 1. Báo cáo phong cách User (Style & Format Rule)
- User yêu cầu báo cáo kết quả batch/reg ngắn gọn theo định dạng:
  ```text
  Success:
  - Machine XX: <username> (<email>, row <N>)

  Fail:
  - Machine YY: <error_code/lý do>
  ```
- Không in log chi tiết từng bước, không emoji, không giải thích dài dòng trừ khi có lỗi cần hỏi.

---

## 2. Quy tắc xử lý khi nick TikTok bị ban / die
1. **Bảng tracking `taikhoan_dat_v2_updated .xlsx`:**
   - Xóa toàn bộ thông tin tài khoản TikTok bị ban (ID, PASS, 2FA, GMAIL, PASS MAIL, NGÀY SINH, NGÀY TẠO) để trả slot đó về trạng thái trống (`None`).
2. **Kho mail `gmail_clean_v2.xlsx`:**
   - **BẮT BUỘC GIỮ NGUYÊN DÒNG MAIL.**
   - Điền trạng thái vào cột `trạng thái` (cột K / col 11): ghi `banned`, `die`, `khoa`, `used`, `da dung`...
3. **Cơ chế lọc tự động (`_is_disallowed_status`):**
   - Cả `social_reg_v1.py` (`load_emails_from_excel`) và `scripts/tiktok_target_eligibility.py` (`load_source_rows`) đều tích hợp bộ lọc fail-safe:
     - Chuẩn hóa Unicode/bỏ dấu (`đ/Đ -> d/D`).
     - Bóc tách safe terms (`unused`, `chưa dùng`, `chưa sử dụng`, `not banned`, `unblocked`, `live`, `ok`, `ready`, `chưa reg`) trước khi kiểm tra.
     - Loại bỏ triệt để các mail có trạng thái: `die`, `banned`, `ban`, `bị ban`, `khoa`, `used`, `da dung`, `dang dung`, `đang dùng`, `da su dung`, `dang su dung`, `su dung`, `da dang ky`, `da reg`, `dinh chi`, `skip`, `loi`, `blocked`, `chet`, `dead`.
   - Đảm bảo tuyệt đối không bao giờ bốc lại mail đã chết đem sang `taikhoan_dat_v2` để reg lại.

---

## 3. Xử lý chuỗi Popup và Auto-Sync của Gmail App khi đọc OTP
1. **Chuỗi Popups trong `_dismiss_gmail_popups`:**
   - **Welcome Tour:** Bấm "OK" / `welcome_tour_got_it`.
   - **Phishing Protection:** "Tăng cường khả năng bảo vệ..." -> Bấm "Không, cảm ơn".
   - **Sender Tooltip:** "Nhấn vào hình ảnh người gửi..." -> Bấm "Bỏ qua".
   - **Meet Onboarding:** Bấm "Đã hiểu".
   - **Setup Addresses:** Bấm "ĐƯA TÔI TỚI GMAIL".
   - **Auto-Sync Alert Dialog:** Tìm node `android:id/alertTitle`, kiểm tra từ khóa đồng bộ/sync, bấm "Bật" (`android:id/button1`).
   - **Auto-Sync Banner:** "Tính năng tự động đồng bộ hóa đang tắt..." -> Bấm "Bật" hoặc icon dismiss `com.google.android.gm:id/dismiss_icon`.
2. **Lệnh ADB bật đồng bộ hệ thống trước khi launch Gmail:**
   ```bash
   settings put global master_sync_enabled 1
   settings put system auto_sync 1
   settings put global auto_sync 1
   ```

---

## 4. Takeover Lock Máy Đơn Lẻ từ Phiên Cron Nuôi Acc
- Khi cần can thiệp 1 máy đang bị lock bởi `tiktok-luot nuoi acc`:
  - Tuyệt đối **CẤM kill PID parent chung** hay dừng toàn bộ phiên nuôi acc của cả farm.
  - Sử dụng lệnh giải phóng lock đích danh cho máy target:
    ```bash
    python python_runner/scripts/release-device-lock.py --machine <N> --serial <serial> --reason "takeover-for-reg"
    ```
  - Sau khi máy được nhả lock, tiến hành khóa và chạy reg riêng cho máy đó.
