# Quy tắc xử lý & xóa tài khoản TikTok bị đình chỉ / khóa / lỗi (Account Cleanup Policy)

## 1. Xóa TikTok khỏi Excel & Database (User Correction 2026-08-31)
- **Trong `taikhoan_dat_v2_updated .xlsx` & `taikhoan_run_safe.xlsx`:**
  - **Xóa toàn bộ thông tin slot tài khoản**: Xóa cả `ID TikTok`, `Pass TikTok`, `2FA Secret`, `GMAIL`, `PASS MAIL`, `NGÀY SINH`, `NGÀY TẠO`.
  - Giữ lại cấu trúc `Máy`, `Folder Video / Tik`, `device ID` với các giá trị tài khoản là `None` (ô trống) để slot sẵn sàng cho lượt reg mới.
- **Trong kho mail sạch `gmail_clean_v2.xlsx`:**
  - **TUYỆT ĐỐI KHÔNG XÓA DÒNG MAIL KHỎI `gmail_clean_v2.xlsx`**: Giữ nguyên dòng mail trong kho.
  - **Đánh dấu cột `trạng thái` (cột K / 11)**: Ghi giá trị `banned`, `die`, `khoa`, `used`, `da dung`, `dang dung`, `bi ban`, `skip`, `loi`, `blocked`, `dead`, `chet`.
  - Script `Tiktok_Reg` (`scripts/tiktok_target_eligibility.py`, `_detect_clean.py` và `social_reg_v1.py`) tích hợp bộ lọc `_is_disallowed_status` (bóc tách safe terms `unused`, `chưa dùng`, `not banned`... trước, sau đó loại trừ 100% các mail có cờ hoặc cụm từ bị ban/đã dùng), đảm bảo không bao giờ bốc lại mail đó để reg.

## 2. Xóa trên thiết bị Android
- Khi user yêu cầu "xóa nick khỏi máy / thiết bị":
  - **Chỉ xóa tài khoản TikTok khỏi TikTok app** (chuyển account, xóa session TikTok hoặc clear cache TikTok nếu được phép).
  - **TUYỆT ĐỐI CẤM XÓA TÀI KHOẢN GOOGLE / GMAIL TRÊN THIẾT BỊ ANDROID** (`Settings` -> `Accounts` -> `Google`).
  - Gmail trên máy luôn phải được giữ nguyên trên thiết bị để nhận OTP và duy trì phiên đồng bộ.

## 3. Takeover máy đơn lẻ trong Batch Feed (Multi-Machine Feed Session)
- Khi cần takeover 1 máy đang chạy trong batch nuôi acc (feed session), TUYỆT ĐỐI KHÔNG kill process cha hay dừng cả dàn máy khác.
- Sử dụng script nhả lock riêng:
  ```bash
  python python_runner/scripts/release-device-lock.py --machine <N> --serial <SERIAL> --reason "takeover"
  ```
- Sau đó chạy runner độc lập trên máy đó với `DEVICE_LOCK_ENABLED=1`.

## 4. Khắc phục cảnh báo OneDrive "UPLOAD BLOCKED" trên Excel
- Khi Excel mở file trong OneDrive (`D:\OneDrive\TaadaaData\kibe\`) báo thanh màu vàng `UPLOAD BLOCKED` do script ngoài sửa file:
  - Bấm nút **`Discard Changes`** trên thanh thông báo.
  - Chọn **`Yes`** để Excel hủy cache tạm và tải lại nội dung mới nhất từ đĩa.

## 5. Phục hồi kết nối Google Add Account (Webview ERR_CONNECTION_RESET)
- **Hiện tượng**: Khi vào `Cài đặt Android` -> `Tài khoản` -> `Thêm tài khoản` -> `Google` (hoặc qua Gmail) và gặp màn hình *"Đã xảy ra sự cố. Vui lòng quay lại và thử một lần nữa"* (logcat: `net::ERR_CONNECTION_RESET` / `MinuteMaidActivity`):
  - **KHÔNG kết luận vội là do IP proxy**: Proxy vẫn có thể sống và truy cập web bình thường.
  - **Cơ chế xử lý an toàn**: Dùng `am force-stop` để giải phóng socket/RAM bị kẹt của tiến trình Google Play Services & Chrome:
    ```bash
    adb shell am force-stop com.google.android.gms
    adb shell am force-stop com.google.android.gsf
    adb shell am force-stop com.android.chrome
    ```
  - **Lưu ý**: Tuyệt đối **CẤM DÙNG `pm clear`** vì sẽ làm văng toàn bộ tài khoản Google khác trên máy.
  - Mở lại intent thêm tài khoản:
    ```bash
    adb shell am start -a android.settings.ADD_ACCOUNT_SETTINGS -e account_types '[\"com.google\"]'
    ```

## 6. Định dạng báo cáo chuẩn
- Báo cáo ngắn gọn, tập trung: `Mục đích → Kết quả → Blocker`.
- Batch/Cron chỉ liệt kê danh sách:
  ```text
  Success:
  - Machine XX: <username> (<email>, row <N>)

  Fail:
  - Machine YY: <error_code/lý do>
  ```
- Không in log chi tiết từng bước, không emoji.

## 7. Quy tắc xử lý Alert [MÁY N] & Chống quét đệ quy ổ đĩa (User Correction 2026-09-02)
- Khi nhận cảnh báo `[MÁY N] DỪNG PHIÊN`:
  - **Đọc Log/Hiện trường:** Đi thẳng vào đúng thư mục run gần nhất `.ai-runs/<latest_run>/machines/machine_N/` để đọc `summary.txt`, `log.jsonl`, `ui.xml` hoặc map serial qua `taikhoan_run_safe.xlsx` / `Tik1.xlsx`.
  - **CẤM TUYỆT ĐỐI:** Chạy `os.walk`, `glob(recursive=True)`, `find`, `grep -r`, `search_files` quét đệ quy qua toàn bộ cây thư mục ổ `D:` hoặc `.ai-runs`. Hành vi này gây nghẽn timeout (900s) và làm mất thời gian phiên làm việc.
  - **Khắc phục lỗi màn hình khóa Samsung (Keyguard):**
    - Kiểm tra `dumpsys window policy | grep showing`. Nếu `showing=true` ("Vuốt màn hình để mở khóa"), máy bị rơi vào màn hình khóa làm mất focus app.
    - Mở khóa: `adb -s <SERIAL> shell "input keyevent 224 && input keyevent 82 && input swipe 360 1000 360 200 200"`
    - Đặt timeout vĩnh viễn: `settings put system screen_off_timeout 2147483647`, `settings put global stay_on_while_plugged_in 7`, `settings put secure lock_screen_lock_after_timeout 2147483647`.

