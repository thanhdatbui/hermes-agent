# Quy Tắc Đổi Nguồn Video, Đánh Số Render Nối Tiếp & Chống Trùng Kênh (Farm Taadaa)

## 1. Quy tắc Đổi Nguồn Video & Đánh Số Render Nối Tiếp (Switch-Source Offset Render)
- **BẮT BUỘC DỌN SẠCH CẢ 2 ĐẦU KHI ĐỔI NGUỒN (CLEAN BOTH ENDS)**:
  * Khi hoán đổi nguồn video cho 1 folder/nick (bằng `swap_single_folder_pipeline.py --clean-old`):
  * **Đầu 1 (Video gốc):** Xóa sạch 100% video cũ trong `D:/video goc/<raw>`.
  * **Đầu 2 (Video render thành phẩm):** BẮT BUỘC XÓA SẠCH 100% video render cũ trong `D:/TIKTOK-videonuoinick/<render>` (hoặc `TIKTOK-videonuoinick-admin`).
  * *Lý do cốt lõi:* TUYỆT ĐỐI KHÔNG để lẫn lộn giữa video render của niche cũ và niche mới trong cùng thư mục; tránh bot upload đăng lung tung làm lệch tệp kênh.
- **GIỮ NGUYÊN MỐC 'VIDEO ĐÃ ĐĂNG' TRONG EXCEL**:
  * Khi đổi nguồn video cho tài khoản đã đăng video (ví dụ đã đăng 13 video):
  * TUYỆT ĐỐI CẤM reset cột `Video Đã Đăng` về `0`. Cột này phản ánh số lượng video đã đăng thực tế của nick.
  * Tool bot upload luôn tự động pick video tiếp theo bằng công thức: `next_seq = video_da_dang + 1` (ví dụ `13 + 1 = 14`).
- **RENDER KHO MỚI ĐÁNH SỐ BẮT ĐẦU TỪ `(ĐÃ_ĐĂNG + 1)`**:
  * Khi dọn kho video render cũ và nạp batch render mới sang thư mục đích (`D:/TIKTOK-videonuoinick/<folder>`), bắt buộc truyền cờ `--start-seq <video_da_dang + 1>` (ví dụ `--start-seq 14`).
  * Danh sách video render mới ra phải là `14.mp4`, `15.mp4`, ..., `53.mp4`.
  * Kho render mới tuyệt đối không có file `1`, `2`, `3`... để tránh tool bị xung đột hoặc đăng trùng mốc cũ.
- **BẪY KIỂM TRA LUỒNG VIDEO (AUDIO-ONLY STREAM TRAP & FFPROBE V:0 CHECK)**:
  * Khi tải video từ TikTok qua yt-dlp, một số video thực chất là ảnh tĩnh kèm nhạc/âm thanh, file tải về chỉ có luồng audio mà không có video stream (`v:0` is empty).
  * FFmpeg render gặp file này sẽ crash ngay lập tức với lỗi `ffmpeg rc=4294967274`.
  * BẮT BUỘC chạy kiểm tra luồng video trước khi render:
    `ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of csv=p=0 "<file.mp4>"`
  * Nếu output rỗng -> Xóa ngay file lỗi và tải bù video khác.

## 2. Quy tắc Chống Trùng Kênh & Tái Tận Dụng Video Thừa (GaiXinh Dedup & Leftover Recycling)
- **QUOTA FOLDER CHUẨN**: Mỗi folder video nuôi nick quy định `min 40, max 45` video (`--min-videos 40 --max-videos 45`).
- **CƠ CHẾ CLAIM ĐỘC QUYỀN (EXCLUSIVE CLAIM)**:
  * Mỗi kênh TikTok gái xinh chỉ gán trọn vẹn cho 1 folder duy nhất.
  * Quản lý lưu vết 2 lớp: File trung tâm `D:/Taadaa/Tiktok-video/data/gaixinh_channel_claims.json` và file cục bộ `channel_info.json` trong thư mục video gốc.
  * Khi chạy phân phối: Tự động bỏ qua `[SKIP CLAIMED]` các kênh đã được nhận.
  * Khi chạy với `--clean-old`: Tự động nhả claim cũ của folder để tái phân bổ sạch.
- **CẮT LÁT & GOM VIDEO THỪA SANG BỂ GỘP (CURATED POOL RECYCLING)**:
  * Kênh Độc Quyền lấy tối đa 45 video đầu (`vids[:45]`) nạp vào folder chính.
  * Toàn bộ video thừa từ video thứ 46 trở đi (`vids[45:]`) tự động đẩy vào **Bể Gộp đa kênh (Curated Channels)** để chia đều cho các nick Đa Kênh, tối ưu 100% tài nguyên đã cào.

