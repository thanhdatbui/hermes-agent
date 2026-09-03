# Quy Tắc Đặt Tên & Vận Hành Batch Reg TikTok (2026-08-23)

## 1. Quy tắc đặt Tên hiển thị (Display Name / Biệt danh)
- **BẮT BUỘC đặt tên tiếng Việt:** Khi hoàn tất đăng ký hoặc màn hình hỏi đặt Tên ("Thêm tên bạn mong muốn" / "Tạo tên"), luôn ưu tiên đặt tên tiếng Việt chuẩn (viết hoa chữ đầu, ví dụ: "Hà", "Kiều Lâm", "Anderus" -> "An", "Minh", "Linh", v.v.).
- Dùng mapping âm Việt từ prefix email hoặc fallback ngẫu nhiên từ danh sách tên tiếng Việt chuẩn (`_VI_NAME_FALLBACK`). Không giữ nguyên prefix tiếng Anh thô nếu không khớp.

## 2. Quản lý Kho Mail `gmail_clean_v2.xlsx` vs Bảng Tracking `taikhoan_dat_v2_updated .xlsx`
- **`gmail_clean_v2.xlsx` là kho mail live:** Không tự ý xóa dòng khỏi file này chỉ vì đã reg xong TikTok.
- **Check-live chỉ xóa mail die khi CHƯA có ID TikTok:**
  - Mail die + chưa có ID trong `taikhoan_dat_v2_updated .xlsx` -> Xóa khỏi `gmail_clean_v2.xlsx`.
  - Mail đã có ID TikTok trong tracking -> BẮT BUỘC GIỮ LẠI trong tracking (và không xóa tracking).
- **Tracking ID bắt buộc cùng hàng mail reg:** Không được để tình trạng mail reg một đằng nhưng hàng tracking lại bị map nhầm sang mail khác (dẫn đến data drift).

## 3. Tài khoản không pass (Passwordless / Bỏ qua mật khẩu)
- TikTok cho phép bỏ qua bước tạo mật khẩu sau khi xác thực OTP/DOB.
- Các tài khoản này vẫn là **SUCCESS** hoàn tất.
- Trong workbook `taikhoan_dat_v2_updated .xlsx`, cột `PASS` để trống (`None`).

## 4. Xử lý Màn hình One-Tap Login (Đăng nhập nhanh)
- Khi mở form đăng nhập hoặc sau khi bấm "Thêm tài khoản", nếu gặp màn hình *"Tiếp tục với tên @username..."* -> Tap *"Sử dụng tài khoản khác"* để mở form chọn phương thức Email/Username.

## 5. Concurrency Gate & Khóa thiết bị
- Helper `_process_mentions_stt` phải match cả 2 dạng CLI: `social_reg_v1.py <stt>` và `social_reg_v1.py <serial> <stt>` để tránh trigger nhầm `TRACKING_WRITER_UNKNOWN`.
