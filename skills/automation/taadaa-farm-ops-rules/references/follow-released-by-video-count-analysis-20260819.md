# Phân Tích Thực Tế Tỉ Lệ Nhả Follow Theo Số Lượng Video Đã Đăng (19/08/2026)

## 1. Dữ Liệu Thực Nghiệm Trên Toàn Farm (64 Trạng Thái / 525 Lượt Follow)
- **Row 1 (Nick đã đăng 8 – 12 video)**:
  - Khả năng follow: Follow thành công 4 – 8 nick liên tiếp trong ca trước khi chạm ngưỡng rate-limit.
  - Tổng sản lượng: Đạt 525 lượt follow thành công trong ngày.
  - Tỉ lệ nhả follow: ~60-70% (sau khi đã follow được một lượng nhất định).
- **Row 3 & Row 5 (Nick 0 video — chưa từng đăng video)**:
  - Khả năng follow: **100% bị TikTok nhả follow ngay từ lượt đầu tiên (followed = 0)**.
  - Hiện tượng: Vừa tap nút Follow -> kéo `pull-to-refresh` -> nút lập tức bật đỏ lại thành "Follow" sau 3.5s.
  - Lý do: TikTok phân loại nick 0 video là "Bot / Tài khoản rác", gắn cờ chặn follow ngay lập tức.

## 2. Quy Tắc Vận Hành Chuẩn
1. **Nick 0 video (Row 2, Row 3, Row 4, Row 5...)**:
   - TUYỆT ĐỐI KHÔNG bật kịch bản Follow.
   - Chỉ chạy thuần túy ca Lướt Feed (nuôi nick) + Đăng tối thiểu 1-2 video trước khi cho đi follow chéo.
2. **Xử lý khi phát hiện nhả follow (`FOLLOW_FAILED`)**:
   - Dừng ngay lượt follow của nick đó, cô lập theo ngày (`follow_failed_date = YYYY-MM-DD`).
   - Tự động đóng app TikTok, clear recent apps và đưa máy về màn hình chính (Home) sạch sẽ.
