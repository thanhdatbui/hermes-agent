# S7 Rolling Cleanup & Hot-Session OAuth Pipeline

Tài liệu chuẩn hóa kiến trúc quản lý dung lượng thiết bị Samsung Galaxy S7 (Rolling Cleanup), cơ chế Hook nạp OAuth Antigravity tức thì trong phiên nóng (Hot-Session OAuth), và quy tắc quản trị combo OmniRoute.

---

## 1. Cơ Chế Preflight Rolling Cleanup Trên Samsung S7

### 1.1. Ngưỡng Dung Lượng & Thời Gian Ngâm (Aging Window)
- **Trần tối đa:** Cố định **5 tài khoản Google / máy Samsung Galaxy S7**.
  - *Về phần cứng:* S7 có 4GB RAM. `AccountManagerService` và Google Play Services gánh 5 acc tiêu tốn ~100–120MB heap, máy chạy mát, không bị phồng pin, giật lag hay crash ADB.
  - *Về chu kỳ farm:* Farm chạy nhịp 10 ngày reg 1 acc mới. Giữ 5 acc tương đương thời gian ngâm trên S7 đạt **40 – 50 ngày** trước khi gỡ. Đây là mốc thời gian vàng để tài khoản thành "acc cổ", cookie trên GPM Profile đã trở thành thiết bị tin cậy chính (Primary Trusted Device).
  - *So sánh:* Nếu giữ 3 acc, thời gian ngâm chỉ 20-30 ngày (chưa đủ độ chín). Nếu giữ >6 acc, Google Play Services đồng bộ nền dày đặc, dễ bị Google gắn cờ thiết bị farm (Device Farm Abuse).

### 1.2. Preflight Check Trước Mỗi Batch Reg (O(1))
Trước khi chạy bất kỳ batch reg Gmail nào trên máy S7:
1. **Kiểm tra số tài khoản Google hiện có:**
   ```bash
   adb -s <serial> shell dumpsys account | grep -E "Account \{name=.*type=com\.google\}"
   ```
   Lệnh này trả kết quả ngay lập tức trong 0.2s, không cần mở màn hình S7, không cần mở app Cài đặt hay Gmail.
2. **Quyết định điều phối:**
   - **Số acc < 5:** Máy còn chỗ trống $\rightarrow$ Cho phép chạy batch reg bình thường (`status: "OK", can_reg: True, action: "NONE"`).
   - **Số acc >= 5:** Đạt trần $\rightarrow$ Kích hoạt kiểm tra gỡ cuốn chiếu 1 acc cũ nhất.

### 1.3. Ba Chốt Chặn An Toàn (3 Safety Gates) Để Gỡ Acc
Chỉ được gỡ tài khoản khi vượt qua đầy đủ cả 3 chốt chặn:
- **Gate 1 (2FA Độc Lập):** Đã kích hoạt 2FA Google Authenticator, Secret Key 32 ký tự đã được lưu an toàn vào `master_gmail_manager.xlsx` và `gmail_clean_v2.xlsx`. Tài khoản đã độc lập hoàn toàn với Google Prompt trên S7.
- **Gate 2 (OAuth Đã Nạp):** Đã kết nối thành công vào OmniRoute (có Refresh Token, đã gán proxy 1:1, đã sync models và nằm trong combo `ag-gemini-pool-3`).
- **Gate 3 (Tuổi Ngâm GPM >= 30 ngày):** Thời gian tính từ lúc đưa lên GPM / reg acc đến thời điểm hiện tại $\ge 30$ ngày.
- **Quy tắc chặn an toàn:** Nếu máy có 5 acc nhưng CHƯA acc nào đủ 30 ngày $\rightarrow$ **CẤM gỡ**, giữ nguyên trạng thái máy để bảo vệ độ trust của acc (`action: "SKIP"`).

### 1.4. Thao Tác Gỡ An Toàn
- **Số lượng gỡ:** Chỉ gỡ **DUY NHẤT 1 acc cũ nhất** thỏa mãn cả 3 gate trên mỗi đợt reg.
- **Phương thức gỡ:** Thao tác trực tiếp trên hệ điều hành Android của S7 bằng ADB (Settings $\rightarrow$ Accounts $\rightarrow$ Google $\rightarrow$ Remove Account) dưới `acquire_device_lock(machine=..., serial=..., project="gpm-cleanup", force_preempt=True)`.
- **CẤM TUYỆT ĐỐI:** Không vào web máy tính `myaccount.google.com/device-activity` bấm "Đăng xuất thiết bị này". Đây là hành vi nhạy cảm kích hoạt Google Sensitive Action Protection cooldown 7 ngày (`signin/rejected?rrk=77`).
- **Script chuẩn hóa:** `D:\Taadaa\GPM auto\scripts\preflight_s7_rolling_cleanup.py`.

---

## 2. Cơ Chế Hot-Session OAuth Hook Trên GPMLogin

### 2.1. Nguyên Nhân Checkpoint Đòi SMS Khi Nạp OAuth Rời Rạc
- Khi chạy quy trình rời rạc: `Login GPM + Bật 2FA` $\rightarrow$ `Đóng Profile` $\rightarrow$ `Chạy script nạp OAuth mở lại profile`:
  - Việc đóng Chromium làm ngắt phiên xác thực.
  - Khi mở lại qua proxy 4G xoay IP, Google phát hiện thiết bị vừa đăng nhập lại trên một IP/session mới, kích hoạt checkpoint `challenge/iap` đòi nhập số điện thoại để nhận SMS xác minh.
