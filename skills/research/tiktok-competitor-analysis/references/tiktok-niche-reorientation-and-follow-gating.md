# Quy hoạch chuyển đổi Niche Gái Xinh & Tách Cổng Follow Tự Nhiên (2026-09-23)

## 1. Bản đồ hiện trạng các Workbook Farm (D:\OneDrive\TaadaaData\kibe)

Khi cần chọn nhóm tài khoản để xây kênh mới hoặc thử nghiệm niche mới (như gái xinh / visual Douyin), quét số lượng video đã đăng (`Video Đã Đăng`) qua 8 workbook Tik:

| Workbook | Tổng Nick | Nick 0 video | Nick < 3 video | Nick ≥ 10 video | Đánh giá & Chỉ định |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `Tik1.xlsx` | 78 | 0 | 0 | 69 (TB 21 vid) | ❌ Niche cũ đã định hình vững, CẤM đụng vào |
| `Tik2.xlsx` | 79 | 0 | 1 | 59 (TB 11 vid) | ❌ Niche cũ đã định hình vững, CẤM đụng vào |
| `tik3.xlsx` | 80 | 1 | 2 | 1 (TB 7 vid) | ⚠️ Đang nuôi dở dang (6–8 video/acc) |
| `Tik4.xlsx` | 80 | 1 | 3 | 1 (TB 7 vid) | ⚠️ Đang nuôi dở dang (6–8 video/acc) |
| `Tik5.xlsx` | 80 | **17** | **53** | 0 (TB 1.4 vid) | ✅ **Rất tốt để chuyển đổi** (nhiều acc mới chỉ đăng 1 clip) |
| `Tik6.xlsx` | 80 | 10 | 44 | 0 (TB 1.9 vid) | ⚪ Dự phòng chuyển đổi |
| `Tik7.xlsx` | 79 | **38** | **34** | 0 (TB 0.8 vid) | 🏆 **KHO VÀNG ĐẸP NHẤT** (38 nick trắng tinh 100%, 34 nick mới đăng 1 clip) |
| `Tik8.xlsx` | 78 | 12 | 63 | 0 (TB 1.3 vid) | ⚪ Dự phòng chuyển đổi |

👉 **Quy tắc điều chuyển:** Ưu tiên số 1 là `Tik7`, kế đến là `Tik5`. Tổng cộng cụm Tik7 + Tik5 cung cấp gần 160 nick non trẻ/trắng tinh, hoàn hảo để triển khai dự án niche visual/gái xinh.

---

## 2. Phân biệt 2 Tầng Follow trong Hệ thống Farm

Hệ thống có 2 cơ chế follow hoàn toàn tách biệt về mặt ngữ nghĩa và vòng đời:

### A. Tầng 1: Subprocess Follow Hook (Follow Chéo / Nội Bộ Farm)
- **Vị trí code:** `_run_follow_hook` trong `multi_machine_feed_session.py`.
- **Hành vi:** Sau khi kết thúc phiên lướt feed, gọi process con chạy `follow_runner.run_follow` (Mode 1 / Mode 2) để follow theo target chỉ định hoặc follow chéo.
- **Cổng an toàn hiện tại:** Dòng 2212:
  ```python
  if video_count < 10:
      # Skip follow hook: 'under-10-videos-follow-disabled'
  ```
- **Mục đích cổng:** Giữ nick clone không đi follow lung tung làm lộ cụm máy nội bộ khi chưa có ít nhất 10 video. Cổng này DÀNH RIÊNG CHO TẦNG 1.

### B. Tầng 2: Natural In-feed Follow (Follow Tự Nhiên Khi Lướt Feed)
- **Vị trí code:** `_maybe_follow_video` trong `feed_swipe_smoke.py`.
- **Hành vi:** Trong quá trình quẹt FYP/For You, gặp video ngẫu nhiên có xác suất bấm follow tự nhiên.
- **Tỷ lệ hiện tại:**
  - `DEFAULT_FEED_FOLLOW_RATES` (For You): 5%.
  - `DEFAULT_DEEP_FOLLOW_RATE_PERCENT` (Deep Inspect): 20%.
- **Vấn đề lịch sử (Silent Action Block / Bị TikTok nhả follow):**
  - Khi nick quẹt trúng video, nếu script bấm nút Follow ngay trong 1–2 giây đầu mà không có thời gian dừng xem (dwell time), AI chống bot của TikTok lập tức gắn cờ hành vi bất thường và âm thầm hủy (nhả) follow. Sau vài giây nút đỏ quay lại hoặc số following không tăng.
