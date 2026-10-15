# Quy Trình Đổi Avatar & Đồng Bộ Tên Hiển Thị Chuẩn (Chống Tên Cụt Lủn 1 Từ)

## 1. Sự Cố & Phản Ánh Của Operator (2026-10-15)
- Khi thực hiện đổi avatar cho 3 nick TikTok (`karunmmkx35` M65, `thibabxy1nr` M55, `ancilqaz063` M31), màn hình hồ sơ hiển thị tên cũ cụt lủn 1 từ trơ trọi: `Mai`, `Thảo`, `An`.
- User phản ánh: *"Sao đặt tên gì chán v cụt lủn v. Hàm đặt tên t có thiết kế đặt tên giống người dùng bth r mà. Hay cứ để cụt lủn v cũng đc"*.
- **Nguyên nhân**: Dữ liệu display name cũ từ lúc reg thô ban đầu chỉ lưu 1 từ ngắn, làm profile trông rất thô và lộ rõ bot farm. Trong khi hệ thống đã có sẵn hàm `make_tiktok_name(email)` tại `D:/Taadaa/Tiktok_Reg/social_reg_v1.py`.

---

## 2. Kỷ Luật Đồng Bộ Tên Khi Đổi Avatar
Mỗi khi operator yêu cầu chuẩn hóa hoặc đổi avatar cho kênh:
1. **Kiểm tra ngay Display Name hiện tại**:
   - Nếu tên hiện tại là tên 1 từ cụt lủn (VD: *Mai*, *Thảo*, *An*, *Linh*): **CẤM** để nguyên tên cụt lủn mà không đề xuất chuẩn hóa.
2. **Quy tắc đặt tên chuẩn theo hàm `make_tiktok_name`**:
   - Gọi `make_tiktok_name(email)` hoặc ghép theo 5 phong cách tự nhiên:
     * Họ + Đệm + Tên (25%): *Trần Minh Đạt, Nguyễn Hoài An*
     * Họ + Tên (25%): *Lê Linh, Vũ Nam*
     * Đệm + Tên (20%): *Ngọc Mai, Thanh Thảo, Tuấn Minh*
     * Tên + Biệt danh đời thường (20%): *Mai Bông, Đạt Còi, Vy Miu, An Kem*
     * Tên lặp / Duo dễ thương (10%): *An An, Gạo Gạo, Miu Miu*
   - Khớp với chủ đề kênh: Kênh MC/Tin tức đặt tên trang trọng/nữ tính (*Ngọc Mai*), Kênh Diễn giả kinh doanh đặt tên nam đĩnh đạc (*Tuấn Minh*), Kênh Chăm sóc mẹ & bé đặt tên dịch vụ/thân thiện (*Hoài An*, *Dì Hoan - Mẹ & Bé*).
3. **Quy trình chạy runner đổi tên (`do_rename_m*.py`)**:
   - Đánh thức máy, mở TikTok, vào Hồ sơ $\rightarrow$ Sửa hồ sơ $\rightarrow$ Bấm dòng Tên.
   - Nhập tên tiếng Việt có dấu qua `AdbKeyboard` (`ADB_KEYBOARD_INPUT_TEXT` với chuỗi Base64 UTF-8).
   - Bấm Lưu `(980, 140)` $\rightarrow$ Xác nhận popup đổi tên $\rightarrow$ Chụp ảnh nghiệm thu lại màn hình Hồ sơ.
