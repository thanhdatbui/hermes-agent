# Quy Chuẩn Đối Soát Baseline T0 & Cơ Chế Idle Scrolls Mode 2 (2026-09-27)

## 1. Bẫy Đối Soát Lệch Dương Ảo Do Thiếu Baseline T0 Sát Giờ Chạy
- **Hiện tượng:**
  - Watchdog báo cáo đối soát sau phiên thường xuyên bị lệch dương: Web tăng nhiều hơn script báo (ví dụ: script báo 1, web tăng +4; script báo 2, web tăng +3).
- **Nguyên nhân gốc rễ:**
  - Watchdog lấy mốc snapshot trước phiên qua điều kiện `timestamp <= session_start_iso`.
  - Nếu trước phiên không có bước cào nào được kích hoạt, snapshot gần nhất bị trôi về tận **07:03 sáng** (mốc cron cào định kỳ toàn farm).
  - Khoảng thời gian từ 07:00 đến 10:00 hoặc 14:00, tài khoản đã chạy qua nhiều ca lướt feed, thả tim, và follow tự nhiên khi xem video. Khi đem số tăng của 3 - 7 tiếng so với 1 phiên follow chéo 15 phút, watchdog sẽ tạo ra số liệu lệch ảo.
- **Giải pháp bắt buộc (Pre-Session Scrape T0):**
  - Trước khi khởi chạy phiên nuôi (hoặc ngay tại bước preflight của runner):
    - Đọc danh sách tài khoản hợp lệ của Row tương ứng từ safe workbook.
    - Kích hoạt `tiktok_account_tracker.py --usernames <uids> --workers 10` để chốt mốc $T_0$ sát giờ chạy (trước khi máy đụng app).
    - Sau khi phiên kết thúc, watchdog cào mốc $T_1$, tính $\Delta = T_1 - T_0$. Đảm bảo số liệu đối soát khớp 100% với phiên thực tế.

---

## 2. Bẫy Ngừng Sớm Trong Following List Của Anchor (Mode 2) & Cơ Chế `idle_scrolls`
- **Hiện tượng:**
  - Máy vào được profile của Anchor, bấm mở tab "Đang follow" (Following list) thành công.
  - Danh sách người đang follow của Anchor rất nhiều (hàng trăm nick), nhưng script chỉ duyệt 1-2 nick rồi kết thúc ca với trạng thái `OK: đã follow sẵn (skip)`.
- **Nguyên nhân kỹ thuật trong code:**
  - Runner chỉ lọc theo `internal_uids` (danh sách nick thuộc farm).
  - Khi cuộn màn hình, nếu liên tiếp gặp các tài khoản ngoài farm (external accounts), biến đếm `idle_scrolls` tăng dần:
    ```python
    if not internal_pending:
        _scroll_follower_list(engine)
        scrolls += 1
        idle_scrolls += 1
        if idle_scrolls >= 5:
            break
    ```
  - Giới hạn cứng `idle_scrolls >= 5` khiến script dừng sớm nếu 5 lần cuộn liên tiếp không xuất hiện nick farm (do nick farm bị trôi xuống sâu hoặc danh sách bị loãng).
  - Kết hợp với việc chỉ thử tối đa 3 Anchor ngẫu nhiên trong pool: Nếu cả 3 Anchor đều gặp tình trạng trên hoặc các nick farm đầu danh sách đã được nick hiện tại follow từ các ca trước, runner sẽ dừng sớm và báo `đã follow sẵn (skip)`.
- **Bài học vận hành & Định hướng tối ưu:**
  - Cần nâng trần `idle_scrolls` hoặc bổ sung cơ chế Fast-Skip: Khi 1 Anchor không còn nick farm khả dụng, runner phải tự động thoát và chuyển sang Anchor tiếp theo trong pool thay vì dừng hẳn.
  - Khi hết toàn bộ Anchor mà chưa đạt session budget, runner phải tự động kích hoạt **Module 1 (Search bù)** để tiếp tục tìm kiếm follow các nick farm khác theo từ khóa/danh sách.
