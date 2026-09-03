# Quy Tắc Bàn Phím, Ảnh Báo Cáo & Xử Lý Session Rác Farm TikTok (2026-08-24)

## 1. Quy tắc chụp ảnh báo cáo lỗi (Farm Alert Screencap Banner)
- **BẮT BUỘC:** Mọi ảnh chụp màn hình máy lỗi khi gửi cho user / báo cáo farm phải chèn **Banner Đỏ** ở đầu ảnh với format chuẩn:
  `[MAY X] - HH:MM:SS dd/mm`
  Ví dụ: `[MAY 11] - 19:50:58 24/08`
- Tuyệt đối KHÔNG gửi ảnh trơn không có nhãn số máy.
- Khi máy lỗi: **Giữ nguyên màn hình lỗi + Giữ device lock**, không tự ý force-stop hoặc bấm Home làm mất hiện trường.

## 2. Chuẩn hóa Bàn phím IME trên toàn hệ thống Farm (AdbKeyboard)
- **Chuẩn toàn farm:** 100% các repo (`Tiktok_Reg`, `tiktok-log-in`, `Hotmail`, `add mail khoi phuc`...) phải chuyển cứng sang `AdbKeyboard`:
  - Package chuẩn: `com.github.uiautomator/.AdbKeyboard`
  - Cơ chế gõ: Bắn broadcast `ADB_KEYBOARD_INPUT_TEXT` kèm chuỗi Base64 UTF-8.
  - Lệnh kích hoạt:
    ```bash
    adb shell ime enable com.github.uiautomator/.AdbKeyboard
    adb shell ime set com.github.uiautomator/.AdbKeyboard
    ```
- **Ngoại lệ duy nhất:** Repo `register gmail` (`gmail_reg_v10.py`) giữ lại `SamsungKeypad` để phục vụ cơ chế `human_type` bypass bot detection của Google Play Services.

## 3. Module Xử lý Màn hình Đăng nhập nhanh & Xóa Session Rác (Fast Login / One-tap Login)
- Khi mở TikTok gặp màn hình "Tiếp tục với tên @..." (One-tap login):
  1. Trích xuất `@handle` hiển thị trên màn hình.
  2. **Đối chiếu bắt buộc với kho Excel:** Quét kiểm tra trong tất cả các workbook (`Tik1-4.xlsx`, `taikhoan_dat_v2_updated .xlsx`, `taikhoan_run_safe.xlsx`, `gmail_clean_v2.xlsx`).
  3. **Quyết định:**
     - Nếu nick **CÓ trong Excel**: **GIỮ NGUYÊN**, tuyệt đối không xóa. Bấm "Sử dụng tài khoản khác" để tiếp tục luồng.
     - Nếu nick **KHÔNG CÓ trong Excel**: Đây là session rác cũ $\rightarrow$ Bấm nút 3 chấm góc phải trên (`bounds [804,78][936,210]`) $\rightarrow$ Chọn **"Xóa tài khoản"** $\rightarrow$ Xác nhận **"Xóa"** $\rightarrow$ Sau đó mới bấm **"Sử dụng tài khoản khác"** để vào luồng đăng ký tài khoản mới.
