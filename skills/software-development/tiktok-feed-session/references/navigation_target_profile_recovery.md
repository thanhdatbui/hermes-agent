# Navigation Target Profile Recovery & Inspection Pitfalls

## 1. Cơ chế lỗi "navigation target profile not found in XML"
- **Nguồn gốc phát sinh**:
  - Xuất phát từ `tap_navigation_target(ctx, target, ...)` trong `python_runner/flows/calibrate_screens.py`.
  - Hàm thực hiện capture UI XML (`capture_required_ui`) và tìm element navigation tương ứng qua `_find_navigation_element(root, target)`.
  - Nếu `point is None` (không tìm thấy selector/text của target profile trong cây XML), hàm sẽ trả về `NavigationResult(ok=False, status="not-found", reason="navigation target profile not found in XML")`.

- **Các tình huống dẫn đến lỗi**:
  1. **TikTok bị crash hoặc mất focus văng ra Launcher** (`com.sec.android.app.launcher` hoặc launcher khác): Cây XML lúc này là của Launcher, hoàn toàn không có bottom navigation bar của TikTok.
  2. **Race condition khi relaunch**: `_relaunch_and_poll_tiktok_focus()` thành công đưa TikTok lên foreground, nhưng UI TikTok vừa khởi động chưa kịp render bottom navigation bar mà script đã gọi ngay `tap_navigation_target()`.
  3. **Màn hình bị che bởi popup/overlay chưa được nhận diện**: Một popup toàn màn hình hoặc dialog chưa có trong registry khiến các tab bar bị ẩn hoặc vô hiệu hoá.

## 2. Vị trí xử lý trong Codebase
- **Flow chính**: `python_runner/flows/feed_swipe_smoke.py` -> `_navigate_profile_for_preflight()`.
- **Logic phục hồi chuẩn**:
  - Khi `not navigation.ok` với reason chứa `not found in XML`:
    - Kiểm tra focus thực tế `get_focused_activity(ctx)`.
    - Nếu package không thuộc `tiktok_pkgs` (hoặc là launcher), kích hoạt `_relaunch_and_poll_tiktok_focus()`.
    - Đệm một khoảng chờ ngắn (`time.sleep(1.5)`) để UI ổn định và tab bar render xong trước khi tap retry.
    - Retry `tap_navigation_target(ctx, _profile_target(), ...)`.

## 3. Pitfall tra cứu & thao tác công cụ
- **Cấm `grep -rn` diện rộng**: Repo `D:/Taadaa/tiktok-luot nuoi acc` chứa thư mục `.ai-runs`, `runs`, `__pycache__` rất lớn. Lệnh grep đệ quy trên Windows sẽ bị treo/timeout (900s). Luôn chỉ định file đích rõ ràng (`calibrate_screens.py`, `feed_swipe_smoke.py`, `benign_popup_registry.py`).
- **Khoảng trắng trong đường dẫn**: Tên thư mục `tiktok-luot nuoi acc` có dấu cách; các công cụ terminal/ripgrep cần được bọc nháy kép đầy đủ.
- **Canary test an toàn**:
  ```powershell
  powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <ID> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
  ```
