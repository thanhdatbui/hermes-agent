# OpenAI Codex OAuth — Phone Verification via 5sim (GPMLogin CDP)

## Tổng quan
Khi chạy OAuth Codex CLI (`auth.openai.com/oauth/authorize?...&originator=codex_cli_rs`),
OpenAI yêu cầu tài khoản phải có số điện thoại đã xác minh (phone_verified = true).
- **Acc chưa có số:** → bị redirect sang `auth.openai.com/add-phone`.
- **Acc đã có số từ trước:** → nhảy thẳng sang màn hình Consent, không hỏi gì thêm.
- **Acc bị ép WhatsApp:** → số ảo bị OpenAI gateway block SMS, chỉ nhận được qua WhatsApp app.

## Quy trình chuẩn đã kiểm chứng (2026-09-24)

### 1. Khởi tạo OAuth
```python
cb = requests.get("http://127.0.0.1:20129/api/oauth/codex/start-callback-server", timeout=15).json()
auth_url = cb.get("authUrl")  # chứa PKCE state + redirect http://localhost:1455/auth/callback
```

### 2. Mở GPM profile & điều hướng (Tránh bẫy `prompt=login`, `ECONNREFUSED` và `ERR_ABORTED`)

**Bẫy 1: Chrome chưa kịp mở WebSocket DevTools (`ECONNREFUSED`):**
API GPM trả về port ngay lập tức nhưng Chrome cần 2–4s để khởi động DevTools WebSocket.
BẮT BUỘC retry kết nối CDP 6 lần (mỗi lần cách 2–3s) và trả về `None` (skip acc an toàn) thay vì để `raise` làm crash toàn bộ script batch:
```python
def connect_cdp_with_retry(pw, cdp, retries=6):
    for i in range(retries):
        try:
            return pw.chromium.connect_over_cdp(f"http://{cdp}")
        except Exception as e:
            if i < retries - 1:
                time.sleep(2.5)
            else:
                print(f"[-] CDP connect failed after {retries} retries: {e}")
                return None
```

**Bẫy 2: Cờ `prompt=login` trong Auth URL (CẤM SKIP NHẦM TƯỞNG VĂNG ACC!):**
URL OAuth của OmniRoute có chứa `&prompt=login&...`. Khi GPM mở lên, OpenAI **LUÔN LUÔN** dừng ở `https://auth.openai.com/log-in` ("Chào mừng trở lại").
- **CẤM TUYỆT ĐỐI** thấy URL `/log-in` là vội vàng kết luận "acc chưa đăng nhập" rồi skip!
- **HÀNH ĐỘNG BẮT BUỘC:** Click ngay nút `Tiếp tục với Google` (`Continue with Google`). Vì profile GPM đã có sẵn Google session, click xong trong 2–4s OpenAI sẽ tự động nhận diện và nhảy thẳng vào `add-phone` hoặc `consent`!
- **Phân biệt Google Session vs ChatGPT Session:**
  - Token trong OmniRoute `chatgpt-web` lưu cookie riêng trong SQLite, gateway vẫn gọi được.
  - Trong GPM trình duyệt, cookie ChatGPT có thể hết hạn, nhưng **Google Session trong GPM vẫn LIVE 100%**. Bấm "Tiếp tục với Google" sẽ SSO ngay mà không cần nhập mật khẩu.
  - Chỉ khi Google chuyển sang `accounts.google.com/v3/signin/identifier` đòi nhập lại email thì acc đó mới thực sự văng Google session.

**Bẫy 3: Lỗi `net::ERR_ABORTED` khi navigate OAuth:**
Ở một số profile có extension hoặc proxy proxy-switch bị chậm, `page.goto(auth_url)` có thể throw `net::ERR_ABORTED`. Phải wrap trong try/except để fail-fast an toàn, tránh vỡ runner.

