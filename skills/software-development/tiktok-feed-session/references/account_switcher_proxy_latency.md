# Case 139: Polling Verification Sau Account Switch Qua Proxy Farm

## 1. Hiện Tượng & Nguyên Nhân Gốc Rễ
- **Hiện tượng:** Máy dừng phiên với lỗi `profile username still mismatched after switch` dù đã tap đúng dòng tài khoản trong switcher.
- **Bản chất kỹ thuật:**
  - Qua proxy farm (192.168.110.2:20008), TikTok mất 6–10s để tải dữ liệu và reload UI Profile tài khoản mới.
  - Cơ chế cũ chỉ sleep 4.5–6.0s rồi chụp XML đọc profile đúng 1 lần duy nhất (single-shot verification).
  - Tại giây thứ 5, UI vẫn hiển thị nick cũ. Runner coi attempt 1 thất bại và vội vàng tap lại switcher (attempt 2), làm gián đoạn và hỏng quá trình reload của TikTok.

## 2. Anti-Pattern Cần Tránh
- **Single-shot Verify Thiếu Polling:** Đọc XML profile 1 lần duy nhất sau sleep ngắn cố định, không tính đến độ trễ mạng của proxy farm.
- **Re-tap Switcher Khi Đang Reload:** Tap lại switcher khi app đang nạp nick mới dẫn tới kẹt state hoặc văng modal.
- **Override Bounds Sang Non-Clickable Child View:** Ép toạ độ tap sang inner `TextView` ($x \approx 393$, `clickable="false"`) thay vì container `Button` full-width ($x=540$, `clickable="true"`).

## 3. Quy Tắc Chuẩn (Best Practice Pattern)
1. **Polling Verification Loop:**
   - Trong `verify_and_switch_profile` (`feed_swipe_smoke.py`), bọc bước verify bằng vòng lặp `max_verify_polls = 3` (mỗi lần poll cách nhau 2.0s).
   - Tổng thời gian chờ có thể lên tới 8.5–10.0s, đủ cho proxy farm tải xong profile.
   - Khi verify thành công ở `poll_idx > 1`, ghi log `verify_profile_after_switch_polled` và break ngay.
2. **Container Target Bounds:**
   - Giữ nguyên toạ độ tâm của container `Button` có `clickable="true"` ($x=540$), không tap vào child view không clickable.
3. **Verification Sau Vá:**
   - Compile kiểm tra cú pháp: `python -m py_compile python_runner/flows/feed_swipe_smoke.py`.
   - Unit tests: `PYTHONPATH="D:/Taadaa/tiktok-luot nuoi acc/python_runner" pytest python_runner/tests/test_account_switcher.py`.
   - Live Canary trên Máy 8: `powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines 8 -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run`.
