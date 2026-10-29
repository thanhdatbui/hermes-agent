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

## 3. Khế Ước Render Nối Tiếp (Offset Render Preservation)
- Khi xoay nguồn cào cho kênh flop:
  * **Bảo toàn số thứ tự**: Lấy mốc `video_da_dang` thực tế trong Excel, bắt buộc render bắt đầu từ:
    `next_start_seq = video_da_dang + 1`
  * Tuyệt đối không reset `video_da_dang` về 0 để tránh bot upload đăng trùng lặp số thứ tự cũ.
  * Lệnh O(1) chuẩn:
    `python D:/Taadaa/Tiktok-video/scripts/swap_single_folder_pipeline.py --machine <M> --tik <T> --folder-raw <raw> --folder-render <rend> --start-seq <next_start_seq> --min-videos 40 --clean-old`
