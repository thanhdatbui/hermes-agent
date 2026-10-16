# Cạm Bẫy Trôi Kho Nguồn & Đối Soát Lưới Video Ngăn Ngừa Avatar Lệch Kênh (16/10/2026)

## 1. Hiện Tượng & Cảnh Báo Hiện Trường
- **Hiện tượng**:
  - User gửi ảnh TikTok profile `@carlosfwagne2` ("Hoàng Kim Hùng" - Máy 59 Tik 3) yêu cầu "Đổi ava", sau đó nhắc tiếp: *"Chuẩn hoá luôn hashtag đi. Ủa mà t thấy ava m tạo klq tới kênh?"*.
  - Nguyên nhân: Coordinator trích xuất ảnh chân dung nam thanh niên ngồi trước micro thu âm podcast tiếng Anh (từ `D:/video goc/467/`) và nạp lên làm avatar.
  - Tuy nhiên, toàn bộ lưới video thực tế của kênh và kho video đang nuôi (`D:/TIKTOK-videonuoinick/467/`) lại là về **Sách giáo dục, sách giáo khoa, dụng cụ học sinh, đồ chơi thiếu nhi của Nhà sách Giáo Dục Cần Thơ** (video Sổ chủ nhiệm, Back to School, sách Tin học 1, mô hình xe bọc thép...).
  - Kết quả: Người xem vào trang thấy kênh bán sách/dụng cụ học sinh tiểu học nhưng avatar lại là thanh niên streamer podcast tiếng Anh, hoàn toàn lệch ngách và lệch phong cách kênh.

---

## 2. Nguyên Nhân Cốt Lõi: Trôi Kho $F_{src}$ vs $F_{out}$ vs Thư Mục Cũ
1. **Lệch giữa $F_{src}$ (Nguồn cào) và $F_{out}$ (Render nuôi)**:
   - Trong workbook `Tik3.xlsx`: Kênh có `Folder Video (Render) = 467`, nhưng `Video Goc (Nguon Cao) = 219`.
   - Kho video thật nuôi kênh thực chất được tải từ folder 219 (Nhà sách Cần Thơ) và render vào `D:/TIKTOK-videonuoinick/467/`.
   - Tuy nhiên, trong thư mục `D:/video goc/467/` lại tồn tại một kho video cũ/lỗi chứa 67 clip một bạn nam ngồi chia sẻ podcast tiếng Anh.
2. **Bẫy "Chỉ Tìm Khuôn Mặt Người" (Human Face Haar Cascade Trap)**:
   - Coordinator mặc định chạy nhận diện khuôn mặt người (`haarcascade_frontalface_default.xml`) trong `video goc/467`.
   - Thuật toán bắt trúng khuôn mặt rõ nét của người nói tiếng Anh trong folder 467 cũ, bỏ qua sự thật rằng kho video nuôi thực tế của kênh (folder 219) không có người nói chuyện mà là sản phẩm sách vở, đồ dùng học tập.

---

## 3. Quy Trình 3 Bước Đối Soát Bắt Buộc Trước Khi Chốt Avatar

### Bước 1: Khám nghiệm Lưới Video Profile (Grid Visual Audit)
- BẮT BUỘC dùng Vision (`ag_cli.py ask` hoặc OCR) đọc nội dung/thumbnail của $\ge 6$ video hiển thị trên lưới trang cá nhân từ screenshot User gửi:
  * Nếu video là gái xinh / creator chia sẻ $\to$ Tìm avatar người thật của chính creator đó.
  * Nếu video là sách, dụng cụ học sinh, đồ chơi, ẩm thực, phong cảnh không có người dẫn $\to$ **CẤM gượng ép lấy avatar người lạ từ kho video khác**.

### Bước 2: Đối Soát Kho Video Render Thực Tế ($F_{out}$) vs Kho Gốc ($F_{src}$)
- Trích xuất frame tại giây 2.0s từ các video $1, 2, 3$ trong `D:/TIKTOK-videonuoinick/<F_out>/` và đối chiếu với thumbnail trên lưới profile:
  * Xác nhận video trong `TIKTOK-videonuoinick/<F_out>/` khớp 100% với thumbnail trên TikTok profile.
  * CẤM chỉ quét `.avatar_work/representative_frames/` của `D:/video goc/<F_out>/` khi chưa xác minh folder đó có phải nguồn thật của kênh hay không.

