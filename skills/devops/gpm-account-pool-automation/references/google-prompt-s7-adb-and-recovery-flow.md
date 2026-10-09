# Google Prompt (Galaxy S7 Push) & Recovery Email Hierarchy

## 1. Cơ Chế Google Prompt Trên Thiết Bị Tin Cậy Bậc 1 (Trusted Device)
Khi một tài khoản Gmail đã được đăng nhập vào CH Play / Google Play Services trên điện thoại Android thật (Galaxy S7 trong farm):
- Google mặc định coi thiết bị đó là **Thiết bị tin cậy bậc 1**.
- Mỗi khi đăng nhập trên trình duyệt mới (GPM / Playwright), Google sẽ tự động đẩy thông báo xác nhận: *"Kiểm tra Galaxy S7 của bạn ... Nhấn vào số XX"*.
- **Khi S7 đang bận (cron nuôi TikTok đang chạy foreground):** Thông báo Google Prompt không pop up kịp → phiên đăng nhập bị hủy. **Không nên dùng S7 Prompt khi cron đang chạy.**

---

## 2. Luồng SECURITY CODE từ Máy S7 — PHƯƠNG ÁN ƯU TIÊN (Đã Chứng Minh Hoạt Động 2026-09-03)

### Lý do dùng Security Code thay vì Google Prompt:
- Google Prompt cần màn hình S7 không bị ứng dụng khác chiếm foreground.
- Security Code không yêu cầu điều đó — máy S7 có thể đang chạy TikTok, chỉ cần lấy code từ Settings.

### Cơ chế:
1. **Trên S7:** Vào `Cài đặt → Google → Tất cả dịch vụ (tab) → Bảo mật → Mã bảo mật`.
2. S7 sẽ hiện 2 mã số 10 chữ số, có hiệu lực **15 phút** kể từ thời điểm mở trang.
3. **Trên GPM Chrome:** Sau khi nhập mật khẩu, trang challenge hiện các options. Click vào `li` có text `"Sử dụng điện thoại hoặc máy tính bảng của bạn để nhận mã bảo mật (ngay cả khi không có kết nối mạng)"`.
4. Trang tiếp theo (`challenge/selection` với `lid=2`) hướng dẫn: mở Settings S7 → Bảo mật → Mã bảo mật → nhập mã.
5. Điền mã vào input trên Chrome → Tiếp theo → **Google xác nhận thành công.**

### Flow tự động hoàn chỉnh (ADB + Playwright):

```python
import subprocess, time, re, requests, xml.etree.ElementTree as ET
from playwright.sync_api import sync_playwright

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
CHROME_EXE = r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\gpm_browser\gpm_browser_chromium_core_142\chrome.exe"

def get_s7_security_codes(serial, machine_num):
    """Lấy 2 Security Code từ máy S7 qua ADB + atx-agent."""
    atx_port = 17000 + int(machine_num)
    subprocess.run([ADB, "-s", serial, "forward", f"tcp:{atx_port}", "tcp:7912"])
    time.sleep(1)

    # 1. Mở Settings → Google
    subprocess.run([ADB, "-s", serial, "shell", "am", "start", "-a", "android.settings.SYNC_SETTINGS"])
    time.sleep(2)

    # 2. Scroll xuống và click "Google" item
    r = requests.get(f"http://127.0.0.1:{atx_port}/dump/hierarchy", timeout=4)
    root = ET.fromstring(r.json().get("result", ""))
    for node in root.iter("node"):
        if node.attrib.get("text", "") == "Google":
            m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.attrib.get("bounds", ""))
            if m:
                x = (int(m.group(1)) + int(m.group(3))) // 2
                y = (int(m.group(2)) + int(m.group(4))) // 2
                subprocess.run([ADB, "-s", serial, "shell", "input", "tap", str(x), str(y)])
                time.sleep(3)
                break

    # 3. Click vào tên tài khoản Gmail mục tiêu
    r = requests.get(f"http://127.0.0.1:{atx_port}/dump/hierarchy", timeout=4)
    root = ET.fromstring(r.json().get("result", ""))
    for node in root.iter("node"):
        text = node.attrib.get("text", "")
        if "@gmail.com" in text:
            m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.attrib.get("bounds", ""))
            if m:
                x = (int(m.group(1)) + int(m.group(3))) // 2
                y = (int(m.group(2)) + int(m.group(4))) // 2
                subprocess.run([ADB, "-s", serial, "shell", "input", "tap", str(x), str(y)])
                time.sleep(3)
                break

    # 4. Click "Tất cả dịch vụ" tab rồi scroll tới "Bảo mật" → "Mã bảo mật"
    r = requests.get(f"http://127.0.0.1:{atx_port}/dump/hierarchy", timeout=4)
    root = ET.fromstring(r.json().get("result", ""))
    for node in root.iter("node"):
        if "Tất cả dịch vụ" in node.attrib.get("text", ""):
            m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.attrib.get("bounds", ""))
            if m:
                x = (int(m.group(1)) + int(m.group(3))) // 2
                y = (int(m.group(2)) + int(m.group(4))) // 2
                subprocess.run([ADB, "-s", serial, "shell", "input", "tap", str(x), str(y)])
                time.sleep(3)
                break

    # 5. Scroll để tìm "Bảo mật và đăng nhập" rồi vào đó
    subprocess.run([ADB, "-s", serial, "shell", "input", "swipe", "500", "1600", "500", "600"])
    time.sleep(2)
    r = requests.get(f"http://127.0.0.1:{atx_port}/dump/hierarchy", timeout=4)
    root = ET.fromstring(r.json().get("result", ""))
    for node in root.iter("node"):
        if "Bảo mật và đăng nhập" in node.attrib.get("text", ""):
            m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.attrib.get("bounds", ""))
            if m:
                x = (int(m.group(1)) + int(m.group(3))) // 2
                y = (int(m.group(2)) + int(m.group(4))) // 2
                subprocess.run([ADB, "-s", serial, "shell", "input", "tap", str(x), str(y)])
                time.sleep(3)
                break

    # 6. Scroll xuống và click "Mã bảo mật"
    subprocess.run([ADB, "-s", serial, "shell", "input", "swipe", "500", "1600", "500", "600"])
    time.sleep(2)
    r = requests.get(f"http://127.0.0.1:{atx_port}/dump/hierarchy", timeout=4)
    root = ET.fromstring(r.json().get("result", ""))
    for node in root.iter("node"):
        if "Mã bảo mật" in node.attrib.get("text", ""):
            m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.attrib.get("bounds", ""))
            if m:
                x = (int(m.group(1)) + int(m.group(3))) // 2
                y = (int(m.group(2)) + int(m.group(4))) // 2
                subprocess.run([ADB, "-s", serial, "shell", "input", "tap", str(x), str(y)])
                time.sleep(4)
                break

    # 7. Đọc các mã
    r = requests.get(f"http://127.0.0.1:{atx_port}/dump/hierarchy", timeout=4)
    root = ET.fromstring(r.json().get("result", ""))
    codes = []
    for node in root.iter("node"):
        text = node.attrib.get("text", "").replace("\u202d", "").replace(" ", "")
        if re.match(r"^\d{10}$", text):
            codes.append(text)
    return codes  # [code1, code2]
```

---

## 3. Tự Động Kích Hoạt 2FA Google Authenticator & Tách Khỏi Sự Phụ Thuộc Máy S7 (Verified 100% 2026-09-03)

Sau khi đăng nhập vào GPM thành công bằng Security Code, **BẮT BUỘC** kích hoạt ngay 2FA Authenticator TOTP trên Chrome để tách vĩnh viễn tài khoản khỏi S7.

### Flow Kích Hoạt Tự Động:
1. Mở trang: `https://myaccount.google.com/signinoptions/twosv`.
2. Nếu Google yêu cầu Re-auth: Bấm *"Thử cách khác"* $\rightarrow$ Chọn *"Mã bảo mật"* $\rightarrow$ Điền mã 10 số từ S7.
3. Bấm **"Turn on 2-Step Verification"** (hoặc Bật).
4. Chọn mục **"Authenticator app"** / **"Add authenticator app"**.
5. Bấm nút **"Set up authenticator"**.
6. Bấm **"Can't scan it?"** (Không thể quét mã?).
7. Trích xuất chuỗi **Secret Key (Base32)** gồm 32 ký tự (ví dụ: `5pct jcg3 6jqb ziax ogdq ftmz 2nfm m3os` $\rightarrow$ `5PCTJCG36JQBIAXOGDQFTMZ2NFMM3OS`).
8. Dùng `pyotp.TOTP(secret_key).now()` sinh mã 6 số.
9. Bấm nút visible **"Next"** trong dialog $\rightarrow$ Điền mã 6 số $\rightarrow$ Bấm nút visible **"Verify"** / **"Done"**.
10. Lưu Secret Key vào file `master_gmail_manager.xlsx` (cột `2FA_Secret`) và `gmail_clean_v2.xlsx` (cột `2fa`).

---

## 4. Bẫy 2 Giai Đoạn Của Google Prompt Trên Galaxy S7 (Kinh Nghiệm Xương Máu 2026-09-06)

### A. Cấu trúc 2 Phase của Dialog Prompt:
Khi trên PC hiện số PIN (ví dụ: `Target PIN: 47`):
- **Phase 1 (Xác nhận người dùng):** S7 hiện dialog *"Có phải bạn đang cố đăng nhập không?"* hoặc *"Cho phép một ứng dụng truy cập dữ liệu của bạn trên Google?"* $\rightarrow$ Chỉ có nút *"Có, đúng là tôi"* / *"Cho phép"*. **Lúc này 3 số PIN chưa xuất hiện trên màn hình!**
- **Phase 2 (Chọn số PIN):** Chỉ sau khi bấm *"Có, đúng là tôi"*, màn hình S7 mới chuyển sang hiển thị 3 ô số (ví dụ: 24, 47, 89).
- **CẠM BẪY CHẾT NGƯỜI:** Nếu script vừa tap nút *"Có"* xong mà lập tức gửi `keyevent 3` (HOME) và báo `return True` $\rightarrow$ Dialog bị đóng ngay lập tức trước khi kịp tap số 47. Trình duyệt trên PC sẽ tiếp tục ngồi chờ người dùng bấm số trên điện thoại cho đến khi hết 60-75s và báo `TIMEOUT`.
- **QUY TẮC THỰC THI CHUẨN:**
  - Nếu `target_pin` có giá trị: Tap *"Có"* chỉ là Phase 1. Script **CẤM** gửi `keyevent 3` hay `return True` ngay. Phải tiếp tục vòng lặp chờ màn hình Phase 2, tìm đúng node số khớp `target_pin`, tap vào số đó rồi MỚI ĐƯỢC gửi `keyevent 3` và `return True`.
  - Nếu `target_pin` là `None` (không yêu cầu số): Tap *"Cho phép"* / *"Có"* xong là hoàn tất.

### B. Xử lý Notification bị gom nhóm trên Galaxy S7:
- Trên Galaxy S7 (Android 8.0), thông báo của Google Play Services thường bị gom lại thành nhóm: `Tổng N thông báo`.
- Tap vào dòng tiêu đề `Dịch vụ Google Play` chỉ đóng/mở nhóm, **KHÔNG** mở dialog xác nhận.
- Cần tap nút mở rộng: `android.widget.Button` có `desc="Mở rộng"` (tọa độ khoảng `[387,261][531,405]`, tâm `459, 333`).
- Sau khi mở rộng nhóm, tap đúng thông báo con: chứa chuỗi *"Cho phép một ứng dụng truy cập dữ liệu của bạn trên Google?"* hoặc *"Bạn đang cố đăng nhập?"* hoặc chứa đúng email mục tiêu.

### C. Quy Tắc Pre-flight Canh S7 Rảnh (Launcher Idle) Trước Khi Nạp:
- **Chỉ đạo bắt buộc**: *"Canh s7 rảnh mới vào lấy mã nhé"* — Tuyệt đối không can thiệp lấy mã OTP/Security Code hoặc duyệt Google Prompt khi máy S7 đang bận chạy tác vụ ngầm (cron nuôi TikTok, feed session, video render).
- **Cơ chế kiểm tra $O(1)$ qua ADB**:
  ```python
  r = subprocess.run([adb, "-s", serial, "shell", "dumpsys", "window", "windows"], capture_output=True, text=True)
  focused = [l.strip() for l in r.stdout.splitlines() if "mCurrentFocus" in l]
  f_str = focused[0] if focused else ""
  is_idle = "LauncherActivity" in f_str or "launcher" in f_str or not f_str
  ```
- **Hành động khi `is_idle == False`**: Tạm thời bỏ qua máy đó (`SKIP`), chuyển sang máy đang ở màn hình chính (Launcher) để không làm gián đoạn tiến trình đang chạy trên điện thoại.

---

## 5. Quyết định Nên Dùng Phương Án Nào

| Tình huống | Phương án |
|-----------|-----------|
| S7 online nhưng cron TikTok đang chạy | **Security Code từ S7** (Section 2) $\rightarrow$ sau đó **Bật 2FA Authenticator** (Section 3) |
| S7 online và không có cron nào | Google Prompt ADB (Tuân thủ Section 4) $\rightarrow$ sau đó **Bật 2FA Authenticator** |
| S7 offline / mất nguồn | Recovery Email $\rightarrow$ sau đó **Bật 2FA Authenticator** |
| Đã bật 2FA Authenticator | Đăng nhập trực tiếp bằng `pyotp.TOTP(secret).now()`, bỏ qua hoàn toàn S7 |

---

## 6. Toàn Diện 9 Handlers Bắt Buộc Của Vòng Lặp Google Cloud OAuth / Antigravity Trên GPM (Verified 2026-09-08)

Khi cấp quyền OAuth ứng dụng cấp cao (Antigravity, Google Cloud Native App) trên profile GPM (kể cả khi profile đã có cookie `myaccount.google.com` sống), Google xếp luồng này vào diện **Hành động nhạy cảm (Sensitive Action)**. Vòng lặp Playwright BẮT BUỘC phải bọc đủ các handlers:
1. Account Chooser Handler
2. Password Re-auth Handler
3. TOTP 2FA Handler (Phần mềm)
4. Recovery Email Handler
5. Phone / SMS Challenge Handler (`challenge/iap` - Chặn `next_btn` rỗng, click *"Thử cách khác"* sang Prompt/Security Code)
6. Google Prompt S7 Handler (`challenge/dp` - 2 Phase)
7. Offline Security Code S7 Handler (`challenge/ootp` - 10 số)
8. Google Sensitive Action Gate (Cooldown 7 ngày / `rrk=77` - Fail-fast ngắt vòng lặp)
9. Consent Screen Handler (Cấp quyền OAuth, bắt callback code)

---

## 7. Quy Tắc Vận Hành Nạp OAuth Song Song & Ứng Phó reCAPTCHA (Kinh Nghiệm Thực Chiến 2026-09-06)

### A. Chiến Lược Scale Song Song Đa Worker:
- Cấm song song cùng 1 máy S7 (tranh chấp Device Lock).
- Cho phép song song khác máy (3-4 Workers), mỗi worker 1 profile GPM + 1 serial S7 + 1 proxy port riêng biệt.

### B. Xử Lý reCAPTCHA Enterprise:
- Tự động click checkbox `#recaptcha-anchor`.
- Nếu Google bật puzzle hình ảnh: DỪNG RETRY NGAY, cho IP hạ nhiệt 2-3 tiếng hoặc xử lý thủ công, chuyển sang tài khoản sạch kế tiếp.

### C. Khóa Xoay Màn Hình Dọc S7:
- `adb -s <serial> shell settings put system user_rotation 0` trước khi mở Settings S7.

---

## 8. Quy Chuẩn Quản Lý Thiết Bị S7 & Vòng Đời Tài Khoản (Device Lifecycle & Checkpoint Safety)

### A. Quy Tắc Gán Proxy & Thiết Bị S7 (1-S7 Multi-Account & Exact Port Binding):
- **Quan hệ N:1**: Một máy điện thoại Samsung S7 và một cổng proxy 4G vật lý (ví dụ cổng 5104..5140) có thể quản lý **nhiều tài khoản Gmail** sinh ra từ các đợt đăng ký khác nhau (chu kỳ reg 10 ngày/acc).
- **Exact Origin Binding**: Gmail nào được reg từ máy S7 nào và cổng proxy nào thì khi mở GPM Profile, khi duyệt Google Prompt trên S7, khi lấy mã bảo mật, hay khi gán proxy cố định trong OmniRoute BẮT BUỘC phải map chuẩn xác đúng serial máy S7 và đúng cổng proxy gốc đó. CẤM gán chéo máy hay fallback direct IP.

