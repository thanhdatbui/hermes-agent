# Follow Hook Two-Tier Feed Gating & Warm-up Strategy (2026-09-05)

## 1. Bối cảnh & Vấn đề thực tế
Trước đây, trong `python_runner/flows/multi_machine_feed_session.py`, hàm `_run_follow_hook` yêu cầu phiên feed phải hoàn thành trọn vẹn 100% (`final_status ∈ {success, degraded}`) hoặc chỉ fail do chạm giới hạn swipe/thời lượng.
- **Hệ quả tiêu cực:** Nếu một máy lướt được 7/8 video rồi gặp popup/lỗi UI nhỏ ở video cuối, phiên feed bị gán `failed`/`manual-needed`. Khi đó, bước follow chéo bị **bỏ qua hoàn toàn**, gây mất oan phiên follow của ca nuôi dù tài khoản thực tế đã có lượng lớn watch time và scroll events.
- **Nguy cơ của Cold Follow:** Nếu bỏ hoàn toàn điều kiện lướt feed mà nhảy thẳng vào tìm kiếm profile để follow, TikTok sẽ phát hiện telemetry bất thường (mở app lên không xem nội dung gì đã đi follow dồn dập) dẫn đến bot check, CAPTCHA hoặc nhả follow sau 3-5 phút.

## 2. Chiến lược Gating 2 Tầng (Two-Tier Warm-up Gating)
Kết hợp đồng thời 2 điều kiện cứu phiên follow mà vẫn bảo toàn trust score:

### Tầng 1: Warm-up tối thiểu trong phiên (≥ 3 video swipes)
- Nếu phiên lướt feed hiện tại hoàn thành **tối thiểu 3 video** (`total_swipes_completed >= 3`), session đã có đủ watch-delay và scroll telemetry cơ bản để coi là "ấm".
- Cho phép tiếp tục chuyển sang bước follow hook kể cả khi flow lướt feed dừng sớm hoặc gặp lỗi vặt ở cuối phiên, miễn là không dính các lỗi bảo mật/tài khoản nặng.

### Tầng 2: Kế thừa trust session trong cùng Ca (Shift Session Trust)
- Một ca nuôi gồm 3 phiên liên tiếp (ví dụ Ca Sáng Row 1-2 có Phiên 1 lúc 06:00, Phiên 2 lúc 07:30, Phiên 3 lúc 09:00).
- Nếu nick/máy này **đã có ít nhất 1 phiên lướt feed thành công trọn vẹn (`status: success`) trước đó trong cùng ca hôm nay**, tài khoản đã được warm-up bài bản trong ngày.
- Ở các phiên sau trong ca (Phiên 2, 3), nếu bước lướt feed gặp sự cố ngay từ đầu (chưa đủ 3 video), hệ thống vẫn kiểm tra lịch sử ca: nếu ca này đã có session pass, vẫn cho phép tài khoản tiếp tục chạy follow hook.

## 3. Các Bất Biến An Toàn Không Được Phép Nới Lỏng
1. **Video Gate ≥ 5:** Nick bắt buộc phải có tối thiểu 5 video đã đăng trên kênh (`video_count >= 5`). Dưới 5 video tuyệt đối cấm đi follow chéo vì trust profile chưa đạt ngưỡng.
2. **Sensitive Account Blockers:** Tuyệt đối không chạy follow nếu phiên feed dừng do lỗi tài khoản nghiêm trọng: `banned`, `suspended`, `logged_out`, `checkpoint`, `login`, `captcha`, `account-update-prompt`.
3. **Follow Cooldown:** Tôn trọng trạng thái cooldown nhả follow (`follow-released-daily-cooldown`) của riêng từng nick trên thiết bị.
