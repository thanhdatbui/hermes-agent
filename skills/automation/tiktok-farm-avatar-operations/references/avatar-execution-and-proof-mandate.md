# Invariant Chuẩn Hóa Toàn Diện: Ghim Top Phải Đi Kèm Đổi Avatar Thực Tế

## 1. Bản chất sự cố
- Khi nhận yêu cầu "chuẩn hoá kênh", Coordinator thường chỉ chạy `pin_top_videos.py` rồi vội vàng chụp ảnh báo cáo hoàn tất ghim top view mà **bỏ quên bước đổi/cập nhật Avatar** lên profile TikTok thật.
- Người dùng bức xúc và bắt lỗi ngay lập tức: `"Chuẩn hoá ava đâu?"`.
- Sự thiếu sót bắt nguồn từ việc ngộ nhận trạng thái cột Avatar trong sổ cái Excel ("OK") hoặc thấy trên profile có hình ảnh là coi như xong, mà không thực sự đẩy file `avatar.jpg` chuẩn hoá vào nick qua công cụ tự động.

## 2. Quy trình chuẩn hoá kênh bắt buộc (Non-negotiable)
Khi thực hiện chuẩn hoá một kênh TikTok (`@username`), Coordinator **BẮT BUỘC** hoàn thành đủ 2 hạng mục cốt lõi trước khi chốt phiên:
1. **Avatar Profile:**
   - Kiểm tra file `avatar.jpg` trên đĩa local (`D:/video goc/<id>/avatar.jpg` hoặc `D:/TIKTOK-videonuoinick/<folder>/avatar.jpg`).
   - Đảm bảo độ nét (Laplacian var đạt chuẩn, sạch chữ 100%, đúng niche xe/người/thú cưng).
   - **BẮT BUỘC chạy engine upload avatar:** `python D:/Taadaa/tools/run_upload_avatar.py --tik <N> --machine <M>` (tách riêng chế độ avatar-only, có khóa an toàn).
2. **Ghim Top Views:**
   - Chạy `python D:/Taadaa/tools/pin_top_videos.py --machine <M> --account <user>`.
   - Ghim các video top view theo quy tắc LIFO.

## 3. Bằng chứng thị giác nghiệm thu (Gate 6)
- **CẤM** chỉ chụp ảnh màn hình sau khi ghim video mà chưa có avatar mới.
- Ảnh chụp màn hình nghiệm thu cuối cùng (`screencap` kéo về local và soi mắt qua `browser_vision`) phải thể hiện đồng thời:
  1. Vòng tròn Avatar hiển thị đúng hình ảnh mới (sắc nét, không còn là hình người mặc định hay logo cũ).
  2. Hàng video đầu tiên có nhãn đỏ "Đã ghim" đúng số lượng video top.
  3. Đúng tên tài khoản `@username` và không bị popup che khuất.