### B. Vòng Đời Tài Khoản & Offboarding Cuốn Chiếu Khỏi Thiết Bị S7:
- **Giới hạn phần cứng S7**: Samsung S7 (4GB RAM) chỉ nên giữ tối đa **3 đến 5 tài khoản Google active** cùng lúc. Giữ vĩnh viễn hàng chục acc sẽ gây tràn RAM, nóng pin, crash Google Play Services ngầm và kích hoạt cờ *Google Device Farm Abuse* (khiến máy bị triệt sản không bao giờ reg được mail mới nữa).
- **CẤM gỡ bỏ tài khoản ngay sau khi đưa lên GPM**: Google nhận diện hành vi vừa tạo acc xong xóa máy ngay là "Device Churn" và sẽ khóa acc đòi SMS.
- **Tiêu chuẩn đủ điều kiện gỡ khỏi S7**:
  1. Đã bật **2FA Google Authenticator** (đã lưu Secret Key 32 ký tự vào Excel, tự sinh OTP độc lập bằng `pyotp`).
  2. Đã nạp thành công **OAuth Antigravity vào OmniRoute** (đã giữ Refresh Token vĩnh viễn).
  3. Đã được ngâm đăng nhập ổn định trên Profile GPM tối thiểu **20 đến 30 ngày** (trình duyệt GPM đã thành Trusted Device).
- **Quy trình gỡ cuốn chiếu**:
  - Khi máy S7 chuẩn bị nạp acc thứ 4 hoặc thứ 5: Thực hiện gỡ bỏ tài khoản CŨ NHẤT (acc đã reg > 30 ngày trước).
  - Thao tác gỡ BẮT BUỘC thực hiện **trực tiếp trong Settings của S7**: `Cài đặt -> Tài khoản -> Google -> [Chọn tài khoản] -> Xóa tài khoản khỏi thiết bị này` (hoặc lệnh ADB).
  - **CẤM TUYỆT ĐỐI**: Không bao giờ vào `myaccount.google.com/device-activity` trên máy tính để bấm "Đăng xuất thiết bị này". Đăng xuất từ xa qua web là nguyên nhân trực tiếp kích hoạt Sensitive Action Protection và lỗi cấm 7 ngày `signin/rejected?rrk=77`.

### C. Phân Biệt Checkpoint Đòi SMS (`challenge/iap`) vs Quét Mã/Prompt S7 & Kỹ Thuật Thoát Bằng 'Thử Cách Khác':
- **Hiện tượng**: Google chuyển sang URL `https://accounts.google.com/v3/signin/challenge/iap` với thông báo *"Xác minh danh tính của bạn. Có điều bất thường về hoạt động của bạn..."* hoặc *"Nhập số điện thoại để nhận tin nhắn văn bản cùng mã xác minh"*.
- **Bản chất**: Đây là **Google Phone SMS Checkpoint** đòi số điện thoại nhận mã OTP SMS, KHÔNG PHẢI quét mã hay prompt S7.
- **Tình trạng tài khoản**: **TÀI KHOẢN VẪN SỐNG 100%**, hoàn toàn không bị Disabled/Banned. Trên máy S7 tài khoản vẫn hoạt động bình thường.
- **Kỹ thuật Thoát SMS Checkpoint bằng nút 'Thử cách khác' (Try another way)**:
  - Khi màn hình đòi nhập SĐT xuất hiện, Google thường có nút / liên kết *"Thử cách khác"* (`Try another way`) ở góc dưới.
  - **CẠM BẪY CHẾT NGƯỜI CỦA `next_btn`**: Nếu bộ nhận diện nút "Tiếp theo" chung không kiểm tra loại trừ trường input điện thoại (`input[type="tel"]`, `input#phoneNumberId`), script sẽ tự động bấm "Tiếp theo" khi input số điện thoại đang trống $\rightarrow$ Google báo lỗi đỏ "Nhập số điện thoại" và kẹt vòng lặp liên tục bấm Next suốt 180s cho đến khi bị TIMEOUT.
  - **Quy trình xử lý chuẩn trong Playwright loop**:
    1. Kiểm tra màn hình phone challenge (`challenge/iap` hoặc từ khóa *"nhập số điện thoại"*, *"tin nhắn văn bản cùng mã xác minh"*, *"số điện thoại để nhận"*).
    2. Chặn `next_btn` không được bấm tiếp tục khi input điện thoại xuất hiện hoặc khi đang ở URL/màn hình phone challenge.
    3. Tìm và click nút *"Thử cách khác"* (`button:has-text("Thử cách khác"), button:has-text("Try another way"), a:has-text("Thử cách khác"), a:has-text("Try another way"), div[role="button"]:has-text("Thử cách khác")`).
    4. **CẠM BẪY VÒNG LẶP 'THỬ CÁCH KHÁC' (Looping Try-Another-Way)**: Google có thể hiển thị lại chính màn hình SMS hoặc trang `challenge/selection` vẫn chứa từ khóa SMS. Nếu không đếm số lần click `try_another_attempts` (giới hạn tối đa 2 lần), script sẽ bấm nút này liên tục mỗi 4s cho đến khi hết 180s timeout. BẮT BUỘC có biến đếm `try_another_attempts`: nếu bấm quá 2 lần mà URL vẫn là `challenge/iap` hoặc không thoát khỏi màn hình SMS, coi như **Hard SMS Checkpoint**, chụp screenshot và abort ngay lập tức (`return {"status": "SMS_CHECKPOINT"}`).
    5. Trình duyệt sẽ chuyển hướng về màn hình chọn phương thức (`challenge/selection`) để kích hoạt Google Prompt S7 (Phase 1/2) hoặc Mã bảo mật 10 số offline (`challenge/ootp`).
    6. Chỉ khi thực sự **KHÔNG CÓ** nút "Thử cách khác" hoặc đã thử 2 lần không đổi màn hình, mới xác định là Hard SMS Checkpoint, chụp debug screenshot và trả về `status: "SMS_CHECKPOINT"`.
- **Quy tắc ứng phó khi Hard SMS Checkpoint**:
  1. Đánh dấu `CHECKPOINT` vào file `gmail_clean_v2.xlsx` và `oauth_pipeline_status.json`.
  2. **KỆ NÓ - CẤM CHẠY NUÔI PROFILE TRONG THỜI GIAN NÀY**: Profile GPM thực chất chưa có cookie đăng nhập thành công. Cố tình mở profile lên chỉ thấy màn hình đòi xác minh, làm tăng Suspicious Score. Trên S7, tài khoản vẫn đang tự đồng bộ ngầm và được "nuôi" sạch tự nhiên.
  3. **Cơ chế nhả Checkpoint sau 3–7 ngày**: Sau thời gian ngâm (cool-down), khi IP proxy 4G đổi dải sạch, Google thường tự động hạ cấp checkpoint từ đòi SĐT về xác nhận thông báo Google Prompt trên S7, giúp giải mở khóa tự động qua ADB mà không tốn chi phí thuê SIM.

### D. Hot-Session OAuth Hook Liền Tay Ngay Sau Khi Bật 2FA (Chống Checkpoint & Bỏ Qua Đăng Nhập Lại):
- **Cạm bẫy đóng trình duyệt**: Sau khi đăng nhập và bật 2FA thành công trên GPM, nếu đóng profile rồi sau đó mới mở lại để nạp OAuth: phiên đăng nhập (session) bị gián đoạn, IP proxy có thể bị reset -> Google phát hiện mở lại từ đầu nên kích hoạt cơ chế bảo vệ danh tính đòi SĐT (`challenge/iap`).
- **Cơ chế Hot-Session Hook (`scripts/hot_session_oauth.py`)**:
  1. Giữ nguyên Playwright `page` đang mở trực tiếp từ GPM Profile ngay sau khi vừa xác nhận 2FA Authenticator thành công (cookie xác thực `SID`, `SSID`, `HSID` đang ở trạng thái tươi nhất, điểm rủi ro bằng 0).
  2. Điều hướng thẳng tới URL Authorize của OmniRoute: `page.goto(f"{OMNI_BASE}/api/oauth/antigravity/authorize?redirect_uri={OMNI_BASE}/callback")`.
  3. Google nhận diện phiên vừa xác thực xong: chỉ hiện bảng Account Chooser và nút *"Cho phép / Tiếp tục"*, **bấm 1 click là lấy được token mà không bao giờ bị hỏi lại mật khẩu hay bắt checkpoint SĐT**.
  4. Lắng nghe network bắt `code=`, gửi POST `/api/oauth/antigravity/exchange` lấy Connection ID (`cid`).
  5. Gọi API gán cố định Proxy 1:1 theo Port của máy (`PUT /api/settings/proxies/assignments`), gọi sync-models (`POST /api/providers/{cid}/sync-models`), và append vào đuôi combo `ag-gemini-pool-3` (bảo toàn nguyên vẹn 100% tên combo).

### E. Cơ Chế Preflight Rolling Cleanup Tự Động Trước Khi Reg (`scripts/preflight_s7_rolling_cleanup.py`):
- **Ngưỡng trần phần cứng & An toàn**: Khóa cứng tối đa **5 tài khoản Google / máy Samsung S7** (4GB RAM). Duy trì 5 acc vừa tối ưu hiệu năng máy vừa cho phép acc được "ngâm" trên S7 tới 40–50 ngày (với nhịp 10 ngày reg 1 acc).
- **Trích xuất tài khoản siêu tốc qua ADB**:
  - Dùng lệnh: `adb -s <serial> shell dumpsys account`
  - Regex: `r"Account\s*\{\s*name=([^,\s]+),\s*type=com\.google\s*\}"`
  - Chạy mất 0.2s ($O(1)$), không cần bật màn hình, không cần mở app hay cài đặt.
- **Quy trình 3 Safety Gates đánh giá gỡ cuốn chiếu**:
  - Khi số tài khoản trên máy `< 5`: Cho phép reg bình thường (`can_reg = True, action = "NONE"`).
  - Khi số tài khoản trên máy $\ge 5$: Kích hoạt thẩm định 3 Safety Gates:
    1. **Gate 1 (2FA Secret)**: Đã cài 2FA Google Authenticator (có Secret Key $\ge$ 16 ký tự trong Excel).
    2. **Gate 2 (OAuth OmniRoute)**: Đã nạp thành công OAuth OmniRoute (`omniroute_success`).
    3. **Gate 3 (Tuổi ngâm GPM $\ge$ 30 ngày)**: Ngày tạo/ngày login trên GPM $\ge$ 30 ngày so với hiện tại.
  - **Quy tắc gỡ an toàn**:
    - Chỉ gỡ **duy nhất 1 acc cũ nhất** thỏa mãn cả 3 Gates bằng lệnh hệ thống trên điện thoại (Settings -> Accounts qua ADB). **CẤM TUYỆT ĐỐI** gỡ qua web `myaccount.google.com/device-activity`.
    - Nếu máy đã chạm 5 acc nhưng **chưa có acc nào đủ 30 ngày**: Chặn đứng lệnh gỡ và bỏ qua máy (`can_reg = False, action = "SKIP"`), tuyệt đối không gỡ non làm mất trust tài khoản.
- **Tích hợp Preflight vào Runner `gmail_reg_v10.py` & Cơ chế Bảo Toàn Lock (`skip_lock=True`)**:
  - **Điểm tích hợp**: Hook trực tiếp vào `gmail_reg_v10.py` ngay sau bước kiểm tra proxy/VPN preflight và trước khi vào vòng lặp reg (`run_s7_rolling_cleanup_preflight(device, stt, dry_run=dry_run, skip_lock=True)`). Đường dẫn import sử dụng dynamic path lookup qua `GPM_AUTO_SCRIPTS_DIR` và `PROJECT_ROOT`, không hardcode đường dẫn tuyệt đối Windows `D:\...`.
  - **Cờ điều khiển**: Hỗ trợ cờ `--skip-s7-cleanup` trên CLI để bypass kiểm tra khi cần thiết.
  - **Safe Skip Chuẩn (`device_lock.finish(succeeded=True)`)**: Khi máy đầy 5 acc và chưa có acc nào thỏa mãn 3 Gates (`FULL_NO_ELIGIBLE_CLEANUP`), script gọi `device_lock.finish(succeeded=True)` và thoát mã 0 an toàn (`sys.exit(0)`). Gọi `finish(succeeded=True)` giúp giải phóng và dọn dẹp sạch sẽ reservation lock mà không để lại file lock mồ côi làm kẹt máy ở các chu kỳ sau, đồng thời không kích hoạt retry lỗi.
  - **Fail-Closed Khi Gặp Exception**: Nếu hàm preflight cleanup gặp ngoại lệ không xác định (`_ce`), BẮT BUỘC ghi log lỗi và fail-closed với `device_lock.finish(succeeded=False, failure_status="handoff")` kèm `sys.exit(1)`. CẤM nuốt ngoại lệ thành warning vì sẽ làm máy đang quá tải tiếp tục bị ép reg mới.
  - **CẠM BẪY MẤT DEVICE LOCK (`skip_lock=True`)**:
    + Nếu hàm gỡ tài khoản `remove_account_adb` tự tiện gọi `with acquire_device_lock(..., force_preempt=True):` trong khi tiến trình cha `gmail_reg_v10.py` đang giữ lock, thì khi khối `with` kết thúc, context manager con sẽ giải phóng (release) lock trên thiết bị.
    + Hệ quả: Runner cha tiếp tục chạy các bước mở app Gmail và reg mà không còn quyền giữ lock độc quyền, dễ bị watchdog hoặc các runner khác giẫm lên.
    + **Giải pháp bắt buộc**: Dùng `lock_ctx = nullcontext() if skip_lock else acquire_device_lock(...)`. Khi gọi từ runner đã giữ lock, truyền tường minh `skip_lock=True` để bảo toàn lock cha.
  - **Tàn Dư Tên Biến ViChanger**: Trong `gmail_reg_v10.py`, toàn bộ tên biến và log `VICHANGER_PROXY_MAPPING_PATH`, `VICHANGER_SERIAL_HEADERS`, `[vichanger-preflight]` đã được chuẩn hóa đồng bộ sang `FARM_PROXY_MAPPING_PATH`, `FARM_SERIAL_HEADERS`, và `[proxy-preflight]`. Farm đã dẹp 100% ViChanger (chạy proxy thuần WiFi/Aruba + Global ADB Proxy `set_proxy_farm_adb.py`), tuyệt đối không hiểu nhầm là app ViChanger đang chạy.

---

## 9. Quy Chuẩn BẮT BUỘC: Canonical Full Pipeline 3 Bước Khép Kín (Login S7 -> Bật 2FA -> Hot-Session OAuth)
*(Theo chỉ đạo trực tiếp của người dùng khi nạp tài khoản Farm lên OmniRoute)*
- **Nguyên tắc tuyệt đối**: CẤM nhảy cóc vào thẳng OAuth URL của OmniRoute khi tài khoản chưa được bật 2FA Authenticator. Việc nhảy cóc vào action nhạy cảm trên browser mới sẽ kích hoạt cơ chế bảo vệ nhạy cảm của Google (`signin/rejected?rrk=77` - *"Thêm tính năng Xác minh 2 bước trong phần cài đặt rồi thử lại sau 7 ngày"*).
- **Trình tự 3 Bước Bắt Buộc**:
  1. **Bước 1: Đăng nhập GPM + Vượt phần cứng Samsung S7**:
     - Mở profile GPM qua Proxy 1:1 của máy (Singbox local port).
     - Điền Email, Mật khẩu. Nếu gặp reCAPTCHA: gọi ngay `solve_recaptcha_audio(page)` bằng speech-to-text/ffmpeg để giải tự động, cấm chỉ click checkbox rồi đợi dẫn đến timeout.
     - Vượt thử thách phần cứng S7 qua ADB:
       + *Google Prompt (`challenge/dp`)*: Duyệt 2 phase (bấm "Có" -> chờ màn hình Phase 2 chọn đúng số PIN PC hiển thị).
       + *Mã bảo mật 10 số (`challenge/ootp`)*: Mở `Settings -> Google -> Quản lý tài khoản -> Bảo mật -> Mã bảo mật` trên S7 qua ADB để trích xuất mã 10 số.
  2. **Bước 2: Bật 2FA Google Authenticator & Lưu 2 Excel**:
     - Điều hướng tới `https://myaccount.google.com/two-step-verification/authenticator`.
     - Bấm Thiết lập -> "Không thể quét mã?" -> Trích xuất chuỗi Base32 Secret Key (32 ký tự).
     - Tính `pyotp.TOTP(secret_key).now()`, điền mã 6 số xác nhận hoàn tất kích hoạt.
     - Lưu ngay Secret Key vào cả 2 file Excel: `master_gmail_manager.xlsx` (sheet `Kibe_Farm_S7`, cột 2FA) và `gmail_clean_v2.xlsx` (cột `2fa`).
  3. **Bước 3: Hot-Session OAuth OmniRoute + Gán Proxy + Append Combo**:
     - **GIỮ NGUYÊN tab browser đang login nóng** (CẤM đóng trình duyệt).
     - Điều hướng sang Authorize URL Antigravity (`/api/oauth/antigravity/authorize`).
     - Bấm "Cho phép / Continue" (1 click, không bị hỏi lại pass hay SMS).
     - Lắng nghe `on_request` bắt `code=`, gửi POST `/api/oauth/antigravity/exchange` lấy Connection ID (`cid`).
     - Gán Proxy ID 1:1 (`PUT /api/settings/proxies/assignments`), gọi `POST /api/providers/{cid}/sync-models`.
     - Append vào đuôi combo `ag-gemini-pool-3` (CẤM đổi tên combo).

