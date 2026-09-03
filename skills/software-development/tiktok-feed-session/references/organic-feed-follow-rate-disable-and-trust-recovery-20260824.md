# Vô Hiệu Hóa Follow Hữu Cơ Khi Lướt Feed & Chiến Lược Hồi Phục Trust Score (2026-08-24)

## 1. Bối cảnh & Nguyên nhân nhả Follow hàng loạt
- **Triệu chứng:** Sau 3 ngày tạm nghỉ follow chéo, khi test thử follow trên một số tài khoản Row 1 thì TikTok vẫn tự động nhả (drop) follow sau vài phút hoặc không ghi nhận lượt follow trên profile tác giả.
- **Bản chất kỹ thuật của TikTok Trust Score & Action Limit:**
  - Thuật toán chống bot của TikTok gắn cờ phạt ngầm (*shadow action penalty / follow ban*) trên tài khoản có trust score thấp (tài khoản mới reg, ít video, hoặc có hành vi search & follow chéo dồn dập).
  - Khung thời gian phạt thường kéo dài **5 – 7 ngày** tính từ lần bị nhả / fail gần nhất.
  - **Quy tắc reset Cooldown:** Mỗi lần người vận hành bấm follow thử nghiệm mà bị nhả, hệ thống an ninh của TikTok coi đó là hành vi tiếp tục vi phạm và **tự động reset chu kỳ phạt 5-7 ngày lại từ đầu**.

## 2. Giải pháp kỹ thuật đã triển khai trong code
1. **Tắt hoàn toàn Organic Follow trên Feed (`feed_swipe_smoke.py`):**
   - Đưa `DEFAULT_FEED_FOLLOW_RATES` về 0% trên tất cả các feed:
     ```python
     DEFAULT_FEED_FOLLOW_RATES = {
         FEED_TYPE_FOR_YOU: 0,
         FEED_TYPE_FOLLOWING: 0,
         FEED_TYPE_FRIENDS: 0,
     }
     ```
   - Hàm `_maybe_follow_video()` tự động trả về `False`, đảm bảo trong quá trình lướt 8–11 video/phiên máy tuyệt đối không bấm nút Follow của bất kỳ video nào.
2. **Tắt hoàn toàn Follow Hook (`multi_machine_feed_session.py`):**
   - Khóa 100% `_run_follow_hook` trên mọi Row (Row 1, 2, 3+), máy hoàn thành phiên nuôi chỉ ghi nhận `status: skipped` với lý do `follow-disabled-by-operator`.
3. **Giữ nguyên hành vi Like (Thả tim):**
   - Tỷ lệ like nhẹ (1-2 video/phiên) được giữ nguyên vì hành vi thả tim không bị cấm/nhả và giúp tạo tín hiệu người dùng thật xem video tự nhiên.

## 3. Quy trình vận hành hồi phục Trust và Test an toàn
- **Giai đoạn nghỉ (3–4 ngày tiếp theo):**
  - Giữ nguyên trạng thái tắt follow 100%.
  - Bắt buộc duy trì đăng video đều (đạt tối thiểu **≥ 3 – 5 video/nick**) kết hợp nuôi feed hàng ngày. Nick có video và có view tự nhiên thì TikTok mới dần gỡ cờ phạt.
- **Giai đoạn Test lại (sau mốc 7 ngày):**
  - Chỉ chọn duy nhất **1 máy** làm mẫu.
  - Bấm thử **1 – 2 lượt follow** từ video Đề xuất (For You), kiểm tra sau 15–30 phút.
  - Nếu giữ follow: Mở lại follow dần từng ca (1 ca/ngày, tối đa 3-5 follow/nick/ca).
  - Nếu vẫn nhả: Dừng ngay lập tức, không test lan sang máy khác để tránh bị reset cooldown toàn farm.
