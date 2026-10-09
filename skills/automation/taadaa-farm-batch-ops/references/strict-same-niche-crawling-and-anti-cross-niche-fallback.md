# Kỷ Luật Bắt Buộc: Khóa Cứng Đúng Niche 100% & Cấm Tuyệt Đối Fallback Chéo Ngách

## 1. Bối cảnh & Sự cố Nghiêm trọng (Incident 2026-10-06)
- **Triệu chứng**: Khi chạy downloader cào bù cho Admin hoặc Kibe, script tự ý lấy các kênh không liên quan (ví dụ: gán kênh bóng đá vào niche `lamdep`, gán kênh tin tức vào niche `nhac`, gán kênh phim vào niche `tamly`).
- **Nguyên nhân gốc rễ**:
  1. *Bẫy `fallback_niches` cũ trong `download_by_niche.py`*: Khi không tìm thấy kênh của ngách gốc, script tự động nhảy sang mảng fallback (Hài hước, Khám phá, Ẩm thực, Mẹo vặt, Review, Phim, Tin tức, Công nghệ) và gán lại `niche = fb_niche`. Đây là hành vi vi phạm nghiêm trọng kỷ luật nghiệp vụ.
  2. *Lọc thô thiếu kiểm định*: File master (`sources.master_1288.json`) chứa nhiều kênh đài truyền hình/tin tức tổng hợp (VTV, HTV, THVL...) được gắn nhiều tag dẫn tới việc lấy nhầm kênh tin tức/truyền hình cho các ngách hẹp.

---

## 2. Hard Invariants (Kỷ Luật Tối Cao - Bắt Buộc Tuân Thủ)

### INVARIANT 1: CẤM TUYỆT ĐỐI FALLBACK SANG NICHE KHÁC
- Mỗi folder được định danh một `niche` duy nhất trong `state.db`.
- **Folder ngách nào khóa chết 100% ngách đó**.
- Khi kênh hiện tại không đủ video hoặc cạn kênh trong danh sách:
  - **BẮT BUỘC tiếp tục tìm kiếm / cào thêm nguồn CÙNG NICHE**.
  - Nếu duyệt hết tất cả query của niche mà vẫn không tìm được kênh $\ge 40$ clips: **DỪNG LẠI VÀ BÁO THIẾU**, chuyển sang folder tiếp theo.
  - **TUYỆT ĐỐI CẤM tráo sang ngách khác hoặc dùng mảng fallback ngách khác.**

### INVARIANT 2: TÌM KIẾM THEO TỪ KHÓA CHUYÊN SÂU CỦA NICHE (TARGETED QUERY SEARCH)
- Không chỉ dựa vào manifest tĩnh, khi thiếu kênh phải kích hoạt tìm kiếm trực tiếp trên YouTube Shorts theo từ khóa chuyên sâu của đúng niche đó:
  ```python
  queries = [
      f"ytsearch15:{niche_label} shorts việt nam",
      f"ytsearch15:kênh {niche_label} shorts việt",
      f"ytsearch15:chia sẻ {niche_label} shorts",
      f"ytsearch15:#{niche_slug} shorts việt nam"
  ]
  ```
  *(Ví dụ: `tamly` -> `tâm lý học shorts việt nam`, `chia sẻ tâm lý shorts`; `thietbi` -> `thiết bị điện tử shorts việt nam`)*.

### INVARIANT 3: BLACKLIST ĐÀI TRUYỀN HÌNH & KÊNH TIN TỨC TỔNG HỢP
- Kênh sáng tạo của farm nuôi nick TikTok phải là kênh cá nhân / creator chuyên sâu về chủ đề đó.
- BẮT BUỘC lọc bỏ triệt để các kênh có uploader hoặc channel name chứa:
  `["vtv", "htv", "thvl", "truyền hình", "truyenhinh", "báo ", "tin tức", "tintuc", "bóng đá", "bongda", "thời sự", "tin nhanh", "chuyển động", "tổng hợp", "phim truyện", "phim hay"]`.

### INVARIANT 4: PROBE GATE TRƯỚC KHI TẢI
- Trước khi tải bất kỳ file video nào vào folder, BẮT BUỘC chạy probe nhanh tab `/shorts` của kênh:
  ```bash
  yt-dlp --flat-playlist --playlist-end 40 --print "%(id)s" <channel_url>/shorts
  ```
- Nếu kênh có $< 35$ shorts: Bỏ qua ngay trong $\le 2$ giây, không tạo rác trên đĩa.
- Chỉ khi kênh có $\ge 40$ shorts mới tiến hành download full 45 clip.

### INVARIANT 5: CHỐNG TRỘN KÊNH (1 FOLDER = 1 KÊNH DUY NHẤT)
- Nếu một kênh trong lúc tải thực tế không đạt đủ chuẩn ($\ge 35$ clip):
  - BẮT BUỘC xóa sạch các file media dở dang (`.mp4`, `.part`, `.jpg`) trong folder đó.
  - Sau đó mới thử kênh tiếp theo CÙNG NICHE.
  - Tuyệt đối không để 1 folder chứa video lẫn lộn từ 2 kênh khác nhau.
