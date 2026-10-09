# Case UI-88: Cơ Chế Tự Động Khấu Trừ Follow Tự Nhiên Khi Follow Chéo Phát Hiện Nick Bị Nhả/Drop (2026-10-02)

## 1. Hiện Tượng & Phản Hồi Từ Operator
- **Thắc mắc/Phản ánh:**
  - *"Dữ liệu web đc cào trc mỗi phiên chạy mà?"*
  - *"Còn fl tự nhiên chạy trc fl chéo đến phiên fl chéo phát hiện ra nick đó bị drop thì phải tự trừ ra lượt fl tự nhiên của nó chứ"*
- **Bối cảnh phiên (Row 5 - Ca 3):**
  - Feed session báo: `Follow tự nhiên: 12 lượt / 1169 video (1.0%)`.
  - Follow chéo: Có 3 máy bị nhả follow liền (`M26, M70, M78`).
  - Web đối soát: Chỉ tăng `+1 Following thật`, lệch `-34` so với script báo 35.
  - Trong đó `M26` có 2 lượt follow tự nhiên và `M70` có 1 lượt follow tự nhiên ở pha lướt feed, nhưng cả 2 đều bị nhả follow ở pha follow chéo và Web tăng `+0`.

---

## 2. Bản Chất Vận Hành & Khẳng Định Kỹ Thuật

### A. Dữ Liệu Web Được Cào Trước Mỗi Phiên (Baseline T0)
- Trong `tiktok_runner.py`, trước khi thực thi `run-feed-session.ps1`, hệ thống luôn chạy bước Pre-session scrape T0:
  ```python
  # Pre-session scrape T0: lấy baseline followingCount cho Row hiện tại
  subprocess.run([target_python(), r"D:\Taadaa\tools\tiktok_account_tracker.py", "--usernames", *_uids, ...])
  ```
- Sau phiên, `feed_session_watchdog.py` cào lại mốc T1 và tính $\Delta = T_1 - T_0$.
- Do đó, số liệu đối soát Web phản ánh đúng biến động trong phiên, không phải do thiếu cào trước phiên.

### B. Quan Hệ Thứ Tự Giữa Follow Tự Nhiên & Follow Chéo
- **Thứ tự thực thi trong phiên:**
  1. **Pha 1 (Nuôi Feed):** App lướt feed video. Khi gặp video phù hợp, hàm `_maybe_follow_video` tap vào nút `+` trên video overlay. App client TikTok đổi trạng thái (Optimistic UI) nhưng **không có thao tác reload profile để kiểm tra**.
  2. **Pha 2 (Follow Chéo):** App mở Profile Anchor/Target, bấm follow và **bắt buộc kéo vuốt (Pull-to-refresh) reload trang**.
- **Quy luật lan truyền trạng thái chặn (Action Block Propagation):**
  - Khi pha Follow chéo phát hiện nút bị nhả ngược về màu đỏ (`FOLLOW_FAILED` / `released`), điều đó chứng minh **tại thời điểm phiên chạy, nick/thiết bị đã bị server TikTok áp đặt Silent Action Block**.
  - Vì Action Block đã tồn tại trên server, các lệnh tap follow tự nhiên ở Pha 1 trước đó **chắc chắn cũng bị server TikTok shadow-drop sạch (Ghost Follows)**.

---

## 3. Quy Tắc Khấu Trừ Tự Động (Auto-Deduction Rule)

Khi tổng hợp báo cáo và lưu database tại watchdog:
1. **Xác định tập máy bị nhả/drop:**
   - Tập hợp các máy có `category == "released"` (từ `classify_machine_follow_result`) hoặc `follow_failed = True` hoặc `status == "FOLLOW_FAILED"`.
2. **Khấu trừ toàn bộ Follow Tự Nhiên của các máy này:**
   - Tính tổng các lượt follow tự nhiên (`for-you`, `following`, `friends`) phát sinh từ các máy thuộc tập bị drop: `dropped_tot_nat`.
   - Số follow tự nhiên hợp lệ thực tế:
     ```python
     valid_tot_nat = max(0, tot_nat_follows - dropped_tot_nat)
     ```
3. **Minh bạch hóa hiển thị Telegram:**
   - Nếu `dropped_tot_nat > 0`:
     ```text
     + Follow tự nhiên: X lượt / Y video (...) [Đề xuất: ... | Bạn bè: ...] (Đã tự trừ Z lượt do nick bị nhả/drop)
     ```
   - Nếu không có máy nào bị drop: Giữ nguyên định dạng thông thường.
4. **Làm sạch Database (`tiktok_tracker.db`):**
   - Khi gọi `save_session_action_stats`, trường `natural_follows` **bắt buộc lưu `valid_tot_nat`**, tuyệt đối không lưu số thô chưa khấu trừ để tránh làm sai lệch biểu đồ tăng trưởng trên Dashboard.

---

## 4. Kiểm Thử Hồi Quy Bắt Buộc
- Bất kỳ thay đổi nào liên quan đến báo cáo watchdog nuôi feed phải kiểm chứng qua unit test:
  - Máy bình thường (`status: success`, không bị nhả): Giữ nguyên số follow tự nhiên.
  - Máy có `follow_failed = True`: Tự động trừ sạch follow tự nhiên của máy đó.
  - Máy nằm trong `fl_released`: Tự động trừ sạch follow tự nhiên của máy đó.
  - Test suite: `python -m unittest python_runner/tests/test_feed_session_watchdog.py`.
