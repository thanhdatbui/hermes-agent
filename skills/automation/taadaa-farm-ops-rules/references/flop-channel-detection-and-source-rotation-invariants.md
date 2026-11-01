# Kỷ Luật Quét Kênh Flop & Xoay Nguồn Cào (Source Rotation Invariants)

## 1. Kỷ Luật Vận Hành Bất Biến (User Invariant): KHÔNG BỎ ACC
- **CẤM TUYỆT ĐỐI bỏ acc, xóa acc hoặc hạ cấp acc**:
  * Khi kênh TikTok farm bị flop (0 view, lẹt đẹt < 200 view, 0 tim), **KHÔNG ĐƯỢC** gỡ nick khỏi lịch upload, không hạ cấp nick thành `SEEDING_ONLY`.
  * Nick flop **VẪN TIẾP TỤC ĐĂNG VIDEO BÌNH THƯỜNG** theo nhịp nuôi nick hằng ngày của farm ("kiểu gì cũng lên").
- **Trọng tâm cứu kênh Flop duy nhất: ĐỔI NGUỒN CÀO (Source Rotation)**:
  * Thuật toán bóp reach hoặc kênh không tăng trưởng phần lớn do video gốc bị trùng lặp (*multimodal duplicate*) hoặc nguồn cào hết nhiệt.
  * Giải pháp cốt lõi: Hoán đổi kho video gốc sang kênh nguồn mới sạch, viral cao (`douyin_visual`, `thucung`, `satisfying`, `gaixinh_vn`).

## 2. Tiêu Chuẩn Phân Loại Kênh Flop (`flop_channel_scanner.py`)
- Công cụ trích xuất: `python D:/Taadaa/tools/flop_channel_scanner.py`
- Dữ liệu đối soát: Kết hợp `snapshots` trong `tiktok_tracker.db` và cấu hình slot trong `Tik1.xlsx` .. `Tik8.xlsx`.
- **4 Cấp độ phân loại deterministic:**
  1. **`NEW_WARMUP`**: Số video đã đăng $< 5$ clip $\rightarrow$ Kênh đang warmup, chưa đủ số liệu để phán xét.
  2. **`HEALTHY`**: Video $\ge 5$, tổng tim $\ge 20$ và tỷ lệ tim/video $\ge 3.0$ $\rightarrow$ Kênh tăng trưởng tốt, giữ nguyên nguồn cào.
  3. **`STAGNANT_WATCH`**: Video $\ge 5$, tim $\ge 20$ nhưng tỷ lệ tim/video $< 3.0$ $\rightarrow$ Tăng trưởng chậm, theo dõi tiếp 3 ca đăng.
  4. **`FLOP_NEED_SOURCE_SWAP`**: Video $\ge 5$ VÀ (tổng tim $< 20$ HOẶC $\ge 3$ snapshot liên tiếp $\Delta heart = 0$ và $\Delta follower = 0$) $\rightarrow$ Kích hoạt ngay kế hoạch xoay nguồn cào.

## 3. Khế Ước Render Nối Tiếp & Quy Trình Dọn Dẹp (Offset Render & Cleaning Protocol)
- **Quy trình dọn dẹp bắt buộc trước khi cào nguồn mới:**
  1. **Dọn sạch video đã render trước:** Xóa toàn bộ file video cũ/tồn dư trong `D:\TIKTOK-videonuoinick\<folder_render>`.
  2. **Dọn sạch video gốc cũ:** Xóa toàn bộ file trong `D:\video goc\<folder_raw>`.
  3. **Cào nguồn mới:** Tải tối thiểu 40 clip mới từ kênh nguồn sạch.
  4. **Render nối tiếp O(1):** Bắt buộc giữ mốc `video_da_dang` thực tế trong Excel, bắt đầu sequence từ:
     `next_start_seq = video_da_dang + 1`
  * Tuyệt đối không reset `video_da_dang` về 0 để tránh bot upload đăng trùng lặp số thứ tự cũ.
  * Lệnh O(1) chuẩn:
    `python D:/Taadaa/Tiktok-video/scripts/swap_single_folder_pipeline.py --machine <M> --tik <T> --folder-raw <raw> --folder-render <rend> --start-seq <next_start_seq> --min-videos 40 --clean-old`

## 4. Kỷ Luật Đánh Giá Niche Hot Toàn Farm (Anti-Small-Sample Bias)
- **CẤM TUYỆT ĐỐI lấy mẫu nhỏ lẻ tẻ (vài nick) để phán niche hot**:
  * Đánh giá hiệu suất niche bắt buộc phải aggregate trên TOÀN BỘ 1.000+ tài khoản của cả 2 cụm (Kibe & Admin) bằng script đối soát `tiktok_tracker.db` + toàn bộ `Tik1..Tik8.xlsx`.
  * Mỏ neo chân lý (Ground Truth) là nội dung video thực tế trong kho raw/render, không được dựa mù quáng vào cột Keyword trong Excel hay claims cũ.
  * Ưu tiên các ngách có tỷ lệ tim/clip cao và tỷ lệ flop thấp toàn farm (ví dụ: *Câu chuyện cuộc sống*, *Giao thông*, *Gym / Fitness*). Tránh các ngách ẩm thực quay cận cảnh không voice/không mặt người hoặc cắt ghép hài xàm dễ dính lỗi unoriginal bị bóp reach 0 view.
