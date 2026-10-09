# Quy Tắc Dọn Sạch Gmail DIE Song Song (Excel & Thiết Bị S7)

> **Cập nhật:** 2026-09-17  
> **Nguyên tắc:** Khi phát hiện tài khoản Gmail DIE (qua preflight `checkmail.live` hoặc khi reg gặp lỗi timeout OTP / Google Block), BẮT BUỘC thực thi dọn dẹp song song trên cả 2 bề mặt: Excel nguồn và Thiết bị S7.

---

### 1. Tại sao phải dọn cả trên máy?
- Nếu chỉ xóa tài khoản DIE trong file Excel (`gmail_clean_v2.xlsx`), thiết bị S7 vẫn còn giữ tài khoản Google đó trong hệ điều hành (`Settings -> Cloud and accounts -> Accounts`).
- Khi chạy các tác vụ tiếp theo (Gmail 2FA, GPM login, TikTok login, hoặc reg bù), hệ thống có thể tái sử dụng tài khoản chết trên máy, gây lỗi One-tap, văng Google Play Services, hoặc nghẽn sync.

---

### 2. Quy trình 2 bước bắt buộc:

1. **Bước 1: Dọn ở Excel (Source Workbook)**
   - Sử dụng hàm chuẩn: `remove_captcha_dead_email_from_source(email)` từ `social_reg_v1.py`.
   - Backup và xóa chính xác 1 row chứa email trong `gmail_clean_v2.xlsx`.

2. **Bước 2: Dọn ở Thiết Bị S7 (Device Account Cleanup)**
   - Sử dụng tool chuẩn: `remove_device_account_fast(serial, email)` từ `D:/Taadaa/tools/remove_device_google_account.py`.
   - Kiểm tra `dumpsys account` qua Xiaowei ADB.
   - Nếu tài khoản Google DIE hiện diện trên máy: Kích hoạt quy trình gỡ tài khoản (`remove_google_account_ui`) hoặc remove account để máy hoàn toàn sạch tài khoản Google trước khi chuyển sang tác vụ khác.

---

### 3. Tích hợp trong `_run_all_targets.py` (Preflight Check Live):
```python
if em.endswith("@gmail.com") and live_map.get(em) is False:
    # 1. Dọn Excel
    remove_captcha_dead_email_from_source(t["email"])
    # 2. Dọn Device S7
    remove_device_account_fast(str(t.get("device") or ""), t["email"])
```
