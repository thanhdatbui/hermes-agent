# AI-Gated Video Crawling & 2-Tier Distribution Architecture

## 1. Nguyên Tắc Bất Biến Về Trải Nghiệm Người Dùng
- **CẤM TUYỆT ĐỐI BẮT USER SOI / XÁC NHẬN VIDEO BẰNG MẮT**: 
  User yêu cầu cào tự động ("vkl tao bảo mày đi cào link h mày bắt t đi nhìn"). 
  Mọi quy trình kiểm duyệt nội dung, lọc bỏ kênh rác, game, hoạt hình, trai đẹp... BẮT BUỘC phải tự động hóa 100% bằng code và AI.

## 2. Hệ Thống Lọc 2 Lớp (AI Filter Pipeline)
Nằm tại `D:\Taadaa\Tiktok-video\scripts\ai_channel_filter.py` (`AIFemaleFilter`):

### Lớp 1 — NLP Metadata Filter (Trước khi tải)
- Quét `title`, `description`, `uploader`, `nickname` và các hashtag.
- **Blacklist (REJECT ngay lập tức)**: `toca`, `boca`, `game`, `gaming`, `roblox`, `freefire`, `lienquan`, `traidep`, `ngamtraidep`, `hoathinh`, `slime`, `review`.
- **Positive (Ưu tiên)**: `gai`, `xinh`, `douyin`, `dance`, `nhay`, `visual`, `beauty`, `cute`, `model`, `ootd`.

### Lớp 2 — ViT ONNX Vision Filter (Sau khi tải frame video)
- Model: `onnx-community/gender-classification-ONNX` (quantized ViT, ~83MB, lưu tại `D:\Taadaa\Tiktok-video\models\onnx\model_quantized.onnx`).
- Chạy bằng `onnxruntime` trên CPU (khoảng 0.05s/frame, hoàn toàn offline không tốn tiền API hay lo rớt mạng).
- **Chuẩn hóa ảnh (Pre-processing Invariant)**:
  - ViT cấu hình `preprocessor_config.json`: resize `(224, 224)`, rescale `1/255.0`.
  - **BẮT BUỘC dùng `mean=0.5, std=0.5`**: `arr = (arr - 0.5) / 0.5`. 
  *(CẢNH BÁO: Dùng ImageNet standard mean `[0.485, 0.456, 0.406]` sẽ làm lệch phân phối của model khiến gái thật bị tụt confidence từ 88% xuống 39%).*
- **Verify Video**:
  - Dùng `ffmpeg -ss 00:00:02 -vframes 1` và `00:00:05` trích xuất 2 frame.
  - Chạy `classify_frame()`: Nếu `female_prob >= 0.60` ➔ PASS (đo thực tế trên video gái xinh đạt 97.2% – 98.7%).
  - Nếu dính hoạt hình (Toca Boca đo thực tế 46.8% female / 53.1% male), nam giới, game ➔ REJECT, tự động xóa file MP4 ngay lập tức và tải video khác bù vào.

## 3. Chiến Lược Phân Bổ Video 2 Tầng (2-Tier Distribution)
Nằm tại `D:\Taadaa\Tiktok-video\scripts\smart_gaixinh_distributor.py`:

```
                       ┌── KHO KÊNH NGUỒN CÀO VỀ ──┐
                       │                           │
             [Kênh có ≥ 40 video]         [Kênh có < 40 video]
                       │                           │
                       ▼                           ▼
            TẦNG 1: ĐỘC QUYỀN (EXCLUSIVE)    TẦNG 2: BỂ GỘP (CURATED HUB)
            (1 Folder = Đúng 1 Bạn Nữ)      (Mọi folder có ĐỦ TẤT CẢ các bạn)
```

### Tầng 1 — Folder Độc Quyền (Exclusive: ≥ 40 videos)
- **Quy chuẩn**: 1 Folder = 1 Kênh duy nhất.
- **Mục đích**: Xây nick Idol / Profile cá nhân (như 2 kênh triệu view của ông anh `@trn.t.t85` và `@hong.thy.qunhhh`). 100% video cùng một gương mặt, phong cách.

### Tầng 2 — Bể Gộp Tổng Hợp (Curated Hub: < 40 videos)
- **Quy tắc phân bổ bắt buộc**:
  - Tuyệt đối **KHÔNG** dồn cục 2-3 kênh vào 1 folder rồi folder khác lại là 2-3 kênh khác.
  - **MỖI FOLDER BỂ GỘP PHẢI ĐƯỢC CHIA TỪ TẤT CẢ CÁC KÊNH THIẾU ĐANG CÓ**:
    Ví dụ nếu trong bể có 9 kênh thiếu, thì mỗi folder đều phải có mặt cả 9 bạn nữ.
  - Mỗi bạn nữ đóng góp số lượng video ngẫu nhiên (`base = min_videos // K + random.randint(-1, 2)`), sau đó toàn bộ video trong folder được **xáo trộn ngẫu nhiên (shuffle)**.
  - **Mục đích**: Xây nick theo phong cách "Tạp chí Gái Xinh / Thiên đường Visual". Mỗi ngày đăng 1 bạn nữ khác nhau, đổi mới liên tục khiến người xem không bị nhàm chán.

## 4. Quy Trình Dọn Dẹp Kho Cũ Khi Chuyển Đổi Slot (--clean-old)
Khi chọn các máy chưa đăng video (hoặc đăng ít, ví dụ các slot trắng của `Tik7`/`Tik5`):
- Tham số `--clean-old` tự động xóa sạch 100% file cũ trong cả 2 thư mục:
  1. `D:\video goc\<folder>` (raw videos cũ)
  2. `D:\TIKTOK-videonuoinick\<folder>` (render videos cũ)
- Đảm bảo khi nạp video mới vào không bị lẫn lộn giữa chủ đề cũ (lập trình, review...) với visual gái xinh.

## 5. Hiện Trường Chuyển Đổi Thực Tế Trên Tik7 (23/09/2026)
Đã chuyển đổi thành công 5 máy chưa đăng video (Row có `Video Đã Đăng == 0`):
- **Máy 4 (Folder 31 — ID: trambe2997)**: 40 video độc quyền, đã dọn sạch render cũ (0 file).
- **Máy 7 (Folder 55 — ID: quangtu7627)**: 40 video độc quyền, đã dọn sạch render cũ (0 file).
- **Máy 8 (Folder 63 — ID: slosspbb3qo)**: 40 video Bể Gộp Xen Kẽ (7 kênh gái xoay vòng đều), đã dọn sạch render cũ (0 file).
- **Máy 10 (Folder 79 — ID: thumiu760)**: 40 video độc quyền (gaixinh_moingay2026), AI ViT score 98.6%, dọn sạch render cũ (0 file).
- **Máy 12 (Folder 95 — ID: arianjwj9qm)**: 40 video độc quyền (gaixinhday.ne), AI ViT score 98.2%, dọn sạch render cũ (0 file).

## 6. Các Công Cụ Cào Douyin Nội Địa Trung Quốc (Top GitHub)
1. `jiji262/douyin-downloader`: Giao diện Douzy Desktop + CLI Python, tải profile không watermark.
2. `Johnserf-Seed/f2`: CLI `pip install f2`, cào profile `f2 douyin -u <url>`.
3. `Evil0ctal/Douyin_TikTok_Download_API`: Tự host API giải mã URL chia sẻ Douyin sang direct MP4 không logo.
