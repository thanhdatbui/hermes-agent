# Full Video Pool Rescan & 2x2 Avatar Showcase Grid (2026-10-10)

## Context & Operator Correction
Khi Operator nhận thông báo "chưa tìm được frame đạt chuẩn từ vài video đầu" và ra lệnh dứt khoát:
**"Quét lại tạo ava coi"**

### Căn nguyên sai lầm của Agent:
1. **Bỏ cuộc sớm (Premature Surrender):** Chỉ kiểm tra 3-4 video đầu (`1.mp4`, `3.mp4`, `5.mp4`, `37.mp4`), thấy dính bẫy góc quay cận cảnh hoặc vignette tối là vội kết luận "toàn bộ kho video không có frame đạt chuẩn" và khôi phục avatar cũ.
2. **Đặc thù thư viện video TikTok (45 clip):** Một folder video nuôi 45 clip thường là hỗn hợp đa dạng: clip hướng dẫn (chụp từ sau gáy), clip b-roll phong cảnh, clip meme chữ dán, xen kẽ với 4-6 clip đời thường chất lượng cao quay ngoài trời, mặc Áo Dài, hoặc selfie cận cảnh.
3. **Thao thức của Operator:** Operator không cần Agent giải thích kỹ thuật dài dòng về việc frame bị mềm hay thiếu headroom; Operator muốn nhìn thấy **các phương án thực tế tốt nhất** được trích xuất từ kho video để trực tiếp chọn bằng mắt.

---

## Canonical 4-Step Rescan & Showcase Workflow

### Bước 1: Quét Lưới Nhanh Toàn Bộ Kho (Fast 45-Video Grid Sweep)
- Không quét dày đặc từng 0.1s trên toàn bộ 45 file làm timeout terminal (>30s trên HDD).
- Lấy mẫu 2-3 mốc thời gian tiêu biểu (ví dụ `1.5s`, `3.0s`, `4.5s`) trên mỗi video.
- Dùng Haar Cascade / OpenCV với kích thước khuôn mặt trung bình (face width từ `200` đến `650px`) để loại trừ các shot quá xa (người bé li ti) hoặc góc cận macro.
- Phân loại nhanh các video có mặt creator thành các nhóm phong cách:
  * Nhóm Chân dung trực diện (Frontal close-up portrait).
  * Nhóm Ngoại cảnh tươi cười (Outdoor daylight candid).
  * Nhóm Trang phục đặc trưng / Áo dài truyền thống (Áo Dài / OOTD).
  * Nhóm Nghệ thuật / Aesthetic tone trầm (Moody / Low-key beauty).

### Bước 2: Tinh Chỉnh & Cắt Khung Vuông Chuẩn 512x512
- Với mỗi phong cách, chọn frame đỉnh cao nhất (nụ cười tự nhiên, mắt mở to, không dính phụ đề vietsub ở cổ/cằm).
- Cắt cúp khung vuông tỷ lệ 1:1, căn chỉnh tâm khuôn mặt sao cho:
  * Đường mắt nằm ở 1/3 trên của hình tròn.
  * Đỉnh đầu / bờm tóc có khoảng thở ~8-12% headroom.
  * Cằm và cổ áo có khoảng đệm tự nhiên, không bị chạm sát biên dưới.

### Bước 3: Dựng Bảng Đối Chiếu 2x2 Vuông 900x900 (Mobile Telegram Standard)
- **CẤM GHÉP DẸT NGANG (Panoramic):** Ghép 3-4 ảnh nằm ngang (ví dụ 1280x560) sẽ bị app Telegram di động bóp dẹt mỏng dính, chữ mờ tịt khiến Operator phản ứng gay gắt.
- **Quy chuẩn hiển thị:**
  * Kích thước tổng: **900x900 px** (lưới vuông 2x2, mỗi ô 450x450 px).
  * Trên mỗi ô: vẽ vòng tròn trắng (bán kính 220px, tâm 225,225) để mô phỏng chính xác khung tròn avatar TikTok.
  * Banner trên: Ghi rõ số tập và mốc thời gian (ví dụ `1. Video 37 (4.5s)`).
  * Banner dưới: Mô tả ngắn gọn thần thái (ví dụ `Chan dung can mat, truc dien`).
- Đồng thời xuất riêng file ảnh vuông nguyên bản **512x512** của phương án được đánh giá cao nhất (Option 1).

### Bước 4: Thẩm Định Vision & Báo Cáo Có Bằng Chứng Trực Quan
- Gọi Vision API soi mắt cả ảnh bảng 2x2 và file avatar 512x512 trước khi gửi:
  * Xác nhận đúng 4 khuôn mặt của creator, chữ rõ ràng, không panel đen, không méo hình.
- Gửi đồng thời:
  1. `MEDIA:<path_to_2x2_grid.jpg>` để Operator chọn trực quan.
  2. `MEDIA:<path_to_top_option_512.jpg>` để Operator kiểm tra độ nét 1:1.
- Nêu rõ 4 option kèm đánh giá ưu/nhược điểm ngắn gọn, đề xuất phương án tối ưu nhất và chờ Operator chốt trước khi đồng bộ kho và kích hoạt runner.
