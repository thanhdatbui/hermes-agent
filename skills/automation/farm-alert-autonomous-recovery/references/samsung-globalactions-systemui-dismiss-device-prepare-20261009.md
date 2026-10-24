# Samsung GlobalActions / SystemUI Occlusion Auto-Dismiss in Device Prepare (2026-10-09)

## 1. Hiện tượng & Nhận diện lỗi
- **Dấu hiệu trên Batch Alert:**
  - Báo lỗi: `login/account screen detected` hoặc `prepare-tiktok failed to focus TikTok after launch`.
  - Thuộc danh mục: `focus/device issue` (ví dụ: máy M261, M270, M271, M275).
- **Hiện trường kiểm tra ADB O(1):**
  - `mCurrentFocus`: `Window{... u0 Tùy chọn thiết bị}` thuộc package `com.android.systemui`.
  - OCR WinRT: Màn hình hiển thị menu nguồn Samsung (`Tắt nguồn`, `Khởi động lại`, `Chế độ khẩn cấp`).
  - Trạng thái nick trên Excel/DB SoT: Toàn bộ nick trên máy vẫn **LIVE 100%**, không hề bị văng phiên hay đổi mật khẩu. Cảnh báo login screen là False Positive do menu hệ thống che khuất app.

## 2. Nguyên nhân cốt lõi (Root Cause)
- Máy bị cấn phím nguồn vật lý hoặc hệ điều hành kích hoạt menu `GlobalActions` / `EmergencyMode`.
- Trong quy trình chuẩn bị app (`prepare_tiktok_app_for_automation` trong `python_runner/flows/device_prepare.py`), vòng lặp kiểm tra focus (`read_focus`) chỉ theo dõi xem package có trùng `com.ss.android.ugc.trill` hay không và retry monkey launch 10 lần.
- Vì dialog `com.android.systemui` là cửa sổ hệ thống cấp cao (system modal), monkey launch thông thường không thể ép nó tắt đi, dẫn tới toàn bộ 10 lượt verify đều thất bại với lỗi `focused package is com.android.systemui`.

## 3. Giải pháp khắc phục triệt để (T1 Fix O(1))
- **Can thiệp vào hook đọc focus:**
  Trong hàm `read_focus()` của `prepare_tiktok_app_for_automation`, bổ sung cơ chế tự động giải phóng dialog hệ thống:
  ```python
  def read_focus() -> tuple[str | None, str | None]:
      focus = get_focused_activity(ctx)
      if focus.get("package") in UIAUTOMATOR_PACKAGES:
          focus = recover_uiautomator_occlusion(ctx, package_name)
      elif focus.get("package") == "com.android.systemui":
          try:
              ctx.adb.shell(
                  ["am", "broadcast", "-a", "android.intent.action.CLOSE_SYSTEM_DIALOGS"],
                  timeout=ctx.timeout("adb_seconds", 5),
              )
              time.sleep(0.3)
              focus = get_focused_activity(ctx)
          except Exception:
              pass
      return focus.get("package"), focus.get("activity")
  ```
- **Hiệu quả:**
  Lệnh broadcast `android.intent.action.CLOSE_SYSTEM_DIALOGS` gửi tín hiệu chuẩn của Android buộc SystemUI thu hồi ngay menu `Tùy chọn thiết bị`, popup khẩn cấp mà không cần chạm tay ADB hay reboot máy. Ngay sau 0.3s, app TikTok đang chạy bên dưới lập tức được kéo lên foreground.

## 4. Kiểm chứng hồi quy & Canary
1. **Focused Test:**
   - Chạy `pytest python_runner/tests/test_device_prepare.py python_runner/tests/test_uiautomator_occlusion_recovery.py` (< 2s, 36/36 passed).
2. **Canary trên máy thật:**
   - Để nguyên hiện trường menu nguồn trên thiết bị, chạy canary:
     ```bash
     ADB_HOST=<host> python "D:/Taadaa/tiktok-luot nuoi acc/python_runner/run_tiktok.py" \
       --device <serial> --machine <N> --account <user> --mode feed-swipe-smoke \
       --allow-navigation-only --allow-feed-swipe --max-swipes 1
     ```
   - Xác nhận log: `prepare-tiktok-app completed`, `feed-swipe-smoke completed`, `Status: success`.
   - OCR hậu kiểm: Xác nhận đã vào đúng màn hình feed (có các tab *Đã follow*, *Đề xuất*, bottom nav bar *Trang chủ*, *Hồ sơ*).
