# Chu kỳ 6 ngày (Modulo 6) & Cơ chế Dưỡng Sinh Rửa Trust Score (2026-09-15)

## 1. Bối cảnh & Bản chất thuật toán TikTok
- Chạy follow liên tục hàng ngày khiến `anomaly score` (điểm nghi vấn spam) tích lũy trên server TikTok không bao giờ về 0, dẫn tới hiện tượng phạt nhả follow dây chuyền.
- TikTok không phạt hành vi mở app lướt xem video giải trí. Việc có **ngày nghỉ hành vi follow (Action Cooldown)** kết hợp lướt feed nuôi chính là cơ chế tự nhiên giúp kích hoạt decay penalty (rửa sạch điểm nghi vấn).
- Tỷ lệ vàng: Cứ 2 cữ follow bắt buộc kẹp 1 video mới để acc có profile creator active.

## 2. Bảng phân bổ chu kỳ 6 ngày (Epoch: 2026-09-01)
`day_cycle = (now.date() - epoch).days % 6`
- **Day 0:** Row 1, 3, 5, 7 $\to$ Cày Follow (10-20/phiên) + Upload video.
- **Day 1:** Row 2, 4, 6, 8 $\to$ Cày Follow (10-20/phiên) + Upload video.
- **Day 2:** Row 1, 3, 5, 7 $\to$ **DƯỠNG SINH RỬA TRUST (100% CHỈ LƯỚT FEED, 0 FOLLOW, KHÔNG UPLOAD)**.
- **Day 3:** Row 2, 4, 6, 8 $\to$ Cày Follow (10-20/phiên) + Upload video.
- **Day 4:** Row 1, 3, 5, 7 $\to$ Cày Follow (10-20/phiên) + Upload video.
- **Day 5:** Row 2, 4, 6, 8 $\to$ **DƯỠNG SINH RỬA TRUST (100% CHỈ LƯỚT FEED, 0 FOLLOW, KHÔNG UPLOAD)**.
- Day 6 lặp lại Day 0 mãi mãi.

## 3. Cơ chế Opportunistic Upload (Đăng video cơ hội cả Phiên 1 & 2)
- Thay vì chỉ cho phép đăng ở Phiên 2 (rủi ro lỗi script làm trượt nhịp kéo dài 6-8 ngày mới up video):
  - Kích hoạt `-AllowUploadHook` cho cả Phiên 1 và Phiên 2 vào các ngày cày.
  - Sổ cái liên tiến trình `shift_upload_history.json` tự động khóa an toàn: nếu Phiên 1 đã đăng thành công, Phiên 2 tự động bỏ qua (`already_uploaded_in_shift`). Nếu Phiên 1 lỗi/chưa đăng được, Phiên 2 lập tức đăng bù.

## 4. Quản trị Bộ nhớ & Thiết bị (Samsung S7)
- **CẤM TUYỆT ĐỐI** thêm bước xóa cache app TikTok trước mỗi lần switch account (tạo signature bot lặp lại).
- Việc dọn cache chỉ nhằm mục đích chống phình ổ cứng 32GB của S7, thực hiện cuốn chiếu cuối ngày qua cron 04:00 sáng.
- Hàm `is_account_in_follow_cooldown` bắt buộc là **pure read-only**, chuẩn hóa 100% UTC, không được mutate/ghi đè file JSON khi đang kiểm tra để tránh race-condition.
