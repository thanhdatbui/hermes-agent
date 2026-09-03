# GPM Account Pool Automation

## GPM Local API
- **Port**: 19995 (GPMLogin Local API v3)
- 16 profile gốc & Live Kibe: CẤM xoá/ghi đè

## Profile Structure
- 1 profile = 1 Gmail
- Profile Kibe (máy 1-80): chỉ log đúng Gmail theo máy Kibe
- Profile Admin: chỉ log Gmail ngoài Kibe
- CẤM Hotmail (chỉ Gmail)

## Proxy Assignment
- **Kibe**: Singbox 20001..20080
- **Admin**: MikroTik 20008..20035 (kho 240 ẩn GroupId=0, Gmail ngoài Kibe)

## Master Excel
- File: `master_gmail_manager.xlsx`
- Tên cột: `[Port/Máy] - [Gmail]`
- Batch 2FA flow: ADB lấy mã S7 → browser bật 2FA Authenticator → lưu 32-char key Excel

## Close Session Rule (QUAN TRỌNG)
Khi GPM/Browser xong hoặc lỗi:
```python
try:
    # ... logic ...
finally:
    gpm.close_profile(profile_id)  # BẮT BUỘC
    kill_chrome_processes()  # BẮT BUỘC
```
Max 10 workers song song.