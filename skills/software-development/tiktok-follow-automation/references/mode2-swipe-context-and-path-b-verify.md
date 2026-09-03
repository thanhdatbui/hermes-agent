# Mode 2 Swipe Context & Path B Profile Verification (TikTok Follow Runner)

## 1. Mục đích & Bối cảnh (Cập nhật 2026-08-30)
Chuẩn hóa và đồng bộ luồng xử lý của **Module 2** (`mode2_follow_followers.py` trong `D:\Taadaa\tiktok-follow`):
- Đồng bộ hành vi người dùng thật trên Feed trước khi search.
- Quét trọn vẹn danh sách Following của anchor, không bị ngắt sớm mâu thuẫn với `max_scrolls`.
- Kiểm tra nhả follow 100% bằng cách mở profile trực tiếp (Path B) không reload/vuốt, quay về list an toàn.

---

## 2. Quy tắc chi tiết

### A. Swipe Context trước Seed Search
- Trước khi tìm kiếm từng anchor UID, sau khi đảm bảo giao diện đang ở Feed (`_back_to_feed`), runner phải thực hiện lướt nhẹ video trên Feed (`swipe_before_search`).
- **An toàn cấu hình & Fail-closed:**
  - Bọc `try-except` an toàn: bắt `(ValueError, TypeError, OverflowError)` khi parse `cfg.swipe_before_search`, clamp giá trị trong khoảng `0..10`, fallback mặc định là `3` nếu cấu hình sai/inf/None.
  - Nếu `swipe_count == 0`: bỏ qua swipe và tiếp tục mở Following.
  - Nếu `swipe_feed` trả về `False` hoặc ném exception (ADB đứt kết nối): fail-closed dừng ngay với trạng thái `MANUAL_REVIEW: swipe context trước seed search thất bại`.

### B. Gỡ bỏ ngắt sớm 20 nick ngoài farm (Continuous Scrolling)
- Trước đây có điều kiện `consecutive_skip >= 20` làm ngắt sớm danh sách Following dù bên dưới vẫn còn nick farm nội bộ.
- **Quy tắc mới:** Gỡ bỏ hoàn toàn ngắt `consecutive_skip >= 20`. Runner cuộn danh sách và duyệt cho đến khi:
  - Đạt đủ budget follow của phiên, **HOẶC**
  - Chạm đáy danh sách (empty surface hoặc 5 lần scroll rỗng `idle_scrolls >= 5`), **HOẶC**
  - Đạt giới hạn cuộn an toàn tối đa `max_scrolls = 40`.
- Các nick ngoài farm (`not in internal_uids`) chỉ được ghi log/skip nhẹ, không lưu vào file state và không làm dừng tiến trình cuộn.

### C. Path B Verification (Xác minh trực tiếp trên Profile)
- Sau khi tap nút Follow ở danh sách (Path A), runner **100% tự động bấm vào username** để mở trang Profile cá nhân của nick đó (`_path_b_verify`).
- **Kiểm tra trạng thái (Không pull-to-refresh / Không vuốt):**
  - Dump XML trang profile vừa mở, đọc nút quan hệ (`Bạn bè` / `Đang theo dõi` / `Nhắn tin` vs `Follow` / `Follow lại`).
  - Nếu profile vẫn hiển thị `Follow` / `Follow lại` $\rightarrow$ Nhả follow thực tế $\rightarrow$ Đánh dấu `FOLLOW_FAILED`, ngắt phiên ngay lập tức và đưa máy về Home an toàn.
  - Nếu profile hiển thị đã follow $\rightarrow$ Gọi `adapter.back()` quay lại màn hình danh sách Following.
- **Fail-Closed khi Back / Restore UI:**
  - Nếu `adapter.back()` trả về `False` hoặc ném `Exception`, hoặc UI sau khi back không khôi phục về danh sách Following $\rightarrow$ Trả về `manual` / dừng phiên an toàn `MANUAL_REVIEW`.
