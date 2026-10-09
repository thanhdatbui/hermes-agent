# OpenAI Phone Verification via 5sim & Step-by-Step Evidence Guard

Tài liệu đúc kết quy trình kỹ thuật, các cạm bẫy DOM của OpenAI và kỷ luật thị giác (Visual Heartbeat) bắt buộc khi tự động hóa xác thực số điện thoại cho OpenAI / Codex OAuth.

---

## 1. Cạm bẫy DOM của OpenAI Add-Phone (`auth.openai.com/add-phone`)

### A. Lỗi React Controlled Component & Thẻ `<select>` ngầm
- **Hiện tượng:** Click vào nút giả lập React-Aria (`button[aria-haspopup="listbox"]`) và chọn quốc gia (ví dụ Campuchia +855), giao diện có thể hiển thị text đã đổi, nhưng khi submit thì OpenAI vẫn gửi đi mã quốc gia mặc định là **`Hoa Kỳ (+1)`** $\rightarrow$ Dẫn đến báo lỗi *"Số điện thoại không hợp lệ"*.
- **Cơ chế ngầm:** Form của OpenAI có một thẻ `<select>` ẩn quản lý mã quốc gia (`ISO code`) song song với component React-Aria.
- **Giải pháp bắt buộc:** Bắt buộc phải đồng bộ trực tiếp giá trị vào thẻ `<select>` ngầm và kích hoạt sự kiện `change`:
  ```javascript
  const sel = document.querySelector("select");
  if (sel) {
      sel.value = target_iso; // Ví dụ: "KH", "ZA", "GB", "PT"
      sel.dispatchEvent(new Event("change", { bubbles: true }));
  }
  ```
  Sau đó kiểm tra lại giá trị thẻ ẩn `input[name="phoneNumber"]` xem đã mang đúng đầu số quốc tế (ví dụ `+855...`) hay chưa.

---

### B. Cạm bẫy "Âm thầm chuyển sang WhatsApp" (Silent WhatsApp Fallback)
- **Hiện tượng:** Khi nhập các số điện thoại ảo (Virtual / VoIP rẻ tiền từ 5sim), OpenAI gọi `POST /api/accounts/add-phone/send` và trả về `HTTP 400`.
- **Hành vi của OpenAI:**
  - OpenAI **KHÔNG BẮN SMS**, mà tự động bật radio WhatsApp và hiện cảnh báo:
    > *"Chúng tôi không thể gửi tin nhắn SMS đến số điện thoại này nên đã chuyển sang WhatsApp. Tiếp tục để gửi mã xác minh qua WhatsApp."*
  - Nếu tiếp tục bấm hoặc ngồi chờ, mã sẽ được gửi vào ứng dụng WhatsApp của số đó (trong khi các dịch vụ thuê SIM như 5sim chỉ nhận SMS văn bản).
- **Quy tắc Fail-Fast xử lý:**
  - Ngay sau khi click Submit, script phải kiểm tra DOM: nếu phát hiện text chứa `"WhatsApp"` hoặc cảnh báo chuyển sang WhatsApp $\longrightarrow$ **HỦY SỐ NGAY LẬP TỨC TRONG 2 GIÂY** trên 5sim để nhận lại 100% tiền hoàn, tuyệt đối không ngồi chờ 60s - 120s vô ích.

---

### C. Nguy cơ Rate Limit tài khoản
- Nếu thử liên tục nhiều số ảo bị từ chối trên cùng một tài khoản, OpenAI sẽ khóa xác minh tạm thời:
  > *"Bạn đã yêu cầu xác minh số điện thoại quá nhiều lần. Vui lòng thử lại sau."*
- **Quy tắc cứng:** Mỗi tài khoản chỉ được phép thử tối đa **3 số không thành công**. Quá 3 lần phải dừng ngay lập tức và chuyển sang tài khoản khác hoặc đổi nguồn SIM (chuyển sang SIM vật lý / Physical SIM).

---

## 2. Kỷ luật Bằng chứng Thị giác (Step-by-Step Visual Evidence Guard)

Trong các tác vụ tự động hóa giao diện (UI, Browser, GPM, Phone Farm, OAuth), Coordinator **CẤM TUYỆT ĐỐI CHẠY VÒNG LẶP NGẦM (BLIND LOOP)**.

### Quy tắc bất biến: MAX BLIND STEPS = 1
Mỗi hành động thao tác đều là một Checkpoint bắt buộc phải gửi ảnh `MEDIA:<path_anh>` cho User:

1. **Checkpoint 1 (Pre-Submit):**
   - Điền xong số và chọn quốc gia $\longrightarrow$ Chụp ảnh full màn hình gửi ngay để xác nhận số và quốc gia đã thực sự nằm trên form.
2. **Checkpoint 2 (Post-Submit / Response):**
   - Bấm nút Tiếp tục $\longrightarrow$ Chụp ảnh ngay phản hồi của OpenAI trong vòng $\le 3$ giây gửi cho User:
     - Nếu hiện ô nhập mã OTP $\longrightarrow$ Mới bắt đầu đợi SMS.
     - Nếu hiện lỗi / WhatsApp $\longrightarrow$ Hủy ngay.
3. **Kỹ thuật chụp ảnh tránh treo font (Playwright Font Hang Fix):**
   - Trang OpenAI (`auth.openai.com`) thường xuyên làm lệnh `page.screenshot()` bị treo do chờ load font từ CDN.
   - Sử dụng giải pháp render qua `html2canvas` hoặc `cdp_session.send("Page.captureScreenshot")` để xuất ảnh tức thì mà không bao giờ bị timeout.
