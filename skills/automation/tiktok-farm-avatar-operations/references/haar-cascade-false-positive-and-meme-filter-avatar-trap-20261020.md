# Bẫy Thuật Toán Haar Cascade & Cạm Bẫy Meme Filter / Sticker Khi Trích Xuất Avatar (2026-10-20)

## 1. Bối Cảnh Sự Cố & Hiện Tượng "Hình Này Không Hiểu"
Khi thực hiện batch tự động quét và "chữa lành" (auto-heal) avatar cho hàng loạt folder bị lỗi/thiếu avatar bằng thuật toán thị giác máy tính cổ điển (`cv2.CascadeClassifier(haarcascade_frontalface_default.xml)`):
- Thuật toán tự động tìm khuôn mặt, tính điểm độ nét Laplacian và tự ý crop ghi đè vào `avatar.jpg` mà không có bước kiểm định ngữ nghĩa (Multimodal Vision LLM / Human verification).
- Khi tạo ảnh tóm tắt gửi cho User kiểm tra, User phản ứng ngay: *"Hình này k hiểu"* vì toàn bộ ảnh crop ra đều dị hợm, vô nghĩa hoặc không phải avatar cá nhân.

## 2. 4 Cạm Bẫy Của Thuật Toán Haar Cascade Trên Video TikTok / Douyin
1. **Bẫy Sticker Hoạt Hình & Đồ Họa 2D (Cartoon Sticker False Positive)**:
   - Các video chèn icon hoạt hình (thỏ, bé chibi, má hồng) thường làm Haar Cascade nhận diện nhầm má hồng / mắt vẽ thành khuôn mặt người thật. Kết quả crop ra nửa khuôn mặt thật bị ghép méo mó với sticker đồ họa.
2. **Bẫy Filter Hài Hước / Biến Dạng Mặt (TikTok Distort & Meme Filters)**:
   - Trong các video giải trí, người dùng hoặc diễn viên hay dùng filter kéo méo mặt (môi sưng to, mắt lồi, đầu dị dạng).
   - Về mặt hình học, Haar Cascade vẫn thấy mắt/mũi/miệng và chấm điểm độ nét cao, dẫn tới việc bóc ra một avatar troll/dị hợm làm ảnh đại diện kênh!
3. **Bẫy Bắt Nhầm Bàn Tay / Vật Thể (False Positive Hand/Object)**:
   - Khi nhân vật cầm điện thoại, cầm cốc nước trước ngực, thuật toán bắt nhầm kẽ tay thành sống mũi/mắt, tính toán bounding box lệch hoàn toàn xuống ngực hoặc tay, dính đầy chữ phụ đề và logo CapCut.
4. **Bẫy Video Gameshow / Truyền Hình Đa Nhân Vật (Celebrity & TV Show Trap)**:
   - Trong các video trích đoạn Running Man, Rap Việt, talkshow: khuôn mặt xuất hiện là khách mời hoặc MC kèm banner chữ vàng to đùng trên màn hình, hoàn toàn không phải creator độc bản của kênh nuôi nick.

## 3. Cạm Bẫy Trình Bày Contact Sheet ("Hình Này Không Hiểu")
- **Lỗi bố cục gây khó hiểu**: Đặt 1 ảnh vuông ở trên và chính ảnh đó vẽ thêm vòng tròn xanh ở dưới, lặp lại cho 4 cột mà không có nhãn đối chiếu `BEFORE (Cũ)` vs `AFTER (Mới)`. Người xem nhìn vào chỉ thấy 2 hàng ảnh giống hệt nhau với nội dung kỳ quặc nên không hiểu ý đồ truyền tải.
- **Quy chuẩn bố cục Contact Sheet**:
  * Luôn đối soát rõ ràng 2 cột hoặc 2 hàng: `ẢNH CŨ TRÊN ĐĨA (Lỗi/Rác)` $\longleftrightarrow$ `ẢNH MỚI BÓC TÁCH (Kèm vòng tròn xanh mô phỏng viền TikTok)`.
  * Ghi rõ nguồn trích xuất: `Folder N | Clip M.mp4 tại X.Xs`.

## 4. Quy Trình Bắt Buộc Khi Auto-Heal Avatar Hàng Loạt
1. **CẤM TUYỆT ĐỐI Ghi Đè Ngầm**: CẤM tự ý ghi đè `avatar.jpg` và cắm marker `.manual_avatar_locked` khi chỉ dựa vào Haar Cascade.
2. **Thẩm Định Đa Tầng (Haar Filter -> Vision LLM Gate)**:
   - Tầng 1 (Haar Cascade / Deep Learning Face Detector): Chỉ đóng vai trò trích xuất thô các ứng viên (candidates).
   - Tầng 2 (Multimodal Vision LLM Gate): Đọc ảnh ứng viên và loại bỏ ngay lập tức:
     * Ảnh có biểu cảm troll/méo mó do filter.
     * Ảnh dính sticker hoạt hình hoặc chữ phụ đề đè lên mặt.
     * Ảnh không phải creator cá nhân (ảnh gameshow, logo kênh cũ).
3. **Canary Phê Duyệt**: Chỉ nạp vào hệ thống chính thức sau khi xuất bảng Contact Sheet có chú thích rõ ràng và được phê duyệt.
