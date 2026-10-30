# Phân Tích Báo Cáo 2FA Ban Đêm & Kỷ Luật Bảo Vệ Ca Nuôi (30/10/2026)

Tài liệu đúc kết từ phiên giải mã báo cáo forward 2FA ban đêm toàn Farm (`night-tiktok-2fa-watchdog`) và quy chuẩn điều phối không xâm lấn ca nuôi.

---

## 1. Quy Trình Giải Mã Báo Cáo 2FA Toàn Farm O(1)
Khi User forward báo cáo tổng hợp dạng:
```text
⏰ [FARM REPORT][TOÀN FARM] BÁO CÁO 2FA TIKTOK BAN ĐÊM:
• Farm Kibe (Máy 1-80): Hoàn tất 22 | Bỏ qua 12 | Lỗi 36
• Farm Admin (Máy 201-280): Hoàn tất 37 | Bỏ qua 16 | Lỗi 35
```

Coordinator bóc tách ngay 3 khối dữ liệu:
1. **Số lượng hoàn tất mới (`success`):**
   - Ghi nhận tổng nick bật mới thành công trong đêm (ví dụ: +59 nick toàn farm).
   - Chạy lệnh Python O(1) đối soát trực tiếp vào 2 Master Excel (`taikhoan_dat_v2_updated .xlsx` của Kibe và Admin) để cập nhật tiến độ luỹ kế:
     * `has_2fa`: tổng nick đã có mã Secret ở Cột E.
     * `has_pass`: tổng nick đã có mật khẩu hợp lệ ở Cột D.
     * `has_both`: tổng nick hoàn thiện chuẩn cả 2FA + Pass.
2. **Nhóm Bỏ qua an toàn (`skip_safe`):**
   - Đa số do `DEVICE_LOCK_UNAVAILABLE` hoặc `PREFLIGHT` (máy đang có tiến trình khác chiếm lock lúc 00:00 - 00:30).
3. **Nhóm Lỗi (`failed`):**
   - Không vội quy kết runner bị crash (kiểm tra returncode = 4 là `partial_failure`, hoàn tất có kiểm chứng).
   - Bản chất: Rơi vào rào chắn bảo vệ `POST_SUCCESS_VERIFICATION_FAILED` (xem Mục 3 bên dưới).

---

## 2. Kỷ Luật Bảo Vệ Ca Nuôi (Feed Session Interlock Guard)
- **Tuyệt đối cấm chạy bù mù quáng vào ca nuôi:**
  * Ngay khi đọc xong báo cáo lỗi, trước khi có bất kỳ ý định re-run hay can thiệp thiết bị, BẮT BUỘC kiểm tra:
    1. Giờ hiện tại có nằm trong `ROLLING_BLOCK_WINDOWS` không:
       - Ca nuôi sáng: `05:05 - 09:30`
       - Ca nuôi trưa: `11:45 - 15:30`
       - Ca nuôi chiều: `17:45 - 21:30`
       - Dọn cache TikTok: `04:00 - 04:30`
    2. Tiến trình `multi-machine-feed` (`run_tiktok.py` / `feed_session`) có đang chạy trên farm không qua `psutil`.
  * **Hành động kỷ luật:** Nếu đang trong ca nuôi, **TUYỆT ĐỐI KHÔNG CAN THIỆP 2FA HOẶC RESET APP**. Báo cáo rõ ràng hiện trạng, giải thích nguyên nhân và chuyển giao cho watchdog tự động cuốn chiếu bù vào đêm tiếp theo hoặc khoảng rảnh giữa ca.

---

## 3. Bản Chất Lỗi "Fail" Do Rào Chắn Dual-Credential Gate
- **Cơ chế:**
  * Các tài khoản đã bật được 2FA nhưng Cột Pass vẫn là `None` (hoặc pass cũ cần xoay vòng) được ưu tiên xếp vào danh sách xử lý (`password_only=True` hoặc luồng kết hợp).
  * Khi vào màn hình đổi mật khẩu, TikTok đưa ra thách thức xác minh danh tính qua Email OTP.
  * Nếu hòm thư Outlook trên máy S7 chưa đồng bộ / chưa lấy được OTP 6 số kịp thời, adapter sẽ kích hoạt fail-safe thoát hàm để không làm crash runner.
  * Tuy nhiên, tại hàm kiểm chứng sau chạy `_verification()`, điều kiện `password_saved = not password_is_blank` phát hiện Cột D vẫn trống -> đánh dấu máy là `failed` kèm lý do `POST_SUCCESS_VERIFICATION_FAILED`.
  * **Ý nghĩa an toàn:** Giữ nguyên trạng thái để không cho phép GPM Supervisor đổi mật khẩu Hotmail trước khi TikTok có mật khẩu thật, tránh mất quyền khôi phục tài khoản vĩnh viễn.

---

## 4. Kiến Nghị Observability Cho Watchdog 2FA
- Trong `cron_night_tiktok_2fa_watchdog.py`, chuỗi `out` trả về từ runner chứa toàn bộ bảng kết quả `machine | source_row | username | status | reason`.
- Watchdog cần ghi chuỗi `out` này xuống file trace theo ngày:
  `D:/Taadaa/runtime/kibe/cron-state/night_2fa_trace_{today_str}.txt`
  và lưu đường dẫn vào `details["trace_path"]` trong `night_tiktok_2fa_state.json`.
- Khi đó, mọi phiên phân tích sự cố có thể đọc ngay danh sách lỗi chi tiết O(1) mà không cần quét lại thiết bị.
