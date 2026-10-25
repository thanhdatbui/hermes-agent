# GPM Re-login Triage Taxonomy & Soak Date Typo Trap

## 1. Candidate Selector Soak Date Typo Trap (`(today - created_date).days < 7`)
### Hiện tượng & Root Cause
Trong các script watchdog chọn ứng viên đăng nhập GPM (như `post_evening_gpm_login_watchdog.py`), candidate selector kiểm tra tuổi ngâm của nick mới:
```python
if (d_today - c_date).days < 7:
    continue
```
* **Bẫy 1 - Gõ nhầm năm tương lai trong Excel:** Khi nhập liệu thủ công trên `gmail_clean_v2.xlsx` hoặc `master_gmail_manager.xlsx`, nếu năm tạo bị gõ nhầm thành năm tương lai (ví dụ `2027-06-13` thay vì `2026-06-13`), phép trừ `(d_today - c_date).days` ra số âm (`-231`). Trong Python, `-231 < 7` là `True`, khiến tài khoản bị skip vĩnh viễn và không bao giờ được chọn đăng nhập.
* **Bẫy 2 - Đặt kiểm tra tuổi ngâm trước kiểm tra Re-login:** Các tài khoản văng cookie cần đăng nhập lại (`is_lost_session = True`) vốn dĩ là nick Group 10 đã được đăng nhập và ngâm session từ trước. Đặt kiểm tra soak 7 ngày trước `is_lost_session` khiến acc re-login bị đối xử như acc mới tạo và bị chặn oan.

### Quy chuẩn xử lý
1. **Ưu tiên Re-login:** Đánh giá `is_lost_session` trước; nếu là nick re-login thì **bỏ qua hoàn toàn** kiểm tra 7-day creation soak.
2. **Chặn cận dưới fail-safe:** Khi so sánh ngày, bắt buộc dùng khoảng `0 <= (d_today - c_date).days < 7`. Nếu `days < 0` (ngày tương lai do lỗi dữ liệu), coi như acc đã ngâm đủ hoặc log warning thay vì drop im lặng.
3. **Sửa dữ liệu nguồn:** Sửa trực tiếp ô ngày bị sai trên file Excel gốc (dùng `openpyxl`) và kiểm tra đối soát với ngày cập nhật trên `master_gmail_manager.xlsx`.

---

## 2. Phân loại 5 trạng thái lỗi Profile Group 10 (GPM Re-login Taxonomy)
Khi nuôi GPM Gmail báo `NEEDS_LOGIN` (do Preflight Cookie Guard phát hiện thiếu cookie `SID/SSID/HSID/SAPISID`), cần phân loại chính xác theo 5 nhóm nguyên nhân thực tế qua bằng chứng (WinRT OCR / ADB / Device Locks):