- **Giải pháp: Watch Time Gate (Cổng Thời Gian Xem):**
  - KHÔNG cần cố nhận diện video là gái hay trai (bất khả thi và lag máy).
  - Điều kiện bấm follow chuẩn:
    1. Chỉ kích hoạt follow trên các video thuộc lượt **Deep Inspect** (`is_deep_inspect_video` hoặc dwell time ≥ 8 – 15 giây).
    2. Đã xem đủ lâu mới thực hiện tap vào nút Follow.
    3. Giữ nhịp tự nhiên: 1 session lướt ~18 video chỉ follow tối đa 1–2 người.

---

## 3. Quy trình Bổ sung Niche Video & Sourcing Gái Xinh

### Sourcing qua `download_by_niche.py`:
1. Mở rộng `D:\Taadaa\Tiktok-video\data\niches_pool.txt`:
   ```text
   vi    gaixinh    Gái xinh Douyin    true
   ```
2. Tạo manifest nguồn `data/source_manifest_gaixinh.jsonl`:
   Chứa danh sách kênh TikTok chuyên reup visual/dance gái xinh chất lượng cao.
3. Chạy download gán vào các folder nguồn tương ứng với Tik7/Tik5:
   ```bash
   python scripts/download_by_niche.py --sources data/source_manifest_gaixinh.jsonl --folders 7,15,23,31,39,47,55,63
   ```

### Mở rộng Sourcing Douyin (Trung Quốc):
- Nguồn visual gái xinh Douyin có chất lượng 1080p, không dính logo watermark TikTok, và hoàn toàn mới với thuật toán TikTok VN.
- Script tải chuyên dụng `D:/Taadaa/Tiktok-video/scripts/download_douyin_visual.py`: Tự động resolve link chia sẻ ngắn (`v.douyin.com`), bóc video MP4 1080p gốc không watermark qua `yt-dlp`.

---

## 4. Triển khai Kỹ thuật Chi tiết & Bài học Vận hành (Production Verified)

### A. Watch Time Gate trong `feed_swipe_smoke.py`:
- **Vị trí:** Trong hàm `_maybe_follow_video`:
  ```python
  if random.randint(1, 100) > int(follow_rate_percent):
      return False

  # Watch Time Gate (Chống nhả follow): Ngâm video tối thiểu 8-12s trước khi tương tác follow
  # Đảm bảo TikTok ghi nhận watch-time đủ độ trust, tránh hành vi bot bấm vội bị server revert
  watch_dwell_s = random.uniform(8.0, 12.0)
  time.sleep(watch_dwell_s)

  xml_text = _capture_xml_text(ctx, "follow_video")
  ```
- **Telemetry & Watchdog Report (`feed_session_watchdog.py`):**
  - Trích xuất `follow_counts` theo tab (`for-you`, `following`, `friends`) từ summary của từng máy.
  - Hiển thị trực tiếp vào báo cáo Telegram ca nuôi:
    `+ Follow tự nhiên: {tot_nat_follows} lượt / {tot_swipes} video ({tot_nat_follow_rate:.1f}%) [Đề xuất: {tot_fy_nat_follows} | Bạn bè: {tot_fr_nat_follows}]`

### B. Pipeline Tải Video Niche Gái Xinh (`download_gaixinh_pipeline.py`):
- **Chỉ tiêu:** Tối thiểu **40 video MP4 / folder** (chuẩn bị nguyên liệu dồi dào cho các slot máy Tik7 / Tik5).
- **Bộ lọc chất lượng:**
  - Thời lượng: 10s đến 45s (tối ưu retention rate của thuật toán TikTok).
  - Định dạng: MP4 gốc, không watermark, dung lượng > 500KB.
- **Pitfall & Cơ chế Multi-Tier Fallback khi cào kênh TikTok:**
  - *Lỗi:* Một số kênh TikTok reup Douyin bị lỗi `Unable to extract secondary user ID` hoặc số lượng video công khai quá ít (< 10 video).
  - *Xử lý:*
    1. **Tier 1 (Kênh lớn đã kiểm chứng):** Ưu tiên các kênh có kho video dày 30–60+ clips (`@hoaa.hanassii`, `@vtkh2004`, `@lebong95`, `@thuy_tien_2000`, `@ngoc.matcha`).
    2. **Tier 2 (Fallback Search Keywords):** Nếu quét hết kênh mà folder vẫn chưa đủ `min_videos`, script tự động fallback sang `ytsearch` từ khóa liên quan (`gái xinh douyin shorts`, `gái xinh tiktok shorts`, `dance gái xinh shorts`) để vét cho đến khi gom đủ 100% quota ≥ 40 video/folder.

---

## 5. Quy Tắc Vận Hành Nguồn Video Farm & Cào Douyin Trung Quốc (User Chốt 2026-09-23)

