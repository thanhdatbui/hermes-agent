# Quy Trình Chuẩn Hoá Kênh TikTok Toàn Diện 4 Món (Avatar - Hashtag/Niche - Ghim Top - Tên/Bio)

## 1. Bối cảnh & Tầm quan trọng
Khi User yêu cầu "chuẩn hoá kênh", "chuẩn hoá acc", tuyệt đối KHÔNG được chỉ làm riêng lẻ Avatar hoặc chỉ Ghim bài rồi bỏ quên các phần khác. Chuẩn hoá toàn diện bắt buộc kiểm tra và thực hiện đủ **4 trụ cột**:
1. **Hashtag & Niche Mapping:** Đúng chủ đề video thực tế, không để lệch ngách (ví dụ video Nhảy nhưng gán tag Bánh ngọt khiến flop view).
2. **Ghim video Top (Pin Top):** Ghim các video $\ge 1.000$ views lên đầu trang cá nhân (tối đa 3 video).
3. **Ảnh đại diện (Avatar mới):** Trích xuất từ clip gốc, lọc sạch chữ qua OCR/Vision, khóa marker cứng `.manual_avatar_locked`.
4. **Tên hiển thị & Tiểu sử (Nickname & Bio):** Tên tiếng Việt có dấu, bio sạch không link/kí tự rác.

---

## 2. Chi Tiết Thực Thi Từng Trụ Cột

### Trụ Cột 1: Hashtag & Niche Khớp Thực Tế
- **Kiểm tra chéo giữa nội dung video và Workbook:**
  - Soi thumbnail các video đã đăng hoặc video trong folder render (`D:/TIKTOK-videonuoinick/<F>/`) và folder gốc (`D:/video goc/<F_src>/`).
  - Kiểm tra cột `Keyword Video` và `Hashtag Pool` trong `Tik<N>.xlsx` (cả cụm Kibe lẫn Admin).
  - Nếu phát hiện lệch ngách (như clip nhảy múa nhưng gán tag "Bánh ngọt"): Cập nhật ngay Keyword và Hashtag Pool chuẩn vào cả 2 sheet `TaiKhoan` và `Hashtag theo Folder`.
- **Khóa marker bảo vệ:**
  - Tạo file `.manual_hashtag_locked` tại thư mục video local và remote (nếu máy $\ge 200$) để các cron đồng bộ tự động không ghi đè lại.

### Trụ Cột 2: Ghim Video Top ($\ge 1.000$ views)
- **Quy chuẩn ghim:**
  - Chỉ ghim video khi view $\ge 1.000$. Video view dưới $1.000$ views TUYỆT ĐỐI KHÔNG GHIM.
  - Tối đa 3 video ghim (LIFO: video cao nhất được ghim sau cùng để đứng ở ô đầu tiên bên trái).
- **Thực thi trên thiết bị:**
  - Mở đúng tab Hồ sơ (`tap 970 1880` hoặc `open_target_profile`).
  - Bấm vào video đạt view cao $\rightarrow$ Bấm nút Chia sẻ (`tap 1000 1600` hoặc icon ba chấm/mũi tên).
  - Chọn nút **"Ghim"** (vị trí hàng icon chức năng dưới cùng, OCR nhận diện chữ "Ghim").
  - Quay lại Hồ sơ, chụp màn hình và soi WinRT OCR xác nhận nhãn đỏ **"Đã ghim"** xuất hiện ở góc trên thumbnail.

### Trụ Cột 3: Trích Xuất & Cập Nhật Avatar Mới
- **Quy tắc trích xuất:**
  - CẤM lấy lại file `avatar.jpg` cũ đã có sẵn nếu không rõ nguồn gốc.
  - Trích xuất frame mặt từ video `.mp4` trong kho video gốc bằng OpenCV Haar Cascade.
  - Căn crop vuông $512 \times 512$ theo tâm mặt sống mũi, đảm bảo đệm an toàn (headroom $\ge 30$px và cằm không chạm viền).
- **Kiểm chứng thị giác (Gate 6 & Invariant Soi Mắt):**
  - Chạy `run_winrt_ocr.py` kiểm tra `lines == 0` (sạch chữ/phụ đề rác).
  - Mở ảnh qua `browser_navigate` + `browser_vision` hoặc Antigravity CLI để xác nhận khuôn mặt người thật rõ nét, đầy đủ ngũ quan.
- **Đồng bộ kho & Khóa cứng:**
  - Ghi đè vào `D:/TIKTOK-videonuoinick/<F>/avatar.jpg`, `D:/video goc/<F_src>/avatar.jpg`.
  - Tạo marker `.manual_avatar_locked` tại các thư mục này.

### Trụ Cột 4: Đổi Tên Hiển Thị & Tiểu Sử (Bio)
- **Tên hiển thị:**
  - Chuyển từ username mặc định (ví dụ `hongdung5409`) sang tên người Việt có dấu (ví dụ `Hong Dung` / `Hồng Dung`).
  - Lưu ý cooldown 7 ngày của TikTok khi đổi tên; thao tác cẩn trọng qua màn hình "Sửa hồ sơ" $\rightarrow$ "Tên" $\rightarrow$ "Lưu" $\rightarrow$ "Xác nhận".
- **Tiểu sử (Bio):**
  - Câu từ tiếng Việt tự nhiên, phù hợp ngách của kênh (ví dụ kênh nhảy múa: *"Những khoảnh khắc vũ đạo ý nghĩa"*).
  - CẤM dính `@`, cấm link rác, cấm trùng lặp giữa các nick.

---

## 3. Checklist Nghiệm Thu Bắt Buộc Trước Khi Báo Cáo
- [ ] Sheet `TaiKhoan` và `Hashtag theo Folder` trong `Tik<N>.xlsx` đã cập nhật đúng Niche & Hashtags.
- [ ] Marker `.manual_hashtag_locked` và `.manual_avatar_locked` đã tồn tại ở các thư mục video liên quan.
- [ ] Video top $\ge 1.000$ views đã hiển thị nhãn "Đã ghim" trên lưới Profile (có ảnh chụp chứng minh).
- [ ] Tên hiển thị và Bio đã cập nhật đúng trên app TikTok.
- [ ] Ảnh nghiệm thu Profile tổng thể gửi cho User qua `MEDIA:<path>` phải được mở và kiểm tra thị giác trước (không gửi ảnh mù).
