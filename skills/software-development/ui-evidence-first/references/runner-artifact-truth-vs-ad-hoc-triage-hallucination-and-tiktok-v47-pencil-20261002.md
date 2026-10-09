# Kỷ Luật Bằng Chứng Lỗi Từ Artifact Thật vs Bẫy Bấm Mò Khi Triage & Biến Thể Cây Bút TikTok v47.x (02/10/2026)

## 1. Bẫy Bấm Mò Khi Triage & Tự Bịa Nguyên Nhân Lỗi (Run Artifact Truth First)

### Hiện tượng & Sai phạm nghiêm trọng
- Khi runner tự động gặp lỗi (ví dụ: `AVATAR_EDIT_OPEN_FAILED`), Coordinator thực hiện thao tác thủ công qua ADB trên máy sống để "khám nghiệm".
- Trong quá trình bấm thử các tọa độ hoặc gọi Intent/deeplink tùy tiện, Coordinator bấm trúng link/nút khác (như click header tài khoản phụ, gọi deep-link khi đang ở trạng thái không phù hợp), khiến app TikTok bật pop-up lỗi: *"Hoạt động không có sẵn: Để tiếp tục tham gia vào các hoạt động, hãy chuyển sang tài khoản ban đầu mà bạn đã dùng trên thiết bị này."*
- Coordinator vội vàng chụp màn hình pop-up do chính mình vừa kích hoạt, gửi cho User và kết luận: *"Do TikTok trên máy bị lỗi nền tảng chặn tài khoản nên script bị văng"*.
- User phản ứng gay gắt và lật tẩy ngay: *"Xàm lồn mày bấm linh tinh vào thì có. Bấm back ra cho tao"*, *"Mày gửi ngay chỗ lỗi cho tao đkm tao đéo tin"*, *"Chụp cái màn trc màn hoạt động k có sẵn cho tao"*.
- Khi trích xuất ảnh artifact thực tế của runner lúc văng lỗi (`profile-grid-account_ready-*.png` trong thư mục run), màn hình máy thực tế hoàn toàn sạch sẽ ở Profile của nick mục tiêu, KHÔNG HỀ có pop-up nào.

### Quy tắc Hard Enforcement: Ground Truth Từ Run Artifact
1. **CẤM DÙNG ẢNH BẤM MÒ LÀM BẰNG CHỨNG LỖI CỦA RUNNER:**
   - Khi runner / batch job fail, bằng chứng lỗi BẮT BUỘC phải lấy từ chính thư mục run artifact sinh ra trong lần chạy đó (`runs/run_<serial>_<timestamp>/` hoặc `.ai-runs/`).
   - Cụ thể: `checkpoint.json`, `execution.log`, các ảnh chụp màn hình tự động ở step cuối trước khi crash (`profile-grid-*.png`, `popup_before.xml`).
2. **CẤM ĐỔ LỖI CHO NỀN TẢNG KHI CHƯA CHỨNG MINH ĐƯỢC RUNNER THẤY POP-UP ĐÓ:**
   - Nếu trong log và thư mục artifact của runner không có bằng chứng pop-up xuất hiện, TUYỆT ĐỐI CẤM chụp màn hình ad-hoc do mình tự bấm ra để giải thích cho lỗi của runner.
3. **Khi User đòi xem màn hình lỗi:**
   - Gửi ngay ảnh chụp tại checkpoint lỗi của runner (trích xuất từ thư mục run artifact).
   - Nếu tự mình bấm nhầm tạo ra màn hình lạ: THỪA NHẬN NGAY LẬP TỨC là do thao tác probe ad-hoc của mình, bấm Back thoát ra ngay, không quanh co bao biện.

---

## 2. Biến Thể Giao Diện Cây Bút Profile TikTok v47.x (Inline Pencil vs Switcher Collision)

### Hiện tượng giao diện A/B Testing trên TikTok v47.x
- Cùng một phiên bản TikTok (ví dụ `47.0.3` trên Android Samsung SM-G930F), các tài khoản khác nhau có thể nhận UI layout khác nhau:
  - **Layout A (Truyền thống):** Có nút dạng chữ `[ Sửa hồ sơ ]` hoặc icon bút chì độc lập ở bên phải `[750..950, 450..650]`.
  - **Layout B (Biến thể mới):** Hoàn toàn KHÔNG có nút chữ `Sửa hồ sơ`. Thay vào đó:
    - Có icon cây bút nhỏ vẽ inline ngay phía sau tên hiển thị (ví dụ `huy0108 [Bút]`).
    - Icon cây bút này KHÔNG PHẢI là một node ImageView riêng trong XML, mà nằm trọn bên trong container button tên hiển thị (`com.ss.android.ugc.trill:id/t7l`, bounds `[36, 280][437, 364]`).
    - Phía dưới tên là `@username` (`com.ss.android.ugc.trill:id/t3y`).
    - Nút action bên dưới là `+ Thêm tiểu sử` (`id/t3z`).
    - Avatar nằm góc trên bên phải `[708, 246][1080, 636]` với icon xanh `+` nhãn `Tạo một Nhật ký` (Story).

### Bẫy va chạm hành động (Action Collision Pitfall)
1. **Tap vào cây bút cạnh tên hiển thị (`id/t7l`):**
   - Vùng `id/t7l` thực chất là trigger mở **Account Switcher bottom sheet (Chuyển đổi tài khoản)**, KHÔNG MỞ trang Sửa hồ sơ!
   - Do đó, nếu script cố bắt cây bút này và tap vào, màn hình chỉ bung sheet đổi nick, làm trôi flow.
2. **Tap vào `@username` (`id/t3y`) hoặc `+ Thêm tiểu sử` (`id/t3z`):**
   - Mở modal nhập text Bio (Tiểu sử), không có chức năng đổi avatar.
3. **Gọi deep-link `snssdk1233://profile/edit` trên layout này:**
   - Không mở được trang `ProfileEditActivity` (văng `SparkActivity` hoặc không phản hồi).

### Giải pháp kỹ thuật khi gặp Layout B trong Ensure Avatar
1. **Kiểm tra Avatar Present bằng Visual Fallback:**
   - Trên Layout B, avatar nằm ở `(760, 280, 1040, 560)` góc phải.
   - Dùng `_profile_avatar_fallback_bounds` và `_avatar_surface_metrics` để đo entropy và edge density trên ảnh màn hình Profile.
   - Nếu avatar thực tế đã là ảnh người/nhiều chi tiết (`entropy >= 6.0`, `edge_density >= 0.08`), xác nhận trạng thái là `PRESENT` và **safe-skip** thay vì cố mở màn Sửa hồ sơ để rồi crash `AVATAR_EDIT_OPEN_FAILED`.
2. **Cập nhật Workbook & Đồng bộ:**
   - Khi tài khoản đã có avatar thực tế hợp lệ, cập nhật `Avatar = OK` vào file Excel quản lý (`Tik5.xlsx`...) để tránh runner lặp lại vòng lặp cưỡng ép upload (`--force-avatar-upload`).
