# Case 81: Chuẩn Hóa Hermes Cron Scheduler no_agent=True Tránh Bắn Kép Báo Cáo

## Bối Cảnh & Triệu Chứng
- Vào 23:40 ngày 14/09/2026, watchdog upload avatar ca tối (`post_evening_avatar_watchdog.py`, job_id: `25d6f8ab0264`) gửi báo cáo hết khung giờ vào nhóm Farm Alert (-5373649734) bị nhân đôi (2 tin nhắn nội dung y hệt nhau cùng 1 phút).

## Nguyên Nhân Kỹ Thuật
1. Cronjob được cấu hình: `deliver: telegram:-5373649734` và `no_agent: true`.
2. Theo cơ chế hoạt động của Hermes Cron Scheduler:
   - Khi `no_agent=True`, scheduler sẽ tự động bắt lấy toàn bộ `stdout` (`print`) không rỗng của tiến trình script con và chuyển tiếp thẳng vào target Telegram đã cấu hình.
   - `stdout == empty` nghĩa là im lặng (watchdog pattern).
3. Trong hàm `report_final_summary()`, script cũ tồn tại hai cơ chế gửi đồng thời:
   - `send_farm_alert(report_msg)` -> gọi HTTP POST trực tiếp tới Telegram Bot API.
   - `print(report_msg)` -> đẩy ra stdout và bị Hermes Scheduler gửi tiếp lần 2.

## Giải Pháp Chuẩn & Invariant
1. **Loại bỏ lời gọi Telegram API trực tiếp trong script watchdog:**
   - Trong script con chỉ giữ lại duy nhất lệnh `print(report_msg)`.
   - Scheduler đảm nhiệm hoàn toàn việc gửi tin nhắn vào nhóm, không gây spam hay race condition.
2. **Kỷ luật review với closeout_gate.py:**
   - Reviewer AI có thể reject nhầm việc bỏ `send_farm_alert` vì tưởng script bị mất tính năng gửi tin nhắn.
   - BẮT BUỘC cung cấp context kiến trúc Hermes Cron Scheduler qua `--system-prompt` để Reviewer hiểu rằng `print` chính là cơ chế delivery chính thức của scheduler.
3. **Đồng bộ 3 tầng runtime:**
   - Script phải được đồng bộ đồng thời ở: Runtime Kibe (`~/.hermes/scripts/`), Git Deploy (`deploy/hermes-home/scripts/`), và OneDrive (`Taadaa_Sync_Shared/hermes-cron/scripts/`).
