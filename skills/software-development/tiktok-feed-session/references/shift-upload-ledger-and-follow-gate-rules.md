# Quy Tắc Upload Video & Gate Follow Trong Lịch 4 Ca x 2 Phiên (Cập Nhật 12/09/2026)

## 1. Cơ Chế Upload Hook Linh Hoạt Cả 2 Phiên (Case 150 & Case 152)

### Bối cảnh & Vấn đề cũ:
- Trước đây hệ thống chỉ bật upload hook ở phiên cuối ca (`session_index == 2` hoặc trước đó là phiên 3).
- Nhược điểm: Nếu phiên 2 gặp sự cố bất ngờ (mạng lag, proxy từ chối, thiết bị bận, video render muộn) thì tài khoản bị bỏ lỡ toàn bộ ca đăng video ngày hôm đó.

### Quy tắc chuẩn hiện tại:
- **Kích hoạt cả 2 phiên:** Cả Phiên 1 và Phiên 2 trong ca đều được truyền cờ `--allow-upload-hook` (qua `run-feed-session.ps1` và `tiktok_runner.py`).
- **Phiên 1:** Máy lướt feed hoàn tất sẽ tự động kiểm tra và đăng video ngay nếu có video tương ứng với row trong ca.
- **Phiên 2:** 
  - Nếu Phiên 1 đã đăng thành công -> Sổ cái nguyên tử `_ShiftUploadLedger` phát hiện khóa `already_uploaded_in_shift` và Safe-Skip ngay trong 0.1s.
  - Nếu Phiên 1 chưa đăng hoặc đăng thất bại -> Phiên 2 tự động bù đăng sau khi lướt feed.
- **Bảo vệ chống đăng trùng:** `_ShiftUploadLedger` đảm bảo tuyệt đối mỗi tài khoản chỉ có tối đa 1 video đăng thành công trong mỗi ca.

## 2. Gate An Toàn Cho Phép Đi Follow (Case 151)

### Quy tắc chuẩn:
- **Ngưỡng tối thiểu 5 video (`video_count >= 5`):** Chỉ các tài khoản đã đăng tối thiểu 5 video mới được phép kích hoạt follow hook (`_run_follow_hook`).
- **Gỡ bỏ chặn cứng theo Row:** CẤM TUYỆT ĐỐI dùng logic chặn cứng `if row_idx in (3, 4, 5, 6): return skipped "tik{row}-warmup-feed-only"`. Mọi Row (Row 1 đến Row 8), cứ nick nào có >= 5 video là được đi follow.
- **Safe-skip nick mới:** Nick < 5 video (0..4 video hoặc không có số liệu) tự động skip an toàn với lý do `under-5-videos-follow-disabled` để chống nhả follow do nick chưa đủ trust.

## 3. Kỷ Luật Báo Cáo Chốt Phiên Của Watchdog
- Mọi báo cáo chốt phiên (cả Telegram bot và log tổng kết) BẮT BUỘC phải phản ánh đầy đủ cả 3 trụ cột:
  1. **Lướt Feed:** Số máy success, số máy fail / manual-needed / proxy-vpn.
  2. **Đăng Video:** Hiển thị `({phien}/2 - N video đã đăng)`, số máy success, timeout, lỗi script, bỏ qua.
  3. **Follow Chéo:** Số máy success (chia theo dải 10+, 5-9, 1-4 lượt), số máy nhả follow, lỗi script, bỏ qua.