| Nhóm lỗi | Biểu hiện qua bằng chứng (OCR / Telemetry / Locks) | Hành vi điều phối chuẩn |
| :--- | :--- | :--- |
| **1. WRONG_PASSWORD (Cần Đối Soát)** | Nằm trong `oauth_pipeline_status.json` (`wrong_password_or_checkpoint`). | **CẤM thử lại mù.** Tuy nhiên, KHÔNG ĐƯỢC coi là sự thật vĩnh viễn: cần đối soát lại Excel (`master_gmail_manager.xlsx`, `gmail_clean_v2.xlsx`) và 2FA Secret. Nếu Excel đã cập nhật mật khẩu chuẩn mới (e.g. `@Ks`) và có 2FA, chạy 1 probe `--login-only`. Nếu thành công, gỡ ngay khỏi blacklist. |
| **2. HARD_PHONE_CHECKPOINT (SMS)** | WinRT OCR đọc thấy màn hình *"Xác minh thông tin để tiếp tục... Quét mã QR bằng điện thoại / SMS"*. | **Yêu cầu SMS xác minh.** Khi quét QR, Google đòi nhập số điện thoại bất kỳ để nhận mã SMS (`G-XXXXXX`). Google chấp nhận mọi SIM phụ/SIM rác chưa chạm limit 3-5 lần/tháng. Nếu không có SIM xác minh -> đưa vào `SMS_CHECKPOINT` trong `oauth_pipeline_status.json` để watchdog bỏ qua vĩnh viễn, tránh lặp vô ích. |
| **3. AUDIO_RECAPTCHA_TIMEOUT** | WinRT OCR đọc thấy *"Nhấn vào nút PHÁT để nghe - Nhập nội dung bạn nghe thấy - Tôi không phải là người máy"*. | Thử thách bot check âm thanh bị nghẽn proxy/timeout. Giữ máy rảnh, đưa vào hàng đợi retry ở ca kế tiếp để hạ nhiệt IP. |
| **4. ADB_DISCONNECTED** | `inspect_machine.py <mid>` báo `device 'serial' not found`. | Rớt cáp USB phần cứng. Script không thể đọc Security Code hoặc duyệt Google Prompt trên S7. Báo cáo kiểm tra cắm lại cáp USB. |
| **5. DEVICE_BUSY** | Tồn tại `machine_<mid>.lock.json` (ví dụ `gmail_reg_v10.py`). | Máy bận tác vụ ưu tiên khác. Hệ thống sẽ tự động đăng nhập khi máy hoàn tất ca và giải phóng device lock. |
| **6. POLICY_EXCLUDED_KHOALEE** | Mail hoặc recovery chứa `khoale`/`khoalee`. Script báo `SKIPPED_KHOALEE`. | **TUÂN THỦ TUYỆT ĐỐI.** Farm Safety Policy loại trừ 100% để chống đụng checkpoint nguy hiểm trên tài khoản có liên kết khoalee. Không tự ý bypass. |

---

