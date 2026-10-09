# Xử Lý Tránh Vòng Lặp Vô Tận (Infinite Loop) Khi Gặp SMS Checkpoint Trong OAuth Automation

## Bối cảnh & Hiện tượng
Khi chạy automation nạp OAuth (qua Playwright / GPM + S7 pipeline), một số tài khoản Google sau khi điền mật khẩu sẽ bị rơi vào màn hình xác minh số điện thoại:
- URL chứa: `challenge/iap`
- Text nhận diện: "nhập số điện thoại", "tin nhắn văn bản cùng mã xác minh", "số điện thoại để nhận mã".

Pipeline tự động thường cố gắng bấm nút "Thử cách khác" (`Try another way`) để chuyển hướng sang Google Prompt (`challenge/dp`) hoặc TOTP/Mã bảo mật 10 số.

Tuy nhiên:
- Nếu tài khoản không có phương thức dự phòng nào khác được kích hoạt, hoặc Google kiên quyết bắt buộc xác minh số điện thoại, việc bấm "Thử cách khác" sẽ quay vòng lại chính màn hình SMS checkpoint này.
- Khi không có biến đếm số lần bấm (loop counter/attempt cap), script sẽ click liên tục mỗi 4-5s cho đến khi bị timeout (200s+), gây nghẽn worker và lãng phí tài nguyên.

## Quy tắc xử lý chuẩn (Fail-Fast Pattern)

1. **Loop Counter cho `try_another`:**
   - Khởi tạo biến đếm `sms_try_another_count = 0`.
   - Mỗi lần bấm `try_another.first.click()`, tăng biến đếm lên 1.
   - Nếu `sms_try_another_count >= 3` mà màn hình vẫn là `is_phone_challenge`, coi đây là **Hard SMS Checkpoint**.
   - Dừng ngay lập tức (fail-fast), chụp screenshot debug, trả về trạng thái `{"status": "SMS_CHECKPOINT", ...}`.

2. **Dọn dẹp môi trường (Cleanup):**
   - Luôn đảm bảo kill tiến trình Chrome mồ côi nếu worker bị abort hoặc timeout:
     ```bash
     taskkill //F //IM chrome.exe 2>nul || true
     ```
   - Không block slot của các worker khác đang chạy song song.
   - Chú ý: Terminal timeout mặc định là 180s. Nếu pipeline chưa kích hoạt fail-fast nội bộ và lặp lại `Thử cách khác` mỗi 4-30s, tiến trình terminal sẽ bị timeout (exit code 124). Cần đảm bảo script wrapper có timeout per-step hoặc sub-process kill để không để lại process Chrome ngầm.

3. **Ghi nhận & Báo cáo:**
   - Đánh dấu tài khoản bị SMS Checkpoint vào báo cáo / blacklist tạm thời để không retry vô ích trong cùng một batch.