```python
try:
    page.goto(auth_url, wait_until="domcontentloaded", timeout=30000)
except Exception as e:
    print(f"[-] page.goto failed: {e}")
    return False
page.wait_for_timeout(2500)

# Vòng lặp điều hướng bypass Google OAuth trong 2 click (ĐÃ KIỂM CHỨNG 2026-09-24)
for step in range(8):
    u = page.url
    if "add-phone" in u or ("1455" in u and "callback" in u):
        break
    # 1. Nếu gặp trang log-in, click Tiếp tục với Google
    if "log-in" in u:
        btn_g = page.locator("button:has-text('Tiếp tục với Google'), button:has-text('Continue with Google'), button:has-text('Google')").first
        if btn_g.count() > 0:
            btn_g.click(force=True, timeout=3500)
            page.wait_for_timeout(3500)
            continue
    # 2. Bẫy Google Account Chooser: Profile GPM đã đăng nhập Google sẵn, click ngay thẻ tài khoản
    if "accountchooser" in u or "choose-an-account" in u:
        row = page.locator("[data-identifier], [data-email], li, div[role='link']").first
        if row.count() > 0:
            row.click(force=True, timeout=3500)
            page.wait_for_timeout(3500)
            continue
    # 3. Màn hình Google OAuth Consent / ID (accounts.google.com/signin/oauth/id): Bấm Tiếp tục
    if "accounts.google.com" in u:
        c_btn = page.locator("button:has-text('Tiếp tục'), button:has-text('Continue')").first
        if c_btn.count() > 0:
            c_btn.click(force=True, timeout=3500)
            page.wait_for_timeout(3500)
            continue
    # 4. Form About-you nếu có
    if "about-you" in u:
        short = email.split('@')[0].capitalize()
        ninp = page.locator('input[name="name"]').first
        if ninp.count() > 0 and not ninp.input_value(): ninp.fill(short)
        ainp = page.locator('input[name="age"]').first
        if ainp.count() > 0 and not ainp.input_value(): ainp.fill("24")
        page.locator('button[type="submit"]').first.click(force=True, timeout=3000)
        page.wait_for_timeout(3500)
        continue
    page.wait_for_timeout(1000)
```

**Bẫy 4: Màn hình kiểm tra người dùng của Google (`Verify it's you` / reCAPTCHA):**
Khi profile mở qua IP lạ hoặc đổi proxy, Google có thể chuyển hướng tới:
`https://accounts.google.com/v3/signin/challenge/recaptcha` ("Confirm you're not a robot").
- **Nhận diện:** URL chứa `challenge/recaptcha` hoặc `Verify it's you`.
- **Hành động:** Trình duyệt tự động không thể bypass reCAPTCHA checkbox mà không có người can thiệp. Phải **fail-fast ngay lập tức**, ghi log và skip sang profile khác trong kho thay vì cố click gây timeout 30s.

### ⚠️ Yếu tố Proxy: Mobile 4G vs Datacenter Proxy (Ảnh hưởng trực tiếp đến SMS vs WhatsApp)
- **Mobile 4G Residential Proxy (MobiProxy `test.taadaa.click:51xx`):** OpenAI phân loại là IP người dùng di động sạch $\rightarrow$ Cho phép nhận mã qua SMS thường (đầu số Smart/TNT Philippines).
- **Datacenter / Fixed Proxy (MikroTik `mirotik1.taadaa.click:1000x`):** OpenAI phát hiện dải IP máy chủ trung tâm dữ liệu $\rightarrow$ Tự động bật chế độ rủi ro cao, **vô hiệu hóa hoàn toàn nút SMS** và ép 100% số điện thoại phải nhận mã qua WhatsApp!
- **Kinh nghiệm:** Chỉ chạy quy trình ver số OpenAI Codex trên các profile GPM được gán proxy Mobile 4G (`test.taadaa.click:51xx`). Tuyệt đối không dùng proxy MikroTik để tránh bị ép WhatsApp liên tục làm tốn thời gian.

### 3. ⚠️ LỖI CHÍ MẠNG: Thao tác chọn Quốc gia và WhatsApp vs SMS trên form add-phone

**Form `add-phone` của OpenAI là React Aria Component (Custom Listbox, KHÔNG dùng `<select>` HTML thông thường):**
- Thẻ dropdown quốc gia là `<button aria-haspopup="listbox">`.
- Danh sách các nước là các item `[role="option"]` chỉ render khi listbox mở.
- **CẤM:** Dùng `page.locator("select").select_option(...)` vì trang không có thẻ `<select>` chuẩn, sẽ gây TimeoutError!
- **CÁCH CHUẨN DUY NHẤT:** Click mở listbox, dùng `keyboard.type` để nhảy nhanh tới `Philippines` rồi click option:
```python
btn = page.locator("button[aria-haspopup='listbox']").first
if "Philippines" not in btn.text_content() and "+63" not in btn.text_content():
    btn.click()
    page.wait_for_timeout(500)
    page.keyboard.type("Philippines")
    page.wait_for_timeout(500)
    ph_opt = page.locator("[role='option']:has-text('Philippines')").first
    if ph_opt.count() > 0:
        ph_opt.click()
        page.wait_for_timeout(500)
```

