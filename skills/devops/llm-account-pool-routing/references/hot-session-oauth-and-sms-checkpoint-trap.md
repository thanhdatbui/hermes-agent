# Hot-Session OAuth Hook, SMS Checkpoint Trap & S7 Rolling Cleanup

## 1. Hot-Session OAuth Hook vs Closed-Session SMS Trap (2026-09-06)

### Sự cố thực tế & Bằng chứng OCR
Khi thực hiện batch nạp tài khoản Gmail lên GPMLogin Profile và cấp quyền OAuth Antigravity vào OmniRoute:
- **Quy trình cũ (Closed-Session):** Đăng nhập Google $\rightarrow$ Bật 2FA Authenticator $\rightarrow$ Đóng profile GPM. Sau vài giờ hoặc sang turn sau, mở lại profile bằng tiến trình khác để nạp OAuth.
- **Hậu quả:** Google phát hiện phiên đăng nhập bị đứt đoạn, khởi động lại Chromium qua dải IP proxy mới $\rightarrow$ Google AI đánh dấu "phiên nghi ngờ" và chuyển hướng sang Checkpoint `https://accounts.google.com/v3/signin/challenge/iap` với thông báo: *"Có điều bất thường về hoạt động của bạn. Để bảo mật tài khoản, hãy nhập số điện thoại để nhận mã xác minh văn bản."* (Đã kiểm chứng trên M53, M07, M32, M25).
- **Bẫy Selector TOTP nhầm lẫn:** Script cũ thấy ô input trên `challenge/iap` thì tưởng là ô 2FA TOTP, liền sinh mã OTP 6 số (ví dụ `491341`, `480586`) điền vào ô Số điện thoại $\rightarrow$ Google báo lỗi: *"Rất tiếc. Google không nhận dạng được số điện thoại đã nhập"* và kẹt timeout 60s.

### Quy chuẩn Hot-Session Hook Liền Tay
BẮT BUỘC giữ persistent session đang mở ngay sau khi bật 2FA thành công:
1. **Không đóng browser** sau khi bật 2FA.
2. Dùng tab hiện tại điều hướng trực tiếp tới URL OAuth Antigravity (`/api/oauth/antigravity/authorize`).
3. Google nhận diện phiên cực "nóng" (vừa chính chủ xác thực xong) $\rightarrow$ Chỉ hiển thị Account Chooser và nút *"Cho phép"* (Allow).
4. Click "Cho phép" $\rightarrow$ Bắt Callback code trong vòng 5-10 giây, **100% không bao giờ bị hỏi lại mật khẩu, không dính checkpoint đòi SĐT hay prompt S7**.
5. Gửi exchange code lấy Refresh Token, gán proxy 1:1 theo port máy, sync models và append vào đuôi combo `ag-gemini-pool-3`.

### Xử lý Checkpoint SMS Khi Re-Auth Closed-Session (2026-09-08)
Khi bắt buộc phải mở lại profile GPM cũ để re-auth (ví dụ tài khoản bị `Token expired` do Google thu hồi token):
1. **Bẫy Selector Nút "Tiếp theo" trên ô SĐT**: Nếu matcher nút "Tiếp theo" (`next_btn`) chỉ kiểm tra password, totp, recovery email, pin, identifier mà quên kiểm tra `tel_vis` (`input[type="tel"]`, `input#phoneNumberId`), Playwright sẽ liên tục click nút "Tiếp theo" khi ô SĐT đang rỗng, gây kẹt lặp màn hình và timeout 180s. Bắt buộc kiểm tra `tel_vis` trước khi click nút Next.
2. **Hard SMS Checkpoint & Lỗi "Rất tiếc, đã xảy ra sự cố"**:
   - Khi Google hiển thị: *"Xác minh danh tính của bạn. Có điều bất thường về hoạt động của bạn... Nhập số điện thoại để nhận tin nhắn văn bản cùng mã xác minh"*, script bấm nút *"Thử cách khác"*.
   - Nếu Google chuyển sang danh sách phương thức (Prompt Có / Mã 10 số): tiếp tục duyệt trên S7.
   - Nếu Google phản hồi lỗi nội bộ: *"Đã xảy ra lỗi: Rất tiếc, đã xảy ra sự cố. Vui lòng thử lại. Bắt đầu lại."* $\rightarrow$ Đây là **Hard SMS Checkpoint**, Google từ chối cấp phương thức thay thế. Script phải fail-fast ngay trạng thái `SMS_CHECKPOINT`, CẤM bấm loop "Thử cách khác".
