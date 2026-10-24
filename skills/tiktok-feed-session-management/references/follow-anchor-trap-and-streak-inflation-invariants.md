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