---

## 10. Bẫy TIMEOUT Im Lặng: Màn Hình "Thêm Tính Năng Xác Minh 2 Bước" Chưa Có Handler (2026-09-08)

### Hiện tượng:
- Chạy `process_account` cho một máy (vd: M29 `chauuyen02072005@gmail.com`, Port 5135) → kết quả trả về `TIMEOUT` sau đúng 180s.
- Log đến đúng bước `Click chọn tài khoản`, rồi im lặng 3 phút rồi timeout.
- Debug screenshot tại `D:\Taadaa\GPM auto\debug_screenshots\oauth_<email>_timeout_<ts>.png` hiện trang tiêu đề **"Thêm tính năng Xác minh 2 bước"**.

### Nguyên nhân gốc rễ:
- Google phát hiện GPM Playwright browser environment là môi trường đáng ngờ (profile mới, proxy 4G, headless-like fingerprint) → **chặn hoàn toàn OAuth flow** bằng trang đặc biệt yêu cầu bật 2SV trước.
- Trang này **khác hoàn toàn với `rrk=77`**: Không redirect tới `signin/rejected`, mà ở ngay trong flow tài khoản với 2 nút: **"Thêm tính năng Xác minh 2 bước"** (Primary, xanh) và **"Quay lại"** (Secondary).
- Pipeline `run_oauth_s7_pipeline.py` (vòng lặp 8 handlers) **không có handler nào** cho màn hình này → vòng lặp quay vô hạn đến khi timeout 180s.

### Cách nhận diện nhanh:
```python
# Check trong body text khi loop bị kẹt
body = page.inner_text("body").lower()
if "thêm tính năng xác minh 2 bước" in body or "add 2-step verification" in body:
    logger.warning(f"[M{mid:02d}] 🚫 Bị chặn bởi màn hình 'Thêm 2SV' — account cần warm-up trước!")
```

### Fix cần thêm vào pipeline (Handler thứ 9):
```python
# Thêm vào đầu vòng lặp while, TRƯỚC các handler khác
add_2sv_body = safe_body_text(page)
if ("thêm tính năng xác minh 2 bước" in add_2sv_body.lower()
        or "add 2-step verification" in add_2sv_body.lower()):
    # Không phải rrk=77 (không có redirect), đây là trang bảo mật trực tiếp
    # Click "Quay lại" để thoát và thử approach khác
    back_btn = page.locator('button:has-text("Quay lại"), a:has-text("Quay lại"), button:has-text("Back")').first
    if back_btn.count() > 0 and back_btn.is_visible():
        logger.warning(f"[M{mid:02d}] 🚫 Màn hình 'Thêm 2SV' — bấm Quay lại...")
        back_btn.click()
        time.sleep(3)
        continue
    else:
        # Không tìm thấy nút Quay lại → fail-fast, không lãng phí 180s timeout
        logger.error(f"[M{mid:02d}] 🚫 Bị chặn 'Thêm 2SV' hoàn toàn — cần warm-up 2SV thủ công trước!")
        raise Exception("BLOCKED_ADD_2SV")
```

### Nguyên nhân sâu xa & phòng ngừa:
- Tài khoản bị màn hình này là tài khoản **chưa có 2FA** + GPM profile **chưa được warm-up** (trusted session chưa hình thành).
- **Đúng quy trình 3 bước** (Section 9): Phải đăng nhập GPM → bật 2FA trước → rồi mới chạy OAuth. Chạy thẳng OAuth trên profile mới/lạnh là sẽ bị màn hình này.
- Singbox port được tính: `20000 + (port - 5100)` khi 5000 < port < 6000. M29 port 5135 → singbox `20035`. Proxy hoạt động bình thường, không phải lỗi proxy.

### Chẩn đoán TIMEOUT nhanh (checklist theo thứ tự):
1. Đọc debug screenshot → Google hiện trang gì?
2. `"thêm tính năng xác minh 2 bước"` → Handler thiếu, cần warm-up 2FA trước.
3. `"nhập mật khẩu" / password field` → profile cookie cũ, cần re-auth.
4. `"reCAPTCHA"` → IP bị flag, cần hạ nhiệt.
5. `"challenge/iap"` → SMS checkpoint, ngâm 3-7 ngày.
6. Màn hình trống / home screen S7 → flow chưa trigger đúng device.

---

## 11. Cạm Bẫy `ERR_CONNECTION_RESET` Khi Chụp Ảnh Callback Qua Proxy 4G & Quy Chuẩn Nghiệm Thu Proof Bắt Buộc (User Approved 2026-09-08)
- **Hiện tượng**: Sau khi nạp OAuth thành công, ảnh chụp trình duyệt trên tab callback hiện `ERR_CONNECTION_RESET` hoặc `HTTP ERROR 502` (*"Không thể truy cập trang web này / 127.0.0.1 không thể xử lý yêu cầu"*). Người dùng nhìn vào sẽ đánh giá là lỗi (*"Này ảnh lỗi r, do oauth xong link bị lỗi"*).
- **Bản chất kỹ thuật**: Trình duyệt đang chạy qua proxy 4G Mobifone của Farm (`192.168.110.2:200xx`). Khi Google redirect về `http://127.0.0.1:20129/callback`, proxy 4G bên ngoài không thể kết nối ngược về `127.0.0.1` của host PC $\rightarrow$ Chrome báo `ERR_CONNECTION_RESET` / `HTTP 502`. Tuy nhiên mã `code=` đã được script bắt thành công qua network listener `on_request` từ trước và token đã nạp xong vào OmniRoute.
- **QUY CHUẨN NGHIỆM THU PROOF BẮT BUỘC (User Directive 2026-09-08 — Đã nghiệm thu "Chuẩn rồi, sau cứ chụp thế này")**:
  1. **Proof OAuth OmniRoute (Tiêu chuẩn số 1)**:
     - Dùng Playwright/Chrome mở thẳng URL quản trị nội bộ: `http://127.0.0.1:20129/dashboard/providers/antigravity`.
     - **BẮT BUỘC CUỘN XUỐNG ĐÁY DANH SÁCH (Bottom of account list)**:
       - Danh sách tài khoản trong OmniRoute sắp xếp theo thứ tự thêm vào; tài khoản mới nhất LUÔN nằm ở cuối bảng.
       - Dùng code cuộn account thứ `N-4` hoặc `N-1` vào view (ví dụ: `page.locator('text=/@/').all()[-4].scroll_into_view_if_needed()`).
       - Chụp ảnh màn hình hiển thị rõ ràng các accounts mới nhất ở cuối danh sách (chấm xanh Connected, email mask, tên proxy gán 1:1).
       - Gửi ảnh qua cú pháp `MEDIA:<path>`.
  2. **Proof 2FA (Tiêu chuẩn số 2 — khi có task bật 2FA)**:
     - Chụp ảnh màn hình trình duyệt GPM profile ngay sau khi vừa hoàn tất xác minh kích hoạt 2FA Google Authenticator thành công (hiển thị popup Secret Key hoặc dòng chữ xác thực Authenticator đã bật).
  3. **CẤM TUYỆT ĐỐI**:
     - CẤM gửi ảnh màn hình tab callback bị `ERR_CONNECTION_RESET` / `HTTP 502`.
     - CẤM gửi ảnh chụp màn hình điện thoại Samsung S7 làm proof nạp GPM/OAuth.
     - CẤM chụp lửng lơ ở đầu danh sách OmniRoute mà không cuộn xuống các account mới nhất ở cuối.

---

## 12. Cạm Bẫy Trích Xuất Target PIN Trên PC & Cơ Chế Multi-Prompt Throttle (Kinh Nghiệm Thực Chiến 2026-09-08)

### A. Trích xuất Target PIN: Thẻ DOM `<strong>`/`<b>` thay vì Regex text thuần:
- **Hiện tượng**: Regex `re.search(r'(?:nhấn vào|chọn|tap|số|number)\s*(\d{1,2})', safe_body_text(page))` dễ trích xuất sai hoặc bắt nhầm chuỗi khác (ví dụ OCR/text bị nhầm số 91 trong khi PIN thật là 3) khi cấu trúc text của Google Prompt thay đổi hoặc ngôn ngữ có dấu.
- **Bản chất**: Trên giao diện Google Prompt (`challenge/dp`), Google **LUÔN LUÔN bọc số PIN trong thẻ `<strong>` hoặc `<b>`** bên trong `div[role="main"]` (ví dụ `<strong>3</strong>`).
- **Giải pháp chuẩn**:
  ```python
  target_pin = None
  # 1. Quét trực tiếp qua DOM locator cho thẻ strong / b
  for tag in ["strong", "b"]:
      elems = page.locator(f'div[role="main"] {tag}, {tag}').all()
      for el in elems:
          try:
              txt = el.inner_text().strip()
              if txt.isdigit() and 1 <= len(txt) <= 2:
                  target_pin = txt
                  break
          except Exception:
              pass
      if target_pin:
          break

  # 2. Fallback regex nếu không tìm thấy qua thẻ
  if not target_pin:
      pin_match = re.search(r'(?:nhấn vào|rồi nhấn vào|chọn|tap|số|number)\s*(\d{1,2})', safe_body_text(page), re.I)
      target_pin = pin_match.group(1) if pin_match else None
  ```

### B. Cơ Chế Multi-Prompt & Throttle Tránh Kẹt Vĩnh Viễn Cờ `prompt_approved = True`:
- **Bẫy cờ đơn phát (Single-shot boolean)**:
  - Nếu dùng biến boolean `prompt_approved = True` sau lần approve đầu tiên: script sẽ **CẤM DUYỆT LẠI** trong toàn bộ vòng lặp còn lại.
  - Tuy nhiên, Google thường xuyên:
    1. Yêu cầu xác minh 2 lần liên tiếp (ví dụ M61: vừa chọn xong PIN 58 thì Google lập tức hiển thị prompt tiếp theo đòi PIN 62).
    2. Hoặc tín hiệu duyệt từ điện thoại bị trễ/mất gói khiến màn hình PC vẫn ở lại `challenge/dp`.
  - Cờ `prompt_approved = True` khiến script bỏ qua nhánh duyệt prompt ở các vòng lặp sau, dẫn đến timeout 180s.
- **Quy tắc Throttle chuẩn**:
  - Khởi tạo `last_prompt_t = 0`.
  - Điều kiện duyệt: `is_dp and (time.time() - last_prompt_t > 10)`.
  - Khi bắt đầu approve: cập nhật `last_prompt_t = time.time()`.
  - Điều này cho phép:
    + Ngăn spam ADB liên tục trong 1 chu kỳ xử lý (giãn cách tối thiểu 10s giữa các lần bấm).
    + Tự động retry hoặc xử lý multi-prompt liền mạch nếu sau 10s trình duyệt vẫn hiển thị thử thách `challenge/dp`.

---

## 13. Cơ Chế Incremental Append Combo & Giới Hạn Batch Subagent (Kinh Nghiệm Thực Chiến 2026-09-08)
- **Incremental Append Ngay Khi Xong Mỗi Acc**: Không gom danh sách chờ hết toàn bộ batch mới gọi `append_connections`. Khi `process_account` trả về `SUCCESS` / `ALREADY_SUCCESS`, lập tức gọi `append_connections([{"cid": cid, "email": email, "port": port}])` ngay tại chỗ. Nếu tài khoản sau bị timeout hay kẹt reCAPTCHA, các tài khoản trước đã vào combo an toàn.
- **Batch Size An Toàn Cho Subagent (1-2 Accs/Subagent)**: Do mỗi tài khoản xử lý qua proxy 4G + duyệt S7 + giải captcha mất 1.5 - 3 phút, một batch 4 tài khoản nối tiếp dễ chạm trần timeout 600s của subagent runtime. Ưu tiên dispatch subagent chạy 1-2 tài khoản/lượt để phản hồi nhanh, cập nhật tiến độ liên tục và tránh timeout lãng phí.

---

## 14. Cạm Bẫy Pointer Intercept Khi Giải reCAPTCHA Playwright & Cơ Chế Bỏ Qua Anchor Vào Thẳng bframe (Kinh Nghiệm Thực Chiến 2026-09-08)

### Hiện tượng:
- Khi Google hiện reCAPTCHA checkbox ("Tôi không phải là người máy"), pipeline gọi `solve_recaptcha_audio(page)`.
- Playwright bị treo 30s rồi throw:
  ```
  Locator.click: Timeout 30000ms exceeded.
  Call log:
    - waiting for locator("#recaptcha-anchor, .recaptcha-checkbox").first
    ...
    - <div></div> from <div>…</div> subtree intercepts pointer events
  ```
- Script lặp lại 2-4 lần thử giải captcha, mỗi lần mất 30s timeout $\rightarrow$ cạn sạch 180s thời gian chờ OAuth $\rightarrow$ `TIMEOUT` và thất bại không lấy được token.

### Nguyên nhân gốc rễ:
1. **Anchor đã click hoặc đang loading**: Khi pipeline chính đã click anchor checkbox một lần, checkbox chuyển sang trạng thái `recaptcha-checkbox-loading` hoặc `aria-disabled="true"`.
2. **Popup challenge `bframe` đã mở đè lên**: Khi popup chọn hình/audio đã pop up, Google chèn một lớp overlay/backdrop toàn phần đè lên anchor. Playwright kiểm tra actionability trước khi click nên từ chối click vào `#recaptcha-anchor` và chờ suốt 30 giây cho đến khi timeout.
3. **Bẫy lặp lại từ đầu trong `solve_recaptcha_audio`**: Hàm solver luôn quét tìm `anchor_frame` trước rồi gọi `anchor_btn.first.click()`, bất kể `bframe` đã hiện hay chưa.

### Quy tắc chuẩn & Code Fix:
1. **Kiểm tra `bframe` trước**: Nếu trong `page.frames` đã có `bframe` (url chứa `enterprise/bframe` hoặc `api2/bframe`) và audio button hiển thị $\rightarrow$ **CẤM** click lại `#recaptcha-anchor`. Nhảy thẳng vào giải audio challenge!
2. **Click anchor an toàn**: Nếu bắt buộc click anchor:
   - Kiểm tra `aria-checked == "true"` thì `return True` ngay.
   - Thêm `force=True` và `timeout=3000`. Bọc trong `try / except` riêng để nếu bị intercept cũng không crash toàn bộ luồng solver mà chuyển tiếp sang bước kiểm tra `bframe`.
```python
# Mẫu triển khai an toàn trong solve_recaptcha_audio:
# 1. Quét tìm frames
anchor_frame = next((f for f in page.frames if "anchor" in f.url and "recaptcha" in f.url), None)
bframe = next((f for f in page.frames if "bframe" in f.url and "recaptcha" in f.url), None)

# 2. Nếu chưa có bframe, mới click anchor (dùng force=True và timeout ngắn)
if not bframe and anchor_frame:
    try:
        anchor_btn = anchor_frame.locator("#recaptcha-anchor, .recaptcha-checkbox")
        if anchor_btn.count() > 0 and anchor_btn.first.get_attribute("aria-checked") != "true":
            anchor_btn.first.click(timeout=3000, force=True)
            time.sleep(2)
    except Exception as e:
        logger.warning(f"Click anchor warning (bỏ qua nếu bframe mở): {e}")

# 3. Quét lại bframe để giải audio challenge nếu chưa có
# ...
```