**BẮT BUỘC CHỌN KÊNH SMS THAY VÌ WHATSAPP:**
- OpenAI mặc định chọn WhatsApp (`input[value='whatsapp']`).
- Nếu không chủ động click chọn `Tin nhắn văn bản` (SMS), OpenAI sẽ gửi mã OTP qua WhatsApp khiến 5sim không bao giờ nhận được SMS!
- **Xử lý chuẩn:**
```python
page.evaluate("""() => {
    const inputs = Array.from(document.querySelectorAll("input[type='radio']"));
    const smsInput = inputs.find(i => i.value && i.value.includes('sms'));
    if (smsInput && !smsInput.checked) smsInput.click();
}""")
page.wait_for_timeout(500)
```

**LỖI KHÁC: SMS radio bị ép sang WhatsApp sau khi gặp lỗi:**
- Khi OpenAI từ chối 1 số (gửi HTTP 400 → hiện warning "chuyển sang WhatsApp"),
  React **tự động disable** radio SMS và set `<input name="channel" value="whatsapp">`.
- Các lần submit tiếp theo sẽ ĐỀU bị gửi `channel=whatsapp` dù cứ click vào radio SMS.
- **GIẢI PHÁP:** Mỗi lần đổi số MỚI phải load lại OAuth URL hoàn toàn từ đầu để reset form.

### 4. Click "Tin nhắn văn bản" (SMS)
```python
page.locator("label:has-text(\"Tin nhắn văn bản\")").first.click()
page.wait_for_timeout(500)
```

### 5. Điền số điện thoại (từ 5sim)
```python
tel = page.locator("input[type='tel']").first
tel.fill("")
tel.fill(local_num)  # Chỉ phần local, không kèm mã vùng quốc gia (+63)
```

### 6. Submit & nhận OTP từ 5sim
```python
page.locator("button[type='submit']").first.click()
page.wait_for_timeout(3500)
```

### 7. Phát hiện kết quả Submit ngay lập tức

| URL sau khi submit | Ý nghĩa | Hành động |
|---|---|---|
| `https://auth.openai.com/phone-verification` | ✅ OpenAI đã gửi SMS | Poll 5sim chờ OTP |
| URL vẫn là `add-phone` + body chứa "WhatsApp" | ❌ Đầu số bị block SMS | Cancel 5sim ngay, reset form, mua số mới |
| URL vẫn là `add-phone` + body chứa "quá nhiều lần" | ❌ Acc bị rate-limit | Dừng acc này 12–24h |
| `add-phone` + lỗi `invalid_auth_step` | Phiên OAuth hết hạn | Reset: gọi `start-callback-server` mới |

### 8. Hoàn tất OAuth & Chuỗi bằng chứng Gate 6 Bắt buộc

**Quy tắc Gate 6 cho tác vụ Codex OAuth (ĐỦ 4 CHECKPOINT - CẤM DỪNG NỬA CHỪNG):**
1. **Checkpoint 1 (Pre-submit):** Form đã điền số + Radio SMS `Tin nhắn văn bản` bật `data-state="on"`.
2. **Checkpoint 2 (Post-submit):** OpenAI chấp nhận số và chuyển sang màn hình `phone-verification` ("Kiểm tra điện thoại").
3. **Checkpoint 3 (OTP Filled - BẮT BUỘC):** Mã OTP nhận từ 5sim đã được điền vào form trước khi bấm Tiếp tục (`code_input.fill(otp)` xong là BẮT BUỘC chụp ảnh ngay, cấm bấm submit rồi tab đóng mất ảnh).
4. **Checkpoint 4 (Final Proof / Success - BẮT BUỘC):** Màn hình Consent / `Authentication Successful` (Callback port 1455) HOẶC Bảng điều khiển OmniRoute (`/dashboard/providers/codex`) hiển thị rõ số lượng kết nối tăng lên và Connection ID mới hoạt động.

