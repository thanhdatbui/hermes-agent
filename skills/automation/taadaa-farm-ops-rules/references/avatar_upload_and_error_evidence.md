# Taadaa Farm Avatar Upload & Error Evidence Rules

## 1. KỶ LUẬT BẰNG CHỨNG LỖI NGUYÊN BẢN (AUTHENTIC ERROR EVIDENCE)
- **CẤM TỰ BẤM BỪA TẠO LỖI GIẢ**: Khi gặp kẹt hoặc lỗi không mở được màn hình (như không thấy nút Sửa hồ sơ), tuyệt đối CẤM bấm mò vào các phần tử khác (như header tên tài khoản, nút điều hướng lạ) dẫn đến các pop-up lỗi không liên quan (ví dụ: *"Hoạt động không có sẵn / Chuyển sang tài khoản ban đầu"*) rồi kết luận sai lệch là lỗi do nền tảng TikTok chặn.
- **CHỤP ĐÚNG MÀN HÌNH NGUYÊN BẢN (RAW SCREENSHOT)**: Khi báo cáo lỗi cho User hoặc giải thích nguyên nhân fail, ảnh gửi kèm phải là ảnh chụp nguyên trạng màn hình của app tại bước xảy ra lỗi thực tế, không qua cắt xén gây hiểu lầm.
- **CUNG CẤP ĐÚNG MÀN HÌNH THEO YÊU CẦU**: Khi User yêu cầu xem "màn hình trước đó" hoặc "ngay chỗ lỗi", phải trích xuất chính xác screenshot tại thời điểm trước khi phát sinh lỗi/pop-up, không ngụy tạo hay gửi nhầm context khác.

## 2. KỶ LUẬT THỰC THI ĐỔI AVATAR (AVATAR REPLACEMENT DISCIPLINE)
- **CẤM BÁO XONG KHI CHƯA UP ẢNH MỚI**: Nếu tài khoản được yêu cầu đổi avatar (`Đổi ava nick này`), nhiệm vụ chỉ hoàn thành khi đã thực sự tải ảnh mới lên và lưu thành công (hoặc chạy Canary pass với `--force-avatar-upload`). Tuyệt đối không được thấy avatar cũ sẵn có trên profile rồi tự ý cập nhật sổ cái `Avatar = OK` và báo xong lừa dối.
- **XỬ LÝ BIẾN THỂ GIAO DIỆN (UI VARIANTS)**:
  - Bản TikTok mới có thể không có nút chữ `Sửa hồ sơ`. Cây bút chỉnh sửa có thể được tích hợp cạnh tên hoặc nằm trong menu chia sẻ.
  - Phải phân tích kỹ XML và toạ độ trước khi tap. Tránh tap nhầm vào vùng nút Story (`+ Tạo một Nhật ký`, bounds chồng lấn với avatar circle).
- **CHỤP ẢNH NGHIỆM THU SAU KHI ĐỔI**: Bắt buộc gửi `MEDIA:<path_anh>` hiển thị avatar mới đã được cập nhật thực tế trên trang cá nhân của tài khoản trước khi chốt task.
