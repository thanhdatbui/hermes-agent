# Gmail Check-Live Audit, False-Positive Fallback Traps & Excel Structure

**Cập nhật:** 2026-10-01  
**Phạm vi:** Kiểm tra live kho Gmail farm S7, bảo vệ tính trung thực của telemetry, và truy vết tài khoản trong `gmail_clean_v2.xlsx`.

---

## 1. Bẫy Ngộ Nhận LIVE (False-Positive Fallback Trap) Trên `checkmail.live`

### Hiện tượng & Nguy cơ:
- Khi kiểm tra live Gmail qua trang `https://checkmail.live/`, trang web bắt buộc phải có session đăng nhập hợp lệ (có trường input ẩn `id="api-key"` trên DOM).
- Nếu mở browser Playwright chay hoặc phiên đăng nhập chưa có `api-key`:
  1. Nút `#btn-check` bị vô hiệu hóa hoặc xuất hiện popup alert `You are not logged in`.
  2. Editor `#live-result` không in ra bất kỳ dòng kết quả `[LIVE]` hay `[DIE]` nào.
- **Bẫy code ngộ nhận nguy hiểm:**
  - Trong các helper probe nhanh (như `check_gmail_live_fast.py`), nếu khởi tạo trước dictionary mặc định:
    ```python
    results = {em: True for em in emails}  # Default True = LIVE
    ```
    và chỉ gán `results[em] = False` khi regex bắt được `[DIE]`, thì khi trang web không chạy check, toàn bộ 100% email đầu vào sẽ được trả về là `True` (LIVE).
  - Ngay cả email rác/chết chắc chắn như `thisisatestdeademail1234567890nonexistent@gmail.com` cũng bị báo nhầm là `LIVE`!

### Quy chuẩn thực thi chuẩn xác (Canonical Standard):
1. **BẮT BUỘC dùng runner chuẩn:** Sử dụng module `run_checkmail_kibe_farm.py` (tại `D:/Taadaa/GPM auto/scripts/run_checkmail_kibe_farm.py`).
2. **Kiểm tra Session & Auto-Login:**
   - Luôn gọi `ensure_logged_in_page(context)` trước khi check.
   - Hàm này kiểm tra `api-key`. Nếu thiếu, tự động chuyển sang `login.php`, bấm nút switch để render Cloudflare Turnstile trên `#a-form`, điền tài khoản ephemeral (`kibeXXXX` / `TaadaaKibe2026`), đợi token `cf-turnstile-response` rồi submit.
3. **Chỉ công nhận kết quả khi có bằng chứng từ DOM:**
   - Đọc kết quả từ `window.liveResultEditor.getValue()`.
   - Chỉ phân loại `LIVE` hoặc `DIE` khi regex match được dòng `[Live]` hoặc `[die]` tương ứng với email đó.
   - Nếu không có dòng kết quả, trạng thái bắt buộc là `UNKNOWN`, tuyệt đối không fallback ngầm về `True` / `LIVE`.
4. **Proxy Authentication:**
   - Proxy Mobile Farm: `http://test.taadaa.click:5101`, auth `mobi1:TaadaaMobi#2026!`.
   - Ký tự `#` trong password phải được URL-encode thành `%23` (`TaadaaMobi%232026!`) khi định dạng URL proxy string.

---

## 2. Quy Tắc Chèn Hàng & Truy Vết Tài Khoản Trong `gmail_clean_v2.xlsx`

### Cơ chế chèn hàng theo máy (`last_row_for_machine`):
- Trong `merge_success_results.py`, hệ thống không chèn tài khoản mới vào cuối bảng tính (`ws.max_row + 1`).
- Thay vào đó, script tìm vị trí dòng cuối cùng của máy đó (`normalize_machine_cell(ws.cell(r, 1).value) == stt`) và gọi:
  ```python
  ws.insert_rows(last_row + 1)
  ```
- **Hệ quả đối soát:**
  - Nếu chỉ đọc 30–50 dòng cuối của file Excel (`tail`), bạn sẽ chỉ thấy tài khoản của các máy có STT lớn (M70, M74, M76...). Toàn bộ tài khoản mới của các máy STT nhỏ (như M04, M05, M09, M11...) được chèn ở giữa bảng tính và bị bỏ sót hoàn toàn.
  - **Cách đối soát đúng:**
    1. Quét toàn bộ cột `ngày tạo` (cột 7) và cột `tài khoản gmail` (cột 2) từ dòng 2 đến `max_row`.
    2. Đọc file artifact tổng kết sáp nhập tại `D:/CodexRuntime/codex_gmail_debug-register-gmail/logs_parallel_*/merge_success_summary.json`.

---

## 3. Thống Kê Tỷ Lệ Sống & Chu Kỳ Quét Của Google (Số liệu Farm S7)

Theo kiểm tra đối soát thực tế 57 tài khoản Gmail reg gần đây (từ 22/09 đến 01/10/2026):
- **Tỷ lệ sống chung:** ~42.1% (24 LIVE, 33 DIE).
- **Chu kỳ sinh tồn 48h:**
  - Tài khoản Gmail S7 nếu vượt qua được 48 giờ ngâm đầu tiên (ví dụ đợt 22/09 đạt 75% LIVE, 25/09 đạt 80% LIVE) thì có tỷ lệ sống rất cao và ổn định lâu dài.
  - Trong các đợt Google siết chặt quét backend (từ 26/09 đến 29/09), Google thường vô hiệu hóa hoặc yêu cầu xác minh số điện thoại (`challenge/iap`) ngầm ngay trong vòng 24h đầu, tỷ lệ DIE có thể lên đến 70–85%.
- **Khuyến nghị vận hành:**
  - Sau khi reg Gmail trên S7, để máy ngâm tĩnh đủ 24–48h.
  - Ưu tiên kéo các tài khoản còn LIVE lên GPMLogin trên PC để kích hoạt 2FA Google Authenticator (sinh Secret Key Base32 độc lập). Tài khoản có 2FA được nâng mức trust level và giảm thiểu tối đa nguy cơ bị khóa sau này.

---

## 4. Dọn Dẹp Downstream Watchdogs Khi Decommission Tính Năng

- **Triệt tiêu báo cáo ma (Phantom Reporting):**
  - Khi gỡ bỏ một tính năng trong core logic (ví dụ gỡ bỏ reg ChatGPT trên S7 trong `gmail_reg_v10.py`), PHẢI rà soát và dọn sạch các script watchdog hạ tầng (như `post_noon_chain_watchdog.py`).
  - Xóa bỏ các template text hardcode (ví dụ: `ChatGPT linked: telemetry riêng...`) và các hàm phân tích log cũ (`parse_chatgpt_warmup_counts`).
  - Sau khi sửa script trong `AppData/Local/hermes/scripts/`, bắt buộc chạy:
    ```bash
    python C:/Users/Kibe/AppData/Local/hermes/scripts/cron_sync_watchdog.py --force
    ```
    để đồng bộ bản sạch sang thư mục Deploy và OneDrive.
