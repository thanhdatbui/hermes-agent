# Profile Grid Niche Cross-Check & Branded/Mascot Avatar Strategy (2026-10-17)

## 1. Hiện Tượng & Nguyên Nhân Gốc Rễ (Root Cause)
- **Hiện tượng**: User gửi ảnh profile TikTok (ví dụ: `@carlosfwagne2` M59 Tik 3) yêu cầu "Đổi ava", nhưng Agent tạo và nạp avatar nam thanh niên ngồi thu âm podcast tiếng Anh trước micro. User lập tức phản ứng: *"Ủa mà t thấy ava m tạo klq tới kênh?"*
- **Nguyên nhân cốt lõi**:
  1. **Bẫy thư mục `video goc` lệch nguồn**: Thư mục `D:/video goc/467/` chứa clip crawl cũ của một creator podcast tiếng Anh. Trong khi đó, nguồn video thật đang nuôi và đã render ra `D:/TIKTOK-videonuoinick/467/` (từ `D:/video goc/219/`) là các clip về: *Sổ chủ nhiệm*, *Khuyến mãi Back to School*, *Bìa sách Tin học 1*, *Đồ chơi lego xe bọc thép* của **Nhà sách Giáo Dục Cần Thơ**.
  2. **Bỏ qua bước đối soát thị giác lưới video (Grid Visual Audit)**: Agent chỉ chạy Haar Cascade tìm mặt người lớn nhất trong `.avatar_work/representative_frames/` của `video goc` mà không nhìn vào 6 thumbnail video trên màn hình Profile người dùng gửi.
  3. Kênh bán sách giáo khoa, đồ dùng học sinh tiểu học nhưng avatar lại là thanh niên streamer thu âm tiếng Anh $\to$ Lệch ngách và lệch vibe nghiêm trọng.

---

## 2. Quy Tắc Đối Soát Lưới Profile Trước Khi Chọn Avatar (Visual Grid Gate)
Trước khi crop avatar cho bất kỳ kênh nào:
1. **Kiểm tra 3-6 thumbnail video trên profile**:
   - Nếu thumbnail là: Sách giáo khoa, dụng cụ học sinh, đồ chơi, ẩm thực, sản phẩm vật lý, đồ gia dụng $\to$ Đây là kênh **Sản phẩm / Thương hiệu / Hoạt hình / Dịch vụ**, **KHÔNG PHẢI** kênh Creator/Vlog cá nhân.
2. **Chiến lược chọn Avatar theo ngách nội dung**:
   - **Kênh Cửa hàng / Nhà sách / Thương hiệu**: Trích xuất Logo chính thức (biểu tượng cuốn sách mở, quả địa cầu GD, tên thương hiệu) đặt trên nền tròn/vuông trắng $512 \times 512$ có viền an toàn.
   - **Kênh Thiếu nhi / Giáo dục / Đồ chơi**: Trích xuất Mascot hoạt hình (ví dụ cậu bé học sinh tươi cười trên bìa sách, nhân vật 2D/3D trong clip), gam màu tươi sáng, thân thiện.
   - **Kênh Creator / Idol / Kể chuyện cá nhân**: Mới dùng ảnh chân dung người thật trích từ clip có nhân vật chính.

---

## 3. Quy Chuẩn Đồng Bộ Niche & Hashtag Kép (Dual Standardization)
Khi User yêu cầu *"Chuẩn hoá luôn hashtag"* hoặc chuẩn hoá kênh:
1. **Định danh lại Niche chuẩn trong `Tik<N>.xlsx`**:
   - Tra soát bảng `TaiKhoan` trong `D:/OneDrive/TaadaaData/kibe/Tik<N>.xlsx`:
     * `wb = openpyxl.load_workbook(path)`
     * `ws = wb["TaiKhoan"] if "TaiKhoan" in wb.sheetnames else wb.active` *(Lưu ý: Bắt buộc chọn đúng sheet `TaiKhoan`, tránh dùng `wb.active` vì có thể trỏ nhầm sheet phụ)*.
   - Cột 6 (`Keyword Video`): Đổi từ nhãn chung chung (ví dụ `Sáng tạo`) sang đúng ngách (`Sách và đọc sách` hoặc `Học sinh`).
   - Cột 7 (`Hashtag Pool`): Gán bộ hashtag chuẩn ngách tương ứng.
2. **Khóa bảo vệ cứng**:
   - Đăng ký folder render (`F_out`) và folder nguồn (`F_src`) vào `manual_hashtag_protected_folders.json`.
   - Tạo marker vật lý `.manual_hashtag_locked` tại cả 2 đầu kho để ngăn cronjob tự động ghi đè.
