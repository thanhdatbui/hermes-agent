# Inter-Session Device Lock Contention & Safe Window Gating (2026-10-19)

## 1. Hiện Tượng Thực Tế
- **Sự cố:** Ca 2 Phiên 1 (Row 3) chạy 80 máy kết thúc trễ lúc `13:56:37`. Phiên 2 khởi chạy lúc `14:02:00`.
- Trong khe hở 5 phút giữa 2 phiên, tiến trình feed runner của P1 đã kết thúc, tiến trình P2 chưa kịp mở.
- Watchdog phụ trợ `tiktok-rolling-rename-watchdog` (chạy định kỳ mỗi 15p) thăm dò và chỉ kiểm tra `is_feed_active()`. Do không thấy tiến trình feed nào đang chạy trong OS process list, script kết luận farm đang rảnh hoàn toàn và lập tức chiếm `device-locks` trên 11 máy (M2, M3, M4, M7, M9, M13, M15, M20, M23, M26, M27).
- Lúc 14:02:00, Phiên 2 bắt đầu quét 80 máy thì gặp 11 máy trên đang bị khóa bởi `project=tiktok-rename` (`do_rename_canonical_runner.py`). Theo cơ chế fail-safe, runner bỏ qua (`skipped-device-locked: 11`) làm mất cữ lướt feed và follow của 11 máy ở Phiên 2.

## 2. Gốc Rễ Kỹ Thuật: Cạm Bẫy Process Liveness != Farm Idle
- **Lỗi ngụy biện trạng thái:** Khoảng nghỉ giữa Phiên 1 và Phiên 2 của một Ca (khoảng 5 - 45 phút) là **khe hở nội bộ của Ca nuôi**, các máy vẫn đang trong chu kỳ tương tác của Ca đó.
- Nếu watchdog phụ chỉ kiểm tra `psutil.process_iter` (`is_feed_active()`), khi P1 vừa tắt thì process list hoàn toàn trống -> watchdog phụ nhảy vào cướp lock -> P2 đến lượt chạy sẽ bị thiếu máy.

## 3. Quy Chuẩn Khắc Phục Bắt Buộc (Time-Window Gate + Process Gate)
Mọi watchdog phụ trợ (đổi tên, nạp nick, dọn dẹp nhẹ) BẮT BUỘC phải có **Chốt chặn 2 tầng**:

### Tầng 1: Time-Window Gate (`is_safe_window()`)
Khóa cứng theo đồng hồ múi giờ HCM (`ZoneInfo("Asia/Ho_Chi_Minh")`). TUYỆT ĐỐI CẤM chạy trong các Ca nuôi và trong khe giữa P1 - P2. CHỈ ĐƯỢC PHÉP CHẠY trong 3 khung giờ rảnh thực sự giữa các Ca:
- **Khung Sáng:** `09:30` <= now < `11:20` (sau Ca 1, trước Ca 2)
- **Khung Chiều:** `15:30` <= now < `17:20` (sau Ca 2, trước Ca 3)
- **Khung Tối / Đêm:** `21:30` <= now < `23:45` (sau Ca 3, trước Ca 4)
*Lưu ý:* Tránh các mốc Reboot tự động của Farm (`05:20`, `11:20`, `17:20`) và giờ dọn cache đêm (`04:00`).

### Tầng 2: Process Gate Mở Rộng (`is_feed_active()`)
Quét toàn diện các biến thể tiến trình nuôi/follow:
```python
any(k in cmd for k in ("multi-machine-feed-session", "multi_machine_feed_session", "run-feed-session.ps1", "run_tiktok.py", "run_follow"))
```
Nếu ca nuôi bị kéo dài quá khung (vd Ca 2 kéo sang 15:40), watchdog vẫn nhường đường không chiếm lock.

### Tầng 3: Cờ Bỏ Qua Kiểm Tra (`--force`)
Hỗ trợ cờ `--force` qua `argparse.ArgumentParser.parse_known_args()` để cho phép kiểm thử thủ công/canary khi cần.
