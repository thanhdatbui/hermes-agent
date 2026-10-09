# Account Switcher Scroll Recovery for Multi-Account Phones (>4 accounts)

## Triệu chứng
`[ACCOUNT_SWITCHER_FAILED] select account failed: ACCOUNT_MISSING: expected account was not found.`
Thường gặp trên các máy có 8 slot tài khoản (Tik1 -> Tik8) khi cần switch sang các tài khoản ở nửa sau danh sách (slot 4–8, ví dụ `luutuoi02`).

## Hiện trường & Nguyên nhân
- Giao diện Account Switcher bottom sheet của TikTok (đặc biệt trên dòng Samsung 1080x1920) chỉ hiển thị tối đa 3-4 tài khoản ở viewport đầu tiên.
- Các tài khoản nằm dưới bị che khuất ngoài khung nhìn màn hình (off-screen) nên XML hierarchy dump ban đầu không chứa node text/content-desc của tài khoản mục tiêu.
- Trong `automation_core/tiktok/account_switcher.py`, hàm `select_exact_account` nếu chỉ gọi `find_exact_account(_dump(adapter), account)` trên đúng viewport đầu tiên mà không cuộn trang sẽ văng ngay `AccountSwitcherError("ACCOUNT_MISSING", "expected account was not found")`.
- Consumer `TikTokAdapter` (`Tiktok-video/scripts/tiktok_workflow/adapter.py`) nếu thiếu method `swipe` sẽ không hỗ trợ cuộn trang qua ADB.

## Giải pháp triển khai
1. **Automation-core (`account_switcher.py`)**:
   - Bọc `find_exact_account` trong `try ... except AccountSwitcherError as exc:`.
   - Nếu `exc.code == "ACCOUNT_MISSING"` và adapter có method `swipe`:
     - Xác định kích thước màn hình qua `adapter.screen_size()` (mặc định 1080x1920).
     - Toạ độ vuốt: `start_x = width // 2`, `start_y = int(height * 0.80)`, `end_x = width // 2`, `end_y = int(height * 0.50)`.
     - Thực hiện vuốt với `duration_ms = 450` (chậm và mượt trên Samsung S7).
     - Chờ 1.0s (`time.sleep(max(1.0, settle * 2))`) để animation trượt kết thúc hoàn toàn trước khi dump lại UI XML.
     - Retry tối đa 3 lần vuốt. Nếu tìm thấy thì break và tiếp tục chọn tài khoản.
2. **Consumer Adapter (`adapter.py`)**:
   - Thêm method `swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 300) -> None` gọi `self._adb.shell(["input", "swipe", ...], timeout=15, check=False)`.