### A. QUY TẮC BẤT BIẾN: 1 FOLDER = 1 KÊNH DUY NHẤT (CẤM PHA TRỘN GƯƠNG MẶT)
- **Quy tắc cốt lõi:** `1 Folder = 1 Kênh duy nhất`.
- **Lý do kỹ thuật & tâm lý người xem:** Một tài khoản TikTok nuôi nick bắt buộc phải có tính nhất quán thị giác cao (cùng 1 khuôn mặt, 1 vóc dáng, 1 phong cách creator). Nếu trộn lẫn video của 2 hoặc nhiều bạn gái khác nhau vào cùng 1 folder, nick nhìn sẽ rất "rác" (như kênh tổng hợp tạp nham), người xem không bấm follow và thuật toán TikTok bị nhiễu loạn khi phân loại tệp nhân vật.
- **Tiêu chuẩn nạp:** Mỗi folder nguồn chỉ tải từ **1 kênh duy nhất** có đủ kho video ≥ 40 video.

### B. QUY TRÌNH CHUYỂN ĐỔI SLOT MÁY ÍT VIDEO (CONVERSION CLEANUP WORKFLOW)
Khi quyết định chuyển đổi 1 slot máy (ví dụ Máy 4 / Folder 31) sang niche gái xinh:
1. **Tiêu chí chọn máy:** Chọn các máy có `Video Đã Đăng == 0` (hoặc < 2-3 clip) trong workbook (`Tik7.xlsx`, `Tik5.xlsx`).
2. **BẮT BUỘC DỌN SẠCH CẢ 2 ĐẦU MỤC:**
   - Xóa toàn bộ video cũ trong thư mục video gốc: `D:/video goc/<folder>/`
   - Xóa toàn bộ video cũ trong thư mục video render: `D:/TIKTOK-videonuoinick/<folder>/`
   - Tuyệt đối không để sót video render cũ tránh việc máy up nhầm video của niche trước đó.
3. **Cập nhật Metadata Workbook:**
   - Đổi `Keyword Video` thành từ khóa gái xinh (ví dụ: `Gái xinh`, `Visual Douyin`, `Dance trend`).
   - Đổi `Hashtag Pool` tương ứng (ví dụ: `#xuhuong #gaixinh #douyin #fyp #viral #trending`).
4. **Script chuyên dụng:** `D:/Taadaa/Tiktok-video/scripts/download_single_channel_to_folder.py`:
   ```bash
   python scripts/download_single_channel_to_folder.py --channel "https://www.tiktok.com/@vtkh2004" --folder 31 --min-videos 40 --clean-old
   ```
   Cờ `--clean-old` sẽ tự động dọn sạch cả 2 thư mục raw và render trước khi tải.

### C. TIÊU CHÍ CHỌN NGUỒN GÁI XINH: TỰ NHIÊN > TOP KOLS
- **User chốt:** *"T đâu có cần phải là kênh tốt nhất, cứ kênh gái là được"*.
- **Phân tích:** 
  - Kênh KOLs/Idol nổi tiếng (triệu follower) thường có mặt quá quen, video dính logo thương hiệu, dính watermark sự kiện, dễ bị người xem nhận ra là reup và dễ bị AI quét trùng khớp bản quyền cao.
  - Kênh gái cá nhân bình thường (quay visual selfie, cam thường, bắt trend nhảy, biến hình, ootd): Độ chân thực cao, người xem dễ lầm tưởng là chủ nick thật tự quay ➔ Tỷ lệ giữ chân (Retention) và bấm Follow cao hơn nhiều.

### D. DANH SÁCH REPO MÃ NGUỒN MỞ CÀO DOUYIN NỘI ĐỊA TRUNG QUỐC HÀNG ĐẦU
Khi nguồn TikTok Việt Nam không đủ hoặc muốn lấy video 1080p gốc hoàn toàn mới chưa từng xuất hiện trên TikTok VN:
1. ⭐ **`jiji262/douyin-downloader`** (12,041 stars):
   - Repo: [https://github.com/jiji262/douyin-downloader](https://github.com/jiji262/douyin-downloader)
   - Tải hàng loạt theo trang cá nhân (User Profile) Douyin, tự động bypass watermark, có cả GUI Desktop (`Douzy`) và Python CLI, tự động lọc trùng bằng SQLite.
2. ⭐ **`Johnserf-Seed/f2`** (2,658 stars):
   - Repo: [https://github.com/Johnserf-Seed/f2](https://github.com/Johnserf-Seed/f2)
   - Thư viện Python chính thức (`pip install f2`), dòng lệnh cực gọn: `f2 douyin -u "https://www.douyin.com/user/..."` tải toàn bộ video MP4 gốc 1080p.
3. ⭐ **`Evil0ctal/Douyin_TikTok_Download_API`** (20,290 stars):
   - Repo: [https://github.com/Evil0ctal/Douyin_TikTok_Download_API](https://github.com/Evil0ctal/Douyin_TikTok_Download_API)
   - Self-hosted REST API giải mã link chia sẻ app Douyin (`v.douyin.com`) sang direct video URL sạch không logo.


