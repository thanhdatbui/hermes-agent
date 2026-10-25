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
| **1. WRONG_PASSWORD** | Nằm trong `oauth_pipeline_status.json` (`wrong_password_or_checkpoint`). | **CẤM thử lại tự động.** Script phải cách ly để tránh Google vô hiệu hóa tài khoản vĩnh viễn. Chờ User cập nhật pass đúng. |
| **2. HARD_PHONE_CHECKPOINT** | WinRT OCR đọc thấy màn hình *"Xác minh thông tin để tiếp tục... Quét mã QR bằng điện thoại / SMS"*. | **FAIL-CLOSED.** Không thể auto-bypass bằng script nếu thiếu SIM/điện thoại quét QR. Giữ nguyên trạng thái báo cáo User. |
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
