# Case 81: CapCut Template Hub & Camera Upload Surface Recovery

## 1. Hiện tượng & Triệu chứng
- **Alert / Log:** `upload_subprocess_nonzero` (exit code 1 hoặc 2), dừng ở `VIDEO_PICK` hoặc `OPEN_TIKTOK` / `ACCOUNT_READY`.
- **Hiện trường UI:**
  - Camera TikTok tự nhảy vào chế độ LIVE hoặc tab `MẪU`.
  - Màn hình xem trước Template CapCut xuất hiện: video mẫu (ví dụ "Beat 1 máy bay"), nút đỏ *"Thử mẫu này"* (`id/use_template`), nút back `<` góc trên bên trái (`id/bq3`).
  - Màn hình Template Creation Hub xuất hiện: các ô tính năng *"Video mới"*, *"Mẫu"*, *"AutoCut"*, *"Trình chỉnh sửa ảnh"*, *"Phụ đề"*, *"AI Self"*, *"Tách nền"*, nút đóng *"Đóng"* (`id/h32` / `content-desc="Đóng"`).
  - Nút mở Thư viện/Gallery bị che khuất hoặc tap trượt sang các tab khác làm timeout.

## 2. Nguyên nhân (Anti-Pattern)
1. **Nhận diện Template Hub hạn hẹp:** Script cũ chỉ bắt một vài từ khóa đơn lẻ mà không nhận diện cấu trúc Creation Hub đa tầng với các nút điều hướng đóng/back (`:id/bq3`, `:id/h32`, `content-desc="Đóng"`).
2. **Selector Content-Desc bị thiếu:** Các helper tap UI thiếu tham số `content_desc`, không bấm được nút `content-desc="Đóng"` khi không có text hiển thị.
3. **Kẹt dải tab Camera:** Khi camera mở ở chế độ LIVE, việc vuốt trượt hoặc tap mù ở thanh dưới dễ rơi trúng vào tab `MẪU`.
4. **Media Fingerprint Ledger Lock:** Sau khi workflow dừng do crash/timeout, fingerprint SHA-256 bị giữ ở trạng thái `reserved`. Lượt chạy retry tiếp theo bị chặn bởi `MediaFingerprintPendingError` nếu không có cơ chế rebind tự động cho cùng target.
5. **Profile Refresh Pending:** Khi vừa đổi tài khoản, XML vẫn giữ snapshot Profile cũ khiến `tap_profile` bỏ qua việc bấm tab, làm chậm quá trình xác nhận tài khoản.

## 3. Giải pháp Codebase Chuẩn (Case 81)

### A. Nhận diện Toàn diện (`_is_capcut_template_surface`)
- Kiểm tra cả Template Preview (`id/use_template`, `"Thử mẫu này"`, `"Use this template"`) và Creation Hub (`id/bq3`, `:id/h32`, `"Video mới"`, `"Mẫu"`, `"AutoCut"`, `"Trình chỉnh sửa ảnh"`, `"Phụ đề"`, `"AI Self"`, `"Tách nền"`).

### B. Cơ chế Dismiss Đa Tầng Bounded (`_dismiss_capcut_template_surface`)
- Ưu tiên 1: Tap nút back top-left `<` (`id/bq3`).
- Ưu tiên 2: Tap nút `Đóng` (`id/h32` hoặc `content_desc="Đóng"`).
- Ưu tiên 3: Fallback `KEYCODE_BACK` có giới hạn (`max_attempts=4`), tự động quét và giải phóng từng tầng màn hình trở lại Camera/Feed an toàn.

### C. Tách biệt Vùng Upload Thumbnail (`upload_hot_area`)
- Nút thumbnail thư viện trên Camera nằm tại `[0,1692][204,1896]` (`(120, 1821)`).
- Chỉ tap chỉ định đích danh sang các tab an toàn (`ĐĂNG`, `TẠO`), không vuốt trượt lan sang mép chứa tab `MẪU`.
- Sau cú tap mở thumbnail, kiểm tra UI tức thì; nếu không mở được picker trong 5s thì kích hoạt ngay nhánh recovery, không chờ timeout mù 60s.

### D. Rebind Reserved Media Fingerprint
- Trong `state_machine.py` (`_handle_resolve_next_video`), bắt `MediaFingerprintPendingError` và kiểm tra nếu payload có `status == "reserved"` cho cùng target machine/account/video_number thì tự động gọi `ledger.rebind_reserved` chuyển sang `run_id` mới.

### E. Force Tap Profile Refresh (`tap_profile(force=True)`)
- Thêm tham số `force: bool = False` vào `TikTokAdapter.tap_profile`.
- Khi ở trạng thái `ACCOUNT_READY` mà verify tài khoản chưa xong (`pending`), gọi `tap_profile(force=True)` để buộc gửi tap làm mới XML thay vì bỏ qua do `is_profile_root` trả về `True`.
