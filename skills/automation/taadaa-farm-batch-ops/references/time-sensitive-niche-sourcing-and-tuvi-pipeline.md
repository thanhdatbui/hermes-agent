# Sourcing Niche Nhạy Cảm Thời Gian (Tử Vi, Phong Thủy, Vận Hạn) & Chiến Lược Phôi Sạch

## 1. Bản Chất Bẫy Niche "Tử Vi / Vận Hạn" Cũ (Stale-Year Pitfall)
- **Hiện tượng:** Các kênh TikTok dạng clone AI công nghiệp (như `@francesuhunt5` - Hồ Mỹ Ly) thường in chết chữ tiêu đề vào video/ảnh bìa: *"Tử vi tuổi Hợi tháng 7 âm lịch 2025"*, *"Tử vi tuổi Ngọ tháng 6 nhuận âm lịch 2025"*.
- **Hậu quả trên Phone Farm:** Nếu downloader quét phải các kênh này và tải về reup/render lên dàn nick vào cuối năm 2026 (năm Bính Ngọ), người xem lướt qua thấy chữ "2025" hoặc "tháng nhuận" (2026 không có tháng 6 nhuận, 2025 mới có) sẽ bỏ qua trong 1 giây, khiến retention tụt dốc, tài khoản bị thuật toán đánh giá spam nội dung rác và bóp reach toàn kênh.

## 2. Quy Luật Thời Điểm & Tâm Lý Người Xem (Temporal Alignment)
Vào giai đoạn cuối năm (từ cuối tháng 10 dương lịch, tức khoảng tháng 9–10 âm lịch):
- **Góc 1: 3 tháng cuối năm hiện tại (Tháng 10, 11, 12 Âm lịch):** Người xem tìm kiếm biến động tài lộc, con giáp đổi vận phút chót, con giáp cần cẩn trọng tiểu nhân/hao tài cuối năm.
- **Góc 2: Đón đầu vận hạn năm mới (Năm tiếp theo):** Từ tháng 10–11 dương lịch là thời điểm vàng người dùng bắt đầu săn đón dự báo cả năm kế tiếp (ví dụ cuối 2026 săn đón "Tử vi năm 2027 Đinh Mùi").

## 3. Kiến Trúc 3 Tầng Cào Nguồn Niche Tử Vi / Thời Điểm

### Tầng 1: Cào TikTok / YouTube Shorts VN (Reup nhanh có chọn lọc)
- **Điều kiện an toàn:** BẮT BUỘC lọc video đăng trong vòng 30 ngày gần nhất (`--dateafter now-30d` trên yt-dlp).
- **Bộ lọc loại trừ:** Tuyệt đối không cào các kênh clone có chữ dán chết trên video; chỉ cào kênh dạng người thật/chuyên gia phong thủy hoặc kênh không chèn mốc năm cũ to đùng trên màn hình.
- **Từ khóa truy vấn chuẩn:**
  - `tử vi tháng 10 âm lịch [NĂM_HIỆN_TẠI]`
  - `tử vi 3 tháng cuối năm [NĂM_HIỆN_TẠI]`
  - `tử vi năm [NĂM_TIẾP_THEO] 12 con giáp`

### Tầng 2: Cào Phôi Sạch từ Douyin / Kuaishou (Chuẩn MMO Bền Vững)
Thực tế 90% video AI linh vật dát vàng, tượng Phật 3D khói sương đều lấy từ các kênh Sinh tiếu / Vận thế bên Douyin:
- **Ưu điểm vượt trội:**
  - Video 1080p/4K cực nét, không dính chữ tiếng Việt trên nền video.
  - Phôi video linh vật / tượng Phật chuyển động có tính "bất tử" (evergreen), dùng làm background loop ghép kịch bản cho bất kỳ tháng hay năm nào.
  - Douyin luôn đi trước xu hướng: Các kênh mảng Sinh tiếu Trung Quốc luôn làm trước vận hạn năm mới từ rất sớm.
- **Từ khóa cào phôi Douyin:**
  - `生肖运势` (Vận thế 12 con giáp)
  - `属相运程` (Vận trình con giáp)
  - `佛祖保佑` / `神像壁纸` / `生肖壁纸` (Hình nền linh vật / tượng Phật động sạch chữ)

### Tầng 3: Tự Động Hóa Toàn Phần (Web Scraper Text + VieNeu-TTS + Video Plate)
Giải pháp độc lập, không phụ thuộc vào việc đi "nhặt mót" video làm sẵn:
1. **Nguồn text kịch bản:** Cào RSS / bài viết mới mỗi tuần từ các chuyên trang lớn: `lichngaytot.com`, `tuvingaynay.com`, `vansu.net`.
2. **Xử lý kịch bản:** LLM tóm tắt thành kịch bản 45–55s theo khung: Hook giật tít -> Vận trình tài lộc -> Điểm chú ý -> Lời khuyên hóa giải.
3. **Lồng tiếng tự động:** Dùng engine VieNeu-TTS sẵn có (`D:/Taadaa/douyin-auto-dub`, giọng `Thiện Minh` trầm ấm phong cách kể chuyện tâm linh hoặc `Trúc Ly` cảm xúc).
4. **Render:** Ghép audio TTS vào kho phôi sạch Douyin + burn phụ đề động tiếng Việt mới 100%.