---

## 15. Quy Chuẩn Đặt Tên Profile GPM Gom Cụm Theo Máy - Port - Email (User Directive 2026-09-08)

### Yêu cầu & Mục đích:
- User yêu cầu: Profile GPM cần xếp theo kiểu gom cụm chung 1 port/máy, chỉ khác email đang đăng nhập:
  `M01 - 5101 - mail_A@gmail.com`
  `M01 - 5101 - mail_B@gmail.com`
  `M02 - 5102 - mail_C@gmail.com`
  ...
- **Lợi ích**: Khi bấm sắp xếp (sort) theo cột **Name** trên ứng dụng GPMLogin, toàn bộ các profile chung 1 máy S7 / 1 cổng proxy sẽ tự động gom thành từng khối liền kề nhau cực kỳ ngăn nắp, dễ dàng kiểm tra đối soát $O(1)$.

### Quy chuẩn cú pháp:
- **Cú pháp bắt buộc**: `M<mid:02d> - <port> - <email>` (ví dụ: `M01 - 5101 - duongkien12022001@gmail.com`, `M49 - 5113 - chuloan02122003@gmail.com`).
- **Thực thi chuẩn hóa**:
  - File database GPM: `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db`.
  - BẮT BUỘC tạo bản sao lưu `profile_data.db.bak` trước khi cập nhật.
  - Sử dụng lệnh SQL: `UPDATE Profiles SET Name = ? WHERE Id = ?` dựa trên mapping đối soát từ `master_gmail_manager.xlsx` / `gmail_clean_v2.xlsx`.
  - Chỉ cập nhật trường `Name` hiển thị, tuyệt đối không đổi `ProfilePath` hay thư mục user data để bảo toàn nguyên vẹn 100% cookie và session đăng nhập.

---

## 16. Chiến Lược 2–3 Worker Song Song (Parallel Scale) & Cạm Bẫy Singbox Port Mapping Theo Machine ID (2026-09-08)

### A. Chiến Lược 2–3 Worker Song Song (Parallel Scale):
- **Sweet Spot (2–3 Worker)**: Tối ưu nhất là chia mẻ nạp thành 2–3 worker chạy song song qua `delegate_task(tasks=[...])`. Mỗi worker đảm nhiệm 1 tài khoản trên 1 máy S7 và 1 cổng proxy riêng biệt.
- **Rút ngắn thời gian**: Thời gian hoàn thành cả mẻ giảm từ 4–6 phút (chạy tuần tự) xuống chỉ còn ~1.5–2 phút.
- **CẤM scale quá 4–5 worker cùng lúc**: Dải mạng Farm là proxy 4G USB modem, nếu mở đồng loạt quá nhiều trình duyệt Chromium gửi request login Google trong cùng 1 giây sẽ gây nghẽn bus USB modem và kích hoạt bot-check reCAPTCHA diện rộng.

### B. Cạm Bẫy Singbox Port Mapping Theo Machine ID Trên Host `192.168.110.2`:
- **Cạm bẫy công thức cũ**: Trong một số script cũ, Singbox port bị tính nhầm theo công thức `20000 + (port - 5100)`. Công thức này chỉ đúng cho Máy 1–8 (nơi cổng proxy 5101–5108 tình cờ trùng với số máy). Từ Máy 9 trở đi, cổng proxy farm KHÔNG trùng với số máy (ví dụ: Máy 49 gắn cổng 5113, nếu tính theo `5113 - 5100 = 13` sẽ trỏ vào port `20013` bị sai hoặc đóng kết nối `WinError 10054`).
- **QUY TẮC BẮT BUỘC**:
  - Cổng local Singbox trên host `192.168.110.2` được cấu hình theo **MACHINE ID**:
    $$\text{Singbox Port} = 20000 + \text{Machine ID (mid)}$$
    *(Ví dụ: Máy 49 $\rightarrow$ `20049`, Máy 45 $\rightarrow$ `20045`, Máy 54 $\rightarrow$ `20054`, Máy 74 $\rightarrow$ `20074`)*.
  - Khi gọi `process_account(acc)`, **BẮT BUỘC** truyền tường minh trường `"singbox_port": 20000 + mid` trong dictionary `acc` để ghi đè công thức fallback.

---

## 17. Xử Lý Khóa Chrome User Data Dir Do Tiến Trình Mồ Côi Khi Subagent Bị Ngắt (Orphan Chrome Lock)

### Hiện tượng:
- Khi worker subagent bị ngắt đột ngột giữa chừng (do gateway restart, timeout, crash), tiến trình con `chrome.exe` (`gpm_browser_chromium_core_142\chrome.exe`) có thể tiếp tục sống ngầm ở chế độ mồ côi (orphan process) và giữ lock độc quyền trên thư mục profile (`user-data-dir`).
- Lần chạy tiếp theo của profile đó sẽ thất bại ngay từ giây đầu tiên:
  ```
  BrowserType.launch_persistent_context: Target page, context or browser has been closed
  ```

### Xử lý & Phòng ngừa:
- Trước khi khởi động `launch_persistent_context` cho một profile, kiểm tra xem có tiến trình Chrome nào đang trỏ vào thư mục profile đó hay không.
- Dọn dẹp an toàn tiến trình Chrome mồ côi chiếm lock bằng lệnh PowerShell lọc theo CommandLine profile path trước khi khởi tạo lại session mới.

---

## 18. Xử Lý Trạng Thái Cảnh Báo `• degraded` Trên OmniRoute Do Thiếu `projectId` (Kinh Nghiệm Thực Chiến 2026-09-08)

### Hiện tượng:
- Sau khi nạp OAuth thành công và tài khoản xuất hiện trong OmniRoute Dashboard (`:20129`), một số tài khoản bị hiện cờ cảnh báo màu đỏ/vàng: `• degraded`.
- Thông báo chi tiết: *"Connected, but the Google Cloud Code projectId could not be found..."*.

### Nguyên nhân:
- Trong quá trình trao đổi OAuth code lấy access/refresh token, Google API đôi khi trả về phản hồi không đính kèm `projectId` (giá trị rỗng `""` hoặc `None`), khiến OmniRoute không xác định được dự án Cloud Code mặc định khi chạy health check.

### Cách xử lý O(1) phục hồi xanh lá 100% (`• đã kết nối`):
1. **Cập nhật `projectId` qua API**:
   Gửi request `PUT /api/providers/{cid}` với payload:
   ```json
   {
     "projectId": "aicode-consumers",
     "providerSpecificData": {
       "clientProfile": "ide",
       "projectId": "aicode-consumers",
       "tier": "free-tier"
     }
   }
   ```
2. **Kích hoạt đồng bộ lại mô hình**:
   Gửi request `POST /api/providers/{cid}/sync-models` (nhận diện 12 models).
3. **Kết quả**: Cờ `degraded` lập tức biến mất, connection chuyển về `status: active` (`• đã kết nối` màu xanh lá) và hoạt động hoàn hảo trong combo định tuyến.

---

## 19. Kỷ Luật Vận Hành Nạp Liên Tục Gối Đầu (Continuous Pipelined Runner Policy)

### Quy định thực thi:
- Khi người dùng ra lệnh *"Làm liên tục luôn đi log cho xong luôn trừ khi lỗi lạ mới được dừng"*:
  1. **Duy trì Queue mốc vàng $O(1)$**: Coordinator chủ động rà soát danh sách tài khoản thỏa mãn 4 điều kiện:
     - Đã có 2FA Secret trong Excel.
     - Thiết bị Samsung S7 đang online.
     - Cổng proxy Singbox tương ứng (`20000 + mid`) phản hồi HTTP 200.
     - Cổng proxy chưa chạy hôm nay (quy tắc 1 port/acc/ngày).
  2. **Bắn gối đầu liên tục 2 Worker**: Ngay khi mẻ 2 worker hiện tại hoàn tất, đối soát chụp ảnh proof nghiệm thu đáy bảng OmniRoute và dispatch ngay mẻ tiếp theo mà không dừng lại chờ user nhắc.
  3. **Tiêu chuẩn Circuit Breaker dừng lại**: CHỈ dừng toàn bộ tiến trình khi gặp **Lỗi Lạ (Unfamiliar Blockers)**:
     - Checkpoint SMS hàng loạt không có nút "Thử cách khác" (Hard Checkpoint $\ge 2$ acc liên tiếp).
     - Sự cố sập mạng toàn diện (proxy Singbox không phản hồi hàng loạt).
     - Lỗi crash runtime hoặc sự thay đổi giao diện DOM mới từ Google chưa có trong 9 handlers.

---

## 20. Giới Hạn Hiển Thị 50 Accounts Trên OmniRoute Dashboard Web UI & Quy Chuẩn Đối Soát Backend API (2026-09-08)

### Hiện tượng:
- Khi tổng số tài khoản Antigravity trong OmniRoute vượt mốc 50 (ví dụ 51 đến 59+ targets), trên giao diện Web UI (`http://127.0.0.1:20129/dashboard/providers/antigravity`), danh sách phần tử DOM có thể dừng hiển thị ở account `#50` (`Total accounts on page: 50`).
- Các tài khoản từ `#51` trở đi không xuất hiện thêm ở đáy trang Web UI thông thường, dễ gây hiểu nhầm là tài khoản chưa được thêm vào hệ thống.

### Bản chất & Cơ chế:
- Web Dashboard frontend của OmniRoute có cơ chế phân trang ngầm hoặc giới hạn kích thước render danh sách (virtualized list / pagination cap = 50).
- Trong khi đó, Backend API (`/api/providers` và `/api/combos`) đã lưu trữ đầy đủ 100% các connection mới và đã append chuẩn xác vào mảng `models` của combo `ag-gemini-pool-3`.

### Quy chuẩn đối soát chuẩn xác:
1. **Kiểm chứng Backend Source of Truth**:
   - Luôn đối soát trực tiếp qua API:
     + `GET http://127.0.0.1:20129/api/providers` $\rightarrow$ kiểm tra `connection.id`, `email`, `priority` và `total` (ví dụ: `total: 55`, `total: 59`).
     + `GET http://127.0.0.1:20129/api/combos` $\rightarrow$ kiểm tra mảng `models` của combo `ag-gemini-pool-3` (ví dụ: `pool-50`, `pool-55`, `pool-59`).
2. **Kỹ thuật chụp ảnh nghiệm thu Proof**:
   - Khi chụp ảnh Dashboard OmniRoute gửi User, cuộn đến vị trí tài khoản sâu nhất hiển thị được trên UI (`#50` hoặc cuối container).
   - Trong báo cáo đính kèm, BẮT BUỘC ghi rõ số lượng targets backend thực tế và ID/email của các tài khoản mới nhất để User nắm bắt đầy đủ tiến độ.

---

## 21. Quy Trình Nâng Cấp Tier OmniRoute (Standard-Tier -> Free-Tier) Qua CodeAssist Personal ToS & Kiểm Thử Upstream Singbox (2026-09-09)

### A. Mục Đích & Nguyên Lý:
- Khi tài khoản Google Cloud Code vừa nạp OAuth vào OmniRoute, mặc định ban đầu có thể chỉ nhận diện được `tier: standard-tier` (bị bóp giới hạn tính năng / quota).
- Để nâng cấp lên **`free-tier`** (đầy đủ model và hạn mức chuẩn), tài khoản cần được kích hoạt chấp nhận điều khoản cá nhân (Personal Terms of Service - ToS) trên portal Code Assist của Google.
- **Yêu cầu môi trường**: Sử dụng Playwright Persistent Context mở trực tiếp thư mục profile GPM gốc (chứa cookie Google LSID, `user_data_dir`) kết hợp proxy Singbox 1:1 tương ứng của máy (`http://192.168.110.2:200xx`), tránh bị checkpoint IP.

### B. Quy Trình Tự Động Hóa 4 Bước:
1. **Khởi chạy Playwright Persistent Context**:
   - `executable_path`: `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\gpm_browser\gpm_browser_chromium_core_142\chrome.exe`
   - `user_data_dir`: Thư mục profile GPM tương ứng (vd: `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\<profile_id>`).
   - `proxy`: `{'server': 'http://192.168.110.2:200xx'}`.
   - `args`: `['--no-first-run', '--no-default-browser-check']`.
2. **Truy cập Code Assist & Kích hoạt ToS**:
   - Điều hướng tới `https://codeassist.google.com/?authuser=0`.
   - Tìm và click các nút chấp thuận:
     `page.locator('button:has-text("Agree"), button:has-text("Accept"), button:has-text("Get started"), button:has-text("Tiếp tục"), button:has-text("Đồng ý")')`.
   - Nếu có checkbox điều khoản: check toàn bộ `input[type="checkbox"]` trước khi submit.
3. **Kích hoạt OmniRoute Refresh & Sync Models**:
   - Gửi POST `http://localhost:20129/api/providers/{conn_id}/refresh` (payload `{}`).
   - Gửi POST `http://localhost:20129/api/providers/{conn_id}/sync-models` (payload `{}`).
4. **Đối soát Tier trong SQLite**:
   - Đọc cột `provider_specific_data` trong bảng `provider_connections` của `C:\Users\Kibe\.omniroute\storage.sqlite`.
   - Kiểm tra trường `tier`: chuyển từ `"standard-tier"` $\rightarrow$ `"free-tier"`.

### C. Cạm Bẫy Kiểm Thử Proxy Singbox (Socket Open vs Upstream Connection Reset):
- **Hiện tượng**: Kiểm tra socket TCP cổng `200xx` trên host `192.168.110.2` bằng `socket.connect_ex` trả về `0` (PORT OPEN), nhưng khi Playwright gọi `page.goto()` thì bị lỗi ngay:
  `net::ERR_CONNECTION_RESET` hoặc urllib báo `HTTP Error 502: Bad Gateway`.
- **Nguyên nhân gốc rễ**: Singbox service trên host `192.168.110.2` vẫn đang lắng nghe cổng local, nhưng modem 4G USB vật lý hoặc đường truyền WAN gắn với cổng đó bị mất kết nối / rớt mạng / chưa cấp được IP WAN từ nhà mạng.
- **Quy tắc Preflight chuẩn**:
  - Không chỉ tin cậy lệnh kiểm tra cổng socket (`connect_ex`).
  - BẮT BUỘC thực hiện probe request HTTP/HTTPS thực tế ra ngoài Internet qua proxy trước khi khởi chạy luồng ToS Playwright để tránh fail-fast hoặc timeout lãng phí.

### D. Cạm Bẫy `net::ERR_TOO_MANY_RETRIES` Với Proxy MikroTik Có Auth Trong Playwright:
- **Hiện tượng**: Khi khởi chạy Playwright `launch_persistent_context` sử dụng proxy MikroTik LAN có xác thực username/password:
  `proxy={'server': 'http://192.168.110.2:100xx', 'username': 'admin@1', 'password': 'admin@1'}`
  và truy cập `https://codeassist.google.com/?authuser=0`, trang lập tức văng lỗi:
  `Page.goto: net::ERR_TOO_MANY_RETRIES at https://codeassist.google.com/?authuser=0`.
- **Nguyên nhân kỹ thuật**:
  - Google hiện tự động redirect từ `codeassist.google.com` sang tên miền mới `https://codeassist.google/products/business`.
  - Cơ chế xử lý HTTP Basic Auth qua proxy của Playwright/Chromium khi gặp HTTP 301/302 redirect liên domain sẽ kích hoạt vòng lặp xác thực lại (Proxy-Authenticate handshake retry loop) dẫn đến `ERR_TOO_MANY_RETRIES`.
- **Giải pháp khắc phục**:
  1. **Ưu tiên dùng Singbox Proxy Port (`200xx`)**: Chuyển sang cổng Singbox tương ứng của máy (`http://192.168.110.2:200xx` với `20000 + mid`) — cổng này không yêu cầu HTTP Basic Auth, Playwright mở HTTPS tunnel trơn tru không bị loop.
  2. **Nếu bắt buộc dùng MikroTik (`100xx`)**:
     - Sử dụng argument dòng lệnh `--proxy-server="http://192.168.110.2:100xx"` kết hợp lắng nghe sự kiện `page.on("authenticate", lambda creds: creds.authenticate("admin@1", "admin@1"))` thay vì truyền dictionary `proxy={'username': ...}` trực tiếp vào Playwright launch options.
     - Hoặc điều hướng trực tiếp vào URL đích sau redirect: `https://codeassist.google/products/business` thay vì qua URL cũ.

