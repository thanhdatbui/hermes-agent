# Farm Close-Session Protocol (Canonical)

## Rule: CLOSE_PROFILE + KILL_CHROME ngay khi xong / lỗi
Khi GPM/Browser profile hoàn tất (Reg, Login, 2FA, Feed...) hoặc gặp lỗi:
```python
try:
    # ... logic browser/GPM ...
finally:
    gpm.close_profile(profile_id)  # BẮT BUỘC
    kill_chrome_processes()  # BẮT BUỘC
```

## Profile Kibe (Máy 1-80) vs Profile Admin
- **Profile Kibe (1-80)**: Chỉ log Gmail theo đúng máy Kibe.
- **Profile Admin (200+)**: Chỉ log Gmail ngoài Kibe.
- CẤM ghi đè / xoá 16 profile gốc & Live Kibe.

## Proxy Assignment
- **Kibe**: Singbox ports 20001..20080
- **Admin**: MikroTik ports 20008..20035 (kho 240 ẩn GroupId=0, Gmail ngoài Kibe)

## Master Excel
- File: `master_gmail_manager.xlsx`
- Chỉ Gmail (CẤM Hotmail)
- Tên cột: `[Port/Máy] - [Gmail]`
- Batch 2FA: ADB lấy mã S7 → browser bật 2FA Authenticator → lưu 32-char key Excel (tách khỏi phone S7)