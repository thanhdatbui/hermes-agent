# GemPhone Pacing, Dwell Time, Feed Bookmark & Upload Hook (14/09/2026)

## 1. Bản chất thực nghiệm về hiện tượng Nhả Follow & Án phạt Cooldown
- **Thực tế dữ liệu 176 nick:** 170/176 nick dính streak phạt (streak 1..3) đều đã đăng trên 5 video (trung bình 10.9 video/nick, nhiều nick 20-23 video).
- **Lý thuyết phản biện:**
  - Cả lý thuyết truyền miệng "ngâm đủ 7 ngày tự khỏi" và "chỉ cần đăng video đều là khỏi" đều **KHÔNG ĐÚNG** nếu nhịp độ follow trong script còn vội vã cơ học.
  - Server TikTok Risk Engine áp dụng Optimistic UI + Async Backend Validation: khi nick thao tác quá nhanh sau khi load profile hoặc các lượt follow cách nhau quá sát (< 5s), hệ thống âm thầm rollback (nhả follow) và đè streak phạt nặng hơn.

## 2. Quy chuẩn nhịp độ GemPhone của ông Khoa (Đã áp dụng vào codebase)
Đối chiếu từ 3 bộ workflow gốc (`TIKTOK-Nuoi-Tai-Khoan-Goc`, `TIKTOK-FLOW-TÌM-KIẾM`, `TIKTIK-ĐĂNG-VIDEO`):

### A. Repo `tiktok-follow` (Follow Pacing)
1. **Dwell Time ngâm Profile trước khi Tap Follow:**
   - GemPhone gốc: node delay `5812, 12549 ms`.
   - Chuẩn hoá code: `time.sleep(random.uniform(6.0, 12.0))` ngay trước khi gọi `_tap_follow_button()` trong `mode1_search_follow.py`.
2. **Delay chờ phản hồi server sau khi Tap Follow:**
   - GemPhone gốc: node delay `1814, 5654 ms`.
   - Chuẩn hoá code: `time.sleep(random.uniform(2.5, 5.0))` sau khi tap center nút follow trong cả Mode 1 và Mode 2.
3. **Khoảng cách nghỉ giữa 2 lần Follow (Inter-follow Delay):**
   - GemPhone gốc: node `rf10473` delay `5142, 29521 ms`.
   - Chuẩn hoá code: `delay_min: 8`, `delay_max: 25` (nghỉ 8.0s - 25.0s ngẫu nhiên giữa các UID trong Mode 1 và Mode 2).

### B. Repo `tiktok-luot nuoi acc` (Feed Interaction & Hook Pacing)
1. **Thẻ Follow lại trên Feed (`follow_back_suggestion`):**
   - Nick sạch (`is_account_in_follow_cooldown == False`): Bấm **"Follow lại"** / **"Theo dõi lại"** để tạo tương tác chéo tự nhiên.
   - Nick đang bị phạt (`is_account_in_follow_cooldown == True`): Bấm **"Không quan tâm"** để bảo toàn án phạt, không tái kích hoạt cờ theo dõi.
2. **Ngẫu nhiên hóa tỷ lệ Like theo từng phiên:**
   - Tab `following`: random [30%, 60%] mỗi phiên.
   - Tab `friends`: random [50%, 80%] mỗi phiên.
   - Tab `for_you`: giữ 8% tự nhiên.
3. **Hành vi Bookmark (Lưu video Yêu thích) sau khi Like (Case 167):**
   - Nguyên tắc: Chỉ khi video đã được thả tim thành công, mới có xác suất bấm Lưu lại (hành vi người dùng thật).
   - Tỷ lệ: Random 15% - 30% khi like thành công.
   - Pacing: Chờ 0.8s - 1.8s sau khi Like rồi tap node Lưu (`x >= 750`), sau đó chờ 0.4s - 0.8s.
4. **Thu gọn Hook Upload Video chỉ vào Phiên 2 (`scripts/run-feed-session.ps1`):**
   - Đổi từ `$SessionIndex -in 1, 2` thành `$SessionIndex -eq 2`.
   - Mục đích: Tránh đốt kho video quá nhanh trong thời gian nick đang chịu cooldown nhả follow. Nếu phiên 2 lỗi, 4 ngày sau nick mới đến lượt upload tiếp, hoàn toàn tự nhiên.