### ⚠️ KỶ LUẬT BẢO VỆ NICK: CHỐNG SPAM SỐ ĐIỆN THOẠI TRÊN FORM ADD-PHONE (ANTI-BAN OPENAI)
- **Rủi ro chí mạng với nick mới:** Nick mới toanh (mới tạo/mới ngâm) có điểm trust thấp. Nếu script nhồi số điện thoại liên tiếp (3–5 số trong vòng 1–2 phút sau khi OpenAI từ chối), hệ thống kiểm duyệt OpenAI sẽ gắn cờ **Phone Brute-force / Verification Abuse** và lập tức vô hiệu hóa/ban vĩnh viễn tài khoản!
- **3 Quy tắc bắt buộc khi chạy script batch:**
  1. **Khống chế số lần thử tối đa (`MAX_ATTEMPTS_PER_ACC = 2`):**
     - Mỗi tài khoản chỉ được phép thử **tối đa 2 số điện thoại**.
     - Nếu cả 2 số đều bị OpenAI từ chối $\longrightarrow$ **DỪNG NGAY**, hủy đơn hoàn tiền trên 5sim, đóng profile GPM và chuyển sang profile tiếp theo. TUYỆT ĐỐI KHÔNG thử lần thứ 3.
  2. **Giãn cách an toàn (Stagger Cooldown):**
     - Giữa 2 lần submit số trên cùng 1 acc: Bắt buộc nghỉ **6 giây**.
     - Giữa 2 profile khác nhau trong batch: Bắt buộc nghỉ **6 giây** để OpenAI gateway reset nhịp request.
  3. **Độc lập IP Proxy:**
     - 100% profile phải đi qua proxy riêng biệt (ưu tiên Mobile 4G `test.taadaa.click:51xx`), không dùng chung 1 IP cho nhiều lần submit.

### 🇦🇷 Chiến thuật Đầu số Argentina (+54, virtual62, $0.05) — Tiết Kiệm & Hiệu Quả Đã Kiểm Chứng (2026-09-24)
- **Chi phí siêu rẻ:** Chỉ **$0.05 / SIM** (tiết kiệm 55% chi phí so với Philippines $0.1077).
- **Tỷ lệ thành công:** Đạt **12.99%** (cao gấp 2.5 lần Philippines 5.08%).
- **Thực nghiệm thành công:** Tài khoản `cathoa060149@gmail.com` đã nhận thành công mã OTP `597605` từ đầu số Argentina `+543743546556`, hoàn tất OAuth Codex tạo Connection `ff82d381-b182-40c9-9ecd-0d5bf911bf80`.
- **Cách điền số Argentina trên form add-phone:**
  - Chọn quốc gia `Argentina (+54)`.
  - Bỏ tiền tố `+54`, lấy chuỗi số phía sau (ví dụ: `+543743546556` $\rightarrow$ điền `3743546556`).
  - Chọn radio `Tin nhắn văn bản` (`SMS`).
  - Nếu OpenAI chấp nhận $\rightarrow$ chờ OTP trong 45 giây $\rightarrow$ nhận OTP điền vào form $\rightarrow$ finish đơn trên 5sim. Nếu OpenAI từ chối $\rightarrow$ cancel đơn hoàn tiền ngay.

### ⚠️ KỶ LUẬT BẢO TOÀN VỐN: KHÔNG BỎ RƠI PROFILE ĐÃ CẮN OTP (ANTI-WASTE CAPITAL)
- **Khi 5sim đã trả SMS OTP và điền vào OpenAI:** Số tiền thuê SIM ($0.1077) coi như ĐÃ BỊ TRỪ KHÔNG THỂ HOÀN LẠI.
- **BẮT BUỘC TUYỆT ĐỐI:** Phải bám sát giải quyết dứt điểm tài khoản này đến khi ra `Authentication Successful` và nạp vào OmniRoute combo pool. CẤM TUYỆT ĐỐI bỏ dở giữa chừng hay chuyển sang test nick khác làm mất tiền oan của user!
- **Bẫy Onboarding 2 tầng sau khi nhập OTP:**
  1. **Tầng 1 — Tuổi & Họ tên (`about-you`):**
     - Form: *"How old are you?"* (`input[name="age"]` hoặc `input[type="number"]`).
     - Tự động điền tuổi (ví dụ: `24`, clamp >= 18) rồi bấm `Continue`.
  2. **Tầng 2 — Chọn Không gian làm việc (`Select a workspace`):**
     - Form hiện radio `Personal account` (đã checked sẵn). Phải scroll xuống bấm nút `Continue` dưới cùng.
  3. **Bẫy Session Expired sau khi điền onboarding ("Your login session has expired"):**
     - Cứu bằng cách cho tab mở thẳng: `https://chatgpt.com/auth/login_with?callback_path=%2F&connection=google-oauth2&screen_hint=login_or_signup` để ăn Google session vào ChatGPT $\rightarrow$ hiện *"You're all set"*.
     - Gọi lại API OmniRoute: `GET http://127.0.0.1:20129/api/oauth/codex/start-callback-server` để lấy `authUrl` mới toanh $\rightarrow$ Màn hình Consent bấm `Continue` $\rightarrow$ `Authentication Successful`.

