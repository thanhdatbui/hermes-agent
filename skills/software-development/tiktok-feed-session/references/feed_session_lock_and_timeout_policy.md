# Quy tắc Device Lock & Timeout Farm Nuôi Acc TikTok

## 1. Per-device Timeout (Thời gian tối đa 1 máy)
- `DEFAULT_DEVICE_TIMEOUT_SECONDS = 1500.0` (25 phút/máy).
- Mục đích: Đảm bảo khi mạng chậm, video tải lâu hoặc qua nhiều bước chụp XML và dismiss popup, phiên lướt vẫn đủ thời gian hoàn thành đủ 15 swipe mà không bị dừng ngang bởi watchdog deadline (`RunPlanDeadlineExceeded`).

## 2. Blocked Lock TTL 2 Giờ (Tự động hết hạn)
- `DEFAULT_BLOCKED_LOCK_MAX_AGE_SECONDS = 7200.0` (2 giờ).
- Khi máy gặp lỗi (mất focus, vướng popup chưa nhận diện, timeout), script chuyển lock sang trạng thái `blocked` để giữ hiện trường.
- Lock này **chỉ được giữ tối đa trong 2 giờ** để người vận hành / Hermes Agent kiểm tra và xử lý.
- Sau 2 giờ, nếu không có can thiệp thủ công, cơ chế đánh giá handoff tự động coi lock đó đã hết hạn (`expired`), cho phép các lượt nuôi acc / batch tiếp theo chạy bình thường, tránh tình trạng hàng loạt máy bị kẹt `skipped-device-locked` vĩnh viễn.

## 3. Quy tắc Lock Vĩnh Viễn
- **CHỈ KHI** user yêu cầu lock trực tiếp bằng lệnh thủ công (manual command) thì mới được giữ lock vĩnh viễn không timeout.
- Mọi lỗi phát sinh trong quá trình chạy tự động (cron / batch) đều tuân thủ TTL 2 giờ.
