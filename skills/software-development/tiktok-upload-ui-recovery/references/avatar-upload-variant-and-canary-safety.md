# TikTok Avatar Upload: UI Variants, Platform Error Discrimination & Canary Verification

## 1. BẪY SKIPPED_EXISTING_AVATAR VS CANARY ĐỔI AVATAR THẬT (CRITICAL)
- **Bản chất**: Khi chạy `tiktok_workflow` với `--avatar-smoke`, nếu không bật `--force-avatar-upload` hoặc script đánh giá avatar hiện tại có entropy/edge đủ cao, hệ thống trả về `avatar_status: SKIPPED_EXISTING_AVATAR` và thoát với exit code 0 (`AVATAR_SMOKE_SUCCESS`).
- **Sai lầm chết người**: Thấy exit code 0 liền kết luận "đã đổi avatar thành công", tự ý ghi `Avatar = OK` vào Excel và báo DONE cho user trong khi thực tế chưa hề upload ảnh mới.
- **Kỷ luật bắt buộc**:
  1. Khi user yêu cầu "đổi ava cho nick này", BẮT BUỘC phải dùng `--force-avatar-upload` và `--force-avatar-machines <N>`.
  2. Báo DONE chỉ hợp lệ khi có đủ 3 bằng chứng:
     - Log ghi nhận tiến trình đi qua các bước: `resolve_avatar_path` -> `push remote avatar` -> `ProfileEditActivity` -> `ProfileAvatarChoosePhotoActivity` -> `CropActivity` -> `SAVE`.
     - `avatar_status` trong `report.json` là `UPLOADED` (hoặc có bằng chứng upload rõ ràng), TUYỆT ĐỐI KHÔNG chấp nhận `SKIPPED_EXISTING_AVATAR` khi yêu cầu là đổi ảnh mới.
     - Ảnh chụp Profile thực tế sau khi đổi và diff so sánh với ảnh nguồn (`diff <= threshold`). CẤM dùng ảnh cũ hay báo DONE mà không có ảnh sau khi đổi.

## 2. PHÂN BIỆT LỖI THỰC TẾ VS ẢO GIÁC LỖI NỀN TẢNG (DISCRIMINATING PLATFORM RESTRICTION)
- **Hiện tượng**: Khi inspect thủ công bằng ADB tap vào các tọa độ không được kiểm chứng (ví dụ tap vào tên tài khoản khác hoặc icon `zsj` trên nick phụ), TikTok bật popup:
  > *"Hoạt động không có sẵn: Để tiếp tục tham gia vào các hoạt động, hãy chuyển sang tài khoản ban đầu mà bạn đã dùng trên thiết bị này."*
- **Sai lầm**: Vội vàng chụp popup này và kết luận "TikTok chặn nền tảng / hạn chế thiết bị / không đổi avatar được" để thoái thác, trong khi lỗi là do thao tác bấm nhầm của chính agent.
- **Quy tắc**:
  1. KHÔNG quy chụp lỗi nền tảng nếu popup sinh ra từ thao tác bấm tay/dò tọa độ mù.
  2. Muốn kết luận lỗi nền tảng chặn tính năng, BẮT BUỘC:
     - Chứng minh qua log workflow chạy tự động theo đúng luồng chuẩn.
     - Cung cấp ảnh chụp màn hình NGAY TRƯỚC khi bấm và NGAY SAU khi bấm để chứng minh hành động hợp lệ nhưng hệ thống từ chối.

## 3. TIKTOK V47.0.3 UI VARIANT: BẪY CÂY BÚT CẠNH TÊN (PENCIL NEXT TO USERNAME)
- **Đặc điểm giao diện mới**:
  - Không có nút text "Sửa hồ sơ" hay "Edit profile".
  - Bên phải tên hiển thị `[36, 280][437, 364]` có vẽ icon cây bút chì nghiêng, nhưng cả cụm này là widget `com.ss.android.ugc.trill:id/t7l`.
  - **Bẫy**: Bấm vào cụm tên `t7l` sẽ mở **Account Switcher bottom sheet (Chuyển đổi tài khoản)**, KHÔNG mở Sửa hồ sơ.
  - Bấm vào `@username` (`t3y`) chỉ mở modal chỉnh sửa Tiểu sử (Bio text).
  - Nút avatar bên phải `[708, 246][1080, 636]` (`bmh`/`bni`) bị đè bởi nút xanh `+ Tạo một Nhật ký` (Story camera). Nếu tap vào tâm `(894, 468)` sẽ mở trình đăng Story thay vì đổi avatar.
- **Giải pháp điều hướng chuẩn**:
  - Dùng deep-link hệ thống: `am start -a android.intent.action.VIEW -d "snssdk1233://profile/edit" -p com.ss.android.ugc.trill`.
  - Chờ giao diện `ProfileHostActivity` xuất hiện rồi tap nút Sửa hồ sơ ở góc trên bên trái `(177, 150)`.
  - Khi tap avatar circle bên phải, phải offset tâm về `(840, 440)` để né hoàn toàn nút Story ở `[931, 499][1080, 636]`.
  - Trong `state_machine.py`, khi bật `--force-avatar-upload`, nếu gặp popup `unavailable` thì đóng popup và tiếp tục thử mở lại màn edit, không được để `SKIPPED_AVATAR_EDIT_UNAVAILABLE` ngắt giữa chừng.
