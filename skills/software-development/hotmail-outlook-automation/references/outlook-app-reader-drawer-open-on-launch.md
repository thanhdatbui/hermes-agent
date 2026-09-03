# Outlook App Reader — Drawer Open on Launch Pitfall & Fix

## Symptom
Khi hàm `read_tiktok_otp_from_outlook_app` hoặc `read_tiktok_magic_link_from_outlook_app` mở app Outlook trên thiết bị Android, app có thể khởi động lại ở trạng thái thanh menu trượt bên (Navigation Drawer / `com.microsoft.office.outlook:id/drawer_content`) đang mở sẵn.

Trình đọc ném ngoại lệ:
```
_taadaa_canonical_hotmail_login.LoginBlocked: OUTLOOK_APP_INBOX_NOT_VERIFIED
```
dù app Outlook đang hoạt động bình thường trên màn hình.

## Root Cause
1. `wait_for` chỉ chờ 4 bề mặt: `outlook_app_inbox_visible`, `outlook_app_archive_visible`, `_outlook_app_folder_surface_visible`, `outlook_app_login_form_visible`.
2. Khi Drawer đang mở, `_outlook_app_folder_surface_visible` trả `False` vì `_outlook_app_node_bounds(xml, OUTLOOK_APP_TOOLBAR_ID)` là `None` (thanh Toolbar chính bị che bởi Drawer).
3. `outlook_app_inbox_visible` cũng trả `False` vì heading toolbar bị che.
4. Do đó, điều kiện `if not (_outlook_app_folder_surface_visible(xml)):` bị kích hoạt và văng `LoginBlocked("OUTLOOK_APP_INBOX_NOT_VERIFIED")` trước khi kịp gọi `_outlook_app_open_inbox_from_archive`.

## Fix Pattern
1. Bổ sung `_outlook_app_drawer_open(value)` vào danh sách điều kiện của `wait_for`:
```python
xml = wait_for(
    adb,
    device,
    lambda value: (
        outlook_app_inbox_visible(value)
        or outlook_app_archive_visible(value)
        or _outlook_app_folder_surface_visible(value)
        or outlook_app_login_form_visible(value)
        or _outlook_app_drawer_open(value)
    ),
    timeout=60,
)
```
2. Điều chỉnh nhánh kiểm tra bề mặt thư mục:
```python
if not (_outlook_app_folder_surface_visible(xml) or _outlook_app_drawer_open(xml)):
    if _outlook_app_email_detail_visible(xml):
        xml = _outlook_app_back_to_inbox_from_detail(adb, device, xml)
        if not (_outlook_app_folder_surface_visible(xml) or _outlook_app_drawer_open(xml)):
            raise LoginBlocked("OUTLOOK_APP_INBOX_NOT_VERIFIED")
    else:
        raise LoginBlocked("OUTLOOK_APP_INBOX_NOT_VERIFIED")
```
3. Sau khi pass điều kiện, `_outlook_app_open_inbox_from_archive` sẽ tự động phát hiện `_outlook_app_drawer_open(xml)` là `True` và bấm thẳng vào item `Hộp thư đến` trong Drawer để mở hộp thư đến chuẩn xác.
