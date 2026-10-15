# Quy Chuẩn Đối Soát Tên Cụt Lủn Khi Đổi Avatar & Cơ Chế State-Machine OCR Rename (2026-10-15)

## 1. Bối Cảnh Sự Cố & Chỉ Trích Của Operator
- **Hiện tượng**:
  - Khi thực hiện đổi avatar cho 3 nick TikTok (`karunmmkx35` M65, `thibabxy1nr` M55, `ancilqaz063` M31), Coordinator nhận thấy tên hiển thị hiện tại trên máy là các tên 1 từ cụt lủn: **`Mai`**, **`Thảo`**, **`An`**.
  - Operator chất vấn trực tiếp:
    > *"Sao đặt tên gì chán v cụt lủn v. Hàm đặt tên t có thiết kế đặt tên giống người dùng bth r mà. Hay cứ để cụt lủn v cũng đc"*
- **Nguyên nhân gốc rễ**:
  - Dữ liệu tên từ đợt reg cũ bị bốc 1 từ duy nhất mà không áp dụng phân phối người dùng thật từ hàm `make_tiktok_name(email)`.
  - Tên 1 từ trơ trọi là dấu hiệu nhận diện bot farm rõ nét nhất đối với thuật toán TikTok và người xem thật, làm giảm trust và tụt tỷ lệ follow/tương tác của kênh.
  - CẤM TUYỆT ĐỐI để tên cụt lủn 1 từ. Khi phát hiện tên 1 từ trong quá trình đổi avatar hoặc audit, BẮT BUỘC phải chủ động đồng bộ đổi tên theo đúng chuẩn người dùng thật.

---

## 2. Quy Chuẩn Đặt Tên Người Dùng Thật (`make_tiktok_name`)
Hàm chuẩn `make_tiktok_name(email)` nằm tại `D:/Taadaa/Tiktok_Reg/social_reg_v1.py` với phân bổ 5 phong cách tự nhiên:
1. **Họ + Đệm + Tên (25%)**: Ví dụ: *Nguyễn Hoài An*, *Trần Minh Đạt*.
2. **Họ + Tên (25%)**: Ví dụ: *Lê Linh*, *Vũ Nam*.
3. **Đệm + Tên (20%)**: Ví dụ: *Ngọc Mai*, *Tuấn Minh*, *Thanh Thảo*.
4. **Tên + Biệt danh đời thường (20%)**: Ghép từ `_TEN_LIST` + `_NICK_SUFFIX` (*Còi, Bé, Heo, Bông, Mập, Kem, Miu, Bơ, Gạo, Nấm...*). Ví dụ: *Linh Bông*, *An Bơ*, *Mai Miu*.
5. **Tên lặp / Duo dễ thương (10%)**: Ví dụ: *An An*, *Miu Miu*, *Gạo Gạo*.

> **Nguyên tắc vàng**: Tên hiển thị TikTok **LUÔN LUÔN tối thiểu 2 từ**, phản ánh đúng ngữ cảnh nhân vật của kênh (MC bản tin, diễn giả kinh doanh, dịch vụ mẹ & bé).

---

## 3. Cạm Bẫy Blind Tapping vs Bắt Buộc State-Machine OCR Khi Đổi Tên
- **Cạm bẫy Blind Tapping (Chết người)**:
  - Khi viết script đổi tên nhanh bằng cách tap cứng tọa độ (ví dụ: `tap(350, 750)` để mở Sửa hồ sơ), script sẽ THẤT BẠI 100% nếu app TikTok không ở màn hình Profile.
  - Thực tế trên farm: App thường thức dậy ở màn hình **TikTok LIVE** (phiên livestream bán hàng) hoặc **Feed Đề xuất** (For You).
  - Cú tap mù vào `(350, 750)` sẽ bấm nhầm vào banner ghim sản phẩm TikTok Shop hoặc phòng chat LIVE, làm văng luồng và không bao giờ đổi được tên.
- **Quy chuẩn State Machine OCR bắt buộc (Canonical `do_rename_m71.py`)**:
  1. **Phân loại trạng thái màn hình qua WinRT OCR**:
     - `FEED`, `LIVE`, `PROFILE`, `SWITCHER`, `EDIT_PROFILE`, `NAME_EDIT`.
  2. **Điều hướng an toàn**:
     - Nếu ở `LIVE` hoặc `FEED`: Chạm tab Hồ sơ tại `XY_PROFILE_TAB (972, 1857)` hoặc bấm phím Back để về Profile.
     - Nếu ở `PROFILE`: Dùng OCR quét tìm nút *"Sửa hồ sơ"* (hoặc icon bút chì) thay vì tap mù tọa độ.
     - Nếu ở `EDIT_PROFILE`: Dùng OCR định vị dòng *"Tên"* (nằm trên dòng *"Tên người dùng"*), tap vào để mở `NAME_EDIT`.
  3. **Gõ tiếng Việt UTF-8 qua AdbKeyboard**:
     - Xóa sạch ô nhập bằng `ADB_KEYBOARD_CLEAR_TEXT` hoặc Select All + Del.
     - Mã hóa base64 tên mới: `base64.b64encode(NEW_NAME.encode('utf-8')).decode('ascii')`.
     - Broadcast intent `ADB_KEYBOARD_INPUT_TEXT` với tham số `--es text <base64>`.
     - Bấm *"Lưu"* `(980, 140)`, xác nhận popup 7 ngày tại `(750, 1150)`.
  4. **Nghiệm thu hai lớp**:
     - Chụp ảnh màn hình Profile, dùng OCR/Vision đọc lại dòng tên ngay trên `@username` để xác nhận tên mới đã hiển thị thực tế trước khi báo DONE.
