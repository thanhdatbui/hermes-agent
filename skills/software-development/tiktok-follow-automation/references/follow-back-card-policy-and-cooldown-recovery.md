# Chính Sách Follow Thẻ Đề Xuất & Trạng Thái Phục Hồi Cooldown (2026-09-14)

## 1. Quy tắc xử lý Thẻ đề xuất follow lại trên Feed (`follow_back_suggestion`)
- **Nick sạch (`is_account_in_follow_cooldown(ctx) == False`):**
  - Cho phép và bấm nút "Follow lại" / "Follow back" / "Theo dõi lại" (detector node) để tạo tương tác tự nhiên bình thường.
- **Nick đang bị phạt nhả follow (`is_account_in_follow_cooldown(ctx) == True`):**
  - BẮT BUỘC bấm "Không quan tâm" (`//node[@text="Không quan tâm" or @resource-id="com.ss.android.ugc.trill:id/cv6"]`) để đóng thẻ.
  - Tuyệt đối CẤM bấm "Follow lại" khi đang dính cooldown để tránh bị TikTok reset streak hoặc gia hạn thời gian giam.

## 2. Thực tế dữ liệu phục hồi Cooldown (192 acc state)
- Cooldown thuần túy theo thời gian (24h, 48h, 4 ngày, 7 ngày) **không tự gỡ được cờ phạt**.
- 100% nick bị phạt ngâm hết cooldown nếu không tích lũy Trust Score (xem video dwell 8-15s, thả tim hợp lệ) khi bấm follow lại sẽ tiếp tục bị drop follow ngay lập tức.
- Phục hồi bắt buộc phải qua chu kỳ warm-up nhẹ (budget thăm dò 3-5 nick) sau khi đã nuôi feed có engagement thật.
