# Hot-Session OAuth Hook & S7 Rolling Cleanup Architecture

## 1. Hot-Session OAuth Hook trên GPM Profile

### Bối cảnh & Hiện trường thực tế
Khi chạy batch đăng nhập Google và cài đặt 2FA Authenticator trên GPMLogin Profile:
- **Lỗi ở quy trình cũ (Tách rời 2 bước):** Sau khi bật 2FA xong, script đóng hoàn toàn Chromium lại. Sau vài giờ hoặc sang turn sau, một tiến trình khác mở lại profile qua proxy 4G để nạp OAuth Antigravity. Lúc này Google thấy session bị gián đoạn, IP proxy xoay dải mới $\rightarrow$ Google AI đánh dấu "phiên nghi ngờ" và kích hoạt Checkpoint `challenge/iap` đòi số điện thoại SMS xác minh danh tính (đã xác minh bằng WinRT OCR trên các máy M53, M07, M32, M25).
- **Pitfall phát hiện:** Khi dính `challenge/iap` đòi SĐT, selector cũ nhận nhầm ô input này là ô 2FA TOTP và điền 6 số OTP vào ô số điện thoại $\rightarrow$ Google phản hồi lỗi *"Google không nhận dạng được số điện thoại đã nhập"* và script bị kẹt timeout 60s.

### Giải pháp: Hot-Session Hook liền tay (Khép kín trong 1 phiên)
Tận dụng triệt để trạng thái "phiên nóng" (cookie `SID`, `SSID`, `HSID`, `OSID` vừa được Google xác thực chính chủ thành công):
1. **Không đóng browser** sau khi bật 2FA thành công.
2. Mở thẳng URL OAuth Antigravity (`/api/oauth/antigravity/authorize`) trên tab hiện tại.
3. Google nhận diện phiên làm việc vừa xác thực xong $\rightarrow$ Chỉ hiển thị Account Chooser và nút *"Cho phép"* (Allow). Không bao giờ hỏi lại mật khẩu, không bao giờ đòi SĐT hay mã xác minh.
4. Bắt Callback Authorization Code qua network listener `page.on("request")` hoặc URL `/callback?code=`.
5. Gửi code lên `POST /api/oauth/antigravity/exchange` lấy Refresh Token.
6. Gán Proxy 1:1 theo port máy (`PUT /api/settings/proxies/assignments`) và sync models (`POST /api/providers/{cid}/sync-models`).
7. Append target vào đuôi combo `ag-gemini-pool-3` (TUYỆT ĐỐI GIỮ NGUYÊN TÊN COMBO).
8. Cập nhật `oauth_pipeline_status.json`.

---

## 2. Preflight S7 Rolling Cleanup (Trần 5 acc / máy S7)

### Tại sao trần 5 acc là tối ưu?
- **Phần cứng S7 (4GB RAM):** Google Play Services đồng bộ tài khoản tốn ~100MB RAM cho 5 acc. Dưới 5 acc máy chạy mát, không bị tràn RAM hay phồng pin.
- **Tuổi tài khoản (Aging):** Với chu kỳ reg 10 ngày / acc, trần 5 acc cho phép tài khoản được ngâm trên S7 từ 40 đến 50 ngày. Đủ độ "già" để Google coi GPM Profile là primary trusted device.
- **Chống gắn cờ Device Farm:** S7 giữ tối đa 5 acc trông tự nhiên như người dùng thật (1 mail chính, 1 mail việc, 2 mail phụ, 1 mail game/mua sắm).

### Quy trình 3 Safety Gates trước khi gỡ cuốn chiếu
Kiểm tra danh sách tài khoản Google qua ADB `dumpsys account` ($O(1)$, 0.2 giây, không cần mở app):
```bash
adb -s <serial> shell dumpsys account
# Regex: Account\s*\{\s*name=([^,\s]+),\s*type=com\.google\s*\}
```
- **Nếu < 5 accs:** Đủ chỗ trống $\rightarrow$ Cho phép chạy reg Gmail mới (`can_reg: True, action: "NONE"`).
- **Nếu >= 5 accs:** Kích hoạt 3 Safety Gates để tìm duy nhất 1 acc cũ nhất thỏa mãn:
  - **Gate 1 (2FA Secret):** Cột 2FA trong `gmail_clean_v2.xlsx` có Secret Key Base32 hợp lệ ($\ge 16$ ký tự).
  - **Gate 2 (OAuth Active):** Đã nạp thành công vào OmniRoute (có trong `omniroute_success` của `oauth_pipeline_status.json` hoặc connection live).
  - **Gate 3 (Độ tuổi ngâm GPM):** Ngày tạo / ngày đưa lên GPM $\ge 30$ ngày so với hiện tại.
- **Quyết định an toàn:**
  - Nếu thỏa cả 3 Gates: Chọn **1 acc cũ nhất** gỡ cuốn chiếu qua lệnh hệ điều hành Android (`acquire_device_lock` $\rightarrow$ `am start -a android.settings.SYNC_SETTINGS` $\rightarrow$ gỡ trên UI điện thoại).
  - **CẤM TUYỆT ĐỐI:** Không vào web `myaccount.google.com/device-activity` từ máy tính bấm "Đăng xuất" (tránh kích hoạt Google Sensitive Action Protection cooldown 7 ngày `rrk=77`).
  - Nếu chưa có acc nào đủ 30 ngày: **Chặn đứng lệnh gỡ** (`action: "SKIP"`), bảo vệ acc tối đa.

---

## 3. Quy tắc Đặt tên Combo & Mapping OmniRoute

- **Combo Name bất biến:** Tên combo trên OmniRoute phải giữ nguyên 100% là `ag-gemini-pool-3`. Các nhãn `pool-19`, `pool-20`, `pool-30`... chỉ là label nội bộ của target, tuyệt đối không sửa tên combo vì sẽ làm gãy model routing của toàn bộ Agent / Coordinator / Worker.
- **1-S7 Multi-Account & Exact Port Binding:** Một máy S7 và một cổng proxy 4G vật lý có thể quản lý nhiều tài khoản Gmail (qua các đợt reg khác nhau). Nhưng khi mở GPM profile, duyệt Google Prompt trên S7 hay gán proxy vào OmniRoute **BẮT BUỘC phải map chuẩn xác đúng serial máy S7 và đúng cổng proxy gốc đã reg ra Gmail đó**.
- **Warmup Fallback Strategy:** Acc mới tạo (starter quota) nạp vào ĐUÔI của combo `ag-gemini-pool-3` để làm tầng tràn tải dự phòng (spillover). Không đưa lên đầu combo làm việc chính để tránh bị 429/checkpoint do rate limit thấp.
