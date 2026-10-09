# Mode 2 Anchor Pull-To-Refresh Shadow Drop & False Abort Triage

## 1. Hiện tượng thực tế (Sự cố Ca 1 ngày 12/09/2026)
- **Triệu chứng:** Hơn 30 máy (như M5, M7, M9, M12, M16, M19, M20, M22...) trong báo cáo watchdog đều ghi nhận **Nhả liền (0 lượt)** với lý do:
  `FOLLOW_FAILED: anchor @<uid> bị nhả sau vuốt — dừng session`
- **Tương phản:** Máy 6 và Máy 64 lại follow thành công trọn vẹn 17/17 lượt follow (`OK`, không nhả).

## 2. Nguyên nhân cốt lõi (Root Cause)
1. **Tại sao M6 và M64 thành công?**
   - Tài khoản trên M6 và M64 **đã follow Anchor từ trước** (hoặc Anchor đã là bạn bè), nên flow bỏ qua bước bấm follow Anchor $\rightarrow$ vào thẳng tab Following của Anchor và cày follow bình thường.
2. **Tại sao 30 máy còn lại bị 0 lượt?**
   - Tài khoản chưa follow Anchor. Hàm `_ensure_anchor_followed` (trong `mode2_follow_followers.py`) thực hiện bấm nút `Follow` Anchor.
   - Sau khi bấm, bot thực hiện `pull_to_refresh_profile(adapter, sleep_after=3.5)` để reload trang cá nhân.
   - Server TikTok với các nick lạ/mới thường thực hiện **shadow-drop** (âm thầm từ chối hành động follow một người lạ). Trên UI trước khi reload có thể đổi màu, nhưng khi kéo tải lại từ server thì nút nhảy ngược về `Follow` (màu đỏ).
   - Code phân loại `_classify_profile_action(refreshed_xml)` thấy `not_followed` $\rightarrow$ kết luận ngay là **"bị nhả sau vuốt"** và **DỪNG TOÀN BỘ PHIÊN NGAY LẬP TỨC (0 lượt)**.
3. **Tại sao tăng cooldown không giải quyết được?**
   - Cooldown chỉ giải quyết rate-limit tần suất. Ở đây là lỗi logic: **Mục đích chính của Mode 2 là đọc tab Following của Anchor để follow các nick con**, việc follow Anchor chỉ là phụ (opt-in).
   - Tab Following của Anchor là công khai, không bắt buộc tài khoản phải follow Anchor mới xem được. Biến việc không follow được Anchor thành Hard-Abort session là một anti-pattern gây sập hàng loạt.

## 3. Quy tắc khắc phục chuẩn
- Trong `_ensure_anchor_followed`: Nếu bấm follow Anchor mà sau khi reload vẫn trả về `not_followed`:
  - Không được gọi `engine.state.set_follow_failed()` và không được dừng session.
  - Ghi nhận `anchor_follow: skipped_or_dropped`, nhưng **vẫn trả về `profile_xml` để tiếp tục mở tab Following của Anchor** và hoàn thành budget follow theo kế hoạch.
