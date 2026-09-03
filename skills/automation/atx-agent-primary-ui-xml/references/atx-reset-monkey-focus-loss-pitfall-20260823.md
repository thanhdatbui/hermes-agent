# Pitfall: `reset_atx_agent` dùng `monkey` làm chiếm Foreground TikTok (2026-08-23)

## Triệu chứng
* Bot Farm Alerts báo dừng phiên trên máy live (ví dụ Máy 25):
  * `TikTok focus lost; swipe recovery (2 swipes) still stuck`
  * Ảnh hiện trường hiển thị app **UIAutomator** (giao diện phím tắt tiếng Trung: `开发者选项`, `无障碍服务`, `识别本机`, `关闭所有服务`, `内部存储`, `本机IP地址`...).
* `dumpsys window | grep mCurrentFocus` trả về: `com.github.uiautomator/com.github.uiautomator.MainActivity`.
* TikTok (`com.ss.android.ugc.trill`) bị đẩy xuống background/stack dưới.

## Nguyên nhân gốc (Root Cause)
1. Trong quá trình capture UI XML, nếu ATX agent timeout hoặc trả XML rỗng 3 lần liên tiếp, tầng `ui_capture.py` gọi hàm `reset_atx_agent(adb)` trong `automation-core`.
2. Hàm `reset_atx_agent` trước đây thực hiện ladder:
   ```python
   # 1. Force stop uiautomator stub packages
   for package in UIAUTOMATOR_PACKAGES:
       adb.shell(["am", "force-stop", package], timeout=timeout, check=False)
   # 2. Kill wedged atx-agent & uiautomator
   adb.shell(["pkill", "-9", "-f", "atx-agent"], timeout=timeout, check=False)
   adb.shell(["pkill", "-9", "-f", "uiautomator"], timeout=timeout, check=False)
   # 3. Start atx-agent daemon
   adb.shell([ATX_AGENT_PATH, "server", "-d"], timeout=timeout, check=False)
   # 4. Wake/warmup stub
   adb.shell(["monkey", "-p", "com.github.uiautomator", "1"], timeout=timeout, check=False)
   ```
3. Lệnh `monkey -p com.github.uiautomator 1` kích hoạt `com.github.uiautomator.MainActivity` lên làm màn hình foreground.
4. Khi flow tiếp tục, màn hình hiển thị UIAutomator thay vì TikTok. Flow chạy `swipe_recovery_on_stuck` (vuốt 2 lần để giải phóng màn hình kẹt), nhưng vuốt trên UIAutomator không thể kéo TikTok quay lại foreground -> Kẹt và fail-closed `TikTok focus lost`.

## Khắc phục & Phòng ngừa (Đã hoàn thiện)
1. **Khởi động Stub ngầm hoàn toàn qua ATX JSON-RPC endpoint (Đã fix trong automation-core 2026-08-23):**
   * Thay thế lệnh `monkey -p com.github.uiautomator 1` bằng lệnh curl trực tiếp từ binary atx-agent:
     ```python
     adb.shell([ATX_AGENT_PATH, "curl", "-X", "POST", f"http://127.0.0.1:{ATX_DEVICE_PORT}/uiautomator"], timeout=timeout, check=False)
     ```
   * Cơ chế này gọi endpoint `/uiautomator` để kích hoạt UiAutomator stub service chạy ngầm (background) 100%, không mở bất kỳ UI Activity nào, tuyệt đối không làm mất focus của app mục tiêu (TikTok/Outlook/Gmail).
2. **Re-focus TikTok sau ATX recovery:** Trong bất kỳ flow nào gọi recovery ATX/stub khi đang chạy giữa phiên, cần verify foreground package và dùng `monkey -p com.ss.android.ugc.trill 1` / `am start` nếu phát hiện focus bị thay đổi.