### Bước 3: Định Hướng Phong Cách Avatar Theo Đúng Niche Kênh
Với kênh dạng Shop / Sản phẩm / Tổ chức giáo dục (không có mặt creator):
1. **Phương án A (Thương hiệu / Shop uy tín - Brand Logo)**:
   - Trích xuất Logo của đơn vị/cửa hàng từ các video giới thiệu, banner hoặc infographic hướng dẫn mua hàng (ví dụ: Logo cuốn sách mở + Quả địa cầu GD của Nhà sách Cần Thơ).
   - Đặt trên nền tròn trắng sạch sẽ $512 \times 512$, căn tâm chuẩn để biểu tượng chiếm $60-65\%$ diện tích vòng tròn.
2. **Phương án B (Mascot Hoạt hình / Nhân vật đại diện - Mascot/Character)**:
   - Trích xuất nhân vật hoạt hình xuất hiện lặp đi lặp lại trên bìa sách, hộp đồ chơi hoặc mascot quảng bá (ví dụ: Cậu bé hoạt hình học sinh tươi cười bên máy tính từ sách Tin học 1).

---

## 4. Chuẩn Hoá Đồng Bộ Niche & Hashtag Pool Khi Chuẩn Hoá Kênh
- Khi phát hiện Niche Drift giữa nội dung video và dữ liệu Excel:
  1. **Cập nhật Workbook `Tik<N>.xlsx` (Lưu ý Sheet Name)**:
     - **Bẫy `wb.active`**: Không dùng `sheet = wb.active` vì có thể rơi vào sheet thống kê khác; BẮT BUỘC chỉ định rõ `sheet = wb["TaiKhoan"] if "TaiKhoan" in wb.sheetnames else wb.active`.
     - Sửa `Keyword Video` về đúng ngách (ví dụ: từ `Sáng tạo` $\to$ `Sách và đọc sách`).
     - Sửa `Hashtag Pool` tương ứng:
       `#sach #sachhay #docsach #sachgiaokhoa #sachthieunhi #nhasach #dodunghoctap #dungcuhoctap #hocsinh #tiktokvietnam #xuhuong #fyp #videohay`
  2. **Khóa bảo vệ Registry & Physical Marker**:
     - Thêm folder vào `D:/Taadaa/data/manual_hashtag_protected_folders.json`.
     - Tạo marker `.manual_hashtag_locked` tại cả 3 đầu kho (`TIKTOK-videonuoinick/<F_out>`, `video goc/<F_src>`, `video goc/<F_out>`).

---

## 5. Xử Lý Lỗi [AVATAR_UPLOAD_MENU_MISSING] Do App Văng Về Trang Chủ (Feed) Sau Media Scan
- **Hiện tượng**:
  - Khi chạy runner upload avatar, quá trình push ảnh và phát broadcast `MEDIA_SCANNER_SCAN_FILE` khiến TikTok bị giật hoặc chuyển tab về **Trang chủ (Home Feed)**.
  - Log ghi nhận: `[AVATAR_UPLOAD_MENU_MISSING] ENSURE_AVATAR: Không tìm thấy Tải ảnh lên`, và `popup_before.xml` chứa danh sách text `['Trang chủ', 'Cửa hàng', 'Hộp thư', 'Hồ sơ']`.
- **Phân loại lỗi**:
  - Đây là lỗi **TRANSIENT L0** (do broadcast hệ thống Android hoặc áp lực RAM làm thay đổi viewport foreground tạm thời).
- **Quy trình xử lý dứt điểm**:
  1. Không tính vào Circuit Breaker.
  2. Dọn sạch Recent apps và đưa thiết bị về Home Launcher qua `automation-core`.
  3. Kiểm tra lock qua `with_device_lock.py --machine <M>`.
  4. Thực hiện retry L0 chạy lại runner ngay lập tức (tối đa 2 lần). Không được đánh dấu BLOCKED hay đóng băng phiên.

