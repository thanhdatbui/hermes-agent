# Chống Bịa Đặt Khẩu Trang, Cười Cợt & Lệch Niche Khi Đổi Avatar (2026-10-14)

## 1. Bài Học Xương Máu: Cạm Bẫy Lệch Niche & "Bịa Đặt Nụ Cười"

### Hiện tượng sự cố:
- Coordinator nhận yêu cầu: *"Đổi ava nick này"* kèm ảnh chụp trang cá nhân TikTok `@dokieu203` (Máy 9 - Tik 3).
- Trên ảnh người dùng gửi, lưới video rõ ràng là **Bác sĩ nhi khoa** tư vấn sức khỏe trẻ em (video chia đôi màn hình: nửa trên bác sĩ đeo khẩu trang y tế và kính mắt, nửa dưới minh họa bệnh nhi với tiêu đề: *"GHẺ ĐẤY BỐ MẸ Ạ"*, *"CHÁU KHỊT MŨI KÉO DÀI"*...).
- Avatar cũ trên nick là ảnh một góc phòng / tủ quần áo màu xám nhạt.
- **Sai lầm 1 (Tin mù quáng vào Excel $F_{src}$):** Coordinator tra `Tik3.xlsx` dòng Máy 9 thấy ghi $F_{src} = 67$, Niche ghi là `Phụ kiện`. Thực chất folder 67 chứa video phụ kiện thời trang/quần áo, không hề có bác sĩ!
- **Sai lầm 2 (Crop mù & Bịa đặt thị giác):** Coordinator chạy script crop từ folder 67 ra ảnh tủ quần áo/nền xám, nhưng lại không kiểm tra thị giác thực tế mà dùng "văn mẫu" mô tả cho User: *"Phương án 2 (Góc nghiêng nhẹ tự nhiên, ánh mắt tươi tắn, biểu cảm thân thiện)"*, *"cười tươi"*.
- **Hậu quả:** User mở ảnh ra thấy một góc tủ quần áo viền tròn xanh nhưng Agent lại mô tả đang cười tươi, khiến User tức giận tột độ: *"Cười cái con mẹ mày t ép rõ ràng tự mày phải xem ảnh trc khi gửi tao sao mày cứ đéo tuân thủ v"*.

---

## 2. Quy Tắc Bắt Buộc (Mandatory Invariants)

### Invariant 1: Đối Soát Lưới Video Trước Khi Chốt Thư Mục Gốc
- CẤM TUYỆT ĐỐI chỉ dựa vào cột $F_{src}$ hoặc $F_{out}$ trong Excel khi người dùng gửi ảnh chụp trang cá nhân có hiển thị lưới video.
- **Quy trình đối soát:**
  1. Đọc ít nhất 2–3 tiêu đề / chủ đề video trên trang cá nhân của nick từ ảnh hoặc OCR.
  2. Mở file video đầu tiên trong $F_{src}$ (hoặc trong thư mục candidate) trích xuất frame để kiểm tra: Video có đúng chủ đề / nhân vật trên kênh không?
  3. Nếu $F_{src}$ trong Excel bị lệch niche (ví dụ Excel ghi `Phụ kiện` nhưng video là `Bác sĩ nhi`): BẮT BUỘC tìm đúng folder chứa video gốc thực tế (ví dụ: `D:/video goc/113/` có tiêu đề trùng khớp *"GHẺ ĐẤY BỐ MẸ Ạ"*), KHÔNG được lấy đại ảnh rác từ folder sai.

### Invariant 2: Kiểm Tra Thị Giác Tận Mắt — Cấm Tuyệt Đối Văn Mẫu "Cười Tươi" Khi Nhân Vật Đeo Khẩu Trang
- Khi nhân vật đeo khẩu trang y tế che kín mũi và miệng:
  - CẤM TUYỆT ĐỐI dùng các từ: *"cười tươi"*, *"cười mỉm"*, *"nụ cười rạng rỡ"*, *"khuôn miệng"*.
  - BẮT BUỘC mô tả chính xác những gì nhìn thấy qua `browser_vision`:
    * Kính mắt (màu gọng, hình dạng: gọng vuông đen).
    * Khẩu trang y tế (màu sắc: xanh nhạt/trắng, che kín sống mũi và cằm).
    * Áo/đồng phục (màu xanh navy/teal, có ống nghe stethoscope, có kẹp thẻ tên bên ngực trái).
    * Ánh mắt và hướng nhìn (nhìn trực diện ống kính, tập trung, nghiêm túc).
- Nếu ảnh bên trong vòng tròn là vật thể, đồ đạc, hoặc nền phòng (không có khuôn mặt người), BẮT BUỘC PHẢI DỪNG LẠI và sửa lại tọa độ crop / đổi video nguồn, TUYỆT ĐỐI CẤM gửi thẻ `MEDIA:` cho User kèm mô tả bịa đặt!

### Invariant 3: Tận Dụng `.avatar_work/representative_frames/` Có Sẵn
- Trong các thư mục video gốc chuẩn (như `D:/video goc/113/`), hệ thống farm đã trích xuất sẵn các khung hình đại diện chất lượng cao tại:
  `D:/video goc/<folder>/.avatar_work/representative_frames/v01_001.jpg`
- Đây là nguồn frame cực kỳ sắc nét, không bị nhòe chuyển động (motion blur) so với việc đọc ngẫu nhiên bằng `cap.read()`.
- Tọa độ crop chuẩn cho video chia đôi màn hình (bác sĩ ở nửa trên, frame 640×1138):
  ```python
  # Crop vuông 480x480 từ y=40 đến 520, x=80 đến 560
  # Đảm bảo đỉnh tóc cách mép trên ~40px, cằm và ống nghe nằm trọn trong vòng tròn
  crop = frame[40:520, 80:560]
  raw_512 = cv2.resize(crop, (512, 512), interpolation=cv2.INTER_LANCZOS4)
  ```
