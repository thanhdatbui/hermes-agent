# Quy tắc vận hành và Báo cáo Đăng ký TikTok (Tiktok_Reg)

## 1. Quy tắc ghi nhận Password vào Excel
- Khi flow reg TikTok không qua màn nhập mật khẩu (do TikTok dùng flow OTP / email-only xác minh thẳng vào trong):
  - **BẮT BUỘC để trống ô PASS (`None` / blank)** trong tracking workbook `taikhoan_dat_v2_updated .xlsx`.
  - **TUYỆT ĐỐI KHÔNG tự generate và lưu password ngẫu nhiên** vào workbook, để sau này thao tác cài đặt pass trong app TikTok.

## 2. Quy tắc báo cáo và gửi ảnh hiện trường
- Ảnh chụp màn hình lỗi/hiện trường gửi user **BẮT BUỘC phải vẽ Banner đỏ trên đầu ảnh** theo định dạng `[MAY XX] - HH:MM DD/MM` (chuẩn như module Auto-Recovery).
- Báo cáo kết quả và lỗi bằng **tiếng Việt ngắn gọn, dễ hiểu**, chỉ rõ nguyên nhân; **CẤM gửi nguyên khối log tiếng Anh / traceback raw / thuật ngữ kỹ thuật phức tạp**.

## 3. Quy tắc quản lý Device Lock
- Khi chạy batch reg hàng loạt (`_run_all_targets.py` hoặc runner khác):
  - **CHỈ NHẢ LOCK cho các máy hoàn thành THÀNH CÔNG (`VERIFIED_SUCCESS`)**.
  - Các máy bị **FAILED / DỪNG HIỆN TRƯỜNG** phải được **GIỮ LOCK ở trạng thái `blocked`** để bảo vệ hiện trường, ngăn chặn các cronjob khác can thiệp chéo.
