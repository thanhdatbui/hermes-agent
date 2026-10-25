# Follow Anchor Trap & Streak Inflation Invariants

## Bối Cảnh Sự Cố & Chẩn Đoán (2026-10-25)
Trong hệ thống `tiktok-follow` (Mode 2 follow followers), có 97 nick bị kẹt `fail_streak >= 3` với cooldown bị giam 7 đến 15 ngày. Khảo sát đối soát 466 nick và log hiện trường (điển hình Row 4 ngày 2026-10-24: 32/32 máy fail cùng 1 lý do):
1. **Phía TikTok:** TikTok thật sự từ chối lượt follow (silent-drop/rate limit), được kiểm chứng khách quan bằng WinRT OCR và Path B re-entry.
2. **Phía Script:** Có 2 lỗi cơ chế logic nghiêm trọng biến một cú nhả bình thường thành vòng lặp án tù vô tận (Infinite Prison Loop):

---

### 1. Cạm Bẫy "Bắt Buộc Follow Anchor" (`_ensure_anchor_followed`)
- **Vấn đề:** Trong Mode 2 (`follow_runner/flows/mode2_follow_followers.py`), script yêu cầu nick phải bấm Follow Anchor (nick Tik 1/Tik 2 làm gốc) trước rồi mới được mở danh sách Following của Anchor để đi chéo.
- **Thực tế:** Trên ứng dụng TikTok, danh sách Following của tài khoản công khai hoàn toàn có thể mở và đọc mà **không cần phải follow tài khoản đó**.
- **Hậu quả:** 
  - Nick cựu binh (Row 1) đã follow Anchor từ nhiều tháng trước -> `classification == "followed"` -> bỏ qua kiểm tra và chạy an toàn.
  - Nick non (Row 2, 3, 4, 5, 6) hoặc nick vừa ra tù -> Bắt buộc bấm Anchor -> Bị TikTok chặn lượt bấm đầu tiên -> Script phán quyết ngay `state.set_follow_failed()` và hủy toàn bộ phiên chạy! Nick hoàn toàn không có cơ hội đi chéo cho bất kỳ nick con nào khác trong list.

---

### 2. Nghịch Lý Tính Streak Khi `used == 0` (`follow_state.py`)
- **Vấn đề:** Trong `FollowState.set_follow_failed()`:
  - Nếu `used > 0` (nick đã follow được ít nhất 1 người rồi mới bị nhả) -> Giữ nguyên streak (`streak = max(1, curr_streak)`).
  - Nếu `used == 0` (nick vừa thả ra, vấp ngay phát đầu tiên ở Anchor khi chưa follow được ai) -> Lại tăng vọt streak (`streak = min(10, curr_streak + 1)`).
- **Hậu quả:**
  - Cứ mỗi lần hết hạn cooldown thả ra -> Lại đâm đầu vào Anchor -> Lại vấp khi `used == 0` -> Streak tăng lũy tiến từ 1 -> 2 -> 3 -> 4 (cooldown 3d -> 5d -> 7d -> 15d).
  - Toàn bộ dàn nick trẻ bị đóng băng liên tục trong cữ phạt 15–19 ngày.

---

### 3. Quy Tắc Thiết Kế Tránh Bẫy Anchor & Lạm Phát Streak (Invariants)
1. **Không chặn Gateway:** Thất bại khi tương tác với Anchor (nick gốc) không được coi là lỗi vi phạm spam của tài khoản. Chỉ bỏ qua Anchor đó hoặc chuyển sang Anchor khác / Mode 1.
2. **Cấm tăng streak khi `used == 0` do lỗi Anchor:** `fail_streak` chỉ được phép tăng khi nick đã vào danh sách mục tiêu thực tế và bị server TikTok từ chối nhiều lần trong chuỗi hành động hợp lệ.
3. **Decouple Anchor Following:** Luôn ưu tiên mở thẳng tab Following của Anchor mà không ép nick phải thực hiện hành động follow Anchor trước.

---

