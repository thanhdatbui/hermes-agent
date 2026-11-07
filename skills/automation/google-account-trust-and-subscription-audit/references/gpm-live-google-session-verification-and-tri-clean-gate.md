# Kỷ Luật Đối Soát Live Session Google GPM & Tiêu Chí Sạch 3 Cổng (Tri-Clean Gate)

## 1. Bối Cảnh Lỗi Thực Tế Từ Người Dùng
Khi User yêu cầu cung cấp tài khoản Google thường (không có gói Pro, không liên kết TikTok Farm) để sử dụng trên GPMLogin:
- **Lỗi 1 (Nhầm gói Pro)**: Coordinator cấp nhầm tài khoản đã kích hoạt gói Google AI Pro / Gemini Pro (hoặc nằm trong pool OmniRoute Pro), bị User phản ứng gay gắt ("acc dokieu có gói pro r mà, ngáo chó à?").
- **Lỗi 2 (Cấp tài khoản không có Live Session)**: Coordinator chỉ tra cứu password/2FA trong CSDL (`farm_master.db`) rồi báo User đăng nhập trên profile GPM rỗng session. Google phát hiện thiết bị/proxy mới và lập tức kích hoạt màn hình chặn cứng: `accounts.google.com/v3/signin/rejected` ("Không thể đăng nhập cho bạn - Bạn không cung cấp đủ thông tin...").

## 2. Tiêu Chí Bộ Lọc Tam Tầng Bắt Buộc (Tri-Clean Gate)
Trước khi bàn giao bất kỳ tài khoản Google nào cho User, BẮT BUỘC thỏa mãn đồng thời cả 3 điều kiện:
1. **Không có gói Google AI Pro / Gemini Pro**:
   - Đối soát `provider_connections` trong OmniRoute SQLite (`C:/Users/Kibe/.omniroute/storage.sqlite`): Không có cờ `tier: g1-pro-tier`, `plan: Pro`, hoặc label Pro trong các combo `ag-gemini-pool-3`, `gemini-web-pro`.
   - Đối soát thực tế trang `https://myaccount.google.com/payments-and-subscriptions`: Bắt buộc không có thuê bao Google One hoặc Google AI Pro / Gemini Pro.
2. **Không liên kết với TikTok Farm**:
   - Đối soát bảng `tiktok_accounts` trong `D:/Taadaa/data/farm_master.db`: Email hoàn toàn không được map vào bất kỳ máy farm nào (M1..M80, M201..M280).
3. **Session Google LIVE 100% trong GPM Profile (Không bắt đăng nhập lại)**:
   - Kiểm tra file SQLite `Cookies` trong thư mục profile GPM (`Default/Network/Cookies`): Phải có đủ bộ 3 cookie xác thực sống: `SID`, `HSID`, `SSID`.
   - Khởi động thử profile qua GPM API (`GET /api/v3/profiles/start/{id}`), kết nối Playwright/CDP vào tab và điều hướng thử `https://myaccount.google.com/?hl=vi`.
   - **Bằng chứng Pass**: URL giữ nguyên `https://myaccount.google.com/?hl=vi`, trang hiển thị tên và email tài khoản thực tế. Nếu URL bị redirect sang `signin/rejected` hoặc `signin/confirmidentifier` -> FAIL ngay lập tức, không được bàn giao.

## 3. Quy Trình Cứu Proxy GPM Khi Route Nội Bộ Timeout
- Các profile GPM cũ gán proxy nội bộ farm (`test.taadaa.click:51xx` hoặc `192.168.110.2:200xx`), nếu cụm proxy này tạm thời không route được từ máy host, GPM sẽ báo lỗi `Không thể kết nối tới proxy`.
- **Giải pháp**: Cập nhật tạm thời `raw_proxy` của profile sang cụm Webshare US sạch của User (`198.46.161.42:5092:opmighkf:htikm8njcmjb`) qua API:
  `POST http://127.0.0.1:19995/api/v3/profiles/update/{profile_id}` kèm body `{"raw_proxy": "198.46.161.42:5092:opmighkf:htikm8njcmjb"}`.
- Profile sẽ khởi động thành công và giữ nguyên session cookie cũ của tài khoản.

## 4. Hướng Dẫn User Tìm Kiếm Nhanh Trên GPM
- GPM có hàng nghìn profile chia nhiều trang. Ô tìm kiếm trên giao diện app GPM hoạt động hiệu quả nhất khi tìm bằng **tên định danh ngắn** (e.g. `lequynh`, `ninhy`) thay vì paste cả chuỗi email dài.
- Luôn cung cấp đúng **Tên Profile hiển thị** và **Từ khoá tìm kiếm** để User tìm và mở một chạm.