- **Cạm bẫy OCR phát hiện:** Script nạp OAuth rời rạc nếu thấy ô input trên trang checkpoint có thể nhận diện nhầm thành ô điền mã 2FA TOTP $\rightarrow$ Tự sinh mã 6 số rồi điền vào ô SĐT $\rightarrow$ Google báo lỗi *"Rất tiếc. Google không nhận dạng được số điện thoại đã nhập"* và script bị kẹt timeout.

### 2.2. Kiến Trúc Hot-Session Hook Liền Tay
Bắt buộc nối bước nạp OAuth vào **ngay trong phiên làm việc đang nóng** của trình duyệt GPM:
```text
[GPM Profile Runner]
  ├── 1. Khởi chạy Profile GPM với đúng Proxy 4G vật lý của máy.
  ├── 2. Đăng nhập Google (Tự giải audio reCAPTCHA nếu xuất hiện).
  ├── 3. Điều hướng bật 2FA Google Authenticator -> Trích xuất Secret Key 32 ký tự -> Lưu 2 file Excel.
  └── 4. [HOT-SESSION HOOK - KHÔNG ĐÓNG TRÌNH DUYỆT]:
        ├── 4.1. Mở thẳng URL OAuth OmniRoute (`/api/oauth/antigravity/authorize`) trên tab hiện tại.
        ├── 4.2. Google nhận diện phiên vừa xác thực 2FA thành công, cookie cực tươi -> KHÔNG hỏi mật khẩu, KHÔNG đòi SĐT.
        ├── 4.3. Chỉ hiện bảng Account Chooser -> Tự click chọn email.
        ├── 4.4. Hiện màn hình đồng ý cấp quyền (Consent) -> Click nút "Cho phép" (Allow).
        ├── 4.5. Bắt Authorization Code qua network listener.
        ├── 4.6. Gửi code exchange lên OmniRoute (`/api/oauth/antigravity/exchange`) lấy Refresh Token.
        ├── 4.7. Gán cố định Proxy 1:1 theo Port của máy (`PUT /api/settings/proxies/assignments`).
        ├── 4.8. Sync models (`POST /api/providers/{cid}/sync-models`).
        └── 4.9. Append target vào đuôi combo `ag-gemini-pool-3` (giữ nguyên tên combo).
```
- **Script module:** `D:\Taadaa\GPM auto\scripts\hot_session_oauth.py`.
- **Điểm tích hợp:** `run_batch_turn2_gmails.py` tại dòng 1125 ngay sau `sync_to_excels`.

---

## 3. Quy Tắc Combo Invariance & Multi-Account Origin Binding

### 3.1. Bất Biến Tên Combo (`ag-gemini-pool-3`)
- **TUYỆT ĐỐI KHÔNG ĐỔI TÊN COMBO:** Tên combo trên hệ thống phải giữ nguyên 100% là `ag-gemini-pool-3`. Đổi tên combo sẽ làm crash toàn bộ router, model mapping và các agent/subagent đang làm việc.
- Các nhãn `pool-1`, `pool-2`, ..., `pool-29`, `pool-30`... chỉ là **label** hiển thị của từng target con bên trong combo.

### 3.2. Chiến Lược Xếp Acc Mới & Tăng Trust Tự Nhiên
- **Không đưa acc mới lên đầu combo chính:** Acc mới (free/starter) có RPM/TPM thấp, đưa lên đầu sẽ dính 429 hoặc validation checkpoint khi worker gọi burst tokens.
- **Không tạo combo micro-warmup lặt vặt:** Gây over-engineering và phân mảnh routing.
- **Cách làm chuẩn:** Xếp acc mới vào **ĐUÔI của combo `ag-gemini-pool-3`**. Dàn Pro gánh việc chính; khi cao điểm tràn tải, OmniRoute tự tràn nhẹ request công việc thật xuống acc đuôi qua đúng proxy 1:1 $\rightarrow$ Vừa làm phao cứu sinh chống nghẽn, vừa nuôi trust hoàn toàn hữu cơ.

### 3.3. Mapping Nguồn Gốc Chuẩn Xác (1-S7 Multi-Account & Exact Port Binding)
- Một máy S7 và một cổng proxy 4G vật lý có thể quản lý nhiều tài khoản Gmail qua các đợt reg khác nhau.
- **Exact Origin Binding:** Mọi thao tác (mở profile GPM, duyệt Google Prompt trên S7, lấy mã bảo mật, bind proxy OmniRoute) BẮT BUỘC phải map chuẩn xác đúng serial S7 và đúng cổng proxy gốc đã sinh ra tài khoản đó.
- Tuyệt đối cấm gán chéo máy hoặc fallback direct IP.

### 3.4. Xử Lý Acc Dính SMS Checkpoint
- Tài khoản dính SMS checkpoint (`challenge/iap`) **vẫn sống 100%**, không bị banned/disabled.
- **Xử lý:** Đánh dấu `CHECKPOINT` trong `gmail_clean_v2.xlsx`, cập nhật `oauth_pipeline_status.json`, xóa profile GPM rác.
- **Không nuôi profile:** Kệ tài khoản cool-down 3–7 ngày, Google thường tự động hạ cấp checkpoint về xác nhận trên thiết bị S7. Tuyệt đối không cố mở đi mở lại profile để tránh bị tăng suspicious score.
