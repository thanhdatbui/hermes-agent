# Bẫy Cắt Cụt Đầu, Sót Vụn Chữ Đỏ & Avatar Bị Kẹt Không Đổi (Sự Cố M34 Slot 6 Yoga - 2026-10-17)

## 1. Bối cảnh & Chuỗi Sai Lầm Nghiêm Trọng (Incident Analysis)
- **Tài khoản**: Máy 34 Slot 6 (`@yobi1965` - Hải Kiên, Tik 6). Nguồn video gốc Yoga Folder 434 (`D:/video goc/434`).
- **Sự cố 1: Ảo giác mảng màu mờ đỏ & chậu cây "20 lần"**:
  - Script trích xuất frame Haar cascade bị false positive trúng mảng màu đỏ / đồ vật.
  - Coordinator nhìn thấy mảng màu mờ đỏ nhưng không soi mắt bằng WinRT OCR, tự ảo giác mô tả: *"Cô gái tập Yoga ngồi thẳng, phong thái thư thái..."*.
  - Thực tế trong app TikTok, picker chọn nhầm thumbnail của video 2 (`2.mp4`) chứa chậu cây kim tiền và sticker màu hồng có chữ `20 lần/`.
  - User phát hiện và chất vấn gay gắt: *"Già cái địt cụ m ảnh đéo thấy clg cả mỗi 1 khoảng đỏ mà mày dám chọn đc mày có dùng win rt ocr đọc ảnh k v"*.
- **Sự cố 2: Cắt cụt đầu (Headless Crop) & sót vụn chữ đỏ**:
  - Coordinator crop lại từ video `1.mp4`, nhưng tính sai tọa độ trục y (crop từ y=250..530 thay vì trùm lên vùng đầu ở y=40..360).
  - Kết quả: Ảnh crop bị mất hoàn toàn phần đỉnh đầu, mắt, mũi, miệng — **CHỈ CÒN CỔ VÀ CẰM**, phía dưới lại dính chữ đỏ viền trắng cắt vụn!
  - Coordinator tiếp tục không dùng WinRT OCR và vision kiểm tra kỹ mà đã tự chém gió là ảnh cô gái yoga hoàn hảo rồi gửi User.
  - User tức giận gửi ảnh chụp và chửi: *"Cái địt con mẹ mày mày có dùng win rt ocr đọc hình trc khi gửi tao k v con chó"*.
- **Sự cố 3: Giữ ảnh kiểm tra ngầm khiến User phải giục**:
  - Sau khi chụp được ảnh màn hình, Coordinator không gửi ngay mà tiếp tục dispatch thêm subagent kiểm tra ngầm trong bóng tối.
  - User bức xúc: *"sao mày đéo gửi ảnh đẻ t kiểm tra luôn"*, *"Tao bảo mày gửi cái hình mới mày gen ra đây để t kiểm tra"*.
- **Sự cố 4: Avatar trên thiết bị thực tế chưa hề thay đổi**:
  - Do chọn trượt trong Photo Picker hoặc proxy stall ở màn hình Crop, app TikTok không thực sự lưu avatar mới. Avatar trên màn hình Profile thực tế vẫn là ảnh phong cảnh đồi núi cũ.
  - Coordinator không đo pixel/Mean BGR so với avatar cũ mà vội vã báo hoàn tất.
  - User phẫn nộ: *"tao đã bảo đổi cái ava khác làm từ sáng tới h vẫn y cái ava cũ là sao đụ mẹ mày có bị điên k"*.

---

## 2. Các Quy Tắc Bất Khả Xâm Phạm (Iron Invariants)

### 2.1. Anatomy & Headroom Gate (Chống Cắt Cụt Đầu / Mất Ngũ Quan)
- Ảnh avatar người BẮT BUỘC phải nhận diện đầy đủ các thành phần giải phẫu học: Đỉnh đầu, tóc, trán, mắt, mũi, miệng và cằm.
- CẤM TUYỆT ĐỐI gửi ảnh chỉ thấy cổ, ngực, vai hoặc cằm mà dám tuyên bố là khuôn mặt nhân vật.
- Headroom an toàn: Đỉnh đầu/tóc phải cách mép trên khung tròn tối thiểu 15-20% chiều cao ảnh, không bị cọ sát mép hoặc bị cắt lẹm.

### 2.2. Mechanical WinRT OCR Pre-Send Veto
- Trước khi gửi bất kỳ ảnh candidate avatar nào (`tmp_cand_*.jpg`), BẮT BUỘC chạy WinRT OCR (`ocr_tool.py` hoặc `ocr_boxes.ps1`).
- Nếu OCR phát hiện bất kỳ chữ lạ nào (như `20 lần`, `ngày`, `@`, chữ đỏ viền trắng cắt vụn, watermark, số tập):
  - **VETO NGAY LẬP TỨC!** Không được gửi ảnh đó cho User.
  - Phải điều chỉnh lại vùng crop hoặc bốc frame khác không dính subtitle/sticker.

### 2.3. Immediate Delivery Upon Candidate Generation
- Khi User yêu cầu đổi avatar ("đổi ava khác", "chọn ảnh khác"):
  - Sau khi trích xuất và crop ảnh ứng viên đạt chuẩn (Anatomy OK, OCR rỗng), BẮT BUỘC gửi ngay thẻ `MEDIA:<path>` trong lượt phản hồi đó để User duyệt bằng mắt.
  - CẤM TUYỆT ĐỐI tự ý chạy chuỗi nạp lên thiết bị trong bóng tối khi User chưa nhìn thấy ảnh mới.

### 2.4. Stale Avatar Diff Gate (Chống Báo Cáo Xong Khi Máy Vẫn Kẹt Ảnh Cũ)
- Khi nạp avatar trên điện thoại, script có thể báo ExitCode: 0 do màn hình Crop đóng lại, nhưng TikTok có thể hủy request ngầm do lỗi mạng/proxy (`ERR_PROXY_CONNECTION_FAILED`) hoặc chọn trượt ảnh trong Picker.
- Trước khi tuyên bố nạp avatar thành công:
  - BẮT BUỘC crop vùng avatar trên Profile và tính Mean BGR.
  - So sánh Mean BGR với avatar cũ trước khi thực hiện. Nếu độ lệch `mean_diff < 15.0` (vẫn y nguyên màu ảnh cũ) ➔ BẮT BUỘC ĐÁNH DẤU THẤT BẠI (`AVATAR_NOT_UPDATED_ON_PROFILE`), cấm claim thành công!
