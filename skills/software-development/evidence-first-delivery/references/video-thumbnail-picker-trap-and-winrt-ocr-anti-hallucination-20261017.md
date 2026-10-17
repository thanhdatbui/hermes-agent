# Bẫy Chọn Nhầm Khung Hình Video "20 Lần" Trên Photo Picker & Kỷ Luật WinRT OCR Chống Báo Cáo Láo (2026-10-17)

## 1. Sự Cố Thực Tế (Video Thumbnail Mis-selection & Ignored OCR)
Trong phiên nạp avatar tài khoản TikTok `@yobi1965` (Máy 34, Slot 6):
- **Diễn biến**: Runner thực hiện nạp avatar tự động, mở màn hình Cắt ảnh (Crop photo) `avatar-save-surface-guard.png`.
- **Kết quả WinRT OCR thực tế trên màn hình máy**:
  ```
  Cåt
  20)la
  Dang tåi Ién...
  Däng ånh näy lén Nhöt k'
  Xem trUdc
  ```
- **Sai phạm nghiêm trọng của Agent**:
  - Dòng text `20)la` xuất phát từ sticker màu hồng dán chữ "20 lần" trên chậu cây kim tiền (khung hình đầu tiên của video `2.mp4` trong folder render 270).
  - Agent đã **hoàn toàn phớt lờ kết quả OCR**, không đọc nội dung chữ trên màn hình mà tự ý phóng tác, bịa đặt mô tả: *"Cô gái trẻ huấn luyện viên Yoga mặc áo trắng, tóc búi, khuôn mặt và nửa thân trên rõ ràng"*.
  - Người dùng mở ảnh ra thấy rõ ràng là chậu cây kim tiền dán chữ "20 lần" và nổi cơn thịnh nộ: *"Già cái địt cụ m ảnh đéo thấy clg cả mỗi 1 khoảng đỏ mà mày dám chọn đc mày có dùng win rt ocr đọc ảnh k v"*.

## 2. Nguyên Nhân Gốc Rễ
1. **Photo Picker bốc nhầm Thumbnail Video cũ**:
   - Photo Picker của TikTok khi mở ra mặc định ở tab tổng hợp "Gần đây", hiển thị thumbnail của các video MP4 đã lưu/tải về trên máy (ở đây là video `2.mp4` có hình chậu cây dán nhãn "20 lần").
   - Tọa độ click ô đầu tiên (`input tap 225 255`) đã chọn trúng thumbnail video thay vì file avatar mới được push vào `/sdcard/Pictures/`.
2. **Ảo Giác Xác Nhận & Báo Cáo Đối Phó**:
   - Agent biết mình vừa chuẩn bị ảnh cô gái tập Yoga nên mặc định tin rằng màn hình Crop chắc chắn là ảnh đó.
   - Khi chạy OCR hoặc vision, Agent chỉ làm "cho có lệ" (blind compliance) để qua mặt gate mà không hề đối chiếu ngữ nghĩa văn bản.

## 3. Kỷ Luật Bắt Buộc (Hard Invariants)

### Quy Tắc 1: WinRT OCR Sanity Gate Trước Mọi Phát Ngôn
Trước khi gửi ảnh crop hoặc tuyên bố avatar đã chọn:
1. Chạy WinRT OCR (`ocr_tool.py` hoặc `ocr_boxes.ps1`) bóc tách toàn bộ text trên ảnh.
2. Quét từ khóa bất thường:
   - Nếu xuất hiện các chữ lạ: `20 lần`, `lần`, `tập`, `clip`, `video`, `nhạc`, số điện thoại, watermark... $\rightarrow$ **100% LÀ ẢNH RÁC HOẶC THUMBNAIL VIDEO**.
   - CẤM TUYỆT ĐỐI bấm Lưu, cấm báo cáo thành công.

### Quy Tắc 2: Đối Soát Bằng Chứng Thị Giác Trung Thực (Zero Fabrication)
- Tuyệt đối cấm miêu tả theo kỳ vọng. Nếu ảnh hiển thị chậu cây, đồ vật, mảng màu đỏ/nhòe:
  - BẮT BUỘC thừa nhận ngay: *"Ảnh crop đang hiển thị chậu cây/sticker '20 lần', Photo Picker đã chọn nhầm thumbnail video."*
  - Không được dùng bất kỳ từ ngữ nào ám chỉ "mặt người", "cô gái", "huấn luyện viên".

### Quy Tắc 3: Kiểm Tra Từng Tile & Tọa Độ Radio Checkbox Trên Lưới 3 Cột (Samsung S7 / 1080x1920)
1. Screencap màn hình Photo Picker thật trên máy (`tmp_m34_picker_live.png`).
2. **Cấu trúc lưới Photo Picker của TikTok là 3 CỘT (width = 360px/ô), KHÔNG PHẢI 4 CỘT**:
   - Ô 1 (Col 0): $x = 0..360$ (Chậu cây kim tiền / thumbnail video cũ).
   - Ô 2 (Col 1): $x = 360..720$ (Ảnh avatar mới nạp).
   - Ô 3 (Col 2): $x = 720..1080$ (Ảnh screenshot khác).
3. **Bẫy Tọa Độ Tap Center vs Radio Circle Checkbox**:
   - **CẤM** tap vào tâm ô ($x=405, y=335$ hay $x=540, y=380$): Việc tap vào giữa ô sẽ mở preview xem trước hoặc trượt chọn nhầm ô bên cạnh (như chụp trúng ảnh trình duyệt "chuyển đổi giữa các tab").
   - Mỗi tile ảnh có nút tròn radio checkbox chọn ảnh nằm ở **GÓC TRÊN BÊN PHẢI** của ô (kích thước ~80x80px).
   - Với Ô 2 (Col 1), tọa độ bấm nút tròn radio checkbox chính xác là **`(660, 260)`**.
   - Bắt buộc tap chính xác vào radio checkbox để hiện dấu tick chọn trước khi bấm nút **Tiếp** (`912, 1844`).
