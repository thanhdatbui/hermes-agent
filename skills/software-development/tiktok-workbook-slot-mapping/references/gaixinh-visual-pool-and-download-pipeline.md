# Nguồn Video Gái Xinh (Tik5 / Tik7) & Pipeline Tải Đa Nguồn (TikTok VN + Douyin TQ)

## 1. Mục tiêu & Định vị Kho Video
- Các slot `Tik7` và `Tik5` (hơn 150 nick đang trắng tinh hoặc mới đăng 1-2 clip) được chọn lọc để chuyển đổi sang xây dựng **Dàn Kênh Gái Xinh / Visual Douyin**.
- **Yêu cầu chỉ tiêu:** Tối thiểu **≥ 40 video MP4 / folder**.
- **Tiêu chuẩn video:**
  - Thời lượng: **10s – 45s** (tối ưu tỷ lệ xem hết 100% video và retention FYP).
  - Không watermark / logo.
  - Tuyệt đối không cào 2 kênh mẫu của "ông anh" (`@trn.t.t85` và `@hong.thy.qunhhh`).
  - Mở rộng đa dạng từ khóa và nguồn: Visual hot trend Việt Nam kết hợp reup Douyin Trung Quốc chất lượng 1080p.

## 2. Các công cụ & Tệp cấu hình (`D:/Taadaa/Tiktok-video`)
- `data/niches_pool.txt`: Đã bổ sung niche `vi	gaixinh	Gái xinh Douyin	true`.
- `data/source_manifest_gaixinh.jsonl`: Danh sách 8 kênh visual chuẩn mẫu:
  - `@tra.dang.97`, `@linh.barbie`, `@quynhle_99`, `@lengoctrinh_99`, `@ngoc.kemm`.
  - `@gai_xinh_douyin_4k`, `@douyin_visual_vn`, `@tieu_ty_ty_douyin`.
- `scripts/download_gaixinh_pipeline.py`: Pipeline tải tự động nạp đủ ≥ 40 video vào danh sách folder chỉ định.
- `scripts/download_douyin_visual.py`: Công cụ CLI tải video từ link Douyin ngắn (`v.douyin.com`).

## 3. Lệnh vận hành chuẩn
```bash
# Tải nạp tối thiểu 40 video vào folder chỉ định (ví dụ folder 7 và 31):
python D:/Taadaa/Tiktok-video/scripts/download_gaixinh_pipeline.py --folders 7,31 --min-videos 40

# Tải video Douyin đơn lẻ hoặc danh sách:
python D:/Taadaa/Tiktok-video/scripts/download_douyin_visual.py --urls "https://v.douyin.com/xxxx/" --output-dir "D:/video goc/7"
```