### E. Cạm Bẫy `codeassist.google.com` Redirect Sang `/products/business` & Web ToS Modal Không Còn Khả Dụng (Thay Thế Bằng Gỡ Cờ `VALIDATION_REQUIRED`):
- **Hiện tượng**: Điều hướng vào `https://codeassist.google.com/?authuser=0` bị Google tự động redirect 302 sang `https://codeassist.google/products/business`. Trang hoàn toàn không hiển thị modal hay button chấp thuận ToS cá nhân ("Agree", "Accept", "Get started"), screenshot chỉ thấy trang landing bán gói doanh nghiệp Gemini Code Assist Standard & Enterprise.
- **Bản chất chính sách mới của Google (Từ 18/06/2026)**:
  - Thông báo chính thức trên banner của Google: *"Unpaid tier (Gemini Code Assist for individuals) and Google One users only: Gemini CLI and Gemini Code Assist IDE extensions were replaced by Antigravity CLI and Antigravity on June 18th 2026."*
  ### E. Cạm Bẫy codeassist.google.com Redirect Sang /products/business & Giải Pháp Gỡ Cờ VALIDATION_REQUIRED (Cập nhật 2026-09-14):
  - Triệu chứng: Tài khoản Antigravity nhận request nhưng 100% trả về `HTTP 403 Forbidden` (`project_route_error`), tokens_in = 0, tokens_out = 0, quota vẫn 100%.
  - Nguyên nhân gốc rễ 1 — Chưa chấp thuận Google Cloud Platform Terms of Service (GCP ToS):
    - Mở profile GPM điều hướng tới `https://console.cloud.google.com/welcome/new?pli=1`.
    - Nếu hiện modal *"I agree to the Google Cloud Platform Terms of Service..."*, tick chọn checkbox và bấm *"Agree and continue"*. Nếu không chấp thuận, mọi API Google Cloud Code / Antigravity bị chặn cứng 403 ở tầng gateway.
  - Nguyên nhân gốc rễ 2 — Dính cờ `VALIDATION_REQUIRED` trên backend:
    - Khi gọi `POST https://cloudcode-pa.googleapis.com/v1internal:loadCodeAssist`, backend trả về `ineligibleTiers` với `reasonCode: "VALIDATION_REQUIRED"`.
    - Trong payload JSON, Google cấp sẵn trường `"validationUrl": "https://accounts.google.com/signin/continue?sarp=1&scc=1&continue=...&plt=..."`.
    - Mở URL này trên tab trình duyệt GPM đang login, trang sẽ chuyển hướng đến `https://accounts.google.com/v3/signin/challenge/iap/qrcode` (*"Verify your info to continue"*).
    - Trích xuất ảnh QR code từ thẻ `img` (base64 `data:image/png;base64,...`), lưu ra file và gửi cho người dùng quét bằng Camera điện thoại (`devicephoneverification`) để gỡ cờ bảo mật.
  - Nguyên nhân gốc rễ 3 — Thiếu Proxy Assignment trong OmniRoute:
    - Kiểm tra `GET /api/settings/proxies/assignments`. Nếu tài khoản chưa có proxy gắn theo `scope: "account"`, OmniRoute sẽ route request qua proxy ngẫu nhiên của provider hoặc IP trực tiếp, kích hoạt Google Device Security Checkpoint.
    - Fix: Gọi `PUT /api/settings/proxies/assignments` với `{"scope": "account", "scopeId": connection_id, "proxyId": proxy_id}` tương ứng với port proxy của máy (ví dụ port 16002 -> proxyId M38).
  - Kích hoạt Onboard Project `aicode-consumers` cho Standard-Tier:
    - Gọi `POST https://cloudcode-pa.googleapis.com/v1internal:onboardUser` với body:
      `{"tierId": "standard-tier", "metadata": {"ideType": "ANTIGRAVITY"}}`
    - Backend Google sẽ trả về `200 OK` với `cloudaicompanionProject: {"id": "aicode-consumers"}` thành công.

---

## 22. Cạm Bẫy `ECONNREFUSED` Khi Kết Nối Playwright `connect_over_cdp` Ngay Sau `gpm.start_profile` (2026-09-09)

### Hiện tượng:
- Khi khởi động profile qua GPM Local API v3 (`gpm.start_profile(pid, skip_proxy_check=True)`), API trả về ngay lập tức dictionary chứa `remote_debugging_address` (ví dụ: `127.0.0.1:51182`).
- Nếu gọi ngay `p.chromium.connect_over_cdp(f"http://{cdp_addr}")` ở dòng tiếp theo, Playwright văng lỗi ngay lập tức:
  ```
  BrowserType.connect_over_cdp: connect ECONNREFUSED 127.0.0.1:51182
  Call log:
    - <ws preparing> retrieving websocket url from http://127.0.0.1:51182
  ```

### Nguyên nhân gốc rễ:
- GPM Local API trả về HTTP 200 ngay sau khi vừa spawn tiến trình Chrome, nhưng Chrome Chromium core cần từ 1 đến 3 giây để khởi tạo, mở socket và lắng nghe cổng remote debugging trên localhost.
- Gọi `connect_over_cdp` khi port chưa kịp listen sẽ bị OS từ chối kết nối (`ECONNREFUSED`).

### Giải pháp chuẩn (Polling Socket Retry Loop):
- **CẤM** gọi `connect_over_cdp` trực tiếp không có retry.
- Thêm vòng lặp kiểm tra socket TCP hoặc retry `connect_over_cdp` trong tối đa 10-15s:
  ```python
  import time, socket

  # Cách 1: Polling socket trước khi connect
  host, port_str = cdp_addr.split(":")
  port = int(port_str)
  for _ in range(15):
      try:
          with socket.create_connection((host, port), timeout=1):
              break
      except (OSError, ConnectionRefusedError):
          time.sleep(1)
  else:
      raise TimeoutError(f"CDP port {cdp_addr} not listening after 15s")

  # Sau đó mới connect Playwright an toàn
  browser = p.chromium.connect_over_cdp(f"http://{cdp_addr}")
  ```
- Hoặc bọc lệnh `connect_over_cdp` trong vòng lặp retry 3-5 lần với `time.sleep(1.5)`.

---

## 23. Cạm Bẫy Đa Profile GPM Trùng Email (Duplicate Profiles & Exact Port/Profile Target Selection) (2026-09-11)

### Hiện tượng & Cạm bẫy:
- Một tài khoản Gmail (ví dụ: `alicelmoralesjvcrj@gmail.com`) có thể tồn tại **nhiều profile GPM** khác nhau trong `profile_data.db` (do các đợt chạy hoặc tạo profile cũ).
  - Ví dụ thực tế:
    - Profile CŨ: `Name = '11 - alicelmoralesjvcrj@gmail.com - 5113'`, `ProfilePath = 'z6BJ3AVtw5-05092026'` (gắn cổng 5113 cũ).
    - Profile MỚI / ĐÚNG PORT: `Name = '10020 - alicelmoralesjvcrj@gmail.com - 10020'`, `ProfilePath = '11-8801315697361_vdvbm'` (gắn cổng 10020).
- Nếu script truy vấn DB dạng `WHERE Name LIKE '%{email}%'` mà không lọc thêm điều kiện Port hoặc `ORDER BY CreatedAt/UpdatedAt DESC` (hoặc chỉ lấy dòng đầu tiên `fetchone()`):
  $\rightarrow$ Script sẽ nhặt nhầm Profile CŨ (`5113`), nạp sai proxy hoặc phiên đăng nhập không đúng, làm hỏng mapping và thất bại khi re-auth OAuth.

### Quy tắc chuẩn truy vấn & chỉ định Profile:
1. **Ưu tiên mapping cứng theo Port / Chỉ đạo người dùng**:
   Khi user hoặc cấu hình chỉ định rõ port (vd: Port `10020`):
   ```sql
   SELECT Id, Name, ProfilePath FROM Profiles 
   WHERE Name LIKE '%alicelmoralesjvcrj@gmail.com%' 
     AND (Name LIKE '%10020%' OR ProfilePath LIKE '%10020%')
   ```
2. **Đối soát cả 2 trường `Name` và `ProfilePath` trước khi mở Playwright**:
   - In rõ log: `Id`, `Name`, `ProfilePath` đã chọn.
   - Tuyệt đối không fallback mù quáng vào dòng đầu tiên trả về của truy vấn wildcard email.

---

## 24. Cạm Bẫy Trích Xuất Port Proxy Từ Cột Master Excel Khi Chuỗi Chứa Cả Cổng Singbox Lẫn Port Proxy Gốc (2026-09-11)

### Hiện tượng:
- Trong file `master_gmail_manager.xlsx` (sheet `Kibe_Farm_S7`), cột 11 (`Proxy Đang Dùng`) thường ghi chú cả 2 cổng theo định dạng:
  `http://192.168.110.2:20057 (test.taadaa.click:5123)` hoặc tương tự.
- Nếu hàm helper trích xuất port dùng regex greedy hoặc tìm số đầu tiên dạng `re.search(r":(\d{4,5})", p_val)`:
  - Match đầu tiên sẽ là `20057` (cổng Singbox host local).
  - Kết quả: `port = 20057`.
  - Khi pipeline chạy tiếp:
    ```python
    singbox_port = acc.get("singbox_port") or (20000 + mid if port == 16002 else (20000 + (port - 5100) if 5000 < port < 6000 else 20000 + (port - 10000)))
    ```
    Biểu thức `20000 + (port - 10000)` sẽ tính ra:
    `20000 + (20057 - 10000) = 30057` $\rightarrow$ **Sai hoàn toàn port Singbox** (gây lỗi kết nối proxy không tồn tại hoặc rớt mạng).

### Giải pháp chuẩn:
1. **Trích xuất cổng Farm Proxy thật (`51xx` hoặc `100xx`)**:
   - Tìm port nằm trong dải cổng proxy Farm thực tế (`5100..5199` hoặc `10000..10100`) trước:
     ```python
     farm_port_match = re.search(r":\b(51\d{2}|100\d{2}|10100)\b", p_val)
     if farm_port_match:
         port = int(farm_port_match.group(1))
     ```
   - Hoặc ưu tiên đọc port từ tên profile GPM (`M57 - 5123 - ...` $\rightarrow$ port là `5123`).
2. **Khóa cứng `singbox_port` theo Machine ID**:
   - Luôn gán trực tiếp:
     ```python
     acc["singbox_port"] = 20000 + mid
     ```
   - Không để fallback tự tính từ `port` nếu chuỗi proxy trong Excel chứa định dạng kép.

---

## 25. Chiến Lược Truy Xuất Metadata Tài Khoản O(1) Cho Các Đợt Re-Auth Đơn Lẻ (Single-Account Re-auth Pattern) (2026-09-11)

### Tình huống & Cạm bẫy quét toàn bộ đĩa (Disk Sweep Timeout):
- Khi nhận yêu cầu re-auth 1 tài khoản cụ thể (ví dụ: `yenduypham2002997@gmail.com` cid `419e1d4f`), nếu tài khoản đó không nằm trong sheet `Kibe_Farm_S7` của `master_gmail_manager.xlsx`, việc chạy script quét đệ quy toàn bộ thư mục `D:\Taadaa` hoặc `D:\OneDrive\TaadaaData` bằng Python `os.walk` sẽ **dễ dàng chạm mốc timeout 180s** và làm cạn kiệt lượt gọi công cụ (iteration limit).

### Trình tự truy xuất O(1) chuẩn xác:
1. **Kiểm tra OmniRoute Proxy Assignment**:
   - Gọi `GET http://127.0.0.1:20129/api/settings/proxies/assignments`.
   - Lọc theo `scopeId` (chính là Connection ID `cid`, ví dụ `419e1d4f-199a-4db2-b476-804bf581f8ab`).
   - Lấy `proxyId` $\rightarrow$ đối soát `GET /api/settings/proxies` để lấy chính xác port proxy (ví dụ `5104`).
2. **Truy vấn SQLite `profile_data.db` của GPMLogin**:
   - `SELECT Id, Name, ProfilePath, JsonData FROM Profiles WHERE Name LIKE '%<email>%' OR Name LIKE '%<port>%'`.
   - Xác định `ProfilePath` thực tế trên ổ đĩa (ví dụ `Sy0xpMIS71-06092026` cho `04 - yenduypham2002997@gmail.com - 5104`).
3. **Tra cứu Script Batch Runner Cũ Trong `D:\Taadaa\GPM auto\scripts`**:
   - Các tài khoản từng được nạp qua các đợt chạy trước đều nằm trong các file cấu hình batch tập trung:
     - `D:\Taadaa\GPM auto\scripts\run_batch_turn2_gmails.py`
     - `D:\Taadaa\GPM auto\scripts\append_to_combo_pool3.py`
     - `D:\Taadaa\GPM auto\logs\batch_turn2_report.json`
   - Chỉ mất $0.05$s để đọc chính xác: Machine ID (`mid`), Mật khẩu (`pwd`), Port (`port`), Serial ADB của máy S7.
4. **Kích hoạt Re-auth Trực Tiếp**:
   - Nạp dictionary tài khoản đầy đủ vào `process_account(acc)` của `run_oauth_s7_pipeline.py`:
     ```python
     acc = {
         'mid': 4,
         'email': 'yenduypham2002997@gmail.com',
         'serial': '9885e6484432423046',
         'port': 5104,
         'profile': 'Sy0xpMIS71-06092026',
         'password': '...',
         'singbox_port': 20004
     }
     ```

---

## 26. Cơ Chế Cách Ly Profile Chuẩn Xác & Chống Xâm Phạm Chéo Tài Khoản (`resolve_profile_dir` & Profile Isolation Guard) (2026-09-11)

### Nguy cơ & Cạm bẫy dùng nhầm profile chéo (Cross-Account Contamination):
- Khi cấu hình tài khoản chạy OAuth pipeline hoặc batch script:
  - Nếu trường `acc['profile']` truyền nhầm một ProfilePath của tài khoản khác (ví dụ: `vukhoa04122002@gmail.com` lại truyền profile `SUNVqFew4a-05092026` của `khahoan240161@gmail.com`).
  - Hoặc `acc['profile']` ghi chuỗi text sai (ví dụ tên hiển thị của email khác `M57 - 5123 - phammai18052001@gmail.com` thay vì ID thư mục profile thật `aq6NHRUdWQ-06092026` của `mockieuplus13@gmail.com`).
- Hậu quả: Chrome mở profile của tài khoản khác, ghi đè cookie/session hoặc OAuth token nạp đè lên tài khoản khác trên OmniRoute $\rightarrow$ **Gây ô nhiễm tài khoản và hỏng session diện rộng**.

### Kiến trúc giải pháp 2 Bước (`resolve_profile_dir`):
1. **Bước 1: Strict DB Lookup ưu tiên theo Email**:
   - Luôn truy vấn `profile_data.db` với `SELECT ProfilePath, Name FROM Profiles WHERE lower(Name) LIKE '%<email>%'`.
   - Nếu tìm thấy và thư mục tồn tại trên ổ đĩa, LUÔN trả về thư mục profile chính chủ này (bỏ qua mọi giá trị sai ở trường `acc['profile']`).
2. **Bước 2: Cross-Account Collision Guard**:
   - Nếu không tìm thấy profile theo email trong DB mà phải xem xét giá trị `acc['profile']`:
     - **Guard A**: Nếu chuỗi `profile` chứa ký tự `@` nhưng không chứa email hiện tại $\rightarrow$ Chặn ngay với mã lỗi `PROFILE_COLLISION_BLOCKED`.
     - **Guard B**: Tra cứu `ProfilePath = acc['profile']` trong `profile_data.db`. Nếu `Name` của profile đó chứa email khác $\rightarrow$ Chặn ngay với `PROFILE_COLLISION_BLOCKED`.
     - **Guard C**: Nếu không tìm thấy thư mục profile hợp lệ trên đĩa $\rightarrow$ Trả về `PROFILE_NOT_FOUND`.
