# XiaoWei OS-Wide Idle vs Manual Close & Port 5038 Lifecycle (16/10/2026)

## 1. Bản Chất Bẫy Nhàn Rỗi Hệ Thống (OS-Wide Idle vs App Interaction)
- **Kỳ vọng vận hành của người dùng:** Người dùng chỉ coi là "đang thao tác" khi thực sự click chuột hoặc gõ phím vào cửa sổ Tiểu Vi (`xiaowei.exe`). Nếu mở Tiểu Vi lên soi vài giây rồi chuyển sang làm việc khác (chat Telegram, làm việc trên GPM Browser, chơi game TFT), Tiểu Vi phải được coi là nhàn rỗi (idle) và tự động đóng lại.
- **Bản chất kỹ thuật Windows API:**
  * Hàm `GetLastInputInfo(&lii)` trong `xiaowei_idle_auto_close_watchdog.py` đo lường thời gian nhàn rỗi **toàn cục của toàn bộ hệ điều hành Windows** (OS-wide input tick count), không phân biệt cửa sổ foreground hay background.
  * Do đó, nếu người dùng vẫn đang gõ phím/rê chuột ở các ứng dụng khác trên Desktop, bộ đếm idle liên tục bị reset về 0 (ví dụ `idle_seconds: 45s`), watchdog **KHÔNG BAO GIỜ kích hoạt auto-close**.
  * Hậu quả: Cửa sổ Tiểu Vi bị bỏ quên chạy ngầm trong suốt ca nuôi acc, liên tục kéo 80 luồng stream màn hình làm nghẽn bus USB 2.0 và duy trì tiến trình `adb.exe -P 5038`.

## 2. Vòng Đời Tiến Trình Khi Người Dùng Tắt Bằng Tay (Manual Close / Nút X)
- **Khoảnh khắc bấm X (Tức thời):**
  * Tiểu Vi xây dựng trên nền tảng Tauri (Rust + WebView2). Khi người dùng click nút X góc trên cửa sổ, Windows chỉ đóng tiến trình cha `xiaowei.exe`.
  * Tiến trình con `"C:\Program Files (x86)\xiaowei\tools\adb.exe" tools/adb -P 5038 nodaemon server start` **KHÔNG tự động thoát**, trở thành tiến trình mồ côi (orphan process) tiếp tục chạy ngầm và độc quyền giữ WinUSB interface của 25–40 máy.
- **Cơ chế thu dọn tự động 2 phút (Defense-in-Depth):**
  * Watchdog `xiaowei-idle-auto-close-kibe` (Job `0a4a81f4f164`, chu kỳ `*/2 * * * *`) quét mỗi 2 phút.
  * Khi phát hiện `not is_xiaowei_running()`: Script tự động kích hoạt `cleanup_orphan_xiaowei_adb()` bắn `adb -P 5038 kill-server` (kết hợp CIM fallback).
  * Ngay khi server 5038 bị hạ sát, WinUSB trả tự do các thiết bị, daemon chuẩn port 5037 tự động handshake nhận lại toàn bộ máy về `device` trong 1–2 giây mà không cần reset máy tính hay can thiệp tay.
  * Ngoài ra, `tiktok_runner.py` có Preflight Guard tự động quét sạch port 5038 trước mỗi ca chạy.

## 3. Quy Tắc Đối Soát Hiện Trường Khi Tiểu Vi Báo "Điện thoại đã ngắt kết nối" Hàng Loạt
- Khi người dùng gửi ảnh Tiểu Vi hiển thị 20–30 ô cam (báo mất kết nối M09, M14, M28, M60, M62...):
  1. **Tuyệt đối không kết luận farm bị sập hoặc bắt cắm lại dây:** Kiểm tra ngay socket ADB port 5037 và 5038.
  2. **Quy luật chia rẽ thiết bị:** Danh sách các máy hiện ô cam trên Tiểu Vi trùng khớp 100% với danh sách máy đang bị gán sang daemon port 5038.
  3. **Giải thích rõ ràng, dứt khoát cho User:** Máy tính vẫn nhận đủ 100% phần cứng (`device`), việc hiển thị thiếu trên Tiểu Vi là do timeout socket kết hợp chia rẽ port 5038 khi mở app trong giờ ca cao điểm. Chỉ cần bấm X đóng Tiểu Vi, hệ thống sẽ tự động dọn sạch port 5038 trong vòng 2 phút.
