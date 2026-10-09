# Quy tắc Tuyển chọn Kênh Gái Xinh, Lọc Nội dung Thực tế & Render Sequence Nuôi Nick

## 1. Tiêu chí Tuyển chọn Kênh Gái Xinh (GaiXinh Niche Invariants)

### Tránh Kênh Cosplay / Anime / Phim ngắn
- **Cạm bẫy:** Nhiều video gắn hashtag `#gaixinh` nhưng thực chất là cosplayer hóa trang nhân vật hoạt hình/game (ví dụ: Kokomi trong Genshin Impact, tóc giả xanh/hồng, trang điểm phong cách anime) hoặc trích đoạn phim truyền hình Trung Quốc.
- **Hệ quả:** Khi trích xuất avatar khuôn mặt tự động, ảnh đại diện sẽ là ảnh nhân vật hoạt hình/anime, sai lệch chủ đề hotgirl đời thực.
- **Quy tắc lọc:** Kiểm tra metadata tiêu đề/mô tả loại bỏ các tag: `#cosplayer`, `#hoathinhtrungquoc`, `#phimngandouyin`, `#phimtrungquoc`.

### Tránh Idol Quốc Dân Triệu View
- Các idol nổi tiếng triệu followers (như Vũ Thị Khánh Huyền `@vtkh2004`, Lê Bống `@lebong95`...) có độ nhận diện quá cao, reup rất dễ bị người dùng phát hiện và bị hạn chế đề xuất.
- **Tiêu chuẩn tối ưu:** Chọn các kênh cá nhân nữ đời thường (ví dụ: `@diepyenvy55`), lượng video dồi dào (>= 40-50 video), clip tự quay nhảy trend nhẹ nhàng, đi biển, cafe, vlog đời sống thực tế người thật 100%.

---

## 2. Quy tắc Phân bổ Kênh Min 40 - Max 45 & Bể Gộp Đa Kênh

- **Kênh Độc Quyền (Exclusive):**
  - Chỉ cấp cho folder khi kênh có `>= 40 video` sạch đạt kiểm duyệt AI Vision (`AIFemaleFilter`).
  - Lấy tối đa **45 video** cho folder độc quyền.
- **Bể Gộp Đa Kênh (Curated Pool):**
  - Toàn bộ video thừa từ video 46 trở đi (hoặc từ các kênh có `< 40 video`) tự động được thu gom vào Curated Pool.
  - Phân bổ xoay vòng cho các tài khoản chạy phong cách đa kênh, tối ưu triệt để tài nguyên đã cào từ TikTok/Douyin.

---

## 3. Render Sequence Invariant & Bảo toàn "Video Đã Đăng"

### BẢO TOÀN SỐ VIDEO ĐÃ ĐĂNG TRÊN SHEET
- **TUYỆT ĐỐI CẤM:** Reset cột `Video Đã Đăng` về 0 trên các sheet quản lý `Tik1.xlsx` -> `Tik8.xlsx` khi thay nguồn video mới.
- Cột `Video Đã Đăng = N` là mốc lịch sử thực tế của nick trên TikTok. Nếu reset về 0, bot đăng video sẽ tìm file `1.mp4`, gây xung đột hoặc đăng lại video cũ.

### Lệnh Render với `--start-seq` và `--randomize`
- Khi render đợt video mới, truyền cờ `--start-seq <N+1>` để đánh số video bắt đầu từ clip tiếp theo tài khoản phải đăng.
  - Ví dụ: Sheet đang ghi `Video Đã Đăng = 3` -> Render bắt đầu từ `4.mp4`:
  ```bash
  python scripts/random_batch_render.py \
      --input-dir "D:/video goc/<folder_goc>" \
      --output-dir "D:/TIKTOK-videonuoinick/<folder_render>" \
      --parallel 4 \
      --start-seq 4 \
      --randomize
  ```
- **Lưu ý:** `random_batch_render.py` trên pipeline mới BẮT BUỘC phải có tham số `--randomize` để áp dụng profile biến đổi ngẫu nhiên chống quét bản quyền nền tảng.
