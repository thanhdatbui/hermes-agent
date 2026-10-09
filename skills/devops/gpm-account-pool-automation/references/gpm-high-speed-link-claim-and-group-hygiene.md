# High-Speed Multi-Link Claiming & GPM Group Separation Pattern

## 1. Bản Chất Vấn Đề
Khi nhận các đợt phát link khuyến mãi / invite số lượng lớn từ bên thứ ba (Google One / AI Premium invite `serviceactivation.google.com/...`):
- Link thường hết hạn rất nhanh (trong vòng 3-5 phút).
- Thao tác thủ công hoặc chạy script mở từng profile tuần tự qua Selenium sẽ quá chậm và dễ nghẽn RAM máy.
- Nếu mở nhầm profile chưa đăng nhập hoặc cookie Google đã hết hạn, link sẽ chuyển hướng về `Sign in - Google Accounts`, làm mất cơ hội claim và lãng phí link.

## 2. Kiến Trúc Tối Ưu: Phân Tách Group GPM & Async Playwright CDP

### 2.1. Quy Hoạch 2 Nhóm Profile Trên GPMLogin
Tuyệt đối KHÔNG kiểm tra trạng thái login ngay tại thời điểm xả link (preflight lúc đó là muộn). Bắt buộc phân tách sẵn 2 Group trong CSDL `profile_data.db`:
- **Group `Google_Live_Ready` (ví dụ Group ID 10):**
  - Chỉ chứa các profile đã xác thực Gmail thành công, session active 100% (mở `myaccount.google.com` vào thẳng dashboard, không văng sign-in).
  - Khi xả link, runner chỉ truy vấn profile từ group này: `GET /api/v3/profiles?group_id=10`.
- **Group `Google_Cooldown_Error` (ví dụ Group ID 11):**
  - Chứa các profile chưa login, văng session, sai mật khẩu, dính checkpoint hoặc đang trong thời gian cooldown 7 ngày (`rrk=77`).
  - Được cách ly hoàn toàn khỏi các tác vụ claiming on-demand.

### 2.2. Kỹ Thuật Async CDP Concurrency (Tốc Độ ~4-5s/link)
- Sử dụng Playwright kết nối trực tiếp WebSocket qua cổng `remote_debugging_address` của GPM v3.
- Dùng `asyncio.Semaphore(3..5)` để giới hạn số luồng song song:
  - Khởi động profile qua API `/api/v3/profiles/start/{id}?win_scale=0.5`.
  - Điều hướng với cờ `wait_until="domcontentloaded"` (không chờ tải toàn bộ tài nguyên đa phương tiện).
  - Bắt DOM và kích hoạt sự kiện click nút nhận ưu đãi.
  - **Kỷ luật dọn dẹp (Crucial Anti-Lag Pattern):** Khối `finally` bắt buộc đóng context và gọi `/api/v3/profiles/stop/{id}`. Tránh để lại tiến trình Chrome mồ côi (orphaned processes) làm đầy bộ nhớ và nghẽn CPU.

## 3. Điều Phối Hồi Sinh Tài Khoản Lỗi (Cooldown & Farm S7 Sync)
- Đối với các tài khoản dính cờ nhạy cảm 7 ngày của Google (`signin/rejected?rrk=77`): theo dõi mốc `retry_after` trong `oauth_pipeline_status.json`.
- Khi tài khoản hết hạn cooldown và cần đăng nhập lại từ S7 qua Google Prompt:
  - Bắt buộc kiểm tra lịch nuôi acc của farm S7 (`farm-schedule-preflight-check`).
  - Tuyệt đối không chạm vào thiết bị khi máy đang trong ca nuôi (ví dụ Ca trưa 11:30 - 15:05).
  - Chỉ kích hoạt đăng nhập vào các khung giờ rảnh an toàn (giữa các ca nuôi: 15:15 - 17:30 hoặc 21:30 - 23:45) kèm watchdog kiểm tra giải phóng file lock vật lý (`machine_<M>.lock.json`).
