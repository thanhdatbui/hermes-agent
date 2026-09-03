# Farm Device Rules: Keyboard Standard, Alert Banner & Fast Login Cleanup (2026-08-24)

## 1. Alert Banner Bắt Buộc Khi Báo Cáo Ảnh Máy Lỗi
- **Định dạng chuẩn:** Mọi ảnh chụp màn hình máy farm gửi user / alert nhóm **BẮT BUỘC** phải gắn **Banner Đỏ** ở đầu ảnh:
  `[MAY X] - HH:MM:SS dd/mm` (ví dụ: `[MAY 11] - 19:50:58 24/08`).
- **Giữ nguyên hiện trường:** Không tự ý force-stop hoặc gửi keyevent HOME làm mất trạng thái màn hình lỗi.
- **Giữ Device Lock:** Máy lỗi giữ lock trạng thái `FAILED_LOCKED` / `handoff`.

## 2. Tiêu Chuẩn Bàn Phím Toàn Farm (AdbKeyboard vs Samsung Keyboard)
- **Chuẩn toàn farm:** 100% các repo (`Tiktok_Reg`, `tiktok-log-in`, `Hotmail`, `add mail khoi phuc`...) phải dùng `AdbKeyboard`:
  - Package: `com.github.uiautomator/.AdbKeyboard`
  - Broadcast: `ADB_KEYBOARD_INPUT_TEXT` (chuỗi Base64 UTF-8)
  - Lý do: Bàn phím Samsung không nhận được tiếng Việt có dấu qua ADB, hay làm bật dialog chọn bàn phím gây che UI và làm lệch layout gợi ý từ.
- **Ngoại lệ duy nhất:** `register gmail` (`gmail_reg_v10.py`) dùng `SamsungKeypad` để phục vụ `human_type` tránh bot Google.

## 3. Quy Trình Xóa Session Rác Trên App TikTok
- Khi gặp màn hình One-tap login ("Tiếp tục với tên @..."):
  1. Trích xuất `@handle` trên màn hình.
  2. Quét kiểm tra đối chiếu trong toàn bộ kho Excel farm (`Tik1-4.xlsx`, `taikhoan_dat_v2_updated .xlsx`, `taikhoan_run_safe.xlsx`, `gmail_clean_v2.xlsx`).
  3. **Chỉ xóa khi nick hoàn toàn KHÔNG CÓ trong Excel**: Tap 3 chấm $\rightarrow$ Chọn **"Xóa tài khoản"** $\rightarrow$ Xác nhận Xóa $\rightarrow$ Bấm **"Sử dụng tài khoản khác"**.
  4. Nếu nick **CÓ trong Excel**: Giữ nguyên không xóa.
