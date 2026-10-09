# TikTok Profile Switch Settle & Network Retry Pattern

## Bối cảnh
Khi tự động chuyển tài khoản (switch profile) trong `feed_swipe_smoke.py` (`verify_and_switch_profile`):
Sau khi tap vào dòng tài khoản mục tiêu trên sheet switcher và navigate/verify lại Profile (`verify_navigation`), có 2 trường hợp chậm/lỗi mạng thường gặp trên các máy farm:
1. Xuất hiện popup hoặc màn hình thông báo lỗi mạng kèm nút **"Thử lại"** (`com.ss.android.ugc.trill:id/dcj` hoặc text `"Thử lại"` / `"Đã xảy ra lỗi"`).
2. UI TikTok profile chưa kịp render dữ liệu của tài khoản mới (recaptured username/display_name vẫn là tài khoản cũ trước khi switch).

## Giải pháp xử lý chuẩn trong code
1. **Xử lý nút "Thử lại":**
   - Kiểm tra trong `latest_identity.get("xml_text")` xem có xuất hiện nút retry:
     - Resource-id: `com.ss.android.ugc.trill:id/dcj`
     - Hoặc text/content-desc: `"Thử lại"`, `"Đã xảy ra lỗi"`, `"Tap to retry"`
   - Bấm (tap) vào nút "Thử lại", sleep `2.5 - 3.5s`.
   - Gọi lại `_read_profile_identity_with_add_phone_guard(...)` để lấy lại `latest_identity` mới nhất.

2. **Retry settle cho profile username:**
   - Nếu `verified` vẫn là `False` (recaptured username chưa khớp với expected hoặc vẫn là nick cũ):
   - Thay vì kết luận ngay `last_reason = "profile username still mismatched after switch"`, thực hiện thêm 1 nhịp đợi:
     - Chờ `2.0 - 3.0s` cho app đồng bộ UI xong.
     - Đọc lại identity một lần nữa bằng `_read_profile_identity_with_add_phone_guard`.
     - Chạy lại kiểm tra verify.

## Quy tắc điều tra (Dev / Debug)
- **CẤM GREP / QUÉT DIỆN RỘNG:** Cấm chạy `grep -rn` hoặc quét đĩa toàn bộ repo `tiktok-luot nuoi acc/python_runner` vì dung lượng lớn dễ gây timeout 180s. Chỉ đọc file flow đích (`feed_swipe_smoke.py`) với offset cụ thể.
- **Canary Test:** Sau khi sửa, chạy `python -m py_compile` rồi kiểm tra trực tiếp trên máy canary:
  ```powershell
  powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines 33 -Row 3 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
  ```
