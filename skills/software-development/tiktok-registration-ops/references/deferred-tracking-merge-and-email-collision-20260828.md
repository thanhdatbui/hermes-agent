# Bẫy Deferred Tracking Merge & Loop Reg Trùng Email (2026-08-28)

## 1. Hiện tượng & Triệu chứng
- Batch Reg TikTok kết thúc báo `14 SUCCESS`, `6 PENDING: account_not_found / Login timeout`.
- Màn hình kết thúc của các máy bị lỗi (ví dụ máy 24, 32, 36) dừng ở màn hình **"Nhập mật khẩu"** với chữ đỏ báo **"Mật khẩu sai"** / popup **"Lỗi"**, bên trong ô mật khẩu hiển thị 6 ký tự chấm tròn `••••••`.
- Các máy 15, 18, 22 bị văng về màn hình Launcher Home.

## 2. Nguyên nhân gốc (Root Cause)
1. **Chưa merge deferred tracking kết quả vào Excel:** Khi runner chạy với `--defer-tracking-write`, các file kết quả `tracking_result_*.json` chỉ được lưu trong thư mục artifacts (`artifacts/runs/social-batch-all/...`) mà không tự động ghi vào `taikhoan_dat_v2_updated .xlsx`.
2. **Detector chọn lại mail cũ:** Lần chạy kế tiếp, `_detect_clean.py` đọc workbook thấy các dòng STT/Tik vẫn trống nên tiếp tục nhặt lại các Hotmail/Gmail đã reg thành công trước đó (ví dụ từ batch ngày 26/08).
3. **TikTok chuyển sang luồng Login thay vì Reg:** Khi nhập mail đã tồn tại, TikTok không mở form đăng ký mới mà chuyển sang màn hình Đăng nhập (yêu cầu nhập mật khẩu tài khoản cũ).
4. **Gõ nhầm OTP vào ô mật khẩu:**
   - Script sinh mật khẩu mới ngẫu nhiên gõ vào ô mật khẩu -> TikTok báo đỏ: "Mật khẩu sai".
   - Luồng fallback thấy chưa auth xong nên gọi Graph API lấy mã OTP 6 số.
   - Hàm `enter_otp_code` tìm EditText duy nhất trên màn hình (chính là ô Mật khẩu đang báo sai) và gõ luôn 6 số OTP vào ô mật khẩu đó -> Bị kẹt màn hình lỗi timeout.

## 3. Quy chuẩn khắc phục bắt buộc
1. **Luôn chạy `apply_deferred_tracking_results.py` sau batch:** Bất kỳ launcher nào (`run_night_chain_pipeline.py`, `_run_all_targets.py`) sau khi chạy xong batch TikTok BẮT BUỘC phải tự động quét các file `tracking_result_*.json` và nạp ngay vào `taikhoan_dat_v2_updated .xlsx`.
2. **Trigger sync tức thì `taikhoan_run_safe.xlsx`:** Gọi `sync-safe-workbook.py` với writer ID hợp lệ để cập nhật 480 dòng an toàn.
3. **Format báo cáo bắt buộc:** Tách riêng Phase 1 (Gmail) và Phase 2 (TikTok), liệt kê rõ tổng số máy, danh sách máy thành công (STT 2 chữ số), danh sách máy thất bại kèm lỗi chi tiết từng máy.