## 3. Quy tắc Đăng Nhập Bù Cho Account Đổi Avatar Khi Thiếu Switcher
- Khi upload avatar tự động gặp lỗi `ACCOUNT_SWITCHER_FAILED` (Profile verify mismatch / không thấy nick trong danh sách switcher):
  * Kiểm tra tài khoản trong `taikhoan_dat_v2_updated .xlsx` hoặc tracker DB.
  * Nếu tài khoản có đủ **ID + Mật khẩu TikTok + Mã 2FA TOTP**, tài khoản hoàn toàn đủ điều kiện đăng nhập (usable) mà **không phụ thuộc vào mật khẩu mail**.
  * Chạy flow đăng nhập bù `python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <id>` trước khi tiếp tục upload avatar.

## 4. Tiêu Chuẩn Niche Hot View Thuần Việt & Không Tiếng Nước Ngoài
- **ĐỊNH NGHĨA "NICHE NHIỀU VIEW" $\ne$ "IDOL TRIỆU FOLLOW QUEN MẶT"**:
  * CẤM cào video của các KOL/Idol nổi tiếng triệu follow (như Ngọc Kem, Lê Bống...) vì mặt quá quen, dễ bị thuật toán TikTok gắn cờ tài khoản reup/clone và ăn gậy bản quyền.
  * BẮT BUỘC chọn kênh quy mô vừa hoặc nhỏ, mang tính chất chia sẻ đời thường cá nhân để nick trông như người dùng thật.
- **CỐT LÕI BẤT BIẾN: KHÔNG ĐƯỢC CÓ TIẾNG NÓI NƯỚC NGOÀI**:
  * Tuyệt đối không có voiceover, lồng tiếng, hoặc tiếng người nói tiếng Trung, tiếng Anh hay ngoại ngữ khác.
  * **Các nhóm nội dung được phép & ưu tiên cao:**
    1. **Douyin Gái Xinh thuần visual / biến hình / nhảy trend:** Chỉ có nhạc nền bắt tai hoặc sound trend, KHÔNG CÓ THOẠI TIẾNG TRUNG $\rightarrow$ Người Việt Nam xem rất nhiều, giữ chân người xem cao, cắn đề xuất mạnh.
    2. **Oddly Satisfying & ASMR:** Cắt xà phòng, cắt cát động lực, ép đồ vật, âm thanh vật lý thu sát mic $\rightarrow$ 100% không tiếng người nói, không rào cản ngôn ngữ, retention rate kịch trần.
    3. **Gái Xinh & Creator cá nhân Việt Nam:** Nhảy trend nhẹ nhàng, đời thường, nhạc TikTok Việt.
    4. **Thú cưng cute / Chó mèo hài hước:** Visual dễ thương, không rào cản ngôn ngữ.

## 5. Quy tắc Xử Lý Tràn Đĩa Admin Farm (0 MB Free / Disk Exhaustion)
- **Bối cảnh:** Ổ `D:` máy Admin chỉ có dung lượng 1 TB (931 GB khả dụng). Khi render thành phẩm đạt ~21.000 clip kết hợp với kho gốc, ổ D: sẽ bị tràn về `0.00 MB free`, khiến Downloader và Render Chain đồng loạt crash (`[Errno 28] No space left on device`, `System.IO.IOException`).
- **Quy tắc Giải phóng Dung lượng An toàn (~100 - 150 GB):**
  * Điện thoại farm chỉ lấy video từ thư mục render (`TIKTOK-videonuoinick-admin`) để đăng, HOÀN TOÀN KHÔNG đụng đến kho video gốc `video goc may 2`.
  * Với các folder ĐÃ RENDER XONG THÀNH PHẨM ($\ge 30-40$ clip trong `TIKTOK-videonuoinick-admin`), tiến hành dọn sạch các file `.mp4` trong `D:/video goc may 2/<folder>` tương ứng, chỉ giữ lại `avatar.jpg` và `channel_info.json`.
- **Phòng Chống Tải Dư Thừa Tái Tràn Đĩa:**
  * Downloader bắt buộc kiểm tra đối soát 2 chiều: Nếu thư mục render thành phẩm đã có $\ge 30$ clip thì BỎ QUA NGAY, tuyệt đối không tải lại raw. Chỉ tải khi CẢ 2 NƠI ĐỀU THIẾU.

