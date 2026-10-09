# Quy trình Hoán Đổi Nguồn Video (Folder Swap), Tiêu Chuẩn Niche Hot Thuần Việt & Dọn Dẹp Đĩa Farm Admin

## 1. Định Nghĩa "Niche Hot View Thuần Việt" Cho TikTok Farm
Khi User yêu cầu "Niche hot nhiều view" hoặc "nội dung thuần Việt", quy tắc cốt lõi là **KHÔNG ĐƯỢC CÓ TIẾNG NÓI NƯỚC NGOÀI** (không tiếng xì xồ tiếng Trung, không tiếng Anh lảm nhảm làm lộ nick clone/reup ngoại lai):
- **Gái xinh Douyin Visual**: ĐƯỢC PHÉP nếu là video thuần visual biến hình, nhảy trend theo nhạc, không có voice nói tiếng Trung.
- **Oddly Satisfying & ASMR**: ĐƯỢC PHÉP nếu 100% là âm thanh vật lý thực tế thu sát mic (cắt xà phòng, cát động lực, ép đồ vật) hoặc nhạc không lời, không có người nói tiếng Anh.
- **Kênh cá nhân / Creator vừa & nhỏ Việt Nam**: Tuyệt đối **KHÔNG** lấy kênh idol triệu view nổi tiếng (Ngọc Kem, Lê Bống...) vì mặt quá quen, dễ bị report và thuật toán bóp reach. Chọn creator cá nhân vừa phải nhảy trend nhạc Việt, đời thường để nick tự nhiên như user thật.
- **Thú cưng / Cute animals**: Visual hành động dễ thương, âm thanh tự nhiên.

## 2. Quy Trình 5 Bước Hoán Đổi Toàn Bộ Nguồn Video Cho Nick (Folder Swap)
Khi nick bị đăng nhầm nội dung (ví dụ profile nữ VN nhưng dính video người nước ngoài) hoặc cạn nguồn:
1. **Dọn dẹp sạch cả 2 đầu**:
   - Xóa toàn bộ file cũ trong folder video gốc: `D:/video goc/<raw_id>` (Kibe) hoặc `D:/video goc may 2/<raw_id>` (Admin).
   - Xóa toàn bộ file cũ trong folder render tương ứng: `D:/TIKTOK-videonuoinick/<render_id>`.
2. **Tải nguồn mới từ kênh chỉ định**:
   - Tải tối thiểu 40 clips đạt dải thời lượng vàng (10s – 45s).
   - Kiểm tra stream qua `ffprobe`: Bắt buộc file MP4 phải có đầy đủ cả luồng `video` và `audio`. Loại bỏ file chỉ có `mp3` audio stream để tránh crash FFmpeg khi render (`ffmpeg rc=4294967274`).
3. **Tạo Avatar mới 512x512**:
   - Dùng FFmpeg hoặc `_make_avatar.py` trích xuất frame rõ nét từ video 1 tạo file `avatar.jpg`.
4. **Render nối tiếp bảo toàn sequence của nick**:
   - Kiểm tra cột `Video Đã Đăng` trong file `TikN.xlsx` (ví dụ: đã đăng 26 clip).
   - Thiết lập `--start-seq = Video_Đã_Đăng + 1` (ví dụ: `--start-seq 27`) để bot auto upload nhặt tiếp tục mà không bị đè hay trùng sequence cũ.
5. **Đồng bộ nguyên tử**:
   - Cập nhật sheet `TaiKhoan` và `Hashtag theo Folder` trong `TikN.xlsx`.
   - Cập nhật SQLite `state.db` (bảng `folders` và `videos`).
   - Ghi nhận độc quyền vào sổ cái `gaixinh_channel_claims.json`.

## 3. Quản Lý Dung Lượng Ổ Đĩa D: Trên Farm Admin (931 GB Hard Cap)
Ổ đĩa D: của Admin có dung lượng nhỏ (931 GB) so với Kibe (4 TB), thường xuyên bị tràn đĩa (`[Errno 28] No space left on device` / `System.IO.IOException`):
- **Nguyên tắc giải phóng đĩa an toàn O(1)**:
  - Chỉ dọn dẹp các file `.mp4` trong `D:/video goc may 2/<raw_id>` của những folder **ĐÃ RENDER XONG THÀNH PHẨM** vào `D:/TIKTOK-videonuoinick-admin/<render_id>` (đạt $\ge 30$ clip).
  - Giữ lại file `avatar.jpg` và `channel_info.json` trong folder gốc.
  - Bot điện thoại chỉ tải từ thư mục render, hoàn toàn không ảnh hưởng tới hoạt động farm.
  - Giải phóng ngay ~90 – 100 GB dung lượng trống để downloader và render chain tiếp tục hoạt động.
- **Mapping Admin**:
  `raw_f = (slot - 1) * 80 + (machine - 200)`
  `render_f = (machine - 201) * 8 + slot`
