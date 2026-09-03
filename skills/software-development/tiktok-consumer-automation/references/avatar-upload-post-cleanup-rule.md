# Up Avatar Post-Verification Clean-up Standard (2026-08-21)

## Quy chuẩn dọn dẹp sau khi cập nhật Avatar thành công
Khi chạy quy trình Upload / Cập nhật Avatar cho nick TikTok (cả script chạy đơn lẻ `run_tiktok_upload_avatar.ps1` lẫn tích hợp trong workflow `state_machine.py`):

1. **Sau khi tải ảnh & xác nhận màn hình Profile thành công**:
   - Chụp màn hình bằng chứng (`screencap`) để lưu artifact / gửi báo cáo nghiệm thu.
2. **BẮT BUỘC Đóng ứng dụng TikTok & Về màn hình Home ngay lập tức**:
   - Gửi lệnh `force-stop` cả 2 package TikTok có thể chạy trên farm:
     ```bash
     am force-stop com.zhiliaoapp.musically
     am force-stop com.ss.android.ugc.trill
     ```
   - Gửi lệnh đưa máy về màn hình chính:
     ```bash
     input keyevent 3  # KEYCODE_HOME
     ```
3. **Mục đích & Lý do**:
   - Giải phóng bộ nhớ RAM và tài nguyên GPU/CPU trên các máy yếu (Samsung Galaxy S7).
   - Tránh việc máy bị giữ ở màn hình Profile/Edit gây xung đột với các ca nuôi acc, follow hoặc download kế tiếp.
   - Bảo đảm an toàn tuyệt đối cho thiết bị ở trạng thái sạch trước khi nhả device lock.
