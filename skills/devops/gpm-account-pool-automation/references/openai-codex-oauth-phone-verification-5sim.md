# Quy Trình Tự Động Xác Minh Số Điện Thoại OpenAI Cấp Quyền Codex CLI Qua 5sim & GPMLogin

## 1. Bối Cảnh & Kiến Trúc
Để đưa tài khoản ChatGPT từ pool GPMLogin sang cấp quyền Codex CLI (`codex` provider trên OmniRoute/9Router), OpenAI yêu cầu hoàn tất OAuth flow `offline_access`.
- **Cổng xác thực:** `https://auth.openai.com/add-phone` (yêu cầu verify SĐT nhận mã OTP SMS 1 lần).
- **Môi trường:** GPMLogin Profile (Playwright CDP port) + 5sim API mua SIM nhận mã.

---

## 2. Các Cạm Bẫy DOM & Bộ Lọc OpenAI

### 1. Bẫy React Aria Dropdown vs. Hidden Native Select
- Giao diện OpenAI hiển thị nút dropdown tùy chỉnh `button[aria-haspopup="listbox"]` nhưng form submit ngầm bằng thẻ `<select>` gốc và `<input type="hidden" name="phoneNumber">`.
- Nếu chỉ click trên UI mà không dispatch sự kiện `change` lên thẻ `<select>`, mã vùng submit thực tế vẫn bị neo ở `US (+1)`.
- **Giải pháp chuẩn:**
  ```python
  page.evaluate(f"""() => {{
      const sel = document.querySelector("select");
      if (sel) {{
          sel.value = "{country_iso}"; // ví dụ 'PH'
          sel.dispatchEvent(new Event("change", {{ bubbles: true }}));
      }}
  }}""")
  ```

### 2. Bẫy Kẹt Trạng Thái Kênh WhatsApp (The WhatsApp Radio Lockout Trap)
- Khi một số điện thoại bị từ chối hoặc submit lỗi trước đó, OpenAI tự động chuyển sang cảnh báo WhatsApp và vô hiệu hóa radio SMS:
  `<input type="radio" value="sms" disabled>` kèm `<input type="hidden" name="channel" value="whatsapp">`.
- Nếu tiếp tục điền số mới trên cùng URL hiện tại, mọi request submit sau đó đều gửi `channel=whatsapp` $\longrightarrow$ OpenAI không bao giờ gửi SMS!
- **Giải pháp chuẩn:**
  1. Mỗi lần thử số mới **BẮT BUỘC** tải lại từ URL OAuth sạch (`authUrl` từ OmniRoute).
  2. Click tường minh vào nhãn SMS: `page.locator("label:has-text('Tin nhắn văn bản')").first.click()`.
  3. Assert kiểm tra:
     ```python
     check = page.evaluate("""() => ({
         sms_state: document.querySelector("label:has-text('Tin nhắn văn bản')")?.getAttribute("data-state"),
         channel: document.querySelector('input[name="channel"]')?.value
     })""")
     assert check["sms_state"] == "on" and check["channel"] == "sms", "Chưa tick chọn đúng kênh SMS!"
     ```

### 3. Kinh Nghiệm Chọn SIM 5sim Cho OpenAI ($\le \$0.16$)
- **Philippines (`virtual58` - $0.1077):**
  - Đầu số Smart (`0928`, `0970`): OpenAI chấp nhận ngay lập tức, SMS về sau 10s!
  - Đầu số DITO (`0991 206`): OpenAI từ chối SMS, ép qua WhatsApp $\longrightarrow$ Fail-fast hủy số trong 2s để hoàn tiền 100%.
- **Chính sách hoàn tiền 5sim:**
  - Nếu trong 120s không có OTP, gọi `GET https://5sim.net/v1/user/cancel/{order_id}` để hoàn lại 100% số dư vào tài khoản.

---

## 3. Quy Trình 4 Bước Bắt Buộc Kèm Ảnh Nghiệm Thu (Gate 6 / §VH)
1. **Bước 1 (Pre-Submit):** Chọn quốc gia, tick SMS, điền số $\longrightarrow$ Chụp ảnh xác nhận `channel=sms` và SĐT đã nằm trên form.
2. **Bước 2 (Post-Submit):** Nhấn "Tiếp tục" $\longrightarrow$ Chụp ảnh phản hồi:
   - Nếu thấy dòng *"chuyển sang WhatsApp"* $\longrightarrow$ Hủy số trong 2s, hoàn tiền.
   - Nếu URL chuyển sang `/phone-verification` $\longrightarrow$ Chờ SMS trong tối đa 120s.
3. **Bước 3 (Nhập OTP):** 5sim nhả code $\longrightarrow$ Điền OTP và chụp ảnh xác nhận mã.
4. **Bước 4 (Consent & Token):** Nhấn ủy quyền $\longrightarrow$ OmniRoute poll bắt `code` và lưu connection vào database.
