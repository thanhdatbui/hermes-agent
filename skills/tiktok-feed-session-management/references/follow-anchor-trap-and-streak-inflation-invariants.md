# Follow Anchor Trap, Streak Decoupling & Cooldown Ladder Invariants

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

### 2. Bóc Tách Hoàn Toàn 2 Hệ Thống: `fail_streak` vs Cấp Độ Quota Tốt Nghiệp

Trước đây hệ thống bị lỗi nghiêm trọng do nhập nhằng giữa **Bộ đếm chuỗi thất bại (`fail_streak`)** và **Tầng Quota Dưỡng Nick (`probation / graduation`)**, khiến nick vừa mãn hạn ra cày được follow sạch nhưng vẫn bị ghim streak cũ, cữ sau lỡ nhả là bị kích hoạt tái phạm oan lên Streak 3, 4 (giam 7–15 ngày).

#### A. Hệ thống 1: `fail_streak` (Chuỗi thất bại liên tiếp)
- **Quy tắc vàng:** Trong `mark(uid, STATUS_FOLLOWED)`, **cứ follow thành công dù chỉ 1 người (`used >= 1`) $\rightarrow$ `self._data["fail_streak"] = 0` ngay lập tức!**
- Chuỗi thất bại bị bẻ gãy ngay tại thời điểm có follow thành công. Không bao giờ để nick đang follow được phải mang án streak 1, 2, 3.
- **Thang phạt Cooldown chuẩn hóa khi dính nhả:**
  - **`Streak 0`:** Nick hoàn toàn sạch, đang chạy khỏe bình thường, không dính án, không cooldown.
  - **`Streak 1` (Nhả lần đầu hoặc chạm trần phiên `used > 0`):** **CHỈ COOLDOWN 24 GIỜ (1 NGÀY)** để xả cache! Tuyệt đối CẤM phạt 3 ngày.
  - **`Streak 2` (Tái phạm lần 2 liên tiếp `used == 0`):** **CHỈ COOLDOWN 3 NGÀY** (Tuyệt đối CẤM phạt 5 ngày).
  - **`Streak 3` (Tái phạm lần 3 liên tiếp `used == 0`):** **CHỈ COOLDOWN 5 NGÀY** (Tuyệt đối CẤM phạt 7 ngày).
  - **`Streak >= 4` (Tái phạm dai dẳng):** Cooldown 15 ngày (giam cách ly kiểm điểm).

#### B. Hệ thống 2: Cấp độ Quota Dưỡng Nick (Hồi phục 1 ➔ Hồi phục 2 ➔ Khỏe)
- Chạy **độc lập 100%** qua `probation_clean_days` và `graduated`, tuyệt đối không phụ thuộc vào `fail_streak`:
  - **Hồi phục 1:** Cấp quota 2–4 lượt.
  - **Hồi phục 2:** Cấp quota 4–6 lượt.
  - **Khỏe (Tốt nghiệp / Graduated):** Cấp quota full 10–15 lượt.
- Cờ `is_post_cooldown_warmup` được kích hoạt khi `(not self.is_graduated) and (not self.follow_failed)` hoặc khi `recovered_date == today`. Nhờ vậy, nick dù có `fail_streak = 0` vẫn giữ đúng quota dưỡng an toàn (2–4 lượt) suốt các phiên cùng ngày và ngày hôm sau, không bị nhảy vọt lên full quota. Nếu cữ sau có lỡ bị nhả thì nick chỉ bị phạt lại ở mức Streak 1 (24h), không bao giờ bị đè lên Streak 2, 3, 4 giam oan.

---

### 3. Quy Tắc Thiết Kế Tránh Bẫy Anchor & Lạm Phát Streak (Invariants)
1. **Không chặn Gateway:** Thất bại khi tương tác với Anchor (nick gốc) không được coi là lỗi vi phạm spam của tài khoản. Chỉ bỏ qua Anchor đó hoặc chuyển sang Anchor khác / Mode 1.
2. **Cấm tăng streak khi `used == 0` do lỗi Anchor:** `fail_streak` chỉ được phép tăng khi nick đã vào danh sách mục tiêu thực tế và bị server TikTok từ chối nhiều lần trong chuỗi hành động hợp lệ.
3. **Decouple Anchor Following:** Luôn ưu tiên mở thẳng tab Following của Anchor mà không ép nick phải thực hiện hành động follow Anchor trước.

---

### 4. Kỷ Luật Dispatch Worker & Timeout
- **Worker Floor 300s:** BẮT BUỘC tuân thủ sàn timeout >= 300s cho mọi lệnh dispatch worker. CẤM TUYỆT ĐỐI Coordinator tự ý gõ cờ `--timeout 30` hay bóp ngắn timeout làm ngắt luồng stream của worker.
- **Claude 100% On-Demand:** Khi user cấu hình Sol Worker, Coordinator BẮT BUỘC tôn trọng Sol Worker. CẤM TUYỆT ĐỐI tự ý đề xuất, hối thúc hay chuyển sang Claude Worker khi user không yêu cầu đích danh. Cấm can thiệp làm hỏng tầng cơ học dispatch worker đã được chuẩn hóa.

---

### 5. Khóa Đồng Bộ Đa Repo (Cross-Repo Sync Contract)
1. **Tại `tiktok-follow` (`follow_runner/core/follow_state.py`):**
   - Trong `mark(uid, STATUS_FOLLOWED)`: Reset `self._data["fail_streak"] = 0` ngay khi có 1 follow thành công.
   - Trong `set_follow_failed()`: Khi `used > 0`, ghi nhận `streak = 1`, không pop `graduated`/`probation_clean_days`, đặt `cooldown_until_local = (now_utc + 24h).astimezone(tz)`. Khi `used == 0`: streak 1 là 24h, streak 2 là 3 ngày, streak 3 là 5 ngày, streak >= 4 là 15 ngày.
2. **Tại `tiktok-luot nuoi acc` (`python_runner/flows/multi_machine_feed_session.py`):**
   - Trong `_is_account_follow_cooldown()`: Tôn trọng tuyệt đối `cooldown_until_at` / `cooldown_until_date` từ state. Khi `streak <= 1`, `streak_days = 1`, cho phép nick đi follow ngay khi hết mốc 24h thay vì tự ý ép phạt 3/5/7 ngày.
3. **Tại Dashboard (`D:/Taadaa/tools/follow_health_helper.py`):**
   - Đối chiếu trực tiếp `cooldown_until_at` với `now` để phân loại trạng thái Cooldown; cấm dùng cờ `follow_failed` đơn thuần làm tiêu chí ném nick vào `🔴 Cooldown`.
4. **Xả án tồn dư (`D:/Taadaa/tools/reconcile_all_streak_cooldowns.py`):**
   - Đồng bộ toàn bộ các file state trên farm để xả án ngay lập tức cho các nick đã hết hạn cooldown 24h (Streak 1), 3 ngày (Streak 2), 5 ngày (Streak 3).
