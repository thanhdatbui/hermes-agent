# Quy Tắc Khóa Follow Nick 0 Video, Mode 2' Scroll Depth & Continuous Jitter (19/08/2026)

## 1. Khóa Cứng Follow Nick 0 Video (`zero-video-follow-disabled`)
- **Dữ liệu thực nghiệm**: 100% nick 0 video (Row 3, 5) khi tap Follow đều bị TikTok nhả ngay sau cú tap đầu tiên (`followed = 0`).
- **Xử lý tại Follow Hook**:
  - `_run_follow_hook` kiểm tra `video_count <= 0` (hoặc missing/None) $\rightarrow$ lập tức trả `status = "skipped"`, `reason = "zero-video-follow-disabled"`.
  - Tuyệt đối không mở `run_follow` cho nick chưa có video đăng.

---

## 2. Cơ Chế Cuộn Mode 2' Tìm Nick Nội Bộ (`_scroll_follower_list`)
- Mode 2' vào tab **Đã follow (Following)** của nick anchor (Tik1/Tik2):
  - Đọc danh sách nick trên màn hình $\rightarrow$ Lọc nick thuộc `internal_uids` (Farm).
  - Bấm Follow nick farm chưa theo dõi.
  - Bỏ qua (skip) nick ngoài farm (không lưu state).
  - **Tự động cuộn xuống dưới (`_scroll_follower_list`)**: Nếu trang hiện tại không có nick farm mới, tự động cuộn xuống tối đa **40 lần (`max_scrolls = 40`)** để quét sạch danh sách following của anchor.

---

## 3. Thứ Tự Điều Phối Hybrid (Mode 2' Trước ➔ Mode 1 Bù)
- Trong `follow_engine.py`:
  1. Chạy `run_mode2()` trước để khai thác list following của anchor.
  2. Tính số lượng còn thiếu: `budget_mode1 = session_budget - len(res.followed)`.
  3. Chỉ khi Mode 2' chưa đủ budget thì mới chạy `run_mode1()` để Search bù đúng số lượng còn thiếu.

---

## 4. Dải Jitter Khởi Động Liên Tục (`JITTER_MINUTES`)
- Trong `python_runner/hermes_cron/blocks.py`:
  - Thay thế tuple 4 mốc rời rạc cũ `(-20, -15, 15, 20)` thành dải số nguyên liên tục `tuple(range(-25, 26))` ($-25$ đến $+25$ phút).
  - Giúp 80–160 máy phân tán ngẫu nhiên thời gian khởi động từng phút thực tế, triệt tiêu hoàn toàn footprint tập trung theo mốc.