### 4. Quy Luật Bất Biến Về Tính Streak & Cooldown (Chốt Phiên 2026-10-25)
* **Éo follow được cái nào (`used == 0`): MỚI TÍNH LÀ STREAK LEO THANG:**
  - Vừa vào bấm phát đầu tiên đã bị từ chối ngay -> Nick đang bị TikTok gắn cờ chặn cứng ở mức 0.
  - Lúc này mới được tính là tái phạm fail streak:
    - **Streak 1 (Nhả lần đầu): CHỈ PHẠT 24H (1 NGÀY)** để xả cache! Tuyệt đối CẤM phạt 3 ngày.
    - **Streak 2 (Tái phạm lần 2):** Nghỉ 5 ngày.
    - **Streak 3 (Tái phạm lần 3):** Nghỉ 7 ngày.
    - **Streak >= 4 (Tái phạm dai dẳng):** Nghỉ 15 ngày (giam cách ly kiểm điểm).
* **Đã follow được ít nhất 1 cái (`used >= 1`): KHÔNG ĐƯỢC TÍNH ĐI TÙ:**
  - Nick đã chứng minh được năng lực bấm ăn và server TikTok đã nhận follow thật (1, 2, hay 5 cái). Việc đứt ở lượt sau thuần túy là **chạm trần phiên trong ngày (Ceiling Reached)**, KHÔNG PHẢI nick bị spam hay bị phế.
  - **Quy tắc bắt buộc:**
    1. `fail_streak = 0`: Xóa sạch chuỗi phạt, cấm leo thang streak.
    2. Bảo toàn hoàn toàn `is_graduated` và `probation_clean_days` (không tước cờ, không xóa công trạng tích lũy).
    3. Cooldown chỉ đúng **24 giờ** (`now_utc + 24 hours`), không giam phạt nhiều ngày.

### 5. Kỷ Luật Dispatch Worker & Phục Hồi Cooldown
* **Worker Governance:** Khi user cấu hình hoặc chỉ định Sol Worker (qua :20129), Coordinator BẮT BUỘC tôn trọng Sol Worker. CẤM TUYỆT ĐỐI tự ý đề xuất, hối thúc hay chuyển sang Claude Worker khi user không yêu cầu đích danh (Claude 100% On-Demand).
* **Xả án Streak 1:** Bất kỳ đợt nhả lần đầu nào dính Streak 1 chỉ nhận cooldown 24h từ thời điểm fail, hết 24h tự động unblock mở cữ chạy tiếp theo.

---

### 5. Khóa Đồng Bộ Đa Repo (Cross-Repo Sync Contract)
1. **Tại `tiktok-follow` (`follow_runner/core/follow_state.py`):**
   - Trong `set_follow_failed()`: Khi `used > 0`, ép `streak = 0`, không pop `graduated`/`probation_clean_days`, đặt `cooldown_until_local = (now_utc + 24h).astimezone(tz)`.
2. **Tại `tiktok-luot nuoi acc` (`python_runner/flows/multi_machine_feed_session.py`):**
   - Trong `_is_account_follow_cooldown()`: Tôn trọng tuyệt đối `cooldown_until_at` / `cooldown_until_date` từ state. Khi `fail_streak == 0`, `streak_days = 0`, cho phép nick đi follow ngay khi hết mốc 24h thay vì tự ý ép phạt 3/5/7 ngày.
3. **Tại Dashboard (`D:/Taadaa/tools/follow_health_helper.py`):**
   - Đối chiếu trực tiếp `cooldown_until_at` với `now` để phân loại trạng thái Cooldown; cấm dùng cờ `follow_failed` đơn thuần làm tiêu chí ném nick vào `🔴 Cooldown`.
4. **Xả án tồn dư (`D:/Taadaa/tools/reconcile_unfair_streaks.py`):**
   - Quét các file state thuộc diện `A_CEILING_DROP` (có `used >= 1` trong ngày fail) để đưa về `fail_streak = 0`, gỡ `cooldown_until_date`, phục hồi quyền tham gia cữ chạy tiếp theo.
