# Quy Chuẩn Chuẩn Hoá Kênh Faceless / Văn Phòng Phẩm (Studygram / Sổ Klong) & Kỷ Luật Guard (2026-11-04)

## 1. Đặc Thù Ngách Faceless (Dụng Cụ Học Tập / Sổ Tay / Bàn Học Chill)
- **Nhận diện Ground Truth:** Video thực tế không xuất hiện khuôn mặt người (chỉ có bàn tay viết, lật sổ, unbox, decor bàn học, viết calligraphy, hoặc sản phẩm như sổ còng Klong, binder, tập học sinh).
- **Bẫy Haar Cascade / Face Detector:** Tuyệt đối không dùng bộ lọc tìm mặt (`haarcascade_frontalface_default.xml`) trên ngách này vì các hình vẽ hoạt hình, chibi thỏ, icon sticker trên bìa vở hay lưới ô ly caro sẽ gây ra false positive nghiêm trọng (hơn 70+ "faces" giả).
- **Tiêu chuẩn 4 Phương án Avatar cho ngách Stationery:**
  1. **PA 1 (Tối ưu):** Bìa sổ kẹp còng/binder decor góc chụp flatlay hoặc góc nghiêng 45 độ dưới ánh đèn bàn học chill.
  2. **PA 2:** Bàn học decor tổng thể (kệ sách mini, khay bút acrylic, đèn học pastel).
  3. **PA 3:** Trang take notes từ vựng / bullet journal viết chữ calligraphy đẹp mắt.
  4. **PA 4:** Bìa vở/tập pastel cute (ví dụ tập 4 ly ngang hình thỏ, màu pastel).
- **Kỷ luật sạch chữ 100%:** Dùng WinRT OCR quét kiểm tra khung hình crop 512x512. BẮT BUỘC text OCR phải rỗng (`''`), triệt tiêu hoàn toàn watermark TikTok, `@klong_official`, số view hay icon play.

## 2. Kỷ Luật Phân Vai Coordinator & Rào Chắn Terminal (Guard Compliance)
- **Lệnh `python -c` trong Coordinator Terminal:** Chỉ dùng để kiểm chứng read-only (tra cứu DB, tính toán độ nét Laplacian, đọc WinRT OCR). Bị chặn cơ học ngay lập tức nếu chuỗi chứa thao tác ghi/xóa/subprocess (`imwrite`, `remove`, `unlink`, `subprocess`).
- **Cấm tự ý sửa file `.py` trực tiếp:** Guard chặn vô điều kiện `write_file` và `patch` trên các file mã nguồn `.py` trong repo git. Không lách luật bằng cách tạo script rác.
- **Kỷ luật phát hành thẻ `MEDIA:`:** TUYỆT ĐỐI KHÔNG phát hành thẻ `MEDIA:<path>` khi chưa có file canvas thật được render và kiểm chứng WinRT OCR / Multimodal. Không bao giờ gửi ảnh cũ của kênh khác để lấp liếm.
- **Quy tắc Ghim Top (Pin Top):** Chỉ ghim khi có video đạt $\ge 1.000$ views. Các kênh mới chỉ có 100 - 300 views TUYỆT ĐỐI KHÔNG ghim cưỡng ép, tránh làm loãng feed và mất tự nhiên.