3. **Kỷ luật dọn dẹp an toàn khi dính Hard SMS**:
   - Xóa ngay thư mục profile GPM trên PC (`rmtree(prof_dir)`) để dọn rác và giải phóng browser lock.
   - **CẤM TUYỆT ĐỐI** gỡ hoặc đăng xuất tài khoản trên điện thoại Samsung S7 (giữ nguyên hardware anchor để Google Play Services tiếp tục duy trì trust).
   - Ghi nhận `SMS_CHECKPOINT (M<id>)` vào `oauth_pipeline_status.json` để runner sau tự động bỏ qua.
4. **Phục hồi tài khoản valid qua OmniRoute API thay vì Re-Auth**:
   - Đối với các tài khoản token còn sống (`POST /api/providers/{id}/test` trả về 200) nhưng bị tắt công tắc do rớt vào standard-tier (nhãn "Business"), **tuyệt đối không mở lại GPM để re-auth** (tránh kích hoạt checkpoint SMS).
   - Gọi trực tiếp `PUT /api/providers/{id}` gán `projectId: "aicode-consumers"`, `tier: "free-tier"`, `subscriptionTier: "Antigravity Starter Quota"` và `isActive: true` để phục hồi tài khoản phục vụ ngay.

---

## 2. Preflight S7 Rolling Cleanup (Trần 5 acc / máy S7)

### Tại sao trần 5 acc là con số vàng?
- **Phần cứng S7 (4GB RAM):** 5 acc Google ngốn ~100MB heap của Google Play Services, máy mát, không tràn RAM.
- **Account Aging (Độ ngâm):** Với chu kỳ reg 10 ngày / acc, 5 acc giúp tài khoản ngâm trên S7 tới 40–50 ngày trước khi rời máy.
- **Telemetry tự nhiên:** Người dùng thật thường có 3-5 tài khoản trên máy; từ 6-8 acc trở lên Google mới gắn cờ device farm abuse.

### Cơ chế 3 Safety Gates & Lệnh ADB O(1)
- **Đọc tài khoản nhanh O(1):** `adb -s <serial> shell dumpsys account` (0.2s, không cần mở app, không bật màn hình).
- **Ngưỡng hành động:**
  - `< 5` accs: Đủ chỗ trống $\rightarrow$ Cho phép reg mới (`can_reg: True, action: "NONE"`).
  - `>= 5` accs: Kích hoạt 3 Safety Gates để tìm duy nhất 1 acc cũ nhất thỏa mãn:
    + Gate 1: Có Secret 2FA trong Excel (`len >= 16`).
    + Gate 2: Đã có OAuth OmniRoute (trong `omniroute_success` hoặc connection live).
    + Gate 3: Ngày tạo / ngâm GPM $\ge 30$ ngày.
- **Thao tác gỡ an toàn:**
  - Dưới lock `acquire_device_lock(machine=str(mid), serial=serial, project="gpm-cleanup", force_preempt=True)`.
  - Gỡ trực tiếp qua Android OS UI (`am start -a android.settings.SYNC_SETTINGS`).
  - **CẤM TUYỆT ĐỐI:** Không vào web `myaccount.google.com/device-activity` từ máy tính bấm "Đăng xuất" (tránh lỗi Sensitive Action Protection cooldown 7 ngày `rrk=77`).
  - Nếu chưa acc nào đủ 30 ngày: **Chặn đứng lệnh gỡ** (`action: "SKIP"`), bảo vệ acc tối đa.
