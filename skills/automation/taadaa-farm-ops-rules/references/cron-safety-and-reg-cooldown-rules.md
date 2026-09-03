# Quy tắc an toàn Bật / Tắt Cron & Cooldown Reg (2026-08-26)

## 1. Cấm Pause Cron khi chạy tay / Recovery
- Mọi cron runner (nuôi acc, feed session, reg đêm) đã tích hợp bộ lọc `device_lock`. Khi một máy đang bị giữ lock (do chạy tay, do recovery, hoặc job khác đang chạy), cron tự động bỏ qua máy đó và chạy tiếp các máy rảnh còn lại.
- **Tuyệt đối KHÔNG pause cron** khi muốn can thiệp tay/recovery trên một vài máy cụ thể.
- Việc pause cron sẽ làm ngừng trệ các cron watchdog an toàn (như `device-locks-watchdog`, `reap-dead-owner-locks`, watchdog kiểm tra tiến độ) khiến các lock quá hạn (TTL 2h) không được giải phóng tự động.

## 2. Cooldown Reg máy (1 lần/ngày/máy)
- **Mỗi máy reg tối đa 1 lần/ngày:**
  - Nếu máy đã đăng ký tài khoản thành công (`SUCCESS`) trong ngày hôm nay, máy sẽ tự động nhận cooldown tới hết ngày (sang ngày hôm sau).
  - Trình quét / lập batch (batch detector) tự động skip các máy đã có status SUCCESS hôm nay.
  - Các trạng thái lỗi (`FAILED`, `STOPPED`) hoặc chưa chạy (`PENDING`) không bị cooldown, có thể chạy lại trong ngày.

## 3. Phạm vi Recovery lỗi
- Khi người vận hành yêu cầu "recovery máy lỗi", chỉ chạy đúng danh sách STT máy/hàng đang gặp sự cố.
- Tuyệt đối không tự ý mở rộng phạm vi (scope drift) thành toàn bộ các máy pending trong đợt.
