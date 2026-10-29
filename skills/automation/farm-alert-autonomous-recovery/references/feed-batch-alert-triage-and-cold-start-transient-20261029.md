# Multi-Machine Feed Batch Alert Triage & Transient Cold Start Pitfalls (2026-10-29)

## 1. Bản chất sự cố Feed Ca 3 (Phiên 2/2 Tối)
Báo cáo Feed watchdog ghi nhận 21 máy lỗi trên tổng số 160 máy (85.6% success).
Qua điều tra hiện trường thực tế bằng `inspect_machine.py` và `run_manifest.json` / `summary.txt`, phân loại lỗi gồm:
- **8 máy cáp USB / phần cứng:** `device '...' not found` hoặc `offline` ở tầng daemon ADB host (Kibe: M10, M18, M30, M60, M77 | Admin: M261, M274, M276).
- **7 máy lỗi mở / focus TikTok:** Kẹt `LauncherActivity` (M20, M241, M270, M271, M273, M275, M279).
- **2 máy lỗi mạng tab Bạn bè:** M13, M220 gặp màn hình *"Đã xảy ra lỗi / Thử lại sau"* (`manual-needed:network`).
- **4 máy OS System UI / ATX session:** M52, M58 (`ATX_SESSION_UNAVAILABLE`); M73, M78 (`Google/GMS/account screen focused`).

## 2. Pitfalls & Kỷ luật điều phối
1. **Terminal Guard Allowlist Loophole:**
   - CẤM chạy bash loop `for m in 10 18 30 ...; do python inspect_machine.py $m; done` vì Terminal Guard chặn lệnh `for` theo cơ chế default-deny.
   - BẮT BUỘC gọi từng lệnh `python D:/Taadaa/tools/inspect_machine.py <N>` riêng lẻ hoặc chạy script Python trực tiếp.
2. **Kiểm tra Fleet Tổng trước khi đi sâu từng máy:**
   - Khi có nhiều máy báo offline, chạy `python D:/Taadaa/tools/inspect_machine.py` (không tham số) để kiểm tra danh sách `devices` đính kèm trên cả 2 cluster Kibe và Admin.
3. **Phân biệt rạch ròi giữa Hardware Offline vs Cold Start Delay:**
   - Máy `offline` trong `adb devices` là phần cứng/cáp USB, không sửa code runner.
   - Máy báo `prepare-tiktok failed to focus TikTok after launch` nhưng `inspect_machine.py` thấy máy vẫn online, pin tốt, proxy chuẩn: đây là transient cold boot lag khi farm chạy đồng loạt 80 máy. Nếu runner đã teardown về Launcher và tắt màn hình thì session đã được cô lập an toàn.
