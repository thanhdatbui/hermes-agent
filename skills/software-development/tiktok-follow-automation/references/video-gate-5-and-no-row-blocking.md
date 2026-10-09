# Quy Tắc Gate Video >= 5 & Không Chặn Cứng Row Cho Follow Hook

## 1. Ngưỡng Tối Thiểu 5 Video (User Chốt 11/09/2026)
- **Quy tắc an toàn:** Bắt buộc tài khoản phải có tối thiểu 5 video (`video_count >= 5`) mới được kích hoạt follow hook.
- **Hiện tượng thực tế:** Các tài khoản mới (< 5 video) chưa đủ điểm trust và tương tác tự nhiên, khi đi follow sẽ bị máy chủ TikTok áp cơ chế silent action-block và nhả follow ngay sau khi tải lại trang cá nhân (unfollow ảo).
- **Hành vi xử lý:** Nếu `video_count < 5`, safe-skip ngay với lý do `under-5-videos-follow-disabled`.

## 2. Gỡ Bỏ Hoàn Toàn Việc Chặn Cứng Theo Row
- **Nguyên nhân lỗi cũ (Anti-Pattern):** Code từng có khối `if row_idx in (3, 4, 5, 6): return skipped (tik{row}-warmup-feed-only)`. Logic này chặn oan tất cả nick ở Row 3..6 dù nick đã có 5–19 video.
- **Chuẩn hóa:** MỌI ROW (Row 1 đến Row 8), bất kỳ nick nào có `video_count >= 5` đều được phép kích hoạt follow hook bình thường.

## 3. Đồng Bộ Báo Cáo Chốt Phiên
- Mọi báo cáo chốt phiên farm nuôi acc BẮT BUỘC phải đề cập đủ 3 trụ cột:
  1. Lướt Feed
  2. Đăng video (Upload hook - chỉ chạy ở Phiên 2)
  3. Follow chéo (Follow hook - số lượt, số máy đủ điều kiện >= 5 video)
- Tuyệt đối không bỏ sót thông tin Follow trong báo cáo.
