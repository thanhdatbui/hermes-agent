# Kỷ luật Bất biến: Cách ly Niche Tuyệt đối (Strict Niche Isolation) & Chống Bẫy Fallback Tráo Niche

## 1. Triệu chứng & Sai lầm Nghiêm trọng (User Invariant 2026-10-06)
- **Triệu chứng & Tiếng chuông cảnh báo từ User**:
  User phản ứng gay gắt: *"VKL MÀY CÁI NÀY T NHẮC ĐI NHẮC LẠI NHIỀU LẦN R SAO CỨ TỰ Ý TẢI NICHE ĐÉO LIÊN QUAN V K BIẾT THIẾT KẾ SCRIPT À"*.
- **Bản chất sai phạm**:
  1. **Bốc kênh từ file JSON Master mà không lọc Niche nghiêm ngặt**: File tổng hợp (ví dụ `sources.master_1288.json`) chứa nhiều kênh tin tức tổng hợp, truyền hình (THVL, VTV, Tuổi Trẻ, Báo Pháp Luật, Tốp 1 Khám Phá...) bị gán bừa bãi hàng chục tag niche. Script lọc thô `if niche in channel['niches']` sẽ bốc trúng kênh phim truyền hình nhét vào folder *Tâm lý*, kênh bóng đá/tin tức nhét vào *Thiết bị* hoặc *Làm đẹp*.
  2. **Bẫy tử thần `NICHE_FALLBACK` trong code cũ**: Một số script cũ có đoạn mã độc hại: khi ngách gốc không đủ video hoặc khó tìm, code tự động nhảy sang mảng `fallback_niches = ['cuoi', 'khampha', 'amthuc', 'meovat', 'tintuc']` để gom cho đủ video. Thao tác này **phá hủy 100% định hướng nuôi nick của tài khoản**, biến nick chuyên đề thành nick tạp nham rác.

---

## 2. Quy tắc Bất biến Bắt buộc (Core Invariants)

### Invariant 1: 1 Folder = 1 Niche Duy Nhất 100% (Không Bao Giờ Tráo Niche)
- Mỗi folder (1..640) trên Farm được ràng buộc chặt chẽ với tài khoản TikTok tương ứng trong workbooks `Tik1..Tik8.xlsx` và cột `niche` trong bảng `folders` của `state.db`.
- **CẤM TUYỆT ĐỐI FALLBACK SANG NICHE KHÁC**: Dù ngách đó cạn kênh, khó tìm hay lỗi stream, TUYỆT ĐỐI KHÔNG ĐƯỢC tự ý chuyển sang ngách khác để gom clip. Nếu chưa tìm được kênh đạt chuẩn, ghi nhận `insufficient_pool` để mở rộng từ khóa trong CÙNG NGÁCH đó.

### Invariant 2: Tìm kiếm có Chủ đích Theo Từ khóa Cốt lõi của Ngách (Targeted Queries)
- Tuyệt đối không dựa vào danh sách flat không kiểm chứng. Phải truy vấn YouTube Shorts theo đúng cụm từ chuyên sâu của ngách (`niches_pool.txt`):
  - `tamly` -> `"tâm lý học cuộc sống shorts"`, `"bài học tâm lý shorts"`, `"chữa lành tâm lý shorts"`
  - `thietbi` -> `"thiết bị gia dụng thông minh shorts"`, `"đồ gia dụng tiện ích shorts"`, `"review thiết bị gia đình"`
  - `chamsocbe` -> `"chăm sóc em bé shorts"`, `"mẹo chăm con nhỏ shorts"`, `"mẹ bỉm chăm bé"`
  - `thien` -> `"thiền định mỗi ngày shorts"`, `"nhạc thiền tịnh tâm shorts"`, `"chuông xoay chữa lành"`
  - `dondep` -> `"dọn dẹp nhà cửa thông minh shorts"`, `"mẹo dọn nhà sạch shorts"`

### Invariant 3: Blacklist Triệt để Kênh Tổng hợp & Đài Truyền hình
- Trong mọi script auto-discover/cào nguồn, bắt buộc loại trừ các kênh không phải người sáng tạo nội dung chuyên sâu:
  ```python
  BLACK_KEYWORDS = [
      "vtv", "htv", "thvl", "báo", "truyền hình", "tin tức", "news",
      "bóng đá", "phim truyện", "tốp 1", "top 1", "khám phá", "showbiz"
  ]
  ```
- Kênh được duyệt phải có tiêu đề và nội dung video phản ánh 100% chủ đề ngách đó.

### Invariant 4: Bảo tồn 1 Folder = 1 Kênh Độc quyền
- Khi một kênh được thử nghiệm nhưng có `< 35` clip (không đủ ngưỡng tối thiểu), script bắt buộc phải **dọn sạch toàn bộ file media dở dang** trong folder trước khi thử kênh khác để chống trộn 2 kênh vào 1 folder.
