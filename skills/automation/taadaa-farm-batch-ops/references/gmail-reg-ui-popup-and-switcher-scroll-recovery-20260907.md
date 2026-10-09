# Gmail Reg: Bento Card Switcher Scroll, Security Popup Dismiss & Wi-Fi Preflight Triage (2026-09-07)

## Bối cảnh & Hiện tượng lỗi cũ
Khi chạy batch hoặc retry từng máy trong repo `D:\Taadaa\register gmail` (`gmail_reg_v10.py`), một số máy (như 01, 02, 36, 47) bị kẹt ở các bước UI hoặc provider:
1. **Account Switcher:** Nút "Thêm tài khoản khác" bị trôi xuống dưới màn hình hoặc chuỗi text trong XML là tiếng Việt có dấu (`Thêm tài khoản khác`), trong khi script cũ chỉ so khớp chuỗi không dấu / lỗi encoding (`Them tai khoan khac`, `ThÃªm tÃ i khoáº£n khÃ¡c`).
2. **Security Update Popup:** Popup "Cập nhật tính năng bảo mật mới của Gmail" xuất hiện đè lên giao diện khi mở switcher hoặc chọn provider Google, làm script không tap trúng item Google provider.
3. **Mất Internet trên Wi-Fi:** Máy kết nối Wi-Fi nhưng router proxy không cấp Internet (`Không có Internet`), dẫn đến GMS crash/báo "Đã xảy ra sự cố" hoặc Gmail Home không tải được avatar/hòm thư.

## Giải pháp & Kỹ thuật đã áp dụng

### 1. Chuẩn hóa so khớp tiếng Việt & Cuộn Switcher (`wait_and_tap_add_account_in_switcher`)
- Bổ sung cả 3 biến thể text: `"Them tai khoan khac"`, `"Thêm tài khoản khác"`, `"Add another account"` trong `is_gmail_account_switcher_xml` và `find_add_account_card_in_switcher`.
- Thêm fallback tự động vuốt lên một nhịp nếu chưa thấy thẻ Add account:
  ```python
  shell(device_id, "input", "swipe", "540", "1500", "540", "900", "300")
  ```
- Kiểm tra `y >= 300` và lọc package `com.google.android.gm` trên các bento card để tránh tap nhầm thanh tiêu cực hoặc banner bộ nhớ Drive.

### 2. Tự động đóng Popup Security Update & Meet Onboarding
- Tại `tap_google_provider_entry`, lồng hàm `dismiss_gmail_security_update_popup(device_id, xml=xml)` vào vòng lặp retry 5 lần. Khi popup xuất hiện, script lập tức bấm đóng/xác nhận và sleep 0.8s trước khi tap tiếp Google provider.
- Tại preflight, tự động xử lý popup Meet Onboarding qua `com.google.android.gm:id/dismiss_button`.

### 3. Triage chẩn đoán lỗi mạng qua SystemUI XML
Khi gặp lỗi `[04b] Google sign-in chưa load xong` hoặc `[PRE_GMAIL][NOT_GMAIL_HOME]`:
- **Đừng vội kết luận do UI selector hay Google bot-block!**
- Mở file UI XML dump (`fail_04b_wait_signin_*.xml` hoặc `preflight_*_not_gmail_home_*.xml`) và kiểm tra node `com.android.systemui:id/wifi_combo`:
  ```xml
  <node ... resource-id="com.android.systemui:id/wifi_combo" content-desc="Tín hiệu Wi-Fi ba vạch.,Không có Internet." />
  ```
- Nếu `content-desc` chứa `"Không có Internet"`, nguyên nhân gốc là do kết nối mạng/proxy của thiết bị tại thời điểm đó bị rớt, khiến Google GMS không tải được form đăng ký (`suc_layout_title: Đã xảy ra sự cố. Vui lòng quay lại và thử một lần nữa`).

---

## 4. Quy tắc Bất biến: Xử lý Thất bại Phone Verify vs Lỗi Script (User chốt 2026-09-07)
- **CẤM RETRY NHÓM PHONE VERIFY:** Khi máy gặp lỗi `PHONE_VERIFY` (`Phone verification` / `[PHONE_VERIFY]`), Google đã gắn cờ yêu cầu số điện thoại xác minh trên luồng tạo tài khoản. Việc cố thử lại (retry) ngay lập tức sẽ đốt proxy, hạ trust thiết bị và chắc chắn tiếp tục dính phone checkpoint.
- **CỜ COOLDOWN 4 NGÀY (Cooldown 4d):** Toàn bộ máy dính `PHONE_VERIFY` phải được lưu nhận diện và gắn cờ cooldown tối thiểu **4 ngày**, tuyệt đối không được đưa vào danh sách retry hay ép chạy lại trong phiên.
- **CHỈ ĐƯỢC THỬ LẠI VỚI NHÓM LỖI SCRIPT:** Khi người vận hành hoặc pipeline chạy bù / retry, **CHỈ ĐƯỢC CHỌN các máy thất bại do lỗi script** (lỗi UI bento switcher, popup bảo mật, timeout chọn provider, selector thay đổi). Bỏ qua 100% nhóm phone verification.
- **CHỐNG MOJIBAKE / LỖI FONT TRÊN BÁO CÁO TELEGRAM:**
  - File PowerShell đọc log (`Get-Content`) trên Windows BẮT BUỘC có `-Encoding UTF8` (mặc định PowerShell 5.1 dùng ANSI/CP1252 làm biến dạng tiếng Việt thành `?` hoặc `Ã¡`).
  - Runner tổng hợp báo cáo (`run_night_chain_pipeline.py`) phải chuẩn hóa nhãn lỗi (ví dụ: `04_google` -> `google provider error`) thay vì nhả exception thô lên báo cáo Telegram.

---

## 5. Bẫy chẩn đoán mạng: ADB Ping 8.8.8.8 (ICMP) ≠ Kết nối Google Play Services (GMS HTTPS)
- **Hiện tượng:** Kiểm tra máy qua `adb shell ping -c 3 8.8.8.8` thấy 0% packet loss (ping thông suốt), nhưng khi chạy script vẫn dính:
  `[04b][GMS_NO_NETWORK] transient Google network screen repeated after recovery` -> `❌ STOPPED: [04b] Google sign-in chưa load xong`.
- **Nguyên nhân gốc:**
  - `ping 8.8.8.8` chỉ kiểm tra tầng IP/ICMP cơ bản ra Internet.
  - Màn hình đăng ký Google do Google Play Services (`com.google.android.gms`) tải qua kết nối HTTPS (port 443) tới các endpoint Google (`android.clients.google.com`, `accounts.google.com`).
  - Nếu proxy Wi-Fi hoặc router proxy bị nghẽn SSL handshake, DNS không phân giải được domain Google, hoặc IP proxy bị Google chặn tạm thời, ICMP ping 8.8.8.8 vẫn phản hồi bình thường nhưng GMS vẫn báo lỗi mạng `transient error/no-network screen`.
- **Hành động:** Khi gặp lỗi `GMS_NO_NETWORK`, không chỉ dựa vào ping ICMP để kết luận mạng OK; cần kiểm tra khả năng kết nối HTTPS ra domain Google qua proxy của máy đó.

---

## 6. Điều kiện Merge Workbook (`merge_success_results.py`)
- Script `scripts/merge_success_results.py` chỉ thực thi khi trong thư mục `--result-dir` có phát sinh file `*.success.json`.
- Khi toàn bộ các máy retry/batch đều không tạo thành công (0 file success), bỏ qua bước merge vào `gmail_clean_v2.xlsx` để tránh thao tác thừa.