## 3. Quy chuẩn Soi Mắt Đọc Ảnh bằng WinRT OCR trên Windows
Khi kiểm tra ảnh chụp màn hình lỗi đăng nhập (`debug_screenshots/oauth_*`):
- Đường dẫn truyền vào `-imgPath` của `ocr_boxes.ps1` **bắt buộc chuẩn hóa dấu gạch chéo ngược (`\`)**: `path.replace('/', '\\')`. Nếu truyền `/`, WinRT `GetFileFromPathAsync` sẽ ném ngoại lệ `AggregateException`.
- Tạo receipt kiểm chứng qua `run_winrt_ocr.py` để đính kèm bằng chứng OCR hợp lệ trước khi gửi `MEDIA:<path>`.

---

## 4. Nurture Verification Timing & State Recovery Caveat
- **Bẫy Timeout Foreground 60s:** Script nuôi `cron_gpm_gmail_nurture.py` chạy tác vụ xem YouTube thực tế từ 90s - 120s (Smart Ad Skip & human scroll). Nếu Coordinator chạy lệnh foreground với `timeout <= 60s`, tiến trình sẽ bị ngắt giữa chừng (Exit 124) trước khi kịp ghi nhận `status: success` vào state file, mặc dù session Google thực tế đã được cứu sống hoàn toàn.
- **Quy trình nghiệm thu chuẩn 2 bước:**
  1. Chạy `run_oauth_s7_pipeline.py <email> --login-only` (chạy nhanh 15-25s): Xác nhận URL hạ cánh `myaccount.google.com` hoặc `gds.google.com` và event `login_only_success`.
  2. Kiểm tra ảnh nghiệm thu `debug_screenshots/nurture_<email>.png` qua WinRT OCR: Xác nhận giao diện YouTube/News có thanh điều hướng hoặc nút `+ Create` (chứng minh session cookie đã sống trên profile GPM), thay vì chạy lệnh nuôi cưỡng bức quá dài gây timeout.

---

## 5. Phân biệt Google AI Pro vs Free Tier trên OmniRoute (:20129) & Bẫy Nhầm Lẫn Tên Tương Tự
### Cơ chế xác thực gói Pro vs Free trên OmniRoute
Khi User thắc mắc hoặc yêu cầu kiểm tra xem một tài khoản lỗi có phải là tài khoản có gói **Google AI Pro** hay không:
1. **Truy vấn thực tế endpoint OmniRoute (`:20129`):**
   * Gọi `GET http://127.0.0.1:20129/api/providers` và đọc trường `providerSpecificData` của connection:
     - **Google AI Pro (Paid Tier):** `tier: "g1-pro-tier"`, `plan: "Pro"` hoặc `subscriptionTier: "Google AI Pro"`. Được nạp độc quyền vào combo **`ag-gemini-pool-3`** (Pool 29-30 accounts Gemini 3.8 Flash Pro cache-optimized).
     - **Free Tier (Antigravity Starter Quota):** `tier: "free-tier"`, `plan: "Antigravity starter quota"` hoặc `subscriptionTier: "Antigravity Starter Quota"`. Được nạp vào combo **`ag-gemini-free-pool`** (Pool 97+ accounts Free).
2. **Bẫy nhầm lẫn tên tài khoản tương tự (Phonetic / Spelling Trap):**
   * Các tài khoản có tiền tố giống nhau rất dễ gây hiểu nhầm lẫn nhau trong vận hành farm:
     - `luunhu290719@gmail.com` (Lưu Như - Máy 19): Thuộc **Free-Tier** (`Antigravity Starter Quota`), trước đây chỉ dùng chạy tải nhẹ/ChatGPT Web. Khi nick này bị Hard Phone Checkpoint, **hoàn toàn không ảnh hưởng tới hạn ngạch Gemini Pro**.
     - `luuhuong28022000@gmail.com` (Lưu Hường - Máy 18): Tài khoản **Google AI Pro xịn** (`g1-pro-tier`, ID: `ag-gemini-pro-24-e1e88b66`), đang Active 100% trong combo `ag-gemini-pool-3`.
   * **Kỷ luật điều phối:** TUYỆT ĐỐI KHÔNG đoán mò hay kết luận vội vã. Bắt buộc tra cứu trực tiếp qua OmniRoute API hoặc combo `ag-gemini-pool-3` để đưa ra câu trả lời dựa trên bằng chứng dữ liệu thời gian thực.

---

## 6. Dò Pass Thực Tế & Xử Lý Di Chứng Blacklist WRONG_PASSWORD Cũ
### Hiện tượng di chứng (Stale Blacklist Flag)
- Khi một tài khoản bị lỗi đăng nhập trong quá khứ (ví dụ kẹt submit form, thiếu flow sinh mã 2FA TOTP), script cũ tự động ghi cờ `"email": "WRONG_PASSWORD (M<mid>)"` vào `oauth_pipeline_status.json` (`wrong_password_or_checkpoint`).
- Sau đó, tài khoản có thể đã được reset mật khẩu mới đồng bộ (ví dụ dạng `Password@Ks`) và lưu vào `master_gmail_manager.xlsx` + `gmail_clean_v2.xlsx`, nhưng entry trong `wrong_password_or_checkpoint` bị bỏ quên không xóa.
- Hậu quả: Mọi ca login watchdog sau đó tự động bỏ qua tài khoản, và agent báo cáo nhầm "sai pass" cho User dựa trên file JSON cũ dù trong Excel pass đã đúng.

### Quy trình dò pass và giải phóng blacklist chuẩn:
1. **Đối soát dữ liệu nguồn Excel:**
   - Đọc cột Password, 2FA Secret, Recovery Email trong cả `master_gmail_manager.xlsx` (sheet `Kibe_Farm_S7`, `Master_All`) và `gmail_clean_v2.xlsx`.
   - Nếu thấy mật khẩu đã được chuẩn hóa (e.g. `Password@Ks`) và có 2FA TOTP Secret hợp lệ: đây là dấu hiệu tài khoản đã được cấp pass đúng.
2. **Chạy Live Canary Probe độc lập:**
   - Chạy lệnh test focused: `python "D:/Taadaa/GPM auto/scripts/run_oauth_s7_pipeline.py" <email> --login-only`.
   - Xác nhận event `login_only_success` và URL đích `myaccount.google.com` hoặc `gds.google.com`.
3. **Giải phóng Blacklist & Cập nhật State:**
   - Xóa ngay key email khỏi `wrong_password_or_checkpoint` trong `oauth_pipeline_status.json`.
   - Cập nhật `status: "success"` kèm `recovered_at` và `recovered_date` trong `gpm_gmail_nurture_state.json`.
   - Kích hoạt phiên nuôi tự nhiên và soi mắt WinRT OCR nghiệm thu trước khi báo cáo.

