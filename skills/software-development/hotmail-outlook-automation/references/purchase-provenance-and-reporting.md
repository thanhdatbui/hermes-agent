# Purchase provenance và báo cáo Hotmail

## Khi cần xác minh pass mua

1. Tra nguồn mua gốc trước: order artifact/log trong repo, file batch mua, rồi mới đối chiếu workbook.
2. Tìm exact email trước; nếu không thấy, thử username/alias đã chuẩn hóa, tên file và lịch sử Git.
3. Báo trạng thái `PURCHASE_RECORD_FOUND` hoặc `PURCHASE_RECORD_NOT_FOUND`, kèm đường dẫn và số dòng nếu có.
4. Không coi `gmail_clean_v2.xlsx` là bằng chứng pass mua gốc; workbook chỉ phản ánh trạng thái hiện tại.
5. Không in mật khẩu, refresh token hoặc OTP. Nếu live login báo sai pass, kết luận `PASSWORD_UNVERIFIED`; không đoán pass, không tự đổi thông tin.

## Phân biệt bằng chứng

- Graph/refresh token HTTP 200 chỉ chứng minh xác thực Graph hoạt động; không chứng minh TikTok đã phát OTP hoặc pass app Outlook đúng.
- TikTok hiển thị “code sent” chỉ chứng minh UI đã chuyển sang trạng thái gửi; không chứng minh mailbox đã nhận thư.
- Kết quả login app phải được xác minh bằng UI Inbox đúng mailbox, không chỉ dựa vào exit code.

## Báo cáo

- Batch/cron: chỉ liệt kê máy `Success` và `Fail`, kèm mã lỗi ngắn; không dán từng dòng log.
- Target đơn: dùng `Mục đích → Kết quả → Blocker`, tách rõ nguồn mua, workbook hiện tại và live verification.

## Lock và live action

- Nếu user yêu cầu thử lại hoặc đăng nhập mailbox trên máy thật: resolve đúng machine→serial, giữ device lock trong toàn bộ flow, dùng canonical runner, capture trước/sau và chỉ release sau success/final block.
- Không dùng ADB ad-hoc để nhập credential; không ghi credential vào log.
