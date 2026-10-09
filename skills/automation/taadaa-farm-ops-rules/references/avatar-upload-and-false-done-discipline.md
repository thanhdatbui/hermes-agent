# Kỷ luật Nghiệm thu Đổi Avatar & Chống Ảo giác Lỗi Nền tảng trên Taadaa Farm

## 1. CẤM BÁO "DONE" TỪ KẾT QUẢ SKIP (CHỐNG FALSE-DONE)
- **Bẫy thường gặp**: Lệnh chạy `--avatar-smoke` khi gặp tài khoản đã có avatar trên app sẽ trả về `avatar_status: SKIPPED_EXISTING_AVATAR` và thoát exit code 0 (`AVATAR_SMOKE_SUCCESS`).
- **Vi phạm nghiêm trọng**: Thấy exit code 0 liền tự ý ghi `Avatar = OK` vào Excel và báo user task đã hoàn thành mà KHÔNG có bằng chứng upload ảnh mới thực tế.
- **Kỷ luật bắt buộc**:
  - Khi user phát lệnh "đổi ava cho nick", BẮT BUỘC chạy với cờ `--force-avatar-upload` và chỉ định `--force-avatar-machines <N>`.
  - Kết quả `SKIPPED_EXISTING_AVATAR` hoặc `SKIPPED_AVATAR_EDIT_UNAVAILABLE` là **CHƯA ĐỔI**, TUYỆT ĐỐI CẤM báo DONE hay cập nhật Excel `Avatar = OK`.
  - Nghiệm thu hoàn tất BẮT BUỘC phải có:
    1. Log thực hiện chu trình upload ảnh mới: Push file -> Edit Profile -> Chọn ảnh Thư viện -> Crop -> Lưu.
    2. Ảnh chụp màn hình Profile thực tế sau khi đổi và diff so sánh khớp với ảnh avatar mới.

## 2. CHỐNG ẢO GIÁC LỖI NỀN TẢNG (DISCRIMINATING AGENT ERROR VS PLATFORM ERROR)
- **Bẫy thường gặp**: Thao tác bấm dò tọa độ bằng tay (ADB tap) trúng nhầm nút chuyển tài khoản, header nick phụ, hoặc icon lạ làm TikTok bật popup cảnh báo:
  > *"Hoạt động không có sẵn: Để tiếp tục tham gia vào các hoạt động, hãy chuyển sang tài khoản ban đầu mà bạn đã dùng trên thiết bị này."*
- **Vi phạm**: Chụp ngay ảnh popup này rồi vội vã báo cáo "lỗi nền tảng TikTok chặn máy" để thoái thác trách nhiệm, trong khi nguyên nhân thực sự là do agent bấm nhầm.
- **Quy tắc điều phối**:
  - Tuyệt đối không quy kết lỗi nền tảng nếu popup sinh ra từ các thao tác bấm thăm dò tự phát ngoài quy trình chuẩn.
  - Kết luận lỗi nền tảng chỉ hợp lệ khi:
    - Có log từ script workflow canonical chạy theo luồng chuẩn.
    - Cung cấp ảnh chụp màn hình NGAY TRƯỚC khi thao tác và NGAY SAU khi thao tác để chứng minh hệ thống từ chối hành động hợp lệ.

## 3. TIKTOK V47.0.3 UI VARIANT: CÂY BÚT CẠNH TÊN LÀ NÚT CHUYỂN TÀI KHOẢN
- **Đặc điểm**:
  - Trên layout Profile mới của TikTok 47.0.3, không có nút text "Sửa hồ sơ".
  - Icon cây bút vẽ cạnh tên hiển thị `huy0108` thực chất nằm chung trong button `com.ss.android.ugc.trill:id/t7l`. Khi click vào đây, TikTok mở **Account Switcher (Chuyển đổi tài khoản)**, KHÔNG PHẢI mở màn Sửa hồ sơ.
  - Vòng tròn avatar bên phải bị nút xanh `+ Tạo một Nhật ký` (Story) đè ở góc `[931, 499][1080, 636]`. Tap vào tâm avatar sẽ mở camera Story thay vì chọn avatar.
- **Luồng mở Sửa hồ sơ chuẩn**:
  - Dùng deep-link: `am start -a android.intent.action.VIEW -d "snssdk1233://profile/edit" -p com.ss.android.ugc.trill`.
  - Chờ mở giao diện Profile Host rồi tap nút Sửa hồ sơ ở góc trên bên trái `(177, 150)`.
  - Nếu tap avatar circle bên phải, phải offset tâm về `(840, 440)` để tránh nút Story.
