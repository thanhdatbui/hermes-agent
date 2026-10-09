# TikTok Upload: Xử Lý Đăng Dở Chừng Hiện Bản Nháp & Tự Động Resume (2026-09-21)

## 1. Hiện Tượng & Nguyên Nhân
- **Bối cảnh**: Khi flow đăng video TikTok bị gián đoạn mạng, timeout upload hoặc crash giữa chừng, TikTok tự động lưu video vào mục **Bản nháp (Drafts)** trên trang Hồ sơ (Profile) của tài khoản.
- **Điểm nghẽn cũ**:
  1. Tại bước `ACCOUNT_READY`, workflow cũ mặc định gọi `_delete_all_profile_drafts()` để dọn sạch bản nháp. Nếu không xoá được hoặc có bản nháp dở dang, workflow dễ kẹt hoặc push đè video mới, gây lãng phí media và mất đồng bộ số video.
  2. Tại bước kiểm đếm baseline video trên Profile (`_profile_video_tile_records`), ô Bản nháp (`Bản nháp: 1`) nếu có bounds tương tự video tile sẽ bị đếm nhầm vào tổng số video đã publish, làm sai lệch baseline so sánh trước và sau khi Post.

## 2. Giải Pháp Chuẩn (State Machine Pipeline)
1. **Phát hiện & Bảo toàn Bản nháp (`ACCOUNT_READY`)**:
   - Thay vì xóa mù quáng, kiểm tra `bản nháp` hoặc `draft` trong `profile_xml`.
   - Nếu có, set `context.has_profile_draft = True` và giữ nguyên bản nháp để chuẩn bị resume ở bước tiếp theo.
2. **Loại trừ Bản nháp khỏi Baseline Đếm Video (`_profile_video_tile_records`)**:
   - Khi quét các node video tile, quét toàn bộ text/desc của các node con.
   - Nếu chứa `"bản nháp"` hoặc `"draft"`, lập tức bỏ qua (`continue`), không tính vào `records`.
3. **Cơ chế Tự Động Mở & Đăng Tiếp (`_resume_draft_from_profile`)**:
   - Kích hoạt trong `VIDEO_PICK` khi `context.has_profile_draft` hoặc màn hình Profile có chữ `Bản nháp`.
   - **Bước 1**: Tap vào tile **Bản nháp** trên Profile (`text_contains="Bản nháp"` hoặc `"Draft"`).
   - **Bước 2**: Tap vào video bản nháp đầu tiên (hỗ trợ `resource_id="cover"`, `"thumbnail"`, `"video_cover"`, `"item_root"` hoặc bounds fallback `t >= 150 and b <= 1800`).
   - **Bước 3**: Chuyển sang màn hình Editor, tự động tìm và tap nút **Tiếp / Next** (`sp3`, `next_btn`).
   - **Bước 4**: Xác nhận giao diện đã chuyển vào màn hình **Composer (Đăng)** (`_is_final_composer_surface` hoặc có text `Đăng`, `Post`, `Thêm mô tả`).
4. **Bỏ Qua Push Lại Media**:
   - Khi resume thành công vào Composer, flow bỏ qua việc push lại media từ PC xuống máy và tiến thẳng tới `CAPTION_FILL` / `POST`.
