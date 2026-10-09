# Quy Chuẩn Tần Suất Watchdog & Nguyên Tắc Báo Cáo Cuốn Chiếu Farm

## 1. Tần Suất Báo Cáo Định Kỳ Giám Sát (Download / Render / Feed)
- Đối với các tiến trình nền chạy dài (Download video gốc, Render video Tik1..Tik8, Nuôi nick):
  - **Tần suất chuẩn: 1 tiếng báo 1 lần** (Cron expr: `0 * * * *`).
  - Tuyệt đối không đặt lịch dày 5-15 phút gây spam nhóm Telegram Farm Alert (`-5373649734`).
  - Giữ báo cáo súc tích, chỉ in thông số thay đổi quan trọng và tổng số clip đạt chuẩn.

## 2. Nguyên Tắc Báo Cáo Của Watchdog Cuốn Chiếu (Retry Batches - Avatar / 2FA / Login)
- Các watchdog cuốn chiếu sau ca (ví dụ: `post_evening_avatar_watchdog`, `post_noon_chain_watchdog`, `post_morning_gmail_2fa_watchdog`):
  - **Hoàn toàn im lặng khi kích hoạt batch**: Không gửi tin nhắn khởi động.
  - **Chỉ gửi duy nhất 1 báo cáo khi MỘT ĐỢT (BATCH) CHẠY XONG**: Sau khi toàn bộ các máy trong đợt đó đã hoàn tất hoặc timeout (thường từ 35-45 phút).
  - **Trường hợp gửi nhiều báo cáo cách nhau 30-45 phút**:
    + Đây là kết quả của các đợt chạy độc lập liên tiếp nhau khi đợt trước còn máy thất bại và hệ thống tự động retry đợt tiếp theo.
    + Không phải là 1 đợt chạy gửi báo cáo nhiều lần.
  - **Giải thích cho User khi có thắc mắc**:
    + Nêu rõ thời lượng thực tế của từng đợt (ví dụ: Đợt 1 chạy 36p lúc 21:34 -> 22:10 xong báo cáo; Đợt 2 chạy 40p lúc 22:11 -> 22:50 xong báo cáo).
    + Khẳng định hệ thống đang tuân thủ đúng nguyên tắc: "Chỉ báo 1 lần khi mỗi đợt chạy xong", cung cấp số liệu tăng trưởng giữa các đợt để user an tâm.
