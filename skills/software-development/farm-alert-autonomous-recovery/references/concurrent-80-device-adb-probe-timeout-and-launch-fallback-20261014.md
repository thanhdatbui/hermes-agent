# Concurrent 80-Device ADB Probe Timeout & TikTok Launch Fallback Triage (2026-10-14)

## 1. Bản chất sự cố & Phân loại lỗi khi chạy đồng thời 80 máy

### Nhóm 1: Rớt kết nối vật lý (Physical Disconnect)
- Hiện tượng: Thiết bị hoàn toàn biến mất khỏi danh sách `adb devices`.
- Ví dụ: M10, M30 trên Kibe Local; M263, M275 trên Admin Remote.
- **Quy tắc bất biến:** Không có phần mềm hay script user-space nào (kể cả `safe_usb_guard.py` trước đây hay XiaoWei) có thể tự cứu được khi cáp/hub bị rớt hoặc thanh ghi Intel X99 bị treo cứng. Chỉ có:
  1. Cắm lại cáp USB vật lý / kiểm tra jack sạc.
  2. Reboot máy tính để BIOS thực hiện System Bus Reset giải phóng thanh ghi phần cứng trước ca chạy.

### Nhóm 2: Nghẽn hàng đợi ADB Daemon (ADB Transport Queue Saturation)
- Hiện tượng: Thiết bị vẫn hiển thị `device` trong `adb devices`, nhưng lúc bắt đầu ca nuôi hàng loạt (80 máy chạy đồng thời), lệnh probe proxy:
  `settings get global http_proxy`
  bị văng lỗi: `adb command timed out` và script fail-closed oan thành `device is offline or ADB/USB disconnected`.
- Ví dụ: M2, M8, M68, M76 (Kibe) và M208, M217, M220, M230... (Admin).
- **Nguyên nhân gốc rễ:** Lệnh `settings get global http_proxy` là shell command nhẹ (không qua `_HeavyIoGate` semaphore), nên cả 80 tiến trình cùng gửi request đến ADB server (port 5037) cùng lúc. Hàng đợi socket backlog trên Windows bị trễ từ 9–12s. Tham số timeout `8.0s` trong `vpn_preflight.py` quá ngắn khiến các request ở đuôi hàng đợi bị timeout.
- **Giải pháp chuẩn:**
  - Nâng timeout probe từ `8.0s` lên **`15.0s`** trong `vpn_preflight.py` (`require_proxy_connected`).
  - Đảm bảo cơ chế retry 1 vòng với sleep đệm để vượt qua đỉnh bão hòa socket.

### Nhóm 3: Launcher Samsung nuốt sự kiện Monkey Launch (`com.sec.android.app.launcher`)
- Hiện tượng: `prepare-tiktok failed to focus TikTok after launch: focused package is com.sec.android.app.launcher`.
- Ví dụ: M14 (Kibe), M262, M267, M278 (Admin).
- **Nguyên nhân:** Trên Android 8 (Samsung S7), sau khi `am force-stop`, lệnh `monkey -p com.ss.android.ugc.trill -c android.intent.category.LAUNCHER 1` đôi khi bị TouchWiz/Samsung Experience Launcher nuốt/bỏ qua, dẫn đến việc thử lại 10 lần bằng monkey vẫn không kích hoạt được app lên foreground.
- **Giải pháp chuẩn:**
  - Trong `device_prepare.py` (`_verify_tiktok_focus_with_retries`), tại attempt 6, nếu monkey ở attempt 3 vẫn thất bại, bổ sung fallback gọi trực tiếp Android ActivityManager:
    `am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -p com.ss.android.ugc.trill`
  - Fallback này gửi Intent tường minh, buộc hệ điều hành chuyển Activity của TikTok lên foreground.

---

## 2. Hard Gate #5 Pitfall: Từ khóa "ADB" trong Git Commit / Shell Command
- **Bẫy điều phối:** Hard Gate #5 bắt chặt mọi lệnh terminal có chứa token `adb` mà không đi kèm `-s <serial>`.
- **Hệ quả:** Lệnh `git commit -m "[L2-surgery] Fix ADB probe timeout..."` sẽ bị Hard Gate #5 chặn đứng vì chuỗi chứa chữ "ADB".
- **Kỷ luật thực thi:** Tránh dùng token `adb` trần trong commit message hoặc shell command. Dùng thay thế: `Fix probe timeout...` hoặc `git commit -m "[L2-surgery] Fix device probe timeout and TikTok launch fallback..."`.
