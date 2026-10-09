# Case 156: Phân Loại Trống Slot vs Fail & Sửa Bug Nuốt Đếm Tab Fast Swipe

## 1. Triệu chứng & Hiện trường (Ca 4 - Row 7 ngày 2026-09-13)
- Báo cáo watchdog Telegram hiện:
  - Success (19-20 máy).
  - Fail (61 máy) -> Gây hiểu nhầm toàn farm gặp lỗi nghiêm trọng.
  - Không có thống kê lượt like / thả tim.
  - 100% video lướt ở tab Đề xuất (For You), lượt xem Bạn bè và Following đều = 0 dù cấu hình `feed_distribution`: 70% FY, 15% Friends, 15% Following và `like_rates`: Friends 70%, FY 8%.

## 2. Root Cause 1: 61 máy Fail là do Trống Slot
- Row 7 & 8 là slot phôi mới của farm, kho `taikhoan_run_safe.xlsx` lúc này mới có 35 máy được điền tài khoản Row 7.
- 45 máy còn lại trả về: `account row 7 is empty (no username) for machine X, skipping` (trạng thái `config-error`).
- Watchdog cũ gom toàn bộ máy `!= success` vào nhóm `Fail`.
- **Khắc phục (`feed_session_watchdog.py`):**
  - Tách riêng nhóm `Trống slot/chưa có nick`: máy có `status == "skipped-empty"` hoặc `reason` chứa `is empty (no username)` / `does not have valid row` hoặc `batch-config-error` mà không thuộc `expected_machines`.
  - Giữ nhóm `Fail` chỉ cho các máy có nick nhưng gặp lỗi thực sự (kẹt lock, offline USB, lỗi profile...).

## 3. Root Cause 2: Kẹt 100% ở tab Đề xuất do Fast Swipe nuốt đếm tab
- Trong `feed_swipe_smoke.py`:
  - Cơ chế Fast Swipe xen kẽ Deep Inspect (lướt nhanh 2-4 video rồi mới inspect sâu 1 video).
  - Khởi tạo: `videos_until_tab_decision = random.randint(3, 8)`.
  - Nhánh Deep Inspect (dòng 22108) có trừ: `videos_until_tab_decision -= 1`.
  - Nhánh `fast_swipe` (dòng 21400-21448) chiếm phần lớn số video (15/21 video) gọi `continue` ngay mà **quên trừ `videos_until_tab_decision -= 1`**.
  - Hậu quả: Biến đếm không bao giờ giảm về `<= 0`, hàm chọn tab `_weighted_feed_choice` không bao giờ được kích hoạt, máy bị kẹt 100% ở tab Đề xuất, tê liệt phân phối tab Bạn bè và tỷ lệ like 70% của tab Bạn bè.
- **Khắc phục (`feed_swipe_smoke.py`):**
  - Bổ sung `videos_until_tab_decision -= 1` ngay trước `continue` ở nhánh `fast_swipe`.

## 4. Chuẩn Hóa Báo Cáo Watchdog Lướt Feed
Báo cáo Telegram phần Lướt Feed bắt buộc có format:
```text
• Lướt Feed:
  + Success (20): 3, 4, 6, 7, 9, 11, ...
  + Fail (15): M1, M2, M5, ...
  + Trống slot/chưa có nick (45): 13, 20, 22, ...
  + Thả tim: 57 tim / 391 video (14.6%) [Đề xuất: 57 | Bạn bè: 0 | Following: 0]
```