### ⚠️ Bẫy Kỹ thuật Playwright CDP & Extension khi Batch Verification
1. **Bẫy Tab Extension chiếm slot 0 (`chrome-extension://.../offscreen.html`):**
   - Nhiều profile GPM có cài MetaMask hoặc ví Web3. Khi khởi động, tab index 0 là trang nền extension không có kích thước màn hình.
   - Gọi `b.contexts[0].pages[0]` hoặc chụp ảnh sẽ bị lỗi: `Protocol error (Page.captureScreenshot): Cannot take screenshot with 0 width` và `TargetClosedError`.
   - **Xử lý chuẩn:**
     ```python
     pages = [pg for pg in context.pages if not pg.url.startswith("chrome-extension://")]
     page = pages[0] if pages else context.new_page()
     ```
2. **Bẫy Google Material Ripple Overlay chặn click (`VfPpkd-Sx9Kwc... intercepts pointer events`):**
   - Trên màn hình `choose-an-account` hoặc `accountchooser` của Google, luôn click bằng `force=True` hoặc click tọa độ tâm bounding box.
3. **Cơ chế Auto-Clean Orders chống rò rỉ tiền 5sim khi Exception/Interrupt:**
   - Khi chạy script batch hoặc gặp crash/kill, các order 5sim ở trạng thái `PENDING` hoặc `RECEIVED` nếu không được cancel sẽ bị giữ tiền hoặc tính phí oan.
   - BẮT BUỘC có hàm dọn dẹp quét lại đơn active trước khi thoát hoặc khởi động.

---

## 5sim — SIM tốt nhất cho OpenAI (cập nhật 2026-09-24)

### Xếp hạng thực tế & Khảo sát 118 quốc gia từ 5sim API:

| Quốc gia | Nhà mạng | Giá ($) | Kho SIM | Tỷ lệ nổ OTP | Kết quả kiểm chứng thực tế trên OpenAI Gateway |
|:---|:---|:---:|:---:|:---:|:---|
| 🇬🇧 **England (Anh)** | `virtual58` | **$0.1815** | 1,083 | **23.64%** | 🔥 **Tỷ lệ cao gấp gần 5 lần Philippines.** Đầu số UK (+44) sạch, OpenAI duyệt nhanh, test mua có số ngay lập tức. |
| 🇦🇷 **Argentina** | `virtual62` | **$0.0500** | 568 | **12.99%** | 💰 **Siêu rẻ (chỉ bằng 1/2 Philippines)**, tỷ lệ nổ OTP vẫn cao gấp 2.5 lần Philippines (13% vs 5%). Test mua có số ngay. |
| 🇵🇭 **Philippines** | `virtual58` | **$0.1077** | 1,340 | **5.08%** | ⚠️ Hoạt động nhưng tỷ lệ khá thấp (5%). Chỉ đầu số **Smart / TNT** (`970`, `907`, `930`, `919`, `920`, `928`, `929`) là nhận SMS. Các đầu Globe (`927`, `936`, `945`, `956`) và DITO (`960`) bị ép WhatsApp 100%. |
| 🇺🇸 USA | `virtual63` | $0.1483 | 1,182 | 80.95% | Tỷ lệ cực cao nhưng thường xuyên báo `no free phones` (hết hàng ảo). |
| 🇻🇳 Vietnam | `virtual34` | $0.1025 | 258k | 28.57% | Rẻ hơn Philippines nhưng hiện tại trả về `no free phones`. |

### Quy luật bắt đầu số vàng Philippines (Golden Prefixes):
1. **Đầu số VÀNG Smart/TNT (`0970`, `0907`, `0930`, `0919`, `0920`, `0928`, `0929`):**
   - 100% tài khoản thành công (`vothimyhanh`, `chuloan`, `buitrang`, `lequynh`, `luunhu`, `dinhlan`, `caoanh`...) đều nằm ở dải này.
   - OpenAI chấp nhận gửi SMS ngay trong 10–20 giây, mã OTP về chuẩn xác.
2. **Chiến thuật săn số vàng không tốn tiền (Zero-cost Hunting):**
   - Mua số Philippines `virtual58`.
   - Bóc 3 chữ số đầu của `local_num` (`phone[4:7]`):
     - Nếu thuộc dải vàng Smart/TNT: **GIỮ LẠI ĐIỀN VÀO FORM $\rightarrow$ ĂN NGAY.**
     - Nếu KHÔNG thuộc dải trên: **GỌI NGAY API `cancel/{oid}` TRONG 0.2 GIÂY.**
     - Khi chưa có SMS, 5sim hoàn tiền 100% ngay lập tức. Ta có thể quét 20–30 lần liên tục mà số dư ví không hao hụt 1 xu.

