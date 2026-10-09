# Recovery live Máy 40: preflight, credential và completion gate

## Bài học tổng quát
Recovery live qua ADB/cron không được coi là hoàn tất theo status của worker. Worker có thể timeout ở 600s trong khi thiết bị vẫn đang awake hoặc flow đã dừng giữa chừng.

## Preflight bắt buộc
1. Chạy `python D:/Taadaa/tools/inspect_machine.py <N>` và ghi lại serial, focus, screen, pin.
2. Kiểm tra device lock và process owner trước khi chiếm máy; không suy luận “rảnh” từ việc cron không báo lỗi.
3. Kiểm tra proxy đúng host/port theo runtime knowledge.
4. Kiểm tra ATX-agent/UI path trước flow; ưu tiên endpoint 7912 nếu đã provisioned.
5. Với Hotmail Graph, export `HOTMAIL_TOKEN_LIST` **trước khi import** `hotmail_provider`/`social_reg_v1`; sau đó kiểm tra `resolve_graph_credentials`, refresh-token exchange và đọc OTP thử bằng provider. Token tồn tại trong file nhưng env chưa được truyền không phải là credential đã sẵn sàng.

## Recovery path
- Passwordless TikTok: dùng email + OTP/reset flow, không thử password placeholder nhiều lần.
- Nếu mailbox có Graph token, đọc OTP trên PC; không mở Outlook trên thiết bị.
- Form “Đặt lại mật khẩu” có câu “mã xác minh” nhưng ô nhập vẫn là email: điền email và bấm Tiếp tục trước, chỉ chuyển sang OTP khi UI có dấu hiệu nhập mã thật.

## Completion gate
Chỉ báo `VERIFIED_SUCCESS` khi đủ cả:
- Flag thành công của recovery tồn tại.
- Có ảnh nghiệm thu thành công mới nhất và kiểm tra được nội dung.
- Đối soát nick/2FA/pass trong nguồn dữ liệu chính nếu workflow yêu cầu.
- Chạy lại `inspect_machine.py <N>` sau cleanup: máy về HOME, màn hình/power state đúng và không còn process owner bất thường.

Nếu worker timeout, không báo “đã xong”. Thu thập artifact mới nhất, inspect máy, xác định `FINAL_BLOCKED` hoặc chạy recovery lại theo contract mới; không retry mù prompt cũ.