3. **Mẫu cài đặt chuẩn (`run_oauth_s7_pipeline.py`)**:
   ```python
   def resolve_profile_dir(acc, gpm_base=GPM_BASE):
       email = acc.get("email", "").strip().lower()
       mid = acc.get("mid", 0)
       prof_field = acc.get("profile", "").strip() if acc.get("profile") else ""
       db_path = os.path.join(gpm_base, "profile_data.db")

       if os.path.exists(db_path) and email:
           try:
               import sqlite3
               with sqlite3.connect(db_path) as conn:
                   cur = conn.cursor()
                   cur.execute("SELECT ProfilePath, Name FROM Profiles WHERE lower(Name) LIKE ?", (f"%{email}%",))
                   rows = cur.fetchall()
                   if rows:
                       for ppath, pname in rows:
                           pdir = os.path.join(gpm_base, ppath)
                           if os.path.exists(pdir):
                               logger.info(f"[M{mid:02d}] ✅ Strict Profile Guard: Đã tìm thấy profile riêng của {email} -> {ppath}")
                               return pdir, None
           except Exception as e:
               logger.warning(f"Error querying profile_data.db: {e}")

       if prof_field:
           if "@" in prof_field and email not in prof_field.lower():
               return None, "PROFILE_COLLISION_BLOCKED"
           if os.path.exists(db_path):
               try:
                   import sqlite3
                   with sqlite3.connect(db_path) as conn:
                       cur = conn.cursor()
                       cur.execute("SELECT Name FROM Profiles WHERE ProfilePath = ?", (prof_field,))
                       row = cur.fetchone()
                       if row and row[0] and "@" in row[0] and email not in row[0].lower():
                           return None, "PROFILE_COLLISION_BLOCKED"
               except Exception:
                   pass
           pdir = os.path.join(gpm_base, prof_field)
           if os.path.exists(pdir):
               return pdir, None

       return None, "PROFILE_NOT_FOUND"
   ```
4. **Bộ test cô lập bắt buộc**: `scripts/test_profile_isolation.py` kiểm thử 3 kịch bản:
   - Sai tên profile nhưng email có trong DB $\rightarrow$ tự động giải quyết đúng profile riêng.
   - ProfilePath thuộc về account khác $\rightarrow$ chặn đứng `PROFILE_COLLISION_BLOCKED`.
   - ProfilePath khớp chính chủ $\rightarrow$ chấp thuận và resolve thành công.

---

## 27. Kỷ Luật Canh S7 Rảnh Trước Khi Duyệt Mã & Lấy Security Code (Pre-flight S7 Idle Check) (2026-09-11)

### Yêu cầu người dùng & Mục đích:
- Chỉ đạo trực tiếp: *"Tiếp tục oauth đi. Canh S7 rảnh mới vào lấy mã nhé"*.
- **Mục đích**: Trên dàn farm S7, các máy có thể đang chạy cron nuôi TikTok, lướt video hoặc chạy batch ngầm. Nếu script nạp OAuth tự tiện mở Google Settings hoặc push dialog Google Prompt trong lúc máy đang có app foreground khác:
  1. Làm đứt gãy phiên chạy nuôi nick TikTok / mất device lock của cron.
  2. Google Prompt không pop-up lên được foreground dẫn tới timeout 180s.

### Quy trình kiểm tra S7 Idle O(1) qua ADB:
1. **Lệnh kiểm tra trạng thái cửa sổ foreground**:
   ```bash
   adb -s <serial> shell dumpsys window windows
   ```
2. **Đối soát chuỗi `mCurrentFocus` / `mFocusedApp`**:
   - **IDLE (Rảnh - An toàn)**: Chứa `com.sec.android.app.launcher` hoặc `LauncherActivity` (điện thoại đang ở màn hình chính Home Screen).
   - **BUSY (Đang bận - CẤM can thiệp)**: Chứa package ứng dụng khác (vd: `com.zhiliaoapp.musically`, TikTok, Chrome, Settings đang mở dở).
3. **Mẫu code Python thực thi**:
   ```python
   def is_s7_idle(serial):
       adb = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
       r = subprocess.run([adb, "-s", serial, "shell", "dumpsys", "window", "windows"], capture_output=True, text=True)
       for line in r.stdout.splitlines():
           if "mCurrentFocus" in line:
               return "com.sec.android.app.launcher" in line or "LauncherActivity" in line
       return False
   ```
   Nếu `is_s7_idle == False`: Bỏ qua máy đó hoặc chờ tới khi máy trở về Launcher mới dispatch lấy mã.

---

## 28. Xử Lý Fallback Authenticator Khi S7 Bị Liệt Google Prompt Trên Màn Hình Selection (2026-09-11)

### Hiện tượng:
- Khi đăng nhập hoặc xác thực OAuth, Google chuyển sang trang chọn phương thức xác minh (`https://accounts.google.com/v3/signin/challenge/selection`).
- Tùy chọn 1: *"Nhấn vào Có trên điện thoại hoặc máy tính bảng"* bị chú thích màu xám: *"Không thể kết nối với thiết bị ngay bây giờ"* (do Google Play Services trên S7 mất kết nối ngầm tạm thời).
- Nhấp vào nút này không có tác dụng, dẫn tới script bị kẹt vô hạn trong vòng lặp chờ và timeout.

### Kỹ thuật xử lý:
- Bên dưới thông báo lỗi của Google Prompt luôn có tùy chọn 2: **"Nhận mã xác minh từ ứng dụng Google Authenticator"** (`div[data-challengetype="12"]`, `div[data-challengetype="5"]`, `li:has-text("Authenticator")`).
- **Quy tắc**: Trong nhánh `if "selection" in cur_url:`, nếu tài khoản đã có `totp_secret`, **BẮT BUỘC** ưu tiên click chọn Authenticator trước:
  ```python
  if "selection" in cur_url:
      if totp_secret:
          totp_opt = page.locator('div[data-challengetype="12"], div[data-challengetype="5"], li:has-text("Authenticator"), li:has-text("xác thực"), div[role="link"]:has-text("Authenticator")').first
          if totp_opt.count() > 0 and totp_opt.is_visible():
              logger.info(f"[M{mid:02d}] Chọn phương thức Google Authenticator (TOTP)...")
              totp_opt.click()
              time.sleep(3)
              continue
  ```
- Thao tác này đưa luồng ngay lập tức về form nhập TOTP 6 số (`input#totpPin`), tự động điền pyotp và vượt xác minh chỉ trong 3 giây mà không cần tương tác phần cứng S7.

---

## 29. Chốt Chặn An Toàn Loại Trừ 100% Tài Khoản Dính Khoalemagic (`SKIPPED_KHOALEE`) (2026-09-11)

### Bối cảnh & Nguyên tắc bất biến:
- Toàn bộ tài khoản có recovery email dính `khoalemagic` / `khoaleemagic` (hoặc email chính có chứa `khoale`) nằm trong danh sách đen cách ly đặc biệt của Farm.
- **Hành vi bắt buộc**:
  - Tại đầu hàm `process_account(acc)`, sau khi trích xuất credentials:
    ```python
    if "khoale" in recovery.lower() or "khoale" in email.lower():
        logger.warning(f"[M{mid:02d}] 🚫 Bỏ qua {email}: TÀI KHOẢN DÍNH KHOALEMAGIC (Loại trừ 100%)!")
        return {"mid": mid, "email": email, "status": "SKIPPED_KHOALEE"}
    ```
  - Tuyệt đối không mở Profile, không chạy login/OAuth Playwright, không nạp vào OmniRoute hay combo.
  - Runner/Worker tiếp nhận kết quả `SKIPPED_KHOALEE` phải ghi nhận trạng thái và chuyển tiếp an toàn mà không retry hay báo lỗi sập hệ thống.

---

## 30. Quy Trình Phân Tách Song Song & Bơm Gối Đầu Fail-Fast Khi Tăng Quy Mô Combo (Pipelined Parallel Scaling) (2026-09-11)

### Nguyên tắc điều phối:
- **Tách bạch Code-surgery vs Batch execution**: Cấm Coordinator tự viết script probe kéo dài trong main turn. Mọi thao tác nạp tài khoản đều ủy thác qua subagent worker.
- **Canh kiểm tra S7 rảnh trước khi phân công**: Chỉ chọn các cặp tài khoản trên máy S7 đang ở trạng thái `LauncherActivity` (Home screen rảnh rỗi).
- **Tiêm Fail-Fast Guard vào worker prompt**: Giới hạn tối đa <= 10 tool calls, thời gian chạy <= 180s. Nếu phát hiện SMS Checkpoint cứng không có nút "Thử cách khác" thì worker phải abort ngay lập tức, tránh đốt hết 600s timeout làm nghẽn hàng đợi.
- **Tự động vá `projectId = "aicode-consumers"` và Sync Models**: Khi nạp thành công tài khoản mới qua API, kiểm tra và gán ngay `projectId: "aicode-consumers"` nếu Google API trả về chuỗi rỗng để tài khoản đạt trạng thái xanh lá `• đã kết nối`, tránh cờ cảnh báo `degraded`.

---

## 31. Cạm Bẫy Vòng Lặp Vô Hạn 'Thử Cách Khác' Tại Màn Hình Phone Challenge (`challenge/iap`) (2026-09-11)

### Hiện tượng:
- Khi pipeline xử lý tài khoản gặp checkpoint yêu cầu số điện thoại SMS (`challenge/iap`):
  ```
  [INFO] [M57] Điền mật khẩu cho lethithanhngan170819901708@gmail.com...
  [INFO] [M57] Phát hiện màn hình yêu cầu số điện thoại/SMS. Tìm nút 'Thử cách khác'...
  [INFO] [M57] Click nút 'Thử cách khác' để chuyển sang Google Prompt / Mã bảo mật...
  [INFO] [M57] Phát hiện màn hình yêu cầu số điện thoại/SMS. Tìm nút 'Thử cách khác'...
  [INFO] [M57] Click nút 'Thử cách khác' để chuyển sang Google Prompt / Mã bảo mật...
  ... (lặp liên tục 15-20 lần mỗi 4 giây)
  [Command timed out after 180s]
  ```

### Nguyên nhân kỹ thuật:
1. **Thiếu bộ đếm số lần click**: Nhánh phone challenge phát hiện từ khóa `"tin nhắn văn bản cùng mã xác minh"` hoặc URL `challenge/iap`, tìm thấy nút *"Thử cách khác"* và click. Tuy nhiên sau khi click, Google vẫn giữ nguyên giao diện hoặc trang `challenge/selection` vẫn chứa cụm từ đó và vẫn có nút/link *"Thử cách khác"*.
2. **Không có ngưỡng thoát Fail-Fast**: Khi tài khoản thực sự không có phương thức thay thế nào khác (Google ép buộc chỉ có SMS), việc bấm *"Thử cách khác"* không chuyển đổi được trạng thái xác thực. Thiếu biến đếm số lần thử khiến vòng lặp quay vô hạn cho đến khi chạm trần 180s timeout của lệnh.

### Mẫu xử lý chuẩn (Fail-Fast Loop Breaker):
```python
# Khởi tạo trước vòng lặp while:
phone_try_another_count = 0

# Trong nhánh xử lý Phone Challenge:
is_phone_challenge = ("challenge/iap" in cur_url or any(kw in body_lower for kw in ["nhập số điện thoại", "tin nhắn văn bản cùng mã xác minh", "số điện thoại để nhận"])) and "selection" not in cur_url
if is_phone_challenge:
    logger.info(f"[M{mid:02d}] Phát hiện màn hình yêu cầu số điện thoại/SMS. Tìm nút 'Thử cách khác'...")
    try_another = page.locator('button:has-text("Thử cách khác"), button:has-text("Try another way"), a:has-text("Thử cách khác"), a:has-text("Try another way"), div[role="button"]:has-text("Thử cách khác")')
    if try_another.count() > 0 and try_another.first.is_visible() and phone_try_another_count < 2:
        phone_try_another_count += 1
        logger.info(f"[M{mid:02d}] Click nút 'Thử cách khác' lần {phone_try_another_count} để chuyển sang Google Prompt / Mã bảo mật...")
        try_another.first.click()
        time.sleep(4)
        continue
    else:
        logger.warning(f"[M{mid:02d}] Đã thử 'Thử cách khác' {phone_try_another_count} lần hoặc không có nút. Hard SMS Checkpoint -> Abort ngay!")
        shot_path = os.path.join(SCREENSHOT_DIR, f"oauth_{email}_hard_sms_{int(time.time())}.png")
        try:
            os.makedirs(SCREENSHOT_DIR, exist_ok=True)
            page.screenshot(path=shot_path)
        except Exception:
            pass
        return {"mid": mid, "email": email, "status": "SMS_CHECKPOINT"}
```
## 32. Cơ Chế Tự Động Append Combo `ag-gemini-pool-3` Sau Khi Nạp OAuth Thành Công (2026-09-11)

### Mục Đích & Nguyên Lý:
- Sau khi nạp OAuth thành công (`SUCCESS` / `ALREADY_SUCCESS`) và đã gán Proxy 1:1, tài khoản cần được đưa ngay vào combo định tuyến tải `ag-gemini-pool-3` để tham gia phục vụ API.
- Tự động hóa qua module `append_to_combo_pool3.py` (hoặc hàm `append_connections`):
  ```python
  from append_to_combo_pool3 import append_connections

  if res.get("status") in ["SUCCESS", "ALREADY_SUCCESS"] and res.get("conn_id"):
      cid = res["conn_id"]
      append_connections([{"cid": cid, "email": acc["email"], "port": acc["port"]}])
      logger.info(f"✅ Đã append {acc['email']} ({cid}) vào combo ag-gemini-pool-3!")
  ```

### Quy Chuẩn & Lưu Ý:
1. **API Endpoint & Cấu Trúc Payload**:
   - OmniRoute quản lý combo qua `http://127.0.0.1:20129/api/combos`.
   - Mỗi model trong combo `ag-gemini-pool-3` tuân theo cấu trúc:
     ```json
     {
       "id": "ag-gemini-pool-3-model-<idx>-antigravity-gemini-3-8-flash-tiered-<cid>",
       "kind": "model",
       "model": "antigravity/gemini-3.8-flash-tiered",
       "providerId": "antigravity",
       "connectionId": "<cid>",
       "weight": 0,
       "label": "pool-<idx>"
     }
     ```
2. **Sao Lưu Tự Động (Combos Backup)**:
   - File cấu hình gốc được lưu trong SQLite của OmniRoute. Sau mỗi lần append qua API, script tự động export bản snapshot vào `D:\Taadaa\AI-Tools\tools\omniroute\combos_backup.json` (dạng list các combo) để audit và phòng ngừa mất cấu hình.
3. **Bảo Toàn Thứ Tự & Kiểm Tra Trùng Lặp**:
   - `append_connections` duyệt danh sách `existing_cids`. Nếu `cid` đã có mặt trong combo thì bỏ qua (`Skipping already present cid`).
   - Tự động tăng số thứ tự index nhãn `pool-<idx>` liên tục (ví dụ: từ 71 lên 72).

---

## 33. Kỷ Luật 'Canh Cron S7 Rảnh' Khi Nạp Profile Mới & Xử Lý Sự Cố ADB Hub Flapping (2026-09-12)

### A. Phân Biệt 'Canh S7 Rảnh Tức Thời' vs 'Canh Lịch Cron An Toàn' (Idle Preflight Hierarchy):
Khi nhận chỉ đạo *"Canh cron máy S7 rảnh chạy nạp tiếp đợt profile mới lên GPM"*, việc kiểm tra phải đi qua 2 tầng:
1. **Tầng 1 - Lịch Trình Farm (Macro Schedule Gate)**:
   - Đọc manifest ca nuôi ngày hiện tại tại `D:\Taadaa\runtime\kibe\cron-state\manifests\<DATE>\assignment-v1-*.json`.
   - Tính toán khoảng cách đến slot nuôi tiếp theo của từng máy:
     $$\text{Safe Idle Machines} = \text{All Farm Machines} - \{ m \mid \text{slot\_time} \le \text{now} + 90\text{ phút} \}$$
   - **Khoảng đệm an toàn**: Chỉ chọn các máy có khoảng cách $\ge 60$ đến $90$ phút không có lịch feed/upload tiếp theo.
2. **Tầng 2 - Trạng Thái Thiết Bị Vật Lý (Micro Window Gate)**:
   - Chạy `adb -s <serial> shell dumpsys window windows` để verify `mCurrentFocus`.
   - BẮT BUỘC máy phải đang ở `LauncherActivity` (Home screen rảnh rỗi).

