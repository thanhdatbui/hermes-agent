# Samsung Power Menu (SystemUI) Occlusion & CLOSE_SYSTEM_DIALOGS Recovery (2026-10-09)

## Hiện tượng & Triệu chứng
- Batch alert hoặc summary báo: `prepare-tiktok failed to focus TikTok after launch`.
- `verify_tiktok_focus` thất bại liên tiếp 10/10 lần với lỗi: `focused package is com.android.systemui`.
- Phân loại lỗi thuộc `category: focus/device issue` (gặp trên các máy Samsung farm như S7 M261, M270, M271, M275).
- Đôi khi kéo theo cảnh báo sai (false positive): `login/account screen detected` do widget campaign (`Nhập ngay có thưởng`) hoặc chữ trên overlay bị gom chung vào bộ phân loại nhạy cảm.

## Nguyên nhân gốc rễ
- Trên các dòng Samsung Galaxy vật lý (như S7), nút nguồn bị kẹt nhẹ hoặc rung động kích hoạt menu nguồn `Tùy chọn thiết bị` (`com.android.systemui:id/global_actions_bg`: Tắt nguồn, Khởi động lại, Chế độ khẩn cấp) hoặc màn hình điều khoản `CHẾ ĐỘ KHẨN CẤP` (`com.sec.android.emergencymode.service`).
- Overlay này thuộc `com.android.systemui`, phủ lên toàn bộ giao diện và bật DimLayer đen màn hình trong SurfaceFlinger, khiến TikTok dù đã được mở bằng `monkey` nhưng không thể chiếm foreground window focus.
- Trình đọc focus (`read_focus`) trước đây chỉ có handler giải phóng `com.github.uiautomator`, không xử lý `com.android.systemui`, dẫn tới hết 10 attempts và abort run.

## Giải pháp kỹ thuật chuẩn hóa (O(1))
1. **Lệnh giải phóng dialog hệ thống tức thì:**
   ```bash
   adb shell am broadcast -a android.intent.action.CLOSE_SYSTEM_DIALOGS
   ```
   Lệnh broadcast này là chuẩn của Android framework, đóng ngay lập tức menu nguồn (GlobalActions), thông báo, thanh điều hướng và màn hình Emergency Mode mà không cần chạm tọa độ mù hay gửi phím cứng.

2. **Patch tự động phục hồi trong `device_prepare.py`:**
   Trong hàm `read_focus()` của `prepare_tiktok_app_for_automation`:
   ```python
   if focus.get("package") in UIAUTOMATOR_PACKAGES:
       focus = recover_uiautomator_occlusion(ctx, package_name)
   elif focus.get("package") == "com.android.systemui":
       try:
           ctx.adb.shell(["am", "broadcast", "-a", "android.intent.action.CLOSE_SYSTEM_DIALOGS"], timeout=ctx.timeout("adb_seconds", 5))
           time.sleep(0.3)
           focus = get_focused_activity(ctx)
       except Exception:
           pass
   ```

3. **Cạm bẫy nhị phân chụp ảnh trên Windows Git Bash / MSYS:**
   - **Tuyệt đối không dùng:** `adb exec-out screencap -p > screen.png` trên MSYS/Git Bash vì stdout bị convert `\n` -> `\r\n` (CRLF) làm hỏng luồng PNG nhị phân, tạo ra file rác ~12KB đen sì.
   - **Bắt buộc dùng:** Chụp vào thiết bị trước rồi pull:
     ```bash
     adb shell screencap -p /sdcard/screen.png && adb pull /sdcard/screen.png local_screen.png
     ```
   - Sau đó chạy WinRT OCR hoặc PIL kiểm tra màu thực tế trước khi gửi hình ảnh chứng cứ.
