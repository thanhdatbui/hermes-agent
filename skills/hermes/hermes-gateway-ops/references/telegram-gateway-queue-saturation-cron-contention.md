# Telegram Gateway Queue Saturation & Long-Running Cron Contention

## Triệu chứng
Người dùng nhắn tin vào các topic Telegram lúc 11h nhưng mãi đến 12h29 không có session nào phản hồi, sau đó hàng loạt câu trả lời đồng loạt xuất hiện cùng lúc.

## Căn nguyên
Khi nhiều cronjob lớn chạy song song (ví dụ cronjob lifecycle healer 55 turns, chatgpt pool 86 turns, audit watchdog toàn farm 1268 nick), Gateway bị quá tải hàng đợi (Queue Saturation).
Các tin nhắn mới từ người dùng bị dồn vào hàng đợi (message queue) và chỉ được xử lý khi các chu kỳ cronjob xả xong.

## Biện pháp xử lý & Phòng tránh
1. Không lầm tưởng là Gateway bị chết hoặc tự ý kích hoạt restart Gateway.
2. Kiểm tra log khởi động `%LOCALAPPDATA%\hermes\gateway-starts.log` để xác thực thời điểm start thật của Gateway.
3. Giới hạn số turn / ngân sách cho các cronjob định kỳ để tránh độc chiếm connection pool tới model provider.