### B. Xử Lý Sự Cố ADB Daemon Rớt Thiết Bị Hàng Loạt (ADB Server Flapping):
- **Hiện tượng**: Khi đang chạy batch qua cụm USB Hub, `adb devices` đột ngột chỉ hiển thị một vài máy (ví dụ 7/77 máy) khiến tưởng lầm là phần cứng mất điện/tuột cáp.
- **Bản chất**: Do tiến trình con ADB fork nhiều luồng hoặc USB descriptor handshake bị reset trên Windows khiến service ADB daemon của máy chủ bị desync.
- **Khôi phục chuẩn O(1)**:
  ```bash
  adb kill-server
  adb devices
  ```
  Sau 2-5 giây, toàn bộ 77+ máy S7 sẽ kết nối lại đầy đủ mà không cần thao tác vật lý.

### C. Quy Trình Nạp Profile Mới Lên GPM Cho Tài Khoản Sạch Chưa Có Profile:
1. Đối soát `master_gmail_manager.xlsx` với SQLite `profile_data.db` của GPM để tìm các tài khoản LIVE chưa có profile GPM.
2. Lọc bỏ 100% tài khoản dính `khoaleemagic` hoặc đang trong `cooldown_7days` (`rrk=77`).
3. Khởi tạo Profile GPM độc lập theo quy chuẩn `M<mid:02d> - <port> - <email>`, cấu hình proxy 1:1 tương ứng của máy (`Singbox 20000 + mid`).
4. Khởi chạy song song 2 Worker (Parallel 2) có tiêm Fail-Fast (<= 180s timeout, thoát ngay nếu Hard SMS Checkpoint).
5. Sau khi đăng nhập và bật 2FA thành công, hot-session OAuth cấp quyền OmniRoute và append vào combo `ag-gemini-pool-3`.

---

## 34. Kỹ Thuật Lật Trang Phân Trang (Pagination Page 2) Khi Chụp Ảnh Nghiệm Thu Đáy Dashboard OmniRoute (`:20129`) (2026-09-12)

