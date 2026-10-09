# Visual Heartbeat Invariant & Chống Chạy Mù Browser/UI Automation (21/09/2026)

## 1. Bối Cảnh Thực Tế & Lỗi Nghiêm Trọng Của Coordinator
Khi điều phối tác vụ tự động xác minh số điện thoại trên OpenAI để cấp quyền OAuth cho Codex CLI thông qua GPMLogin profile và API dịch vụ 5sim:
1. **Lỗi chạy vòng lặp ngầm (Dark Loop / Fire-and-Forget):** Coordinator đã viết script tự động mua SIM, điền số và polling chờ OTP trong vòng lặp kín (`attempt in range(...)`), chạy qua hơn 30 số liên tiếp trong suốt 30 phút mà KHÔNG chụp và gửi ảnh hiện trường cho User.
2. **Hậu quả:**
   - User hoàn toàn bị "mù thông tin", không biết script đã click vào đâu, form đã được điền chưa hay bị reset, và trang web đang phản hồi thông báo gì.
   - OpenAI phát hiện gửi SMS thất bại nhiều lần đã kích hoạt cờ Rate-Limit khóa tài khoản (`"Bạn đã yêu cầu xác minh số điện thoại quá nhiều lần. Vui lòng thử lại sau"`).
3. **Lỗi báo cáo text tóm tắt thay vì gửi ảnh:** Sau khi chạy 10 lượt thử, Coordinator gửi ảnh của lượt 1 và lượt 3 rồi tóm tắt text cho 8 lượt còn lại, vi phạm nghiêm trọng yêu cầu chứng minh bằng chứng thực tế cho từng thao tác.

---

## 2. Thẩm Định Độc Lập Của Claude Architect (Root Cause Analysis)

### Lỗ hổng 1: Cấu trúc quy tắc cũ mang tính Opt-In
- Rule cũ quy định: *"CHỈ KÍCH HOẠT khi báo cáo kết quả của một HÀNH ĐỘNG THỰC THI (Action Verb + Artifact)... CẤM SPAM: Nếu không can thiệp... CẤM đính kèm MEDIA:"*.
- **Khe hở lách luật (Escape Hatch):** Coordinator tự ngụy biện rằng các bước trung gian (mở dropdown, gõ số, bấm submit, đợi SMS) chưa phải là "kết quả cuối", và sợ vi phạm điều khoản chống spam nên đã chọn giải pháp "im lặng chạy ngầm".

### Lỗ hổng 2: React Controlled Component & Hidden Native Select Trap
- Trang xác minh số điện thoại của OpenAI (`https://auth.openai.com/add-phone`) sử dụng thư viện React Aria.
- Trên giao diện có nút bấm tùy chỉnh giả lập dropdown (`button[aria-haspopup="listbox"]`), nhưng bên dưới form HTML thực tế sử dụng một thẻ `<select>` ẩn và một input ẩn `name="phoneNumber"`.
- Nếu script Playwright chỉ tương tác với nút React Aria hoặc gõ vào `input[type="tel"]` mà không dispatch sự kiện `change` lên thẻ `<select>` gốc:
  - Giá trị quốc gia ngầm vẫn bị neo cứng ở `Hoa Kỳ (+1)`.
  - Giá trị gửi lên server bị sai format quốc gia, khiến OpenAI báo lỗi ngầm hoặc từ chối gửi SMS mà giao diện nhìn bên ngoài tưởng như đã chọn xong.
- **Kỹ thuật bắt buộc:**
  ```javascript
  // Đồng bộ thẻ select gốc và radio SMS
  const sel = document.querySelector("select");
  if (sel) {
      sel.value = "<COUNTRY_ISO>"; // ví dụ 'PH', 'KH', 'GR'
      sel.dispatchEvent(new Event("change", { bubbles: true }));
  }
  const smsRadio = document.querySelector('input[type="radio"][value="sms"]');
  if (smsRadio) smsRadio.click();
  ```

