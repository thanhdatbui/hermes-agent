# Quy Chuẩn Cào & Phân Bổ Video Gái Xinh (Tiktok-video & Douyin)

Tài liệu này lưu trữ quy chuẩn đã được User xác nhận và chốt hạ trong session 2026-09-23.

---

## 1. QUY TẮC PHÂN BỔ 2 TẦNG (EXCLUSIVE vs CURATED DIVERSE)

### A. Tầng 1: Kênh Độc Quyền (Exclusive - 1 Kênh Duy Nhất >= 40 Video)
- **Tiêu chuẩn:** Kênh nguồn quét được $\ge 40$ video hợp lệ (thời lượng 10s - 45s).
- **Phân bổ:** 1 Kênh cấp riêng cho đúng **1 Folder**.
- **Mục đích:** Xây dựng kênh TikTok idol/cá nhân, profile đồng nhất 100% cùng một khuôn mặt từ trên xuống dưới, giữ fan và trust cao.

### B. Tầng 2: Bể Gộp Tổng Hợp (Curated Diversity - Gom Các Kênh Thiếu < 40 Video)
- **Tiêu chuẩn:** Kênh quét được ít video ($< 40$ clip).
- **QUY TẮC BẮT BUỘC TỪ USER:**
  - **CẤM:** Không được gom cục bộ 2-3 kênh vào 1 folder này rồi 2-3 kênh khác vào folder kia.
  - **ĐÚNG:** Mọi folder bể gộp **BẮT BUỘC PHẢI CHỨA VIDEO CỦA TẤT CẢ CÁC KÊNH THIẾU ĐANG CÓ TRONG BỂ**.
    - Ví dụ: Bể có 9 kênh thiếu $\rightarrow$ Mỗi folder bể gộp đều phải có mặt cả 9 bạn nữ.
    - **Random ngẫu nhiên số lượng:** Mỗi bạn nữ đóng góp 3-6 video ngẫu nhiên, tổng vừa đủ $\ge 40$ video.
    - **Xáo trộn (Shuffle):** Trộn đều thứ tự các video trong folder trước khi hoàn tất.
  - **Mục đích:** Tạo kênh phong cách "Tạp chí gái xinh / Thiên đường visual", mỗi ngày người xem được ngắm một bạn gái khác nhau, nội dung đổi mới liên tục.

---

## 2. QUY CHUẨN XÓA FILE CŨ KHI NẠP MỚI (`--clean-old`)
Khi chuyển đổi máy hoặc nạp nguồn mới:
- Bắt buộc xóa sạch 100% video cũ trong cả 2 thư mục:
  1. Thư mục video gốc: `D:/video goc/<folder>/`
  2. Thư mục video render tương ứng: `D:/TIKTOK-videonuoinick/<folder>/`
- Chỉ nạp video mới sau khi 2 thư mục này đã trống hoàn toàn.

---

## 3. LỌC NGUỒN TỰ ĐỘNG BẰNG AI — CẤM BẮT USER SOI BẰNG MẮT
**Lời nhắc/Feedback cốt lõi từ User:** *"vkl tao bảo mày đi cào link h mày bắt t đi nhìn"*
Tuyệt đối không bắt User phải duyệt mắt thủ công kênh hoặc video. Quy trình tự động 100%:

1. **Lớp 1: NLP Blacklist / Negative Filter:**
   - Quét tiêu đề, bio, hashtag:
   - REJECT ngay lập tức nếu chứa: `toca`, `boca`, `game`, `gaming`, `roblox`, `freefire`, `lienquan`, `traidep`, `ngamtraidep`, `hoathinh`, `slime`, `review`.
2. **Lớp 2: AI Vision ViT (Vision Transformer) Offline:**
   - Dùng model local ONNX `D:/Taadaa/Tiktok-video/models/onnx/model_quantized.onnx` (`onnx-community/gender-classification-ONNX`) chạy qua `onnxruntime` CPU (~0.05s/frame).
   - Tự động cắt frame video ở giây thứ 2-3 để kiểm tra:
     - Hoạt hình, đồ chơi, nam giới, thú cưng, game $\rightarrow$ Xóa bỏ video ngay.
     - Xác nhận nữ thật $\rightarrow$ Chấp nhận đưa vào folder.

---

## 4. SCRIPTS LIÊN QUAN TRONG REPO `D:/Taadaa/Tiktok-video/`
- `scripts/smart_gaixinh_distributor.py`: Script điều phối 2 tầng (exclusive và curated đa dạng).
- `scripts/download_single_channel_to_folder.py`: Tải độc quyền 1 kênh cho 1 folder kèm `--clean-old`.
- `scripts/download_douyin_visual.py`: Tải video Douyin trực tiếp từ shortlink.
- `scripts/ai_channel_filter.py`: Module AI ViT + NLP kiểm duyệt video tự động.
- `data/source_manifest_gaixinh.jsonl`: Danh sách nguồn kênh gái xinh đã được xác thực.