### Hiện tượng & Cạm bẫy:
- Dashboard OmniRoute tại `http://127.0.0.1:20129/dashboard/providers/antigravity` có phân trang mặc định giới hạn hiển thị tối đa **50 tài khoản/trang** (`1–50 / N`).
- Khi tổng số tài khoản trong combo vượt mốc 50 (ví dụ từ #51 đến #74+), việc chỉ cuộn trang đơn thuần trong view 1 sẽ chỉ thấy đến tài khoản thứ `#50`. Các tài khoản mới nhất vừa nạp (#51..#74) nằm ở **Trang 2** (`51–74 / 74`).
- Nếu chỉ chụp ảnh cuộn đáy ở Trang 1, người dùng sẽ thấy danh sách chỉ dừng ở tài khoản cũ và hiểu lầm là tài khoản mới chưa được thêm vào hệ thống.

### Quy trình chụp nghiệm thu chuẩn cho Page 2+:
1. Điều hướng Playwright tới `http://127.0.0.1:20129/dashboard/providers/antigravity`, chờ DOM load và danh sách hiển thị.
2. Kiểm tra thanh phân trang bên dưới danh sách (`div.border-t.border-border:has-text("1–50")`).
3. Nếu tổng số tài khoản > 50, click nút chuyển trang `chevron_right`:
   ```python
   btn_next = page.locator('button:has(span:text("chevron_right"))')
   if btn_next.count() > 0 and btn_next.first.is_enabled():
       btn_next.first.click()
       time.sleep(2)
   ```
4. Giao diện chuyển sang Trang 2 (`51–74 / 74`), hiển thị đầy đủ các tài khoản mới nhất ở cuối danh sách (ví dụ `#73 hak**********@******com`, `#74 qua***************@******com`).
5. Chụp ảnh màn hình toàn cảnh Trang 2/2 hiển thị rõ ràng các tài khoản mới nhất và gửi kèm trong báo cáo nghiệm thu (`MEDIA:<path>`).

---

## 35. Khởi Tạo Profile GPM Trực Tiếp Khi GPM Local API (Port 19995) Đang Tắt (Headless SQLite Injection & Profile Directory) (2026-09-12)

### Bối cảnh:
- Ứng dụng GPMLogin trên máy tính có thể đang tắt hoặc Local API port `19995` chưa khởi động (`WinError 10061: Connection refused`).
- Để không làm gián đoạn luồng tự động hóa chạy liên tục, agent hoàn toàn có thể khởi tạo profile GPM độc lập mà không cần bật app GPMLogin.

### Trình tự khởi tạo độc lập 3 bước:
1. **Khởi tạo thư mục User Data**:
   Tạo thư mục trên ổ đĩa theo quy chuẩn đặt tên:
   `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\M<mid:02d> - <port> - <email>`
2. **Đăng ký vào SQLite CSDL GPM (`profile_data.db`) — BẮT BUỘC FULL 124-KEY SCHEMA**:
   *CẢNH BÁO TỐI QUAN TRỌNG: TUYỆT ĐỐI CẤM chèn JsonData chỉ có 2 keys (`{"Name": ..., "Proxy": ...}`). Xem chi tiết tại Mục 36 về cạm bẫy WPF lag khi tải 100 kết quả.*
   BẮT BUỘC clone cấu trúc từ một donor profile chuẩn (124 keys) trong `profile_data.db`, sau đó randomize riêng `MacAddress` và `AudioNoise`:
   ```python
   import sqlite3, uuid, datetime, json, copy, random
   conn = sqlite3.connect(r'C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db')
   c = conn.cursor()
   
   # Lấy template chuẩn 124 keys từ donor (ví dụ M01)
   c.execute("SELECT JsonData FROM Profiles WHERE Name LIKE '%M01 - 5101%'")
   donor_json = json.loads(c.fetchone()[0])
   
   # Quét danh sách MAC và AudioNoise đã có để chống trùng lặp
   c.execute('SELECT JsonData FROM Profiles WHERE JsonData IS NOT NULL')
   all_macs = set()
   all_audio = set()
   for r in c.fetchall():
       try:
           d = json.loads(r[0])
           if 'MacAddress' in d: all_macs.add(d['MacAddress'])
           if 'AudioNoise' in d: all_audio.add(str(d['AudioNoise']))
       except: pass
       
   def get_unique_mac():
       while True:
           mac = '-'.join([f'{random.randint(0, 255):02X}' for _ in range(6)])
           if mac not in all_macs:
               all_macs.add(mac)
               return mac
               
   def get_unique_audio():
       while True:
           an = round(random.uniform(-5.0, 5.0), 15)
           if str(an) not in all_audio:
               all_audio.add(str(an))
               return an

   uid = str(uuid.uuid4())
   name = f"M{mid:02d} - {port} - {email}"
   now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
   
   new_d = copy.deepcopy(donor_json)
   new_d['Name'] = name
   new_d['Proxy'] = raw_proxy
   new_d['MacAddress'] = get_unique_mac()
   new_d['AudioNoise'] = get_unique_audio()
   new_json_str = json.dumps(new_d, ensure_ascii=False)
   
   c.execute('INSERT INTO Profiles (Id, Name, ProfilePath, JsonData, GroupId, CreatedAt) VALUES (?, ?, ?, ?, 1, ?)', 
             (uid, name, name, new_json_str, now_str))
   conn.commit()
   conn.close()
   ```
3. **Khởi chạy Playwright Persistent Context**:
   Mở trực tiếp Chromium Core 142 (`C:\Users\Kibe\AppData\Local\Programs\GPMLogin\gpm_browser\gpm_browser_chromium_core_142\chrome.exe`) với `user_data_dir` là thư mục vừa tạo và proxy Singbox tương ứng (`http://192.168.110.2:200xx`). Toàn bộ cookie đăng nhập sẽ được lưu trữ tự động vào profile và GPMLogin sẽ nhận diện ngay lập tức khi mở app.

---

## 36. Cạm Bẫy WPF UI Lag / Infinite Loading Khi Chuyển Page Size 100/200 Trên GPM-Login v4.3.x Do Thiếu Schema JsonData (2026-09-12)

### Hiện tượng & Triệu chứng:
- Trên giao diện phần mềm GPMLogin v4.3.x, khi để cấu hình `Số profile trên mỗi trang = 50`: Trang 1 tải bình thường, mượt mà.
- Nhưng khi chuyển cấu hình sang `100` kết quả / trang (hoặc bấm sang Trang 2 ở mức 50): Giao diện lập tức bị đơ cứng, hiện vòng xoay (loading spinner màu xanh) quay vô tận, không thể click hay thao tác được các profile.

### Nguyên nhân kỹ thuật gốc rễ:
1. **WPF DataGrid DataBinding Exception**:
   - GPM-Login v4.3.x được viết bằng công nghệ WPF (.NET/C#). DataGrid hiển thị bảng profile liên kết (binding) trực tiếp các cột giao diện (Browser icon, OS, Proxy, Audio noise, Canvas, WebGL, Last run...) với các trường bên trong chuỗi `JsonData` của bảng `Profiles`.
2. **Sự không đồng nhất Schema (Schema Inconsistency)**:
   - Toàn bộ các profile cũ (#1 đến #50) đều có đầy đủ **124 trường** JSON fingerprint chuẩn.
   - Khi bảng render 50 dòng đầu: Tất cả các trường binding đều tồn tại $\rightarrow$ DataGrid render trơn tru.
   - Khi chọn hiển thị 100 dòng: DataGrid phải render toàn bộ danh sách (ví dụ 82 profile). Trong đó các profile vừa mới được tạo thủ công nếu chỉ chèn chuỗi JSON rút gọn 2 keys (`{"Name": ..., "Proxy": ...}`) sẽ bị thiếu 122 trường còn lại.
   - Khi WPF DataGrid cố gắng bind các thuộc tính thiếu vào các cell template, nó sẽ ném ra hàng loạt ngoại lệ `BindingExpression / TargetNull / KeyNotFound` trên luồng UI (UI Thread Dispatcher). Luồng UI bị nghẽn làm đứng frame và treo spinner vô tận.

### Giải pháp khắc phục & Phòng ngừa triệt để:
1. **Tuyệt đối không bao giờ chèn `JsonData` rút gọn vào SQLite của GPMLogin**.
2. **Luôn luôn nhân bản từ Donor chuẩn 124 keys**:
   - Sao chép toàn bộ 124 keys từ một profile đang hoạt động tốt (`GroupId=1`).
   - Cập nhật đúng `Name` và `Proxy`.
   - **Bắt buộc Randomize riêng** `MacAddress` và `AudioNoise` để đảm bảo tính duy nhất tuyệt đối (Zero Fingerprint Collision), chống bị Google phát hiện clone máy ảo.
3. **Câu lệnh kiểm tra tính đồng nhất Schema**:
   ```sql
   -- Kiểm tra độ dài và số lượng key của GroupId=1
   SELECT length(JsonData), count(*) FROM Profiles WHERE GroupId = 1 GROUP BY length(JsonData) > 500;
   ```
   Tất cả các profile trong GroupId=1 phải có `length(JsonData) > 2000` (đạt chuẩn ~3900-4700 ký tự). Khi đồng nhất 100% schema, GPM-Login sẽ load tức thì ngay cả khi chọn 100 hay 200 profile trên mỗi trang.

---

## 37. Cạm Bẫy Trì Hoãn Security Code S7 Qua Google Settings Khi Điều Hướng UI Thất Bại & Kỹ Thuật Đọc Trực Tiếp Code 10 Số (2026-09-12)

### Hiện tượng:
- Khi đăng nhập vào Google trên GPM profile, luồng kích hoạt challenge nhận mã bảo mật ngoại tuyến (`challenge/ootp`).
- Script gọi `get_s7_security_code(machine_id, serial, target_email)` để mở `com.google.android.gms/.app.settings.GoogleSettingsLink`, chọn account picker, vào "Bảo mật", cuộn tìm "Mã bảo mật".
- Tuy nhiên do độ trễ render UI XML của `atx-agent` (hoặc picker bị kẹt, hoặc màn hình Security Settings chưa kịp load xong danh mục "Bảo mật"), hàm liên tục thử lại 4-5 lần nhưng không lấy được mã 10 số kịp thời, dẫn tới pipeline bị `TIMEOUT` sau 180s.

### Nguyên nhân & Cơ chế:
1. `am start -n com.google.android.gms/.app.settings.GoogleSettingsLink` mở trang chủ Google Services. Việc chuyển đổi tài khoản trên giao diện Google Settings cần qua 3-4 màn hình con (Picker -> Tài khoản Google -> Tab Bảo mật -> Mã bảo mật).
2. Khi tài khoản chưa phải là tài khoản mặc định trên S7 (như M74 với 6 tài khoản cùng add trên máy), bước switch account qua UI XML rất dễ bị trượt bounds hoặc dump hierarchy timeout nếu S7 đang đồng bộ ngầm.

### Giải pháp khắc phục & Phòng ngừa:
1. **Kiểm tra sự hiện diện của tài khoản trước**:
   - Chạy `dumpsys account` kiểm tra chắc chắn target email có trong danh sách com.google.
2. **Tối ưu hóa vòng lặp lấy mã bảo mật**:
   - Nếu UI XML của `GoogleSettingsLink` bị trễ, dùng shortcut intent mở trực tiếp màn hình bảo mật nếu khả dụng, hoặc tăng thời gian chờ `time.sleep(1.0)` giữa các lần swipe.
   - Thêm cơ chế chụp ảnh màn hình S7 (`adb exec-out screencap -p > debug_s7.png`) khi dump hierarchy không tìm thấy node "Mã bảo mật" để đối soát ngay nguyên nhân lệch tọa độ hoặc popup đè.
3. **Ưu tiên kích hoạt 2FA TOTP ngay sau khi login thành công**:
   - Khi đã lấy được mã và vào được tài khoản, bắt buộc chạy ngay Bước 2 (Bật 2FA Google Authenticator) để các lần OAuth sau dùng thẳng `pyotp.now()`, hoàn toàn thoát ly khỏi giao diện Settings của S7.

---

## 38. Cạm Bẫy `atx-agent` Daemon Dead Trên S7 Khi Duyệt Prompt / Lấy Security Code (`RemoteDisconnected` Port 7912) & Helper `ensure_atx_agent` (2026-09-12)

### Hiện tượng & Triệu chứng:
- Script chạy `run_oauth_s7_pipeline.py` (hoặc script nạp OAuth lẻ như `run_m74_phannhu_auto.py`) gặp thử thách `challenge/ootp` (Mã bảo mật) hoặc `challenge/dp` (Google Prompt).
- Log ghi:
  ```
  [M74] Phát hiện challenge/ootp! Lấy mã bảo mật từ S7...
  [M74] Acquiring device lock on ce061606c21e153d03 to fetch Security Code for phannhu05012005@gmail.com...
  ```
  Sau đó log lặp lại 4 lần liên tiếp mỗi ~50 giây mà không hề có log "Opening account picker..." hay "Tapping 'Tài khoản Google'...", rồi kết thúc bằng:
  ```
  [ERROR] [M74] Timeout không nhận được callback code!
  Kết quả M74: {'mid': 74, 'email': 'phannhu05012005@gmail.com', 'status': 'TIMEOUT'}
  ```

### Nguyên nhân gốc rễ:
- Cả 2 hàm `approve_s7_google_prompt()` và `get_s7_security_code()` đều forward cổng `tcp:17000+mid` tới `tcp:7912` trên điện thoại S7 để gọi `http://127.0.0.1:{atx_port}/dump/hierarchy`.
- Sau khi máy S7 bị rớt cáp USB / reconnect ADB, hoặc khởi động lại thiết bị, tiến trình `atx-agent` trên máy S7 chưa được bật lại (`ps -A | grep atx` trả về rỗng, khiến HTTP request tới 17000+mid bị `RemoteDisconnected`).
- Hàm `dump_ui()` trong script nuốt exception (`except Exception: pass`) và trả về `None`, dẫn đến thất bại im lặng (silent failure): toàn bộ các bước mở picker, tap "Tài khoản Google", chuyển tab "Bảo mật", cuộn "Mã bảo mật" bị bỏ qua hoàn toàn và đốt hết 180s-240s timeout.

### Cách chẩn đoán & Khôi phục chuẩn:
1. **Kiểm tra tiến trình trên S7 qua ADB**:
   ```bash
   adb -s <serial> shell "ps -A | grep atx-agent"
   ```
2. **Khởi động nhanh daemon `atx-agent` thủ công**:
   ```bash
   adb -s <serial> shell "/data/local/tmp/atx-agent server -d"
   ```
3. **Phòng ngừa tự động trong code (`run_oauth_s7_pipeline.py`)**:
   Xây dựng helper `ensure_atx_agent(serial)` và gọi tại cả 2 vị trí trước khi forward port:
   ```python
   def ensure_atx_agent(serial: str) -> None:
       try:
           check = subprocess.run([ADB_EXE, "-s", serial, "shell", "ps -A | grep atx-agent"], capture_output=True, text=True, timeout=5)
           if "atx-agent" not in check.stdout:
               logger.info(f"atx-agent not running on {serial}, starting daemon...")
               subprocess.run([ADB_EXE, "-s", serial, "shell", "/data/local/tmp/atx-agent server -d"], capture_output=True, timeout=8)
               time.sleep(1.0)
       except Exception as e:
           logger.warning(f"ensure_atx_agent warning on {serial}: {e}")
   ```
   **Vị trí gọi bắt buộc**:
   - Trong `approve_s7_google_prompt`: ngay sau khi acquire device lock và trước khi `forward tcp:{atx_port} tcp:7912`.
   - Trong `get_s7_security_code`: ngay sau khi acquire device lock và trước khi `forward tcp:{atx_port} tcp:7912`.

---

## 39. Cạm Bẫy Selector 'Chạm Vào Có' (Google Prompt Tiếng Việt) & Xử Lý Đa Tài Khoản Trên S7 Khi Lấy Mã Bảo Mật (2026-09-12)

### A. Cạm bẫy Selector Google Prompt Tiếng Việt ("Chạm vào Có" vs "Nhấn vào Có"):
- **Hiện tượng**:
  - Khi Google chuyển sang thử thách Google Prompt trên trình duyệt GPM tiếng Việt, giao diện hiển thị: *"Chạm vào Có trên điện thoại hoặc máy tính bảng của bạn"*.
  - Hoặc trên màn hình lựa chọn phương thức xác minh (`challenge/selection`), liên kết có text: *"Chạm vào Có trên điện thoại hoặc máy tính bảng"*.
  - Nếu script Playwright chỉ quét các selector cũ: `li:has-text("Nhấn vào Có")`, `div[role="link"]:has-text("Nhấn vào Có")`, `"nhấn vào có" in body_content`:
    $\rightarrow$ Script không nhận diện được phương thức Google Prompt, bỏ qua hoặc bị trôi sang fallback khác, dẫn đến timeout 180s.
- **Giải pháp chuẩn**:
  - Bổ sung toàn diện từ khóa `"chạm vào có"` vào cả 3 vị trí:
    1. Kiểm tra URL/Body: `is_dp = ("challenge/dp" in cur_url or "kiểm tra galaxy" in body_content or "nhấn vào có" in body_content or "chạm vào có" in body_content)`.
    2. Regex trích xuất PIN dự phòng: `pin_match = re.search(r'(?:nhấn vào|rồi nhấn vào|chạm vào|rồi chạm vào|chọn|tap|số|number)\s*(\d{1,2})', safe_body_text(page), re.I)`.
    3. Locator chọn phương thức trên trang selection:
       `prompt_opt = page.locator('div[data-challengetype="6"], li:has-text("Nhấn vào Có"), li:has-text("Chạm vào Có"), li:has-text("Tap Yes"), div[role="link"]:has-text("Nhấn vào Có"), div[role="link"]:has-text("Chạm vào Có"), div[role="button"]:has-text("Chạm vào Có")').first`.

### B. Xử Lý Đa Tài Khoản Trên Màn Hình "Mã Bảo Mật" (Google Settings S7):
- **Hiện tượng**:
  - Thiết bị S7 thường được dùng để quản lý 3–5 tài khoản Google cùng lúc (kiểm tra qua `dumpsys account`).
  - Khi mở `com.google.android.gms/.app.settings.GoogleSettingsLink` -> vào tab Bảo mật -> "Mã bảo mật", màn hình mặc định hiển thị mã 10 số của **tài khoản Google đầu tiên** trên máy (ví dụ `phamthimyduyen...`).
  - Phía trên mã có một dropdown/spinner (`android.widget.Spinner`) để chuyển đổi giữa các tài khoản đã thêm trên máy.
- **Cạm bẫy & Xử lý**:
  - Cần đối soát email đang hiển thị trên header của màn hình Mã bảo mật: nếu `target_email` không khớp email hiện tại, click vào `android.widget.Spinner` để mở popup danh sách tài khoản.
  - Quét node trong popup chứa `target_email` và tap vào để đổi tài khoản trước khi trích xuất chuỗi 10 số `re.match(r"^\d{10}$", text)`.
  - Nếu chuyển đổi tài khoản trên UI S7 bị chậm hoặc không bắt được mã, ưu tiên dùng phương thức Google Prompt (với selector "Chạm vào Có" đã được vá) hoặc kích hoạt ngay 2FA Authenticator sau khi vào được tài khoản để thoát ly hoàn toàn khỏi S7.

---

## 40. Cạm Bẫy Vuốt Tab Ngang 'Bảo Mật' Trong Màn Hình Quản Lý Tài Khoản Google S7 (Horizontal Tab Swipe vs Vertical Page Scroll Khi Lấy Mã 10 Số) (2026-09-12)

### Hiện tượng & Triệu chứng:
- Khi đăng nhập vào Google gặp thử thách `challenge/ootp` (nhận mã bảo mật 10 chữ số ngoại tuyến trên S7).
- Script điều khiển S7: mở `GoogleSettingsLink`, chọn account picker, tap `'Tài khoản Google'` tại `(540, 939)` thành công.
- Tuy nhiên sau đó log im lặng ~30 giây, không thấy log `Tapping Security section`, rồi lặp lại thông báo:
  ```
  [INFO] [M74] Phát hiện challenge/ootp! Lấy mã bảo mật từ S7...
  [INFO] [M74] Acquiring device lock on ce061606c21e153d03 to fetch Security Code for phannhu05012005@gmail.com...
  [INFO] [M74] Tapping 'Tài khoản Google' at (540, 939)...
  ```
  Lặp đúng 5 lần rồi script báo `TIMEOUT không nhận được callback code!`.

### Nguyên nhân gốc rễ:
1. **Thanh Tab Ngang (Horizontal Tab Bar)**:
   - Sau khi tap `'Tài khoản Google'` (Quản lý Tài khoản Google), giao diện mở trang quản lý tài khoản Google của Android.
   - Các danh mục nằm trên **thanh tab trượt ngang**: `Trang chủ` | `Thông tin cá nhân` | `Dữ liệu và quyền riêng tư` | `Bảo mật` (Security).
   - Tab `'Bảo mật'` nằm ở vị trí thứ 4, bị khuất về phía bên phải màn hình nếu độ phân giải của máy S7 không hiển thị hết 4 tab.
2. **Sai hướng Swipe trong vòng lặp tìm tab**:
   - Nếu script thực hiện lệnh cuộn dọc: `subprocess.run([ADB_EXE, "-s", serial, "shell", "input", "swipe", "500", "1400", "500", "600"])`:
     $\rightarrow$ Lệnh này chỉ cuộn nội dung trang bên dưới theo chiều dọc, **hoàn toàn KHÔNG cuộn thanh tab ngang**.
   - Do đó node chứa chữ `"Bảo mật"` hoặc `"Security"` không bao giờ xuất hiện trong hierarchy dump $\rightarrow$ `found_sec = False` $\rightarrow$ hàm thoát mà không lấy được mã, gây timeout.

### Giải pháp chuẩn & Phòng ngừa:
1. **Thực hiện swipe ngang trên vùng Tab Bar**:
   - Khi không tìm thấy node `"Bảo mật"` / `"Security"` trên màn hình sau khi tap `'Tài khoản Google'`, thực hiện swipe ngang từ phải sang trái trên vùng tab bar (khoảng tọa độ Y = 300 - 450 trên màn hình S7):
     ```python
     # Vuốt ngang từ phải sang trái trên vùng tab bar để làm lộ tab 'Bảo mật'
     subprocess.run([ADB_EXE, "-s", serial, "shell", "input", "swipe", "800", "380", "200", "380"], capture_output=True, timeout=5)
     ```
2. **Tìm trực tiếp bằng class `android.widget.HorizontalScrollView` hoặc text tab**:
   - Tìm kiếm node con bên trong `HorizontalScrollView` hoặc cuộn thanh tab sang trái trước khi dump lại hierarchy XML.
3. **Fail-fast & Fallback sang Google Prompt**:
   - Nếu lấy Security Code không thành công sau 2 lần thử, trên trình duyệt Playwright click *"Thử cách khác"* để chuyển sang Google Prompt (`challenge/dp`) — phương thức này chỉ cần bấm "Có" trên notification mà không cần điều hướng qua các tầng tab ngang của Google Account Settings.

---

## 41. Chiến Lược Tuyển Chọn Hàng Đợi Nạp OAuth: Ưu Tiên Tuyệt Đối Tài Khoản Có Sẵn 2FA TOTP & Fail-Fast Hard SMS (2026-09-12)

### A. Ưu Tiên Tuyệt Đối Tài Khoản Đã Có 2FA Secret Key (TOTP-First Strategy):
- **Cơ chế**: Khi duyệt danh sách tài khoản cần nạp OAuth Antigravity vào OmniRoute (`ag-gemini-pool-3`), đối soát cột `2FA_Secret` trong `master_gmail_manager.xlsx` (sheet `Kibe_Farm_S7`).
- **Lợi thế vượt trội**:
  - Với tài khoản đã có 2FA Secret: Google form hiển thị ô nhập mã TOTP (`input#totpPin`), Playwright tự tính mã 6 số bằng `pyotp.TOTP(secret).now()` và điền ngay lập tức.
  - **Hoàn toàn không cần tương tác S7**: Không cần kết nối ADB, không cần mở Google Settings, không cần swipe ngang tab Bảo mật, không bị nghẽn khi S7 đang bận.
  - **Tỷ lệ thành công 100% trong 15-30s**, không bao giờ bị Google leo thang thành SMS Checkpoint.
- **Quy tắc xếp hàng**: Luôn đẩy toàn bộ các tài khoản đã có 2FA TOTP lên đầu hàng đợi nạp OAuth; chỉ xử lý các tài khoản chưa có 2FA (phụ thuộc S7 Prompt/Security Code) khi đã hết danh sách có TOTP.

### B. Kỷ Luật Fail-Fast Hard SMS Checkpoint & Đưa Vào Danh Sách Ngâm Tĩnh:
- **Hiện tượng**: Google hiển thị *"Xác minh danh tính của bạn. Google sẽ gửi mã xác minh gồm 6 chữ số đến số điện thoại ••••••••XX"*.
- **Xử lý chuẩn**:
  - Khi không có nút *"Thử cách khác"* (hoặc sau 2 lần click mà Google vẫn giữ nguyên màn hình SMS), coi đây là **Hard SMS Checkpoint**.
  - **CẤM** tiếp tục để browser chờ callback code đến khi hết timeout 180s.
  - Thoát ngay lập tức với `status: "SMS_CHECKPOINT"`, cập nhật vào `config/oauth_pipeline_status.json` trong mục `wrong_password_or_checkpoint` kèm tên máy (ví dụ `"phannhu05012005@gmail.com": "SMS_CHECKPOINT (M74)"`).
  - Đưa tài khoản vào trạng thái **ngâm tĩnh 24 - 48h** trên thiết bị S7, tuyệt đối không cố đăng nhập hay spam OTP làm Google khóa cứng tài khoản.

---

## 42. Kiến Trúc Điều Khiển Phân Tách Máy Kibe vs Máy Admin (Cross-Host GPM Centralization & Remote S7 ADB Bridge) (2026-09-13)

### Bối cảnh & Bài toán:
- **Tình huống thực tế**: Máy Kibe sở hữu bản quyền GPMLogin (Local API v3 port `19995`), quản lý tập trung toàn bộ profile và OAuth token. Máy Admin (dàn S7 máy 200+) reg ra Gmail mới và nuôi TikTok độc lập.
- **Vấn đề**: Khi tài khoản Gmail mới được đưa lên GPM Kibe để đăng nhập lần đầu, Google đòi duyệt Google Prompt hoặc lấy mã bảo mật 10 số trên S7 nằm bên dàn Admin.
- **Sai lầm kiến trúc cần tránh**:
  - Không mua thêm key GPM cho Admin (lãng phí và phân mảnh quản lý tài khoản).
  - Không kéo toàn bộ cron/tác vụ từ Admin về Kibe (dễ gây nghẽn mạng LAN, rủi ro Single Point of Failure làm sập cả farm khi Kibe restart, và mất khả năng giải cứu phần cứng tức thời của local watchdog).

### Mô hình tối ưu "Bán tập trung" (Master-Worker Architecture):
1. **Máy Admin (Worker & Physical Hardware Guardian)**:
   - Giữ nguyên 100% cron reg Gmail, nuôi TikTok và ghi nhận dữ liệu (Excel/JSON) độc lập tại local.
   - Giữ local watchdog bảo vệ S7 (tắt màn hình `stayon=0`, mute âm thanh, reap app treo).
   - Mở remote ADB server trên port `5037` để nhận lệnh từ Kibe khi cần:
     ```cmd
     :: Script chạy trên Admin: D:\OneDrive\Taadaa_Sync_Shared\bat_remote_adb_admin.bat
     adb kill-server
     netsh advfirewall firewall add rule name="ADB Remote 5037" dir=in action=allow protocol=TCP localport=5037
     adb -a nodaemon server
     ```
2. **Máy Kibe (Central Controller & GPM Authenticator)**:
   - Đọc dữ liệu tài khoản mới từ Admin.
   - Khởi chạy profile GPM qua Local API port `19995` để login.
   - Khi gặp Google Prompt hoặc challenge 10 số: gửi lệnh on-demand sang máy Admin thông qua `tools/remote_admin_adb.py` (hoặc `adb -H 192.168.110.119 -s <serial>`):
     ```bash
     python D:/Taadaa/tools/remote_admin_adb.py -s <serial_admin> shell input keyevent 3
     ```
   - Lấy mã xác thực xong, kích hoạt ngay 2FA Authenticator để ngắt kết nối phụ thuộc khỏi S7, lưu secret key và nạp OAuth vào OmniRoute. S7 bên Admin lập tức quay về trạng thái nghỉ/nuôi nick bình thường.

---

## 43. Cạm Bẫy Nhận Diện Profile Sống Khi Trùng Email & Khởi Động Trực Tiếp Qua GPM Local API (2026-09-14)

### A. Hiện tượng trùng Profile & Phân tầng Group ID:
- Khi tra cứu tài khoản trên GPM Local API (`GET /api/v3/profiles?search=<email>`) hoặc SQLite `profile_data.db`, một email có thể có nhiều profile trùng tên (do các đợt chạy và khôi phục khác nhau).
- **Phân biệt nhóm qua `group_id`**:
  - `group_id: 10` (`Google_Live_Ready`): Chứa profile chuẩn, cookie sống đầy đủ (kích thước file `Network/Cookies` > 60KB).
  - `group_id: 11` (`Google_Cooldown_Error`): Profile đang bị cờ lỗi hoặc đang trong thời gian ngâm cooldown (~45KB).
- **Quy tắc chọn profile chuẩn**: Luôn ưu tiên profile thuộc `group_id: 10`, sau đó kiểm tra `profile_path` thực tế trên đĩa trước khi launch.

### B. Mở Profile GPM O(1) qua Local API (Port 19995):
- Khởi động profile:
  ```http
  GET http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}
  ```
  Phản hồi trả về: `{"success": true, "data": {"remote_debugging_address": "127.0.0.1:<port>", "process_id": <pid>}}`.
- Điều hướng và kiểm tra tab qua CDP HTTP API (không cần khởi tạo toàn bộ framework Playwright nếu chỉ cần mở trang):
  - Mở tab mới: `PUT http://127.0.0.1:<port>/json/new?<target_url>` (Bắt buộc dùng method `PUT`, method `GET` bị Chromium chặn).
  - Liệt kê các tab đang mở: `GET http://127.0.0.1:<port>/json/list`.
  - Kết nối Playwright/CDP khi cần automation: `p.chromium.connect_over_cdp("http://127.0.0.1:<port>")` kết hợp vòng lặp polling socket (Section 22).