### ⚠️ Bẫy Onboarding Post-OTP (Nguyên nhân thất bại sau khi đã trừ tiền OTP)
- Sau khi nhập 6 số OTP thành công, OpenAI chuyển hướng sang `https://auth.openai.com/about-you`.
- Nếu script không xử lý `about-you` (điền tên và tuổi `24` rồi bấm Submit), trang web sẽ kẹt lại và callback OAuth port 1455 sẽ bị timeout.
- **HẬU QUẢ NGHIÊM TRỌNG:** Tiền thuê SIM 5sim đã bị trừ ($0.1077 / $0.1815) nhưng tài khoản không được nạp vào OmniRoute!
- **BẮT BUỘC:** Vòng lặp sau khi điền OTP phải quét 3–4 lần:
  ```python
  for _ in range(4):
      page.wait_for_timeout(2000)
      if "about-you" in page.url:
          short_name = email.split('@')[0].capitalize()
          ninp = page.locator('input[name="name"]').first
          if ninp.count() > 0: ninp.fill(short_name)
          ainp = page.locator('input[name="age"]').first
          if ainp.count() > 0: ainp.fill("24")
          sbtn = page.locator('button[type="submit"]').first
          if sbtn.count() > 0:
              sbtn.click()
              page.wait_for_timeout(4000)
      if "consent" in page.url or page.locator("button:has-text('Continue'), button:has-text('Tiếp tục')").count() > 0:
          page.locator("button:has-text('Continue'), button:has-text('Tiếp tục')").first.click()
          page.wait_for_timeout(4000)
  ```

---

## Quy trình Đồng bộ 2 Chiều: ChatGPT-Web Pool ⟷ Codex Pool

### Chiều 1: Từ Codex ⟶ ChatGPT-Web Pool
Các nick đã có trên Codex nếu chưa có trên `chatgpt-web`:
1. Mở GPM Profile tương ứng qua CDP.
2. Điều hướng vào `https://chatgpt.com`, trích xuất toàn bộ cookie domain `https://chatgpt.com`.
3. Kiểm tra có cookie `__Secure-next-auth.session-token`. Nếu chưa có: bấm "Tiếp tục với Google" để ăn session Google sẵn có trong profile.
4. Validate qua OmniRoute:
   ```python
   v = requests.post("http://127.0.0.1:20129/api/providers/validate", json={"provider": "chatgpt-web", "apiKey": cookie_str}).json()
   assert v.get("valid") is True
   ```
5. **Tạo Connection:** BẮT BUỘC dùng endpoint `POST /api/providers` (CẤM gọi `/api/providers/connections` vì route này trả về 404):
   ```python
   res = requests.post("http://127.0.0.1:20129/api/providers", json={
       "provider": "chatgpt-web",
       "name": f"{email} (GPM Web)",
       "apiKey": cookie_str,
       "isActive": True
   }).json()
   cid = res.get("connection", {}).get("id") or res.get("id")
   ```
6. Gán Proxy 1-1 (`PUT /api/settings/proxies/assignments`) và thêm vào combo `chatgpt-web-pool` (`9c68197d-410a-4267-a3e7-c843aa82cab0`).

### Chiều 2: Từ ChatGPT-Web ⟶ Codex Pool
Các nick đã có trên `chatgpt-web` nếu chưa có trên Codex:
1. Mở GPM Profile tương ứng qua CDP.
2. Khởi chạy callback server: `GET /api/oauth/codex/start-callback-server` $\rightarrow$ lấy `authUrl`.
3. Điều hướng tới `authUrl`, click chọn Google / thẻ tài khoản email.
4. Nếu gặp form `add-phone`:
   - Chuyển quốc gia về Philippines (`+63`).
   - Chọn radio `Tin nhắn văn bản` (`SMS`).
   - Săn SIM Smart TNT Philippines ($0.1077) trên 5sim, submit số, bắt mã OTP SMS điền vào form.
5. Xử lý màn hình onboarding `about-you` (điền tên + tuổi `24`) và Consent (`Continue`).
6. Poll callback server: `POST /api/oauth/codex/poll-callback` để nhận `connection.id`.
7. Gán Proxy 1-1 (`PUT /api/settings/proxies/assignments`) và thêm vào combo `codex-terra-pool` (`6a11df82-c1ba-4bb7-b8e7-5cda108ee11f`).
8. Test inference HTTP 200 qua `/v1/chat/completions` để nghiệm thu.

