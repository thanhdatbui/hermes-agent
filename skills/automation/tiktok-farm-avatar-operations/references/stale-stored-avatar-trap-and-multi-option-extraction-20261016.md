# Bẫy Tàn Dư Avatar Cũ Khi Chuẩn Hóa Lệch Niche & Kỷ Luật Trích Xuất Đa Phương Án (2026-10-16)

## 1. Bản Chất Sự Cố & Dấu Hiệu Nhận Biết
- **Hiện tượng**: Khi user gửi ảnh profile TikTok yêu cầu "Chuẩn hoá acc này", hệ thống phát hiện kênh bị lệch niche (ví dụ video trên profile 100% là Mèo con / Thú cưng, nhưng Excel ghi "Làng quê" và avatar trên profile là chữ 3D rác `LUẬN NG V`).
- **Cạm bẫy chết người (Stale Stored Avatar Trap)**:
  * Trong thư mục video gốc `$F_{src}$` hoặc video render `$F_{out}$` (ví dụ `D:/video goc/614/avatar.jpg`), thường tồn tại sẵn một file `avatar.jpg` từ các đợt vận hành cũ.
  * Coordinator vội vã ngộ nhận rằng file `avatar.jpg` này "đã có sẵn chú mèo rất đẹp" và dùng luôn để tạo preview, thậm chí hallucinate mô tả khuôn mặt mèo dù chưa thực sự soi mắt mở ảnh.
  * Thực tế: File `avatar.jpg` cũ đó là tàn dư của chủ đề Làng quê cũ (ảnh phong cảnh, người lớn, nhà cửa, hoa màu), dẫn đến việc gửi preview sai hoàn toàn và user phản ứng: *"Có phải mặt chú mèo éo đâu"*.

## 2. Quy Tắc Bắt Buộc Khi Chuẩn Hóa Kênh Bị Lệch Niche
1. **CẤM TUYỆT ĐỐI Dùng Lại `avatar.jpg` Có Sẵn**:
   - Bất kỳ khi nào phát hiện kênh bị lệch niche hoặc avatar hiện tại là tranh chữ/comic/rác:
   - Toàn bộ file `avatar.jpg` có sẵn trong `$F_{src}$` và `$F_{out}$` bị coi là **UNTRUSTED / STALE ARTIFACT**.
   - CẤM lấy file này làm preview hay gán lại cho kênh.

2. **Trích Xuất Frame Trực Tiếp Từ Video Thực Tế**:
   - Quét các video thực tế đang nuôi trên kênh trong `D:/TIKTOK-videonuoinick/<F_vid>/` (`1.mp4`, `2.mp4`...).
   - Trích xuất các frame tại các mốc giây `1s, 2s, 3s, 5s` để tìm đúng chủ thể (khuôn mặt nhân vật, con vật đại diện).
   - Nếu video nuôi chưa tải đủ hoặc không khớp: Crop trực tiếp từ thumbnail chất lượng cao trên screenshot profile người dùng cung cấp.

3. **Kỷ Luật Xuất Đa Phương Án (Multi-Option Contact Sheet)**:
   - Không chỉ xuất 1 ảnh đơn độc dễ bị chê không hợp gu. BẮT BUỘC tạo ít nhất **2 đến 4 Options** khác nhau (Option A: cận cảnh tươi sáng, Option B: hoạt cảnh sinh động, Option C: góc chụp khác...).
   - Ghép thành contact sheet 2x2 hoặc hàng ngang có nhãn Option A, B, C, D rõ ràng kèm circle preview mô phỏng viền tròn TikTok (R=256, làm tối 70% vùng ngoài).
   - Soi mắt thực tế xác nhận đúng chủ thể trước khi gửi `MEDIA:` cho user.

4. **Kỷ Luật Ngân Sách Diff Contract O(1) Cho Worker (<= 30 dòng)**:
   - Khi Coordinator ủy quyền Worker sửa script trích xuất qua `delegate_task` (TASK_KIND: EDIT):
   - Guard kiểm tra nghiêm ngặt `DIFF_BUDGET <= 30` dòng code thay đổi.
   - Để tránh lỗi `DIFF_BUDGET_EXCEEDED`:
     * Không viết code sinh từng option lặp đi lặp lại dài dòng.
     * Cô đọng bằng mảng cấu hình:
       ```python
       cfg = [('A','1.mp4_sec2.jpg',(0.2,0.7,0.15,0.85)), ('B','2.mp4_sec1.jpg',(0.15,0.65,0.2,0.8))]
       for k, fn, b in cfg:
           # crop, resize 512, make_circle, save
       ```
     * Giữ tổng `NEW_STRING` thay đổi gọn gàng trong 15–25 dòng code.
