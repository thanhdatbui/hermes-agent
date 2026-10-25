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

### 4. Quy Luật Bất Biến Về Tính Streak & Cooldown (Chốt Chuẩn Hóa 2026-10-25)

#### A. Thang Cooldown Chuẩn Toàn Farm:
- **`Streak 0`:** Nick hoàn toàn sạch, đang chạy khỏe bình thường, không dính án, không cooldown.
- **`Streak 1` (Nhả lần đầu hoặc chạm trần phiên `used > 0`):** **CHỈ COOLDOWN 24 GIỜ (1 NGÀY)** để xả cache! Tuyệt đối CẤM phạt 3 ngày.
- **`Streak 2` (Tái phạm lần 2 liên tiếp `used == 0`):** **CHỈ COOLDOWN 3 NGÀY** (Tuyệt đối CẤM phạt 5 ngày).
- **`Streak 3` (Tái phạm lần 3 liên tiếp `used == 0`):** **CHỈ COOLDOWN 5 NGÀY** (Tuyệt đối CẤM phạt 7 ngày).
- **`Streak >= 4` (Tái phạm dai dẳng):** Cooldown 15 ngày (giam cách ly kiểm điểm).

#### B. Bóc Tách Hoàn Toàn 2 Hệ Thống: `fail_streak` vs Cấp Độ Quota Tốt Nghiệp:
1. **Hệ thống `fail_streak` (Chuỗi thất bại liên tiếp):**
   - Thuần túy là bộ đếm số lần fail liên tiếp (0 follow).
   - Trong hàm `mark(uid, STATUS_FOLLOWED)`: **Cứ follow thành công dù chỉ 1 cái -> `fail_streak = 0` ngay lập tức!** Chuỗi thất bại bị bẻ gãy hoàn toàn vì server TikTok đã nhận follow thật. CẤM ghim giữ `fail_streak > 0` trong các ngày dưỡng nick.
   - Khi chạm trần ở cuối cữ (`used > 0`): Ghi nhận là **Streak 1 (nhả lần đầu, phạt 24h)**.
2. **Hệ thống Cấp độ Quota Dưỡng Nick (Hồi phục 1 -> Hồi phục 2 -> Khỏe/Tốt nghiệp):**
   - Chạy **hoàn toàn độc lập** qua `probation_clean_days` và `graduated` (không phụ thuộc vào `fail_streak`):
     - **Hồi phục 1:** Cấp quota 2–4 lượt.
     - **Hồi phục 2:** Cấp quota 4–6 lượt.
     - **Khỏe (Tốt nghiệp):** Cấp quota full 10–15 lượt.
   - Cờ `is_post_cooldown_warmup` được kích hoạt khi `(not self.is_graduated) and (not self.follow_failed)` hoặc khi `recovered_date == today`. Nhờ vậy, nick dù có `fail_streak = 0` vẫn giữ đúng quota dưỡng an toàn (2–4 lượt) suốt các phiên cùng ngày và ngày hôm sau, không bị nhảy vọt lên full quota.

### 5. Kỷ Luật Dispatch Worker & Timeout
* **Worker Floor 300s:** BẮT BUỘC tuân thủ sàn timeout >= 300s cho mọi lệnh dispatch worker. CẤM TUYỆT ĐỐI Coordinator tự ý gõ cờ `--timeout 30` hay bóp ngắn timeout làm ngắt luồng stream của worker.
* **Claude 100% On-Demand:** Khi user cấu hình Sol Worker, Coordinator BẮT BUỘC tôn trọng Sol Worker. CẤM TUYỆT ĐỐI tự ý đề xuất, hối thúc hay chuyển sang Claude Worker khi user không yêu cầu đích danh. Cấm phá tầng cơ học dispatch worker đã được chuẩn hóa.

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
