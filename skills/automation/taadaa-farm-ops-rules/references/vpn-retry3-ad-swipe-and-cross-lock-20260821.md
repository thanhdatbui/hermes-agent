# VPN Fail-Closed, Retry 3 Lần, Ad Swipe Up & Cross-Project Lock Rules (2026-08-21)

## 1. Retry ViChanger GET_IP Broadcast (3 Lần) Tránh False-Positive
- **Hiện tượng**: `tun0` UP và proxy thực tế vẫn hoạt động (traffic internet ra đúng IP proxy), nhưng lệnh broadcast `vn.vichanger.app.GET_IP` bị timeout/delay hoặc trả về không kịp ở lần đầu tiên, khiến script lầm tưởng proxy chết và dừng oan máy.
- **Quy tắc chuẩn hóa (`automation-core/src/automation_core/preflight.py`)**:
  - Broadcast `GET_IP` tối đa **3 lần** (mỗi lần nghỉ 2.0s).
  - Nếu có bất kỳ lần nào trả về `result=200` kèm IP hợp lệ -> Xác nhận VPN An toàn (`ip_verified = True`).
  - Nếu sau 3 lần retry vẫn không có IP hợp lệ -> **BẮT BUỘC DỪNG HẲN MÁY (Fail-Closed)**, tuyệt đối cấm mở TikTok lướt tiếp làm lộ IP thật.

## 2. Quy Tắc Quảng Cáo / Sponsored Card / Overlay (Ưu Tiên Vuốt Lên)
- **Chỉ đạo của User**: "Gặp dạng quảng cáo thế này cứ vuốt qua (lưu rule để sau cứ gặp quảng cáo thì vuốt cho nó qua), đóng chỉ là fallback."
- **Quy tắc thực thi**:
  - Mọi màn hình quảng cáo (Sponsored ad, Brand card, Interactive overlay, Ads feedback survey): **BẮT BUỘC VUỐT LÊN (Swipe Up `540, 1600 -> 540, 400`)** để chuyển sang video tiếp theo.
  - TUYỆT ĐỐI KHÔNG tự chế handler tap nút "Đóng" / "Hủy" / "Tìm hiểu thêm" làm hành động chính. Nút "Đóng" chỉ là fallback cuối cùng khi đã vuốt 2 lần mà không thoát được.
  - Gỡ bỏ điều kiện `after_attempt is None` trong nhánh `unhandled_popup_swipe_recovery` để cơ chế vuốt 2 lần cứu kẹt (`_swipe_recovery_on_stuck`) được kích hoạt đầy đủ.

## 3. Tôn Trọng Device Lock Liên Tiến Trình (Cross-Project Lock Gate)
- Khi một máy đang bị tiến trình khác nắm giữ lock (Botmail, Hotmail login, Gmail reg, TikTok reg... trong `~/.codex/device-locks/machine_<N>.lock.json` với status `running`/`queued`/`recovery`/`failed_locked`):
  - **AI Auto-Recovery và Cron Nuôi Acc BẮT BUỘC DỪNG NGAY LẬP TỨC**, safe-skip máy đó.
  - Tuyệt đối CẤM gửi bất kỳ lệnh ADB nào (như Back, Tap, Swipe, Force-stop) can thiệp vào máy đang chạy flow khác.

## 4. Hành Vi Xem LIVE Tự Nhiên Trước Khi Thoát
- Khi máy vô tình lọt vào phòng TikTok LIVE:
  - Dừng lại xem nội dung tự nhiên **5.0 – 10.0 giây** như người dùng thật.
  - Sau đó mới bấm nút **✕** (`dismiss_tiktok_live_room`) hoặc gửi phím `BACK` để thoát về Feed For You.

## 5. Dọn Dẹp Bytecode Cache Python (`.pyc`) Khi Cập Nhật Code Runner
- Khi sửa code trên live repository mà máy vẫn chạy code cũ: kiểm tra và dọn sạch `__pycache__/*.pyc` để tránh trường hợp Python nạp bytecode cũ trong RAM/Disk.