---

## Tự Động Phục Hồi Session Google (Google Login + TOTP) & Giám Sát 3 Pool

### Tự động xử lý khi Profile GPM văng Google Session:
Khi điều hướng OAuth mà bị Google đẩy về `accounts.google.com/v3/signin/identifier`:
1. Tra cứu thông tin tài khoản từ CSDL Master (`master_gmail_manager.xlsx`, sheet `Master_All`):
   - Cột B: `Email`
   - Cột C: `Password`
   - Cột E: `2FA_Secret` (chuỗi base32 32 ký tự)
2. Điền email vào `#identifierId` $\rightarrow$ Next $\rightarrow$ Điền password vào `input[name="Passwd"]` $\rightarrow$ Next.
3. Khi gặp challenge 2FA (`challenge/totp` hoặc `#totpPin`):
   - Tính mã OTP động: `code = pyotp.TOTP(totp_secret).now()`.
   - Điền vào `#totpPin` $\rightarrow$ Next.
4. Xử lý màn hình cấp quyền Consent Google (`button:has-text("Tiếp tục")` / `Continue`) để quay lại luồng OpenAI.
5. **Cảnh báo Checkpoint reCAPTCHA:** Nếu gặp `challenge/recaptcha`, lập tức skip acc, không cố retry.

### Giám sát sức khỏe 3 Pool trên OmniRoute (:20129) qua Watchdog:
Script watchdog (`cron_chatgpt_web_pool_watchdog.py`) kiểm tra định kỳ 3 provider:
- **ChatGPT-Web:** Validate cookie qua `/api/providers/validate`. Nếu hỏng: mở GPM profile ăn lại Google Session / direct OAuth.
- **Antigravity:** Quét `testStatus`. Nếu chỉ bị tắt toggle (`isActive=0`): auto-heal bật lại bằng SQLite. Nếu hỏng token: chạy lại OAuth consent.
- **Codex:**
  - Nếu bị tắt toggle: tự động bật lại qua SQLite `UPDATE provider_connections SET is_active=1`.
  - **ĐẶC TÍNH BẮT BUỘC:** OmniRoute KHÔNG hỗ trợ `/api/providers/{id}/refresh-token` cho provider `codex` (trả về lỗi `Manual token refresh not supported for provider codex`).
  - Khi token Codex bị lỗi 401 (`Token invalid or revoked`), **BẮT BUỘC** phải chạy lại luồng OAuth hoàn chỉnh (`start-callback-server` + CDP GPM) để lấy token mới, không được gọi API refresh đơn lẻ.

---

## Đối Soát Đồng Bộ Đa Combo Codex (`codex-terra-pool` ⟷ `codex-luna-pool`)

### Bản chất kiến trúc Combos Codex trên OmniRoute:
1. **Các combo model Codex:**
   - `codex-terra-pool`: Model `codex/gpt-5.6-terra` (18/18 accounts).
   - `codex-luna-pool`: Model `codex/gpt-5.6-luna-medium` (18/18 accounts).
   - `codex-terra`: Model alias ngắn `codex/gpt-5.6-terra`.
   - `codex-luna`: Model alias ngắn `codex/gpt-5.6-luna-medium`.
2. **Quy tắc đồng bộ bắt buộc (All-or-Nothing Sync):**
   - Mọi tài khoản Codex mới sau khi OAuth thành công BẮT BUỘC phải nạp đồng thời vào cả 4 combo trên.
   - Tránh bẫy lệch tài khoản: Một combo có 18 acc nhưng combo kia chỉ có 7 acc sẽ khiến tải dồn cục bộ làm rate-limit dải acc cũ.
   - Script cập nhật combo phải đồng bộ danh sách `connectionId` từ `codex-terra-pool` sang `codex-luna-pool`, `codex-terra` và `codex-luna` với đúng định dạng model ID tương ứng:
     ```python
     combos = requests.get("http://127.0.0.1:20129/api/combos").json().get("combos", [])
     terra = [c for c in combos if c.get("name") == "codex-terra-pool"][0]
     luna = [c for c in combos if c.get("name") == "codex-luna-pool"][0]
     # Ánh xạ connectionId sang codex/gpt-5.6-luna-medium và PUT cập nhật
     ```
