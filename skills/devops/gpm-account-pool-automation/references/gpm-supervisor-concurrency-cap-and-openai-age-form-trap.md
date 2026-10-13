# GPM Supervisor Concurrency Cap & OpenAI Onboarding Age Form Trap

## 1. Supervisor Hard Concurrency Cap (Chống tràn Taskbar / Treo RAM)

### Triệu chứng & Nguyên nhân
- Cronjob chạy chu kỳ ngắn (ví dụ mỗi 5 phút) gọi supervisor batch/lifecycle.
- Tiến trình con (đăng ký ChatGPT, login, OAuth) bị kẹt ở bước UI nào đó với timeout quá dài (ví dụ 1.800s / 30 phút).
- Supervisor thiếu cơ chế kiểm tra tiến trình đang chạy (Concurrency Cap), cứ mỗi tick lại khởi tạo thêm N profile mới (`ThreadPoolExecutor`).
- Kết quả: Tích tụ hàng chục (30-40) cửa sổ Chromium GPM chạy ngầm đè lên nhau, làm sập RAM, nghẽn mạng proxy và kẹt toàn bộ desktop.

### Quy tắc phòng chống bắt buộc
1. **Hard Concurrency Cap trước khi chọn candidate:**
   Trước khi `select_candidates()` hoặc `pool.map()`, supervisor bắt buộc phải đếm số lượng Chromium GPM đang chạy trên máy (qua `psutil` lọc `gpm_browser` hoặc qua GPM API `GET /api/v3/profiles`).
   ```python
   import psutil

   def count_running_gpm_browsers() -> int:
       try:
           return sum(
               1 for p in psutil.process_iter(['name', 'cmdline'])
               if p.info['name'] and 'chrome' in p.info['name'].lower()
               and any('gpm_browser' in a for a in (p.info['cmdline'] or []))
               and not any('--type=' in a for a in (p.info['cmdline'] or []))
           )
       except Exception:
           return 0

   # Trong hàm tick:
   try:
       active_gpm = count_running_gpm_browsers()
       if active_gpm >= 5:
           print(f"[CONCURRENCY_CAP] Dang co {active_gpm} profile GPM hoat dong. Bo qua tick.")
           log_telemetry_event("concurrency_cap_skipped", {"active_profiles": active_gpm})
           return 0
   except Exception as exc:
       log_telemetry_event("concurrency_cap_scan_failed", {"error": str(exc)})
   ```
2. **Cap timeout tối đa cho mỗi lượt thao tác web:**
   Giảm timeout của `run_cmd` khi gọi script tương tác browser từ 1.800s xuống tối đa 300s (5 phút).
3. **Cưỡng chế dọn sạch profile trong finally:**
   Mỗi profile khởi chạy phải đảm bảo gọi API đóng profile (`/api/v3/profiles/close/{pid}`) hoặc kill tiến trình nếu crash/timeout.

---

## 2. OpenAI Onboarding Form Trap (Bẫy lồng điều kiện Name & Tuổi)

### Triệu chứng
- Script đăng ký ChatGPT trực tiếp qua GPM vượt qua OTP email thành công nhưng kẹt ở bước "Bạn bao nhiêu tuổi? - OpenAI" / "Hãy xác nhận tuổi của bạn - OpenAI".
- Cửa sổ trình duyệt dừng lại ở màn hình hỏi tuổi, không điền tuổi và không bấm nút Tiếp tục, dẫn đến timeout `FAIL_NO_PROMPT_TEXTAREA`.

### Nguyên nhân logic
- Code cũ lồng điều kiện:
  ```python
  # SAI LẦM:
  if name_inp.is_visible(timeout=5000):
      name_inp.fill("Chau Ta")
      if age_inp.is_visible():
          age_inp.fill("25")
      click_continue_btn(page)
  ```
- Với tài khoản Hotmail/MS, OpenAI thường bỏ qua bước hỏi Tên (hoặc đã có sẵn) mà chuyển thẳng sang màn hình riêng "Bạn bao nhiêu tuổi?" / "Hãy xác nhận tuổi của bạn".
- Vì không có `name_inp`, điều kiện ngoài cùng trả về `False` -> Bỏ qua toàn bộ khối điền tuổi và lệnh click nút Tiếp tục.

### Giải pháp chuẩn hóa
Tách biệt hoàn toàn việc kiểm tra Name, Age, Birthday và lệnh click Continue:
```python
# 1. Khởi tạo cờ kiểm soát form
form_active = False

# 2. Điền Tên nếu có
name_inp = page.locator('input[name="name"], input#name, input[autocomplete="name"]').first
if name_inp.is_visible(timeout=3000):
    name_inp.fill("Chau Ta")
    form_active = True

# 3. Điền Tuổi độc lập (không lồng trong Name)
age_inp = page.locator('input[name="age"], input#age, input[type="number"], input[placeholder*="Age"], input[placeholder*="tuổi"], input[placeholder*="Tuổi"], input[aria-label*="Age"], input[aria-label*="tuổi"], input[inputmode="numeric"]').first
if age_inp.is_visible(timeout=2000):
    age_inp.fill("25")
    form_active = True

# 4. Điền Ngày sinh nếu có
dob_inp = page.locator('input[name="birthdate"], input#birthdate, input[name="birthday"], input[type="date"]').first
if dob_inp.is_visible(timeout=2000):
    dob_inp.fill("2000-04-17")
    form_active = True

# 5. Fallback kiểm tra tiêu đề màn hình hỏi tuổi
if not form_active:
    try:
        heading = page.locator('h1, h2').first.inner_text(timeout=1000).strip().lower()
        if any(kw in heading for kw in ["tuổi", "age", "about you"]):
            form_active = True
    except Exception:
        pass

# 6. Chỉ click continue khi form thực sự đang active (tránh click mù ngoài luồng)
if form_active:
    click_continue_btn(page)
    time.sleep(5)
```
- Bổ sung vào danh sách nút của `click_continue_btn`: `button:has-text("Bắt đầu")`, `button:has-text("Xác nhận")`, `button:has-text("Hoàn tất")` để không bị kẹt ở modal Onboarding tiếng Việt.
