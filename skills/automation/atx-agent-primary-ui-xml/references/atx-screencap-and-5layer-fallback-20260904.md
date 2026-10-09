# ATX Screencap & 5-Layer Alert Fallback (2026-09-04)

## Bối cảnh & Vấn đề
1. **SurfaceFlinger Framebuffer Protection**: Trên một số dòng máy (như máy 59) hoặc khi có streaming layer bảo vệ, `adb exec-out screencap -p` bị hệ thống từ chối (`W/SurfaceFlinger: FB is protected: PERMISSION_DENIED`), trả về payload rỗng 12 byte (`0x00...`).
2. **ADB Transport Freeze/Timeout**: Khi thiết bị gặp lỗi dừng phiên, `adbd` trên máy có thể rơi vào trạng thái nghẽn socket khiến lệnh `adb shell` / `screencap` bị timeout.
3. **Lỗi ATX 502 Bad Gateway**: Khi `atx-agent` daemon đang chạy nhưng tiến trình uiautomator backend chưa được bật, request JSON-RPC chụp ảnh hoặc dump XML sẽ trả về HTTP 502.

## Kiến trúc 5 Tầng Phục Hồi Ảnh Hiện Trường (`automation_core.alerts`)
1. **Tầng 1 (Primary Live Screencap)**: Gọi `adb exec-out screencap -p` (timeout 10s).
2. **Tầng 2 (ATX-Agent / UiAutomator2 JSON-RPC)**: Setup dynamic port forward tới port `7912`/`9008`. Nếu backend trả về 502 / inactive, gửi request `POST /uiautomator` để kích hoạt stub service rồi gọi JSON-RPC `takeScreenshot` (params: `[1.0, 90]`). Cơ chế này bypass hoàn toàn bảo vệ framebuffer của SurfaceFlinger.
3. **Tầng 3 (ADB Reconnect + ATX Retry)**: Nếu ADB transport timeout, thực thi `adb -s <serial> reconnect` (chỉ reset kết nối của máy đích, không kill server ADB tổng), chờ 1.5s và thử lại chụp ảnh qua ATX JSON-RPC.
4. **Tầng 4 (Shell SDCard Stream)**: Chụp file đệm vào `/sdcard/__alert_screencap.png` qua `adb shell screencap` rồi stream về PC bằng `exec-out cat`.
5. **Tầng 5 (Session Artifact Fallback)**: Nếu tất cả các tầng live đều không phản hồi, tự động quét thư mục `D:\Taadaa\runtime\kibe\live` (hoặc `artifact_dir` được truyền vào) để lấy file `screen.png` mới nhất của `machine_<N>` sinh ra trong phiên chạy.
