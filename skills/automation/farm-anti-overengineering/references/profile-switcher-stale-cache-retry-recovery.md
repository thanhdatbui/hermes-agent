# Profile Switcher Stale Cache & "Thử lại" Network Error Recovery (11/09/2026)

## 1. Triệu chứng & Bối cảnh
- **Alert:** `[BATCH ALERT: LỖI HỆ THỐNG]` hoặc `[FARM ALERT: MÁY N]` dừng phiên với signature `profile username still mismatched after switch`.
- **Tình huống xuất hiện:** Khi runner thực hiện chuyển đổi giữa các slot nick (ví dụ: Slot 3 nick `phanlan097`, trong khi profile đang mở ở nick cũ `lebaothao8787`).
- **Hiện trường kiểm chứng:**
  - Trong bottom sheet switcher, nick mong muốn (`phanlan097`) ĐÃ CÓ trong danh sách và script đã tap trúng phần tử (`tap_expected_account`).
  - Sau khi tap và quay lại màn hình Profile:
    1. Do mạng chập chờn hoặc TikTok nạp trang chậm, app hiển thị thông báo lỗi mạng: *"Đã xảy ra lỗi / Thử lại sau"* kèm nút *"Thử lại"* (`com.ss.android.ugc.trill:id/dcj`).
    2. Hoặc Profile XML vẫn còn cache username của tài khoản cũ trong 2-4 giây đầu (`recaptured_username` != `expected_norm`).
  - Khi đó, điều kiện `verify_selected_account` bị fail và fallback kiểm tra thấy `recaptured_username` có giá trị nhưng không khớp `expected` $\rightarrow$ `verified = False` $\rightarrow$ script kết luận ngay `profile username still mismatched after switch` và rơi vào `manual-needed`.

## 2. Kỷ luật Khắc phục (Resolution Pattern)
- **Vị trí xử lý:** `python_runner/flows/feed_swipe_smoke.py` trong hàm `verify_and_switch_profile` (ngay sau block fallback check `verified` khi `selected_account_by_exact_switcher` là True).
- **Cơ chế phục hồi 2 bước:**
  1. **Nhận diện & Tap nút "Thử lại":** Quét `recaptured_xml`. Nếu có `com.ss.android.ugc.trill:id/dcj` hoặc text *"Thử lại"* / *"Đã xảy ra lỗi"*, thực hiện tap nút retry và chờ 2.5–3.0s.
  2. **Settle Retry đọc lại Profile Identity:** Chờ thêm settle delay 2.5–3.0s, gọi lại `_read_profile_identity_with_add_phone_guard(...)` để lấy XML profile mới nhất sau khi UI cập nhật, re-evaluate lại `verified` trước khi kết luận lỗi.

## 3. Quy chuẩn Coordinator Dispatch
- Tuyệt đối tuân thủ **Hard Gate #3 (Dispatch Contract)**: Prompt dispatch worker qua `delegate_task` phải luôn có đủ 3 block:
  - `FILE: D:\Taadaa\tiktok-luot nuoi acc\python_runner\flows\feed_swipe_smoke.py`
  - `SCOPE: <mô tả chi tiết vị trí hàm và giải pháp retry>`
  - `FOCUSED_TEST: python -m py_compile "D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/feed_swipe_smoke.py"`
- Yêu cầu worker phải chạy lệnh Canary Test thực tế trên máy gặp lỗi (ví dụ: M33) trước khi báo cáo kết quả:
  `powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row <R> -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run`
