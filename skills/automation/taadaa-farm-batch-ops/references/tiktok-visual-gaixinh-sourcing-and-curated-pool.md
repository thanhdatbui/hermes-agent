# TikTok Visual Gái Xinh Video Sourcing & Curated Pool (2026-09-23)

## 📌 Bối cảnh & Mục tiêu
- **Niche mới**: `gaixinh` (Gái xinh Douyin / Visual Video) trong `D:/Taadaa/Tiktok-video/data/niches_pool.txt`.
- **Đặc trưng thuật toán**: Video gái xinh thời lượng ngắn (10s – 45s) có Stop-scroll rate và Retention rate cực cao, giúp nick mới dễ cắn đề xuất For You và gom follow nhanh nhất.
- **Kho máy chuyển đổi**: Các máy chưa đăng hoặc đăng ít video trong `Tik7.xlsx` / `Tik5.xlsx` (như M4-F31, M7-F55, M8-F63, M10-F79...).

---

## 🎯 2 Tầng Cấu Trúc Folder Bắt Buộc

### 1. Tầng Độc Quyền (Exclusive — 1 Folder = 1 Kênh duy nhất $\ge 40$ video)
- **Quy tắc**: Kênh nguồn nào có sẵn $\ge 40$ video ngắn chuẩn form thì cấp riêng 1 folder độc quyền.
- **Mục đích**: Xây dựng kênh dạng **Idol / Cá nhân** (chuẩn form 2 kênh triệu view của ông anh). Toàn bộ video từ trên xuống dưới đều là cùng một khuôn mặt, tạo độ tin cậy và gắn kết fan cao.

### 2. Tầng Bể Gộp Tổng Hợp (Curated Hub — Gom các kênh lẻ $< 40$ video)
- **Quy tắc cốt lõi (User invariant)**:
  - Rất nhiều bạn nữ chỉ đăng 5 – 15 video cực đẹp nhưng không đủ 40 video để làm kênh độc quyền. Gom toàn bộ vào Bể Gộp.
  - ⚠️ **INVARIANT: BẮT BUỘC TRỘN XEN KẼ ROUND-ROBIN (Interleaved Shuffle)**:
    - Clip 1: Kênh A (bạn nữ 1)
    - Clip 2: Kênh B (bạn nữ 2)
    - Clip 3: Kênh C (bạn nữ 3)
    - Clip 4: Kênh D (bạn nữ 4)
    - Clip 5: Kênh A (clip 2 của bạn nữ 1)...
  - 🚫 **CẤM TUYỆT ĐỐI GỘP TUẦN TỰ** (Kênh A đăng hết 10 ngày rồi mới sang Kênh B). Gộp tuần tự làm nick bị "đổi mặt" đột ngột sau 10 ngày, khiến người xem cảm thấy bị lừa và hủy follow. Trộn xen kẽ định vị tài khoản thành **"Kênh Tạp Chí / Thiên Đường Gái Xinh"**, mỗi ngày một visual mới lạ.

---

## 🧹 Quy tắc Dọn Dẹp File Cũ (`--clean-old`)
Khi chuyển đổi một máy/folder từ niche cũ (lập trình, mẹ bé, âm nhạc...) sang niche gái xinh:
- **BẮT BUỘC XÓA SẠCH 100% CẢ 2 NƠI**:
  1. `D:/video goc/<folder>` (kho video gốc cũ)
  2. `D:/TIKTOK-videonuoinick/<folder>` (kho video render cũ)
- Không được để sót bất kỳ video cũ nào kẻo tool upload đăng lẫn lộn video cũ và video gái.

---

## 🛠️ Bộ Lệnh Vận Hành Canonical (`D:/Taadaa/Tiktok-video`)

### 1. Nạp Bể Gộp Xen Kẽ (Curated Round-Robin)
```bash
python D:/Taadaa/Tiktok-video/scripts/smart_gaixinh_distributor.py --folders <folder_num> --mode curated --min-videos 40 --clean-old
```

### 2. Nạp Kênh Độc Quyền (Exclusive 1 Người)
```bash
python D:/Taadaa/Tiktok-video/scripts/smart_gaixinh_distributor.py --folders <folder_num> --mode exclusive --min-videos 40 --clean-old
```
Hoặc chỉ định trực tiếp kênh cụ thể:
```bash
python D:/Taadaa/Tiktok-video/scripts/download_single_channel_to_folder.py --channel "https://www.tiktok.com/@<username>" --folder <folder_num> --min-videos 40 --clean-old
```

### 3. Tải từ Link Douyin Trung Quốc Không Watermark
```bash
python D:/Taadaa/Tiktok-video/scripts/download_douyin_visual.py --urls "https://v.douyin.com/xxxx/" --output-dir "D:/video goc/<folder_num>"
```

### 4. Manifest Nguồn Chuẩn
- `D:/Taadaa/Tiktok-video/data/source_manifest_gaixinh.jsonl`
- Đã loại bỏ hoàn toàn 2 kênh mẫu của ông anh, chỉ lưu các kênh visual tuyển chọn và kênh chuyên reup Douyin chất lượng cao.