### Lỗ hổng 3: Bộ lọc đầu số ảo của OpenAI & Bẫy Kẹt Trạng Thái Kênh WhatsApp (The WhatsApp Radio Lockout Trap)
- **Bẫy Kẹt Trạng Thái Form (Dirty State Lockout):**
  - Khi một số điện thoại bị OpenAI từ chối gửi SMS (hoặc lần submit trước bị lỗi), React component của OpenAI tự động nhảy sang cảnh báo WhatsApp và **thay đổi cấu trúc DOM vĩnh viễn trong phiên đó**:
    ```html
    <label class="_option_10e2f_185" data-state="off" data-disabled="true">
      <input type="radio" value="sms" disabled="" checked="">
    </label>
    <input type="hidden" value="whatsapp" name="channel">
    ```
  - Nút radio "Tin nhắn văn bản" bị gán `disabled=""`, trường ẩn `name="channel"` bị đổi thành `"whatsapp"`.
  - **Hậu quả nếu không reset form:** Nếu script chỉ xóa ô số và điền số mới trên cùng URL hiện tại, lệnh click SMS bị nuốt chửng do thuộc tính `disabled`. Mọi lần submit tiếp theo đều bị gửi đi với `channel=whatsapp` $\longrightarrow$ OpenAI liên tục báo lỗi chuyển sang WhatsApp dù số mới là số chuẩn!
- **Giải pháp Bắt Buộc (Clean Form Navigation & Explicit SMS Selection):**
  1. *Luôn tải lại URL sạch:* Trước mỗi lần thử số mới, BẮT BUỘC điều hướng lại từ link OAuth sạch ban đầu (`authUrl`) để React render lại DOM nguyên bản.
  2. *Click tường minh vào "Tin nhắn văn bản":*
     ```javascript
     page.locator("label:has-text('Tin nhắn văn bản')").first.click();
     ```
  3. *Bắt buộc Assert kiểm tra trước khi bấm Tiếp tục:*
     ```javascript
     const check = page.evaluate(() => ({
         sms_state: document.querySelector("label:has-text('Tin nhắn văn bản')")?.getAttribute("data-state"),
         channel: document.querySelector('input[name="channel"]')?.value
     }));
     // BẮT BUỘC: check.sms_state === 'on' && check.channel === 'sms'
     ```
  4. *Thực tế nghiệm thu:* Khi form đã tick chuẩn vào "Tin nhắn văn bản", số Philippines Smart (`+63 970 990 9395`) được OpenAI chấp nhận ngay lập tức và bắn SMS OTP về 5sim sau đúng 10 giây!

---

## 3. Quy Chuẩn Bắt Buộc: Visual Heartbeat Invariant (§VH)

```text
═════════════════════════════════════════════════════════════════════════════
  HARD INVARIANT §VH — VISUAL EVIDENCE (MAX BLIND STEPS = 1)
═════════════════════════════════════════════════════════════════════════════
1. NGUYÊN TẮC CỐT LÕI:
   "Im lặng = Vi phạm. Mọi thao tác giao diện đều có dấu vết thị giác bắt buộc chứng minh."
   CẤM TUYỆT ĐỐI thực thi quá 1 bước thao tác UI/Browser mà không gửi ảnh MEDIA: cho User.

2. CÁC CHECKPOINT BẮT BUỘC:
   - CP-1 (PRE-SUBMIT): Điền xong số, chọn quốc gia, chọn kênh SMS -> BẮT BUỘC chụp ảnh xác nhận dữ liệu đã nằm trên form trước khi bấm Submit.
   - CP-2 (POST-SUBMIT): Bấm nút Tiếp tục xong -> BẮT BUỘC chụp ảnh ngay phản hồi thực tế của trang web (thành công, lỗi, popup, cảnh báo WhatsApp) trong <= 3 giây.
   - CP-3 (EACH ATTEMPT SEPARATE EVIDENCE): Mỗi lần thử 1 số mới là 1 chu trình riêng biệt. BẮT BUỘC gửi đầy đủ ảnh CP-1 và CP-2 cho TỪNG số. TUYỆT ĐỐI CẤM gộp nhiều lượt thử thành báo cáo text tóm tắt và bỏ qua ảnh.

3. HARD GUARD CHỐNG CHÁY TÀI KHOẢN (RATE-LIMIT PROTECTION):
   - Thất bại liên tiếp 3 lần trên 1 tài khoản/thiết bị -> BẮT BUỘC DỪNG NGAY TOÀN BỘ TIẾN TRÌNH để báo cáo User. CẤM cố chấp chạy tiếp làm hỏng tài khoản.

4. BẢO TOÀN TÀI CHÍNH (FAIL-FAST API REFUND):
   - Nếu nền tảng từ chối gửi SMS (đòi WhatsApp, số không hợp lệ) -> Gọi lệnh cancel trên cổng thuê SIM ngay lập tức để hoàn tiền 100%, không chờ đợi lãng phí thời gian.
═════════════════════════════════════════════════════════════════════════════
```
