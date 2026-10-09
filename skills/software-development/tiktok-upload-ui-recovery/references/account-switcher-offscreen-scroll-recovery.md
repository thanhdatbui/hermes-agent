# Account Switcher Off-Screen Scroll Recovery (TikTok Farm)

## 1. Triệu chứng & Bối cảnh
- **Log Error:**
  `[ACCOUNT_SWITCHER_FAILED] select account failed: ACCOUNT_MISSING: expected account was not found. Cần MANUAL_REVIEW: kiểm tra TikTok đã login chưa, dismiss popup/onboarding thủ công rồi retry.`
- **Bối cảnh thực tế:**
  - Máy nuôi nhiều nick (ví dụ 8 nicks tương ứng Tik1 -> Tik8).
  - TikTok UI bottom sheet của Account Switcher chỉ hiển thị tối đa 3-4 tài khoản trên viewport đầu tiên (khoảng `y = 900` đến `1800` trên màn hình 1080x1920).
  - Các tài khoản ở vị trí sau (Row 4-8) bị đẩy xuống dưới (off-screen).
  - Khi `select_exact_account(adapter, target_account)` được gọi, nếu logic chỉ dump XML 1 lần trên viewport tĩnh, `find_exact_account` không tìm thấy node tương ứng trong XML hierarchy và ném ngay `AccountSwitcherError("ACCOUNT_MISSING", ...)`.

## 2. Điểm lỗi kép (Dual-point failure)
1. **Automation-core (`account_switcher.py`)**:
   - `select_exact_account` không có vòng lặp scroll retry khi `find_exact_account` ném `ACCOUNT_MISSING`.
   - Cần bắt `ACCOUNT_MISSING`, kiểm tra xem `adapter` có hỗ trợ `swipe` không, thực hiện vuốt nhẹ danh sách switcher lên (scroll down) từ vùng giữa bottom-sheet (ví dụ `start_y ~ 1600` lên `end_y ~ 1100`), sleep ngắn và recapture UI XML để tìm lại account (tối đa 3 lần).
2. **Consumer Adapter (`TikTokAdapter` trong `Tiktok-video/scripts/tiktok_workflow/adapter.py`)**:
   - Thiếu method `swipe(start_x, start_y, end_x, end_y, duration_ms)` để automation-core gọi.
   - Bắt buộc implement `swipe()` duck-typed thông qua `self._adb.shell(["input", "swipe", ...])`.

## 3. Quy trình chẩn đoán O(1) của Coordinator
1. Dùng `python D:/Taadaa/tools/inspect_machine.py <N>` kiểm tra trạng thái màn hình và app foreground.
2. Kiểm tra `Tik<X>.xlsx` để xác định danh sách nick đã gán cho máy.
3. Kiểm tra artifact screenshot `soft-reboot-account_switcher-before.png` hoặc `account-switcher-profile.png` trong thư mục run. Cắt ROI nửa dưới màn hình để xem switcher panel đã mở hay chưa và danh sách nick đang hiển thị những ai.
4. Nếu switcher panel đã mở và nick mục tiêu thuộc danh sách nick hợp lệ của máy nhưng không có trên màn hình đầu tiên -> Khẳng định ngay nguyên nhân nick bị off-screen cần scroll, không đoán mò lỗi mất session hay login popup.
