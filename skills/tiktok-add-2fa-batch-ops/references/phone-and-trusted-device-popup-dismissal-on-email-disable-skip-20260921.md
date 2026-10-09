# Bẫy Early Return Gỡ Email Bỏ Quên Popup "Thêm Điện Thoại" & "Thiết Bị Tin Cậy" (21/09/2026)

## Ngữ cảnh & Sự cố (21/09/2026)
Vào ngày 21/09/2026, chuỗi sau ca trưa (`post_noon_chain_watchdog.py`, job `7d32d8c1907e`) chạy từ 15:30 đến 17:05 (95 phút):
- Phase 1 (Reg Gmail): 1/15 máy thành công.
- Phase 2 (TikTok Add 2FA): 92 mục tiêu, 28 skipped (preflight/lock), **0 thành công, 64 thất bại toàn diện**.
- Có 19 tài khoản đã hoàn tất bước enroll TOTP, tạo file Journal DPAPI tại `journals/`, nhưng không một tài khoản nào ghi được Secret Key vào Excel `taikhoan_dat_v2_updated .xlsx`.

---

## 1. Cơ Chế Phát Sinh Lỗi (Root Cause)

### A. Chỉ đạo nghiệp vụ (18/09/2026)
"Bỏ hoàn toàn bước gỡ Email khỏi 2FA TikTok (không gọi tắt email vì nick no-phone bị TikTok v46+ server-side chặn toast bảo mật)."

### B. Sai lầm khi triển khai (Code Anti-Pattern)
Trong `python_runner/core/live_phase_b_adapter.py`:
```python
def disable_email_and_confirm_stable(self) -> None:
    # BỎ BƯỚC GỠ EMAIL: TikTok v46+ chặn xóa email với tài khoản không có SĐT.
    # Chuyển thành no-op để luồng chạy thẳng sang lưu mật khẩu và kết thúc thành công.
    return
    if "thiết bị tin cậy" in values or "trusted device" in values:
        ...
```
Người lập trình chèn lệnh `return` ngay ở dòng đầu tiên của hàm `disable_email_and_confirm_stable()`.

### C. Hậu quả liên hoàn
1. Sau khi nhập OTP TOTP thành công, TikTok **luôn luôn hiển thị màn hình / popup tiếp theo**:
   - Màn hình 1: **"Thêm số điện thoại"** / **"Thêm điện thoại"** (`Add phone`) với nút "Bỏ qua" ở góc trên trái (`[24,72][232,228]` hoặc tọa độ fallback `(128, 150)`).
   - Màn hình 2: **"Thiết bị tin cậy"** (`Trusted device`) với nút "Bỏ qua" / "Thêm".
2. Hàm `confirm_authenticator_stable()` chỉ kiểm tra:
   ```python
   self._wait_stable(
       lambda xml: "thêm số điện thoại" in xml.casefold() or "thêm điện thoại" in xml.casefold(),
       "OTP_SUCCESS_PHONE_STEP_NOT_REACHED",
   )
   ```
   Tức là nó chỉ đợi màn hình "Thêm điện thoại" xuất hiện để xác nhận OTP đã ăn vào hệ thống, sau đó **nhường quyền hạ màn hình cho hàm kế tiếp**.
3. Do `disable_email_and_confirm_stable()` bị `return` sớm, cả 2 popup/màn hình "Thêm điện thoại" và "Thiết bị tin cậy" **hoàn toàn KHÔNG được bấm "Bỏ qua"**.
4. Luồng chạy tiếp vào `ensure_account_password_saved()`:
   - Hàm này dump UI tìm các nhãn Settings: "Cài đặt và quyền riêng tư", "Tài khoản", "Thông tin tài khoản", "Mật khẩu".
   - Nhưng trên màn hình thiết bị lúc này vẫn đang là popup "Thêm điện thoại".
   - Script không tìm thấy anchor nào, lặp 8 lần nhấn Back làm văng ra ngoài hoặc timeout, dẫn đến toàn bộ 64 máy bị fail và không tài khoản nào ghi được Secret Key vào Excel.

---

## 2. Giải Pháp Chuẩn Hóa (Patch Pattern)

Hàm `disable_email_and_confirm_stable()` mang **hai trách nhiệm độc lập**:
1. **Trách nhiệm 1 (BẮT BUỘC):** Dọn dẹp/hạ các popup trung gian sau TOTP ("Thêm điện thoại", "Thiết bị tin cậy") để đưa UI trở về danh sách phương thức 2FA / màn hình Cài đặt an toàn.
2. **Trách nhiệm 2 (BỎ QUA):** Tap vào dòng Email để Xóa / Xác nhận xóa.

Đoạn code sửa đúng:
```python
def disable_email_and_confirm_stable(self) -> None:
    current = self._dump()
    values = current.casefold()
    # 1. Bắt buộc hạ màn hình Thêm điện thoại
    if "thêm điện thoại" in values or "thêm số điện thoại" in values or "add phone" in values:
        try:
            self._tap_value("Bỏ qua", prefix=True)
        except LiveAdapterError:
            self.adb.shell(["input", "tap", "128", "150"], check=False)
        time.sleep(1.0)
        current = self._dump()
        values = current.casefold()

    # 2. Bắt buộc hạ màn hình Thiết bị tin cậy
    if "thiết bị tin cậy" in values or "trusted device" in values:
        try:
            self._tap_value("Bỏ qua", prefix=True)
        except LiveAdapterError:
            pass
        time.sleep(1.0)

    # 3. Bỏ qua bước gỡ email (TikTok v46+ chặn trên nick no-phone)
    # Kết thúc an toàn sau khi UI đã về danh sách phương thức / cài đặt
    return
```

---

## 3. Bài Học Giám Sát Watchdog (`post_noon_chain_watchdog.py`)
- `run_batch_live_2fa.py` xuất bảng kết quả chi tiết từng máy (`machine | source_row | username | status | reason`), nhưng watchdog nuốt chửng stdout mà không lưu ra file log nào ngoài việc in tóm tắt text.
- Khi có sự cố hàng loạt, cần ghi `t2fa_out` vào file log runtime (ví dụ `D:/Taadaa/reports/2fa_batch_last_run.log`) để Coordinator có thể trích xuất O(1) lý do lỗi mà không phải đoán mò hay quét đĩa.
