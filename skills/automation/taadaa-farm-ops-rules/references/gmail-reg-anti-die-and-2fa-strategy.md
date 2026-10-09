# Chiến Lược Phòng Chống Google Quét Khóa (Die) & Quy Trình Vận Hành Reg Gmail

## 1. Bản Chất Hiện Tượng Gmail DIE Hàng Loạt (Tỷ lệ DIE 70% sau 3-5 ngày)
Khi phân tích đợt Gmail reg tự động đầu tháng 9/2026 so với dàn Gmail reg từ tháng 6-7/2026 (tỷ lệ sống 80%+):
- **Nguyên nhân chính:** Tài khoản đăng ký trên điện thoại Android nhưng **không gắn Email khôi phục (Recovery Email)** và **chưa bật 2FA**.
- Google xếp các tài khoản này vào diện "High-risk bot profile" hoặc "Ghost account". Sau 48–72h, thuật toán tự động quét ngầm và vô hiệu hóa / đòi xác minh SMS.

## 2. So Sánh: Add Recovery Email vs Add 2FA (Google Authenticator)
- **Email Khôi Phục (Recovery Email):**
  - Nhược điểm: Nếu dùng chung 1 mail khôi phục (ví dụ `thanhdatbui1995@gmail.com`), toàn bộ máy phải chờ lấy OTP từ cùng 1 hộp thư -> Gây nghẽn hàng đợi (queue timeout) và bị Google liên kết (chain-ban) toàn bộ đàn nick do trùng danh tính.
- **Bật 2FA (Google Authenticator TOTP - LỰA CHỌN TỐI ƯU):**
  - Mỗi tài khoản sinh ra một **Secret Key Base32 độc lập**, không dùng chung bất kỳ thông tin nào.
  - Sau khi bật 2FA, Google xếp tài khoản vào nhóm **High Security Trust** -> Chấm dứt hoàn toàn tình trạng bị khóa ngầm sau vài ngày.

## 3. Quy Tắc Vận Hành Reg Gmail Bắt Buộc (Invariant Policy)
1. **CẤM ĐỔI IP TRƯỚC KHI REG:** Giữ nguyên IP proxy đang gán, tuyệt đối không restart modem hoặc gọi API change IP trước khi vào flow reg.
2. **CHIẾN LƯỢC PICK 15 MÁY CÓ PROXY KHÁC NHAU:**
   - Dàn 80 máy phân bổ trên 40 cổng proxy (2 máy / 1 cổng).
   - Khi runner pick 15 máy chạy batch reg, BẮT BUỘC gom theo nhóm proxy: **mỗi cổng proxy chỉ chọn tối đa 1 máy duy nhất** trong cùng một thời điểm. Đảm bảo 15 máy chạy song song hoàn toàn trên 15 đường truyền/IP độc lập.
3. **TĂNG CƯỜNG RANDOM HÓA HỌ TÊN & USERNAME:**
   - CẤM dùng công thức cố định `ho + dem + ten + year`.
   - Bắt buộc random họ, tên đệm (1-2 từ), tên chính, từ ngữ tự nhiên, kết hợp từ khóa nghiệp vụ (`top`, `life`, `pro`, `plus`, `tech`, `corp`...) kèm salt ngẫu nhiên 3–5 ký tự và số ngẫu nhiên để triệt tiêu bot pattern.
4. **QUY TRÌNH DỌN GMAIL DIE TRƯỚC KHI REG:**
   - Trước khi máy bắt đầu mở flow tạo tài khoản mới, script gọi module `preflight_s7_rolling_cleanup.py` (`remove_account_adb()`) để gỡ bỏ toàn bộ tài khoản Google DIE đã xác nhận ra khỏi máy Android, giải phóng slot sạch sẽ.
