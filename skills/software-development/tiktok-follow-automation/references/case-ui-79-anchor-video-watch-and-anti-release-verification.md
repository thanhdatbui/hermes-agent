# Case UI-79: Cơ Chế Xác Thực Nhả Follow (Mode 1 & Mode 2 Anchor), Chu Kỳ Progressive Cooldown và State Dedupe

## 1. Bối cảnh & Hiện tượng thực tế (2026-09-30)
- Trong các đợt chạy nuôi acc kết hợp Follow chéo trên dàn 80 máy Kibe, xuất hiện các máy dừng sớm với kết quả:
  `FOLLOW_FAILED: anchor @<uid> bị nhả sau vuốt — dừng session`
- Đặt ra các câu hỏi cốt lõi về cơ chế vận hành:
  1. Vì sao lại có thông báo "bị nhả sau vuốt" và hành động xem video / thả tim / follow anchor có thực sự chạy không?
  2. Module 1 (Search Follow) xác thực nhả follow bằng cách nào?
  3. Khi bị nhả follow, UID đó có bị ghi vào danh sách đã follow (`followed`) hay không?
  4. Thuật toán Cooldown nhả follow (`fail_streak`, `progressive backoff`) đang hoạt động như thế nào?

---

## 2. Chi tiết Cơ chế Xác thực Nhả Follow

### A. Chuẩn bị Anchor trong Mode 2 (`_ensure_anchor_followed`):
Trước khi mở tab Following của Anchor (Tik1/Tik2 Kibe có $\ge 10$ video), nếu nick hiện hành chưa follow Anchor:
1. **Tìm video:** Quét lưới video trên Profile của Anchor (các node có `cover`, `tv_play_count`, `aweme`), nếu chưa thấy thì vuốt nhẹ 1–2 lần. Nếu không có video -> bỏ qua anchor (`no_video`).
2. **Xem video:** Tap cover video đầu tiên, giữ màn hình ngẫu nhiên 8.0 – 15.0s (`dwell = random.uniform(8.0, 15.0)`).
3. **Thả tim ngẫu nhiên:** Tỷ lệ 65%, tìm icon Like (`content-desc="thích"` hoặc `like_icon`) và tap tim.
4. **Bấm Follow:** Tìm nút Follow overlay trên video (nút có dấu `+` đỏ bên cạnh avatar người đăng hoặc content-desc `Follow`) -> Tap follow.
5. **Độ trễ máy chủ:** Chờ 2.0 – 4.0s cho TikTok backend ghi nhận quan hệ.
6. **Quay lại & Vuốt Reload:** Bấm `Back` về lại Profile Anchor -> **Kéo vuốt màn hình xuống (`pull_to_refresh_profile`, chờ 3.5s)** để ép app tải lại dữ liệu thật từ máy chủ (phá cache Optimistic UI).
7. **Bắt nhả follow:** Nếu sau reload, trạng thái nút vẫn là `not_followed` -> Gán `engine.state.set_follow_failed()` và báo lỗi `FOLLOW_FAILED: anchor @{uid} bị nhả sau vuốt — dừng session`.

### B. Xác thực nhả follow trong Module 1 (`verify_after_tap` & `_reload_profile`):
Module 1 search trực tiếp UID mục tiêu, sau khi tap Follow trên profile:
1. Chờ dwell time 6.0 – 12.0s, đọc nút quan hệ lần 1.
2. Nếu nút đã đổi sang `followed` ("Đã follow" / "Nhắn tin"), **bắt buộc reload profile để chống Optimistic UI**:
   - **80% xác suất:** Pull-to-refresh (vuốt kéo làm mới tại chỗ có jitter, delay 3.0 – 4.5s).
   - **20% xác suất:** Natural Re-entry (bấm Back ra kết quả Search, tap lại vào thẻ người dùng).
3. Sau khi reload, đọc lại nút:
   - Nếu nút vẫn là `followed` -> Ghi nhận `STATUS_FOLLOWED`.
   - Nếu nút bị nhảy ngược về `not_followed` -> Gán `set_follow_failed()`, trả về `VerifyResult("failed", "FOLLOW_FAILED: follow bị nhả sau re-entry — dừng session")`.

---

## 3. Thuật toán Progressive Cooldown & Cơ chế State Dedupe

### A. State Dedupe (Chống nuốt mất UID khi bị nhả):
- Khi follow thành công và không bị nhả: Ghi vào `self._data["followed"][uid] = now_iso`. Hàm `is_followed(uid)` chỉ kiểm tra trong dict `followed`.
- Khi follow bị TikTok nhả hoặc thất bại:
  - Ghi vào `self._data["failed"][uid] = now_iso`.
  - **TUYỆT ĐỐI KHÔNG GHI VÀO `followed`**.
  - Kết quả: Khi hết hạn Cooldown, nick **vẫn có thể được chọn để follow lại UID này**, không bị mất target vĩnh viễn.

### B. Progressive Cooldown Backoff (`follow_state.py` - Cập nhật 2026-10-02):
- **Thực tế vận hành:** Đối soát 4.479 lượt chạy follow (25/09 - 02/10) cho thấy mức phạt Streak 1 cũ (nghỉ 1 ngày) có tỷ lệ tái phạm nhả follow tới 97.1% (67/69 nick thử lại bị nhả tiếp) do rolling-window rate limit của TikTok kéo dài tối thiểu 3-7 ngày (dù app đã có ca lướt feed đầy đủ $\ge 3$ swipes trước khi follow). Chỉ các nick nghỉ $\ge 4-6$ ngày mới phục hồi thành công.
- **Thang Cooldown 3-5-7 Chuẩn Hóa:**
  - **Streak 1 (Bị nhả lần đầu):** Nghỉ **3 ngày** (`+ timedelta(days=3)` đến `23:59:59 local`). Grace window: 7 ngày (3 + 4).
  - **Streak 2 (Bị nhả 2 cữ liên tiếp):** Nghỉ **5 ngày** (`+ timedelta(days=5)`). Grace window: 9 ngày (5 + 4).
  - **Streak $\ge 3$ (Tái phạm nhiều lần / Acc lì đòn):** Nghỉ **7 ngày (1 tuần)** (`+ timedelta(days=7)`). Grace window: 11 ngày (7 + 4).
- **Post-Cooldown Warmup:** Khi vừa hết hạn cooldown (`fail_streak > 0 and not follow_failed`), tài khoản chỉ được cấp quota thăm dò nhỏ (**3 – 5 follow/phiên**). Nếu phiên này chạy thành công không bị nhả, hệ thống mới reset `fail_streak = 0`.

---

## 4. Preflight Gates & Phân Loại Lỗi Feed Trước Follow Hook
1. **Lỗi bảo mật nặng (`_SENSITIVE_ACCOUNT_WORDS`):** Checkpoint, banned, suspended, logged_out, captcha, otp, 2fa, account_locked -> Bỏ qua ngay follow hook (`sensitive-skip-*`).
2. **Lỗi script / Timeout trong Feed Session:**
   - Nếu đã hoàn thành $\ge 3$ swipes (đủ warm telemetry) -> **VẪN CHO CHẠY FOLLOW**.
   - Hoặc nếu nick đã từng thành công ở phiên trước trong cùng ca -> **VẪN CHO CHẠY FOLLOW**.
   - Chỉ khi vừa mở app lên đã crash/lỗi ngay ($< 3$ swipes và chưa có phiên nào thành công) -> Bỏ qua follow để tránh hành vi mở app là đi search/follow ngay.
