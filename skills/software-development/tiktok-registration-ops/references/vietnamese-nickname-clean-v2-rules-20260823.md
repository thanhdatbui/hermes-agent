# Quy Tắc Bổ Sung Cho TikTok Registration Operations (User Rules)

## 1. Quy tắc đặt Tên hiển thị (Nickname / Display Name) sau khi Reg
- **BẮT BUỘC đặt tên tiếng Việt:** Khi gặp màn "Tạo tên" / "Thêm tên" / đổi tên hồ sơ sau khi reg, luôn ưu tiên gán tên tiếng Việt chuẩn (viết hoa chữ cái đầu, tra `_VI_NAME_MAP` hoặc lấy ngẫu nhiên từ `_VI_NAME_FALLBACK`, tuyệt đối không để tên tiếng Anh/ngoại lai).

## 2. Nguyên tắc đồng bộ `gmail_clean_v2.xlsx` vs `taikhoan_dat_v2_updated .xlsx`
- `gmail_clean_v2.xlsx` là **KHO MAIL LIVE**, không được xóa email chỉ vì email đó vừa reg TikTok thành công.
- Khi quét check-live/quarantine phát hiện mail bị mất/die trên máy:
  - Nếu **chưa có ID TikTok** trong `taikhoan_dat_v2_updated .xlsx` → **XÓA** khỏi `gmail_clean_v2.xlsx` để tool reg không bốc lại làm target.
  - Nếu **đã có ID TikTok** → **GIỮ LẠI** phục vụ nuôi acc và đối soát.
- Mọi tài khoản reg thành công bắt buộc tracking ID TikTok cùng hàng với mail đăng ký trong `taikhoan_dat_v2_updated .xlsx`.

## 3. Xử lý màn hình One-Tap Login ("Tiếp tục với tên @username")
- Khi mở form đăng nhập/đăng ký nếu gặp màn hình One-Tap Login (chỉ có nút "Tiếp tục với tên @username" của tài khoản cũ), phải tap vào liên kết **"Sử dụng tài khoản khác"** ở dưới cùng để mở màn hình chọn phương thức (Email/SĐT).

## 4. Concurrency Gate Regex cho Child Process
- Trong `social_reg_v1.py` hàm `_process_mentions_stt`, regex bắt lệnh automation phải hỗ trợ cả cú pháp truyền `<serial> <stt>`: `(?:gmail_reg_v10|social_reg_v1)\.py[\"']?\s+(?:[a-zA-Z0-9_\-]+\s+)?{int(stt)}(?!\d)` để tránh bị chặn nhầm bởi `TRACKING_WRITER_UNKNOWN` khi chạy batch song song.
