# TikTok 2FA Popup Bypass With No-Email-Disable & Journal Recovery (21/09/2026)

## 1. Ngữ cảnh & Triệu chứng Sự cố
Ngày 21/09/2026, watchdog sau ca trưa (`post_noon_chain_watchdog.py`) chạy 95 phút nhưng báo cáo:
- Phase 1 (Reg Gmail): 1/15 success (ChatGPT linked 0/1, 3 fail).
- Phase 2 (Add 2FA TikTok): 0/92 success, 64 fail.

---

## 2. Root Cause 1: Bẫy Popup "Thêm điện thoại" khi bỏ gỡ Email 2FA
- **Cơ chế lỗi:**
  - Từ 18/09/2026, chính sách farm bỏ bước gỡ Email khỏi 2-step verification (vì TikTok v46+ chặn tắt email trên tài khoản no-phone).
  - Khi triển khai trong `live_phase_b_adapter.py`, lệnh `return` bị chèn ngay đầu hàm `disable_email_and_confirm_stable()`:
    ```python
    def disable_email_and_confirm_stable(self) -> None:
        # BỎ BƯỚC GỠ EMAIL: TikTok v46+ chặn xóa email với tài khoản không có SĐT.
        return
        if "thiết bị tin cậy" in values: ...
    ```
- **Hậu quả liên hoàn:**
  - Sau khi nạp mã TOTP OTP thành công, TikTok luôn hiển thị popup **"Thêm điện thoại"** hoặc **"Thiết bị tin cậy"** trước khi đưa người dùng về danh sách phương thức bảo mật.
  - Do `return` sớm, script **hoàn toàn không tap "Bỏ qua"** (`self._tap_value("Bỏ qua", prefix=True)` hoặc tọa độ fallback `[128, 150]`).
  - Màn hình bị kẹt cứng ở popup này, khiến các bước tiếp theo (`ensure_account_password_saved`, verify trạng thái 2FA, teardown) bị timeout hoặc ném ngoại lệ trên toàn bộ 64 máy.

---

## 3. Khắc phục Chuẩn: Giữ dọn Popup trước khi Return
Hàm `disable_email_and_confirm_stable()` phải xử lý dọn dẹp các popup trung gian rồi mới `return` bỏ qua phần gỡ email:
```python
def disable_email_and_confirm_stable(self) -> None:
    current = self._dump()
    values = current.casefold()
    if "thêm điện thoại" in values or "thêm số điện thoại" in values or "add phone" in values:
        try:
            self._tap_value("Bỏ qua", prefix=True)
        except LiveAdapterError:
            self.adb.shell(["input", "tap", "128", "150"], check=False)
        time.sleep(1.0)
        current = self._dump()
        values = current.casefold()
    if "thiết bị tin cậy" in values or "trusted device" in values:
        try:
            self._tap_value("Bỏ qua", prefix=True)
        except LiveAdapterError:
            try:
                self._tap_value("Thêm", prefix=True)
            except LiveAdapterError:
                pass
        time.sleep(1.0)
    # BỎ BƯỚC GỠ EMAIL: TikTok v46+ chặn xóa email với tài khoản không có SĐT.
    # Bỏ qua phần tap Xóa Email phía dưới, return sớm sau khi dọn popup.
    return
```

---

## 4. Bảo tồn Dữ liệu & Cơ chế Cứu 2FA qua DPAPI Journal
- **Phát hiện quan trọng:** Khi Phase 2 báo 0 success, **không được hoảng loạn kết luận là mất nick hoặc chưa add được 2FA**.
- Điều tra `C:/Users/Kibe/AppData/Local/codex_gmail_debug-tiktok-add-bao-mat-f2a/journals/`:
  - 22/23 máy fail thực chất đã **vượt qua OTP thành công**, đã kích hoạt Authenticator ổn định trên thiết bị và lưu mã **Secret Base32 32 ký tự** ở state `authenticator_confirmed`.
  - Chỉ vì bước ghi workbook hoặc kẹt UI popup mà tiến trình chưa kịp chuyển sang state `written`.
- **Quy trình cứu nick:**
  - State `authenticator_confirmed` nằm trong `RESUMABLE_STATES`.
  - Đọc tuần tự các file journal qua `JournalStore.load()`.
  - Gọi `write_2fa(workbook_path, backup_root, target, record, secret)` tuần tự từng dòng để cập nhật Secret vào cột E Excel `taikhoan_dat_v2_updated .xlsx`.
  - Re-verify Excel readback rồi dọn dẹp journal qua `journal.purge(account_hash)` hoặc transition `written`.

---

## 5. Nguyên nhân Thất bại Đăng ký ChatGPT sau Reg Gmail (Phase 1)
- **Log hiện trường (`machine_55.log`):**
  1. `checkmail.live`: Bị lỗi timeout mạng 25s (`Page.goto: Timeout 25000ms exceeded`).
  2. `Cloudflare Turnstile / Bot Protection`: Khi submit form email đăng ký trên ChatGPT web, trang bị treo không chuyển sang màn hình OTP (`FAILED_AT_EMAIL_SUBMIT (EMAIL_SUBMIT_TIMEOUT, 1440.35s)`).
  3. Cần có cơ chế fail-fast cho warm-up ChatGPT (giảm timeout từ 1440s xuống <= 120s) để không làm nghẽn tiến trình của toàn bộ chuỗi.
