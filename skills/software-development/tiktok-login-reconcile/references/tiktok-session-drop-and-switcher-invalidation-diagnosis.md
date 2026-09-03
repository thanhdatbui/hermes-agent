# TikTok Session Drop & Switcher Invalidation Diagnosis (2026-09-02)

## Hiện tượng
- Thiết bị (ví dụ Máy 10) đã đăng nhập đủ tài khoản trước đó, nhưng khi chạy phiên nuôi (`multi-machine-feed-session`) thì Account Switcher chỉ còn lại 1 tài khoản (hoặc văng phiên hàng loạt).
- Lỗi kích hoạt: `account switcher requires manual review` / `account-switcher-missing-expected`.

## Anti-Pattern Cần Tránh Khi Chẩn Đoán (User Corrections 2026-09-02)
1. **Không đoán mò các lý do generic không có cơ sở:**
   - *ViChanger*: Trên farm thực tế chỉ đóng vai trò VPN kết nối, các flow clean/fake device đã được loại bỏ khỏi runner.
   - *Proxy rớt gây văng session*: Proxy 4G đi kèm định tuyến WiFi; mất proxy là mất toàn bộ kết nối mạng trên thiết bị, không tạo ra hiện tượng chọn lọc rớt session từng tài khoản.
   - *Đổ lỗi RAM*: Cả farm đồng cấu hình (Samsung Galaxy S7 3GB RAM); nếu máy khác chạy bình thường thì không quy chụp do thiếu RAM chung chung.
   - *Trùng nick giữa các máy*: Farm quản lý nick cố định theo từng máy; luôn kiểm tra đối chiếu bảng dữ liệu trước khi kết luận.

## Quy Trình Chẩn Đoán Thực Tế (Evidence-First)

### Bước 1: Kiểm Tra Tính Toàn Vẹn & Trùng Lặp Của Dữ Liệu
- Quét đối chiếu toàn bộ các bảng Excel master (`taikhoan_dat_v2_updated .xlsx`, `taikhoan_run_safe.xlsx`, `Tik1.xlsx` -> `Tik6.xlsx`).
- Xác nhận các nick trên máy đích có bị duplicate hoặc mapping sai sang máy khác hay không.

### Bước 2: Kiểm Tra Kết Nối Vật Lý & Ổn Định Nguồn Điện (Hardware/USB Brownout)
- Phát lệnh kiểm tra trạng thái và tải thử khởi chạy app (`am start SplashActivity`).
- **Dấu hiệu sụt nguồn / lỏng cáp**: Khi app khởi động (CPU/GPU tăng đột biến), nếu máy lập tức rớt kết nối ADB (`device not found` / `offline`), chứng tỏ máy bị sụt áp trên cổng USB hub hoặc pin ảo.
- **Hệ quả**: Khi máy bị tắt/khởi động lại đột ngột, cache SQLite chưa kịp flush xuống bộ nhớ NAND (`aweme.db-wal`) sẽ bị rollback về snapshot cũ, làm mất các tài khoản vừa thêm.

### Bước 3: TikTok Server-Side Silent Token Revocation
- Khi thêm nhiều tài khoản liên tiếp trong thời gian ngắn trên cùng một thiết bị, API verify token (`/passport/token/beat/`) có thể từ chối token.
- TikTok âm thầm gỡ tài khoản hết hạn khỏi danh sách Account Switcher mà không hiển thị dialog thông báo lỗi.

### Bước 4: Quy Tắc "Profile Soak" Khi Đăng Nhập Tài Khoản Mới
- Khi đăng nhập tài khoản vào TikTok app qua UI/ADB:
  - Bắt buộc phải giữ màn hình Profile/Feed tối thiểu **10–15 giây** để app hoàn tất các handshake bảo mật và commit session xuống Keystore/SQLite.
  - Không thoát app hoặc bấm chuyển sang nick khác ngay lập tức khi vừa vào profile.
