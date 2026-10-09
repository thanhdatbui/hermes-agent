# Pipeline Phân Phối Video Gái Xinh 2 Tầng & Cào Douyin Nội Địa (2026-09-24)

## 1. Kiến Trúc 2 Tầng Chuẩn Hóa (`smart_gaixinh_distributor.py`)
- **Tầng 1 (Độc Quyền - Exclusive)**: 
  - Lấy chính xác **45 video đầu tiên** (`vids[:45]`) nạp trọn vẹn 1 bạn nữ cho 1 folder riêng (1 kênh duy nhất).
- **Cơ chế Chống Trùng Nguồn (`gaixinh_claims.py`)**: 
  - Đăng ký quyền sở hữu tại `data/gaixinh_channel_claims.json` và `channel_info.json` của từng folder.
  - Khi folder đã claim kênh thì bất kỳ folder độc quyền nào khác chạy sau sẽ bị hàm `is_channel_claimed` bỏ qua, chống trùng người 100%.
- **Cơ chế Video Thừa / Thặng Dư (`Leftover Pool`)**: 
  - Toàn bộ video từ clip 46 trở đi (`vids[45:]`) của kênh độc quyền KHÔNG bị bỏ phí, tự động đẩy sang `curated_channels` để chia sẻ bù vào các folder bể gộp đa kênh.
- **Tầng 2 (Bể Gộp Đa Dạng - Curated Hub)**: 
  - Nhận các kênh lẻ (< 40 clip) + video thừa từ kênh độc quyền, phân bổ đều tay từ tất cả các bạn nữ theo thuật toán Round-Robin/Interleaved Shuffle, random biến thiên tỷ lệ giữa các folder.

## 2. Bộ Lọc Kép AI Tự Động 100% (`ai_channel_filter.py`)
- **AI Vision ViT ONNX**: 
  - Model `model_quantized.onnx` chuẩn hóa `(arr - 0.5) / 0.5`. Quét từng khung hình tại giây thứ 2 và thứ 5.
  - Chỉ giữ bạn nữ người thật (`score >= 70%`), loại bỏ triệt để tranh vẽ, 3D, anime, hoạt hình, game, review, nam giới.
- **AI Whisper Audio Gate (`verify_audio_no_speech`)**: 
  - Model `faster_whisper` tiny (int8) chạy cực nhanh (0.5s/clip).
  - Quét âm thanh: **TỰ ĐỘNG XÓA BỎ 100% clip có tiếng nói tiếng Trung (`zh_speech`)** hoặc nói chuyện liên tục.
  - **CHỈ GIỮ video thuần nhạc nền (Dance / Biến hình / Dạo phố khoe dáng / OOTD)** không lời thoại phục vụ dàn nick nuôi.

## 3. Cào Video Douyin Nội Địa Trung Quốc (`f2` CLI v0.0.1.7)
- Tự động bóc tách cookie sống từ Chrome CDP (port 9222) truyền qua cờ `-k`.
- Bẻ khóa chữ ký `a_bogus` / `msToken`, kéo trực tiếp video Full HD 1080p MP4 không watermark / không logo.
- Tải theo Profile: `f2 dy -u "https://www.douyin.com/user/<sec_uid>" -M post -k "<cookie>" -o 40 -p "<path>"`.
- Cào tự động theo feed Douyin: `douyin_feed_ai_crawler.py --folder <id> --min-videos 40 --parallel 10`.

## 4. Cấu Hình Tải & Render Tối Ưu Tải Server (56 Cores / 64GB RAM)
- **Download**: 20 workers song song (`--parallel 20`) qua proxy xoay tua (`proxy_pool_67.txt` URL-encoded `TaadaaMobi%232026%21`).
- **Render**: Chạy 2 workers FFmpeg song song (`--parallel 2`) giúp tăng tốc x2 (~3.5 phút/folder), CPU tải 70-80% an toàn tuyệt đối.
- **Windows Explorer Thumbnail**: Cài đặt `Microsoft.HEVCVideoExtension_x64.Appx` để Windows 10 tự sinh thumbnail preview sắc nét cho video MP4 chuẩn HEVC.
