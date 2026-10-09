# Gmail Reg UI Detours & Error Triage Discipline

Áp dụng cho quy trình đăng ký Gmail tự động trên farm Samsung S7 (Android 7) trong chuỗi đêm (`night-chain-reg-pipeline`) và các lượt chạy on-demand.

---

## 1. Kỷ Luật Phân Loại Lỗi & Quy Tắc Retry (Phone Verify vs Script Error)

Khi batch đăng ký Gmail kết thúc và có máy lỗi, Coordinator & Operator TUYỆT ĐỐI tuân thủ nguyên tắc phân loại:

### A. Nhóm Phone Verification (Ví dụ: máy 10, 26, 59...)
- **Quy tắc bất biến:** **TUYỆT ĐỐI CẤM THỬ LẠI NGAY** trong phiên.
- **Thời gian ngâm (Cooldown):** Máy tự động dính cờ cooldown **4 ngày (4d)** trước khi được phép cấp lượt reg tiếp theo.
- **Lý do kỹ thuật:** Khi Google phát hiện tín hiệu nghi vấn và yêu cầu Phone Verification, thiết bị và IP proxy tương ứng đã nằm trong danh sách theo dõi (trust penalty). Việc cố tình khởi động lại flow reg ngay lập tức sẽ dẫn đến tỷ lệ fail 100% và làm tăng nguy cơ flag cứng thiết bị.

### B. Nhóm Lỗi Script / UI Detours (Ví dụ: máy 01, 02, 36, 47...)
- **Quy tắc:** **CHỈ ĐƯỢC PHÉP THỬ LẠI VỚI NHÓM NÀY** sau khi đã điều tra nguyên nhân (UI detour, provider mismatch, bug script) và áp dụng bản vá code.
- Được phép chạy bù (retry on-demand) trong các khung giờ rảnh (đêm 02:00 - 05:30 hoặc trưa 10:00 - 11:45).

---

## 2. Các Điểm Nghẽn UI Detours Thực Tế Trên Samsung S7 (Android 7)

### 2.1. Popup Cảnh Báo Hệ Điều Hành Cũ ("Hãy cập nhật thiết bị để đảm bảo an toàn")
- **Hiện tượng:** Sau khi bấm nút chọn provider Google trong ứng dụng Gmail, Google Play Services / Gmail thường bung bottom sheet cảnh báo:
  * Tiêu đề: *"Hãy cập nhật thiết bị để đảm bảo an toàn"* / *"Update your device to stay secure"*.
  * Nội dung: *"Để tiếp tục dùng ứng dụng Gmail... hãy cập nhật hệ điều hành của thiết bị"*.
  * Resource ID nút đóng: `com.google.android.gm:id/app_update_dismiss_button` (Text: *"Đóng"* / *"Close"*).
- **Cách xử lý:** Trong hàm `tap_google_provider_entry()`, bắt buộc gọi `dismiss_gmail_security_update_popup(device_id)` tại mỗi vòng lặp kiểm tra trước khi chờ màn hình Sign-in xuất hiện.

### 2.2. Tràn Bento Account Switcher & Click Nhầm Status Bar (SystemUI)
- **Hiện tượng:**
  * Khi máy đã có sẵn nhiều tài khoản Google cũ hoặc có card *"Cảnh báo bảo mật quan trọng"*, nút *"Thêm tài khoản khác"* bị đẩy tụt xuống dưới màn hình hiển thị.
  * Nếu thuật toán fallback tìm card không chặn biên trên, nó sẽ match nhầm vào icon thông báo GemPhone trên thanh SystemUI (`[12,0][66,71]`, `y=35`), dẫn đến tap trúng status bar và máy bị kẹt mãi ở switcher.
- **Cách xử lý:**
  1. Giới hạn chặt chẽ node chỉ thuộc `package="com.google.android.gm"` và tọa độ `y >= 300` (loại bỏ hoàn toàn vùng SystemUI).
  2. Bổ sung cơ chế tự động vuốt cuộn trang (`adb shell input swipe 540 1500 540 900 300`) trong `wait_and_tap_add_account_in_switcher()` khi không tìm thấy text ở viewport đầu tiên.

---

## 3. Kỷ Luật Báo Cáo Telegram & Encoding UTF-8

1. **Chuẩn hóa chuỗi tiếng Việt:**
   - Mọi chuỗi thông báo, log và exception trong Python (`gmail_reg_v10.py`) phải lưu chuẩn UTF-8, tuyệt đối không để dính chuỗi lỗi font/mojibake (như `Kh?ng ch?n ???c...`).
   - Trong PowerShell runner (`run_parallel.ps1`), khi đọc file log phải chỉ định rõ `-Encoding UTF8` (`Get-Content -LiteralPath $LogPath -Encoding UTF8`).
2. **Sanitize & Grouping mã lỗi trên báo cáo Telegram:**
   - Script tổng hợp chuỗi (`run_night_chain_pipeline.py`) phải mapping sạch sẽ các lý do lỗi thành nhãn ngắn gọn (`google provider error`, `proxy timeout`, `phone verification`, `proxy unavailable`), không in nguyên văn chuỗi traceback hoặc exception thô làm hỏng layout thông báo Telegram.

---

## 4. Đồng Bộ Chốt Chặn Proxy Preflight (Proxy Gate Parity với TikTok Repos)

- **Cạm bẫy LAN Ping Fallback trong `automation-core`:**
  * Tại chế độ router proxy (`wlan0`), `check_android_vpn` nghiệm thu: `if egress_ip_ok or (ping_ok and wifi_validated): ip_verified = True`.
  * Khi proxy upstream bị lỗi (trả về `HTTP 502 Bad Gateway` hoặc port đóng), probe IP public thất bại (`egress_ip_ok=False`), nhưng do máy vẫn ping được router LAN và Wi-Fi vẫn kết nối, hàm trả về `allowed=True` kèm `proxy_ip=""`.
  * Nếu consumer script (`gmail_reg_v10.py`) chỉ kiểm tra `require_android_vpn().allowed` mà bỏ qua `proxy_ip`, máy sẽ được cho phép vào reg và lập tức dính lỗi mất mạng GMS (`[04b][GMS_NO_NETWORK]`).
- **Chốt chặn bắt buộc:**
  * Gọi `require_android_vpn(..., verify_live_ip=True)`.
  * Khóa chặt điều kiện: nếu `vpn_required=True` thì BẮT BUỘC `status.allowed`, `status.connected` VÀ `proxy_ip` không rỗng.
  * Nếu thiếu `proxy_ip`, lập tức ném `ConsumerPreflightError("VPN verification failed: live proxy IP proof missing")`, log `❌ STOPPED: [PREFLIGHT_PROXY]` và thoát mã lỗi 2, nhả device lock ngay trong 1-2s đầu tiên mà không mở app Gmail.

