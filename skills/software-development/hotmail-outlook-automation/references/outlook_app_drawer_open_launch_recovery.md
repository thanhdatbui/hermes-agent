# Outlook App Reader — Drawer Open on Launch Recovery

## Vấn đề & Triệu chứng (Anti-pattern)
Khi gọi `read_tiktok_otp_from_outlook_app` hoặc `read_tiktok_magic_link_from_outlook_app`, nếu app Outlook khởi chạy với navigation drawer đã mở sẵn (`_outlook_app_drawer_open(xml) == True`):
1. Toolbar bị navigation drawer che khuất dẫn tới `_outlook_app_folder_surface_visible(xml)` trả về `False`.
2. Vòng lặp `wait_for` trên launch không chứa `_outlook_app_drawer_open(value)` -> timeout 60s hoặc trượt trạng thái.
3. Điều kiện kiểm tra `if not _outlook_app_folder_surface_visible(xml):` ném exception `LoginBlocked("OUTLOOK_APP_INBOX_NOT_VERIFIED")` trước khi kịp gọi recovery `_outlook_app_open_inbox_from_archive`.

## Giải pháp chuẩn (Pattern)
1. Bổ sung `or _outlook_app_drawer_open(value)` vào predicate của `wait_for` khi launch app.
2. Cập nhật pre-archive check:
```python
if not (_outlook_app_folder_surface_visible(xml) or _outlook_app_drawer_open(xml)):
    if _outlook_app_email_detail_visible(xml):
        xml = _outlook_app_back_to_inbox_from_detail(adb, device, xml)
        if not (_outlook_app_folder_surface_visible(xml) or _outlook_app_drawer_open(xml)):
            raise LoginBlocked("OUTLOOK_APP_INBOX_NOT_VERIFIED")
    else:
        raise LoginBlocked("OUTLOOK_APP_INBOX_NOT_VERIFIED")
xml = _outlook_app_open_inbox_from_archive(adb, device, xml)
```
3. `_outlook_app_open_inbox_from_archive` đã có sẵn nhánh xử lý khi drawer đã mở: bỏ qua việc tap account button và tap trực tiếp item `Hộp thư đến` trong drawer để chuyển về Inbox an toàn.
