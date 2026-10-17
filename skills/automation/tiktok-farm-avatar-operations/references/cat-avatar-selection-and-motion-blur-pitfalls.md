# Chống Cắt Frame Mờ Cảnh Động & Tiêu Chuẩn Bộ Ảnh Chân Dung Avatar Mèo/Thú Cưng (2026-10-17)

## 1. Bài Học Sự Cố: "Có Phải Mặt Chú Mèo Éo Đâu" & "K Cái Nào Ổn Cả"
1. **Lỗi 1 (Lấy nhầm avatar rác cũ)**:
   - Thư mục nguồn video của kênh (`D:/video goc/<F_src>/avatar.jpg`) chứa file avatar tàn dư của chủ đề cũ (chữ 3D nền lửa, phong cảnh làng quê).
   - Agent ngộ nhận file có sẵn là avatar hợp lệ, dẫn đến nạp ảnh sai lệch hoàn toàn so với nội dung 6 video mèo trên kênh.
2. **Lỗi 2 (Cắt frame tự động từ video chuyển động mờ/nhếch nhác)**:
   - Khi sửa sai bằng cách cắt frame ngẫu nhiên từ video (ví dụ 1s, 2s trong `1.mp4`, `2.mp4`, `3.mp4`), cảnh video là hoạt cảnh mèo ăn dặm, mèo đi lại ngoài trời, dính góc chụp xa, ánh sáng mờ hoặc phụ đề/vật thể xung quanh.
   - User phản hồi: *"K cái nào ổn cả đổi cái khác"*.
   - **Nguyên nhân**: Avatar profile TikTok là hình tròn nhỏ hiển thị trên mobile. Ảnh cắt thô từ cảnh chuyển động không đạt tiêu chuẩn chân dung: mắt không nhìn thẳng, tỷ lệ khuôn mặt quá nhỏ hoặc phông nền nhếch nhác.

## 2. Tiêu Chuẩn Vàng Của Avatar Kênh Thú Cưng / Mèo (Studio-Grade Cat Portrait)
Đối với kênh chủ đề Thú cưng / Mèo vui / Chó cảnh:
1. **Tiêu chuẩn ngũ quan & ánh mắt**:
   - **Mắt nhìn thẳng ống kính**: Đôi mắt to tròn, sáng rõ (màu xanh biếc, hổ phách hoặc xanh ngọc), thể hiện rõ thần thái tinh anh/dễ thương.
   - **Rõ nét từng cọng lông & ria mép**: Ảnh chụp cận cảnh chân dung (close-up portrait), không mờ nhòe do nén video.
   - **Bố cục khung tròn**: Khuôn mặt mèo chiếm 65% - 75% diện tích vòng tròn, khoảng trống đỉnh đầu (headroom) từ 10% - 15%, cấm cắt lẹm tai hay cúp cằm.
2. **Nguồn ảnh chất lượng cao**:
   - Nếu frame video gốc không có cảnh cận cảnh tĩnh đạt chất lượng cao:
   - Tận dụng kho avatar chân dung đã qua kiểm duyệt của các kênh cùng Niche trong farm:
     * Niche `Mèo vui` / `Thú cưng`: `D:/video goc/95/avatar.jpg`, `D:/video goc/415/avatar.jpg`, `D:/video goc/114/avatar.jpg`, `D:/video goc/118/avatar.jpg`...
   - Luôn tạo contact sheet 4 options (2x2 grid) với các giống mèo khác nhau (mèo mướp vằn mắt xanh, mèo con trắng ngây thơ, mèo tam thể lông xù, mèo Anh lông ngắn mắt cam) để User lựa chọn nhanh.

## 3. Quy Trình Trình Bày 4 Options Cho User
1. Luôn xuất ảnh contact sheet tổng hợp 2x2: `cat_batch_preview.jpg` kèm viền tròn profile mô phỏng.
2. Soi mắt qua `browser_vision` kiểm chứng:
   - Xác nhận cụ thể giống mèo, màu mắt, tư thế khuôn mặt.
   - Không mô tả chung chung hoặc hallucinate.
3. Khi User chốt option cụ thể: đồng bộ ngay vào cả 3 đầu thư mục (`F_src`, `F_out`, và `TIKTOK-videonuoinick/<F_out>`), gắn marker `.manual_avatar_locked` và đẩy vào `avatar_replace_queue`.
