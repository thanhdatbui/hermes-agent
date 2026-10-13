# GPM Supervisor Concurrency Cap & ChatGPT Age Flow Pitfalls

## 1. Concurrency Cap cho GPM Lifecycle Supervisors

### Bối cảnh & Hiện tượng
Khi một cronjob chạy với chu kỳ ngắn (ví dụ `*/5 * * * *`) gọi supervisor spawn các profile trình duyệt qua GPMLogin:
- Nếu một bước trong browser automation bị kẹt (ví dụ đợi modal, hỏi tuổi, giải captcha), tiến trình con sẽ sống tới timeout của nó (thường 300s - 1.800s).
- Cứ mỗi 5 phút, cronjob tiếp tục khởi chạy đợt mới. Nếu không có cơ chế giới hạn số lượng profile đang mở trên toàn máy, các profile cũ chưa đóng sẽ tích tụ lũy tiến:
  $$\text{Số profile} = \text{Batch Size} \times \frac{\text{Timeout}}{\text{Cron Interval}}$$
  Với batch = 5, timeout = 1.800s (30m), interval = 5m $\rightarrow$ tích tụ tới 30–38 profile Chrome mở đè lên nhau, làm sập RAM, nghẽn mạng proxy và tràn ngập Taskbar Windows.

### Invariant Bắt buộc
1. **Hard Concurrency Cap trước khi Spawn:**
   Trước khi mở bất kỳ profile mới nào, supervisor BẮT BUỘC phải gọi `GET /api/v3/profiles` để đếm số profile đang chạy (`running` hoặc có PID active).
   - Nếu số profile đang mở $\ge$ ngưỡng cho phép (khuyến nghị tối đa 3–5 profile trên máy Kibe), supervisor PHẢI lập tức bỏ qua (skip tick) hoặc từ chối spawn mới.
2. **Timeout Subcommand Thắt chặt:**
   - CẤM đặt timeout 1.800s (30 phút) cho các bước tự động hóa browser đơn lẻ. Timeout tối đa chỉ nên đặt 300s (5 phút).
   - Khi hết timeout, bắt buộc cưỡng chế đóng profile qua `GET /api/v3/profiles/close/{profile_id}` trong khối `finally`.

---

## 2. OpenAI Registration: Bẫy Lồng Điều Kiện Màn Hình Tuổi (Age Verification)

### Bối cảnh & Bug Logic
Trong script tự động đăng ký ChatGPT (`chatgpt_gpm_direct_reg.py`), luồng Onboarding điền thông tin người dùng:
```python
# CODE LỖI (BUG):
name_inp = page.locator('input[name="name"], input#name, ...').first
if name_inp.is_visible(timeout=5000):
    name_inp.fill("Chau Ta")
    # Lồng điền tuổi bên trong name_inp:
    age_inp = page.locator('input[name="age"], input[type="number"], ...').first
    if age_inp.is_visible(timeout=2000):
        age_inp.fill("25")
    click_continue_btn(page)
```

### Hiện tượng Thực tế từ Giao diện OpenAI mới
- OpenAI thường xuyên A/B test hoặc phân luồng riêng cho tài khoản Microsoft / Hotmail:
  - Tài khoản Hotmail đã có thông tin tên trong session Microsoft, do đó OpenAI **bỏ qua bước hỏi Tên** và chuyển thẳng tới trang xác minh tuổi độc lập.
  - Tiêu đề trang (Window Title) hiển thị: `"Bạn bao nhiêu tuổi? - OpenAI - GPM-Browser"` hoặc `"Hãy xác nhận tuổi của bạn - OpenAI - GPM-Browser"`.
- Vì trang này **hoàn toàn không có ô `name_inp`**, câu lệnh `if name_inp.is_visible()` trả về `False`.
- Toàn bộ khối điền tuổi (`age_inp`) và bấm nút `click_continue_btn(page)` bị bỏ qua. Trình duyệt đứng yên tại màn hình hỏi tuổi, script chuyển sang bước đợi `#prompt-textarea` rồi báo lỗi sau 30s.

### Quy tắc Fix Chuẩn
1. **Tách rời độc lập các màn hình Onboarding:**
   - Không lồng `age_inp` hoặc `dob_inp` vào trong `name_inp`.
   - Kiểm tra riêng biệt:
     - Form Tên: Nếu thấy `input[name="name"]` $\rightarrow$ điền tên $\rightarrow$ Continue.
     - Form Tuổi: Nếu thấy trang có tiêu đề/text chứa `"bao nhiêu tuổi"`, `"xác nhận tuổi"`, `"how old are you"`, `"age"` hoặc có `input[name="age"]`, `input[type="number"]` $\rightarrow$ điền tuổi $\rightarrow$ Continue.
2. **Xử lý Modal "Bắt đầu | ChatGPT":**
   - Sau khi hoàn thành đăng ký, bắt buộc click qua modal onboarding chào mừng ("Bắt đầu", "Let's go", "Tiếp tục") trước khi assert ô `#prompt-textarea`.