3. **Phân tích số liệu lệch tài khoản giữa Pool Web và Pool Codex:**
   - Số lượng Web (21) - Codex (18) = 3 tài khoản lệch.
   - Thực chất gồm: 4 tài khoản Web chưa qua Codex (1 tài khoản DIE trong DB, 1 tài khoản bị OpenAI xóa, 1 tài khoản vướng reCAPTCHA robot, 1 tài khoản bị Cloudflare chặn) và 1 tài khoản Codex Session CLI local (`~/.codex/auth.json`) không có trên Web.
   - Khi báo cáo đối soát cho user, BẮT BUỘC phải phân tích rõ danh tính từng tài khoản thuộc nhóm nào để tránh gây hiểu nhầm về độ toàn vẹn của dữ liệu.

---

## Phân Tích Nguyên Nhân Tài Khoản ChatGPT Web Bị Ban Từ OmniRoute `call_logs`

Khi một tài khoản trong `chatgpt-web-pool` đột ngột bị OpenAI vô hiệu hóa ("Tài khoản đã xóa hoặc vô hiệu hóa"), truy vấn bảng `call_logs` trong `C:\Users\Kibe\.omniroute\storage.sqlite` để xác định chuỗi nguyên nhân:
1. **Dồn dập lỗi HTTP 413 (Payload Too Large):**
   - Các client agentic (Cline, Kilo, Roo) gửi context prompt hoặc đính kèm file quá lớn so với giới hạn của giao diện Web thông thường.
   - Lỗi này lặp đi lặp lại nhiều lần làm tài khoản bị xếp vào diện rủi ro cao (anomalous client behavior).
2. **Kích hoạt lá chắn Sentinel / Turnstile (HTTP 403):**
   - Hệ thống Cloudflare / Sentinel của OpenAI phát hiện traffic giả lập web qua IP proxy trung tâm dữ liệu hoặc gửi request bất thường -> Chặn HTTP 403 đòi giải Turnstile.
3. **Vô hiệu hóa tài khoản vĩnh viễn:**
   - Sau khi dính cờ Sentinel, hệ thống kiểm duyệt tự động của OpenAI khóa tài khoản và trả về lỗi:
     *"Bạn không có tài khoản vì tài khoản đã xóa hoặc vô hiệu hóa. ID yêu cầu: <uuid>"*.
4. **Quy tắc phân lập tài sản:**
   - **Tài khoản Google gốc vẫn LIVE 100%:** Chỉ có dịch vụ ChatGPT Web bị OpenAI ban. Tài khoản Google vẫn đăng nhập bình thường và tiếp tục phục vụ provider Antigravity (`gemini-3.8-flash-tiered`) với hàng ngàn request không bị ảnh hưởng.
   - Hành động: Xóa connection hỏng khỏi `chatgpt-web-pool`, giữ nguyên tài khoản bên Antigravity.

---

## Chuẩn Hóa Core Module Đăng Nhập Gmail Tích Hợp Audio reCAPTCHA (User Directive 2026-09-24)

Để tránh phân mảnh code đăng nhập Google rải rác ở nhiều script con, quy trình đăng nhập Gmail qua GPM Profile BẮT BUỘC tuân thủ chuẩn module dùng chung:
1. **Thứ tự các bước xử lý:**
   - Nhập Email vào `#identifierId` -> Bấm Next.
   - Nhập Password vào `input[name="Passwd"]` -> Bấm Next.
   - **Giải reCAPTCHA tự động (Audio Solver):** Nếu Google kích hoạt màn hình `Verify it's you` (`accounts.google.com/v3/signin/challenge/recaptcha`):
     + Tự động chuyển sang Audio Challenge (`#recaptcha-audio-button`).
     + Tải file âm thanh MP3 về thư mục tạm, chuyển đổi sang WAV bằng FFmpeg.
     + Nhận diện giọng nói qua `speech_recognition` (Google Speech API miễn phí).
     + Điền kết quả text vào `#audio-response` và bấm Verify để vượt qua checkpoint tự động.
   - **2FA TOTP Challenge:** Nếu gặp `challenge/totp` hoặc `#totpPin`:
     + Đọc `2FA_Secret` từ `master_gmail_manager.xlsx`.
     + Tính mã `pyotp.TOTP(secret).now()` và điền tự động.
   - **Consent / Cho phép:** Click nút cho phép ủy quyền hoặc tiếp tục để hoàn tất đăng nhập.
2. **Quy tắc tái sử dụng:**
   - Mọi script tạo mới liên quan đến đăng nhập Google / OAuth (Codex OAuth, ChatGPT Web hồi sinh, Antigravity hồi sinh) BẮT BUỘC gọi hàm core chung này, không tự viết lại logic đăng nhập thô thiếu audio solver.
