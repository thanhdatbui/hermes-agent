# Gmail DIE Cleanup Lifecycle & Staged Maturation Pipeline (Sol High Architecture)

**Thời điểm chuẩn hóa:** 2026-10-01  
**Thẩm định độc lập:** Sol Auditor (`chatgpt-web/gpt-5.6-sol-high` qua OmniRoute `:20129`)  
**Phạm vi áp dụng:** Hệ thống Phone Farm S7, GPMLogin PC, `gmail_reg_v10.py`, `preflight_s7_rolling_cleanup.py`, `sync_gpm_lifecycle.py`, và các watchdog cronjobs liên quan.

---

## 1. Phân Tích Kiến Trúc: Vì Sao CẤM Tạo ChatGPT Ngay Sau Khi Reg Gmail?

### 1.1. Lập Luận "Lấy Tài Sản Chưa Trưởng Thành Để Đẻ Ra Tài Sản Thứ Hai"
- **Tình trạng của Gmail mới sinh (Birth / Probation):**
  + Trong 24–72 giờ đầu, Google đặt tài khoản mới vào trạng thái thử việc (*probation*).
  + Dữ liệu thực nghiệm 10 ngày (22/09 – 01/10/2026): Tỷ lệ quét rụng tự nhiên của Google là **50% – 60%** (chủ yếu là Phone Verification Checkpoint `challenge/iap`).
- **Rủi ro khi vội vàng liên kết ChatGPT:**
  + Dù triển khai theo cách GPM PC submit web rồi S7 chỉ nhận OTP, nếu Gmail gốc bị Google khóa sau 2 ngày thì tài khoản ChatGPT gắn theo sẽ **mất hoàn toàn khả năng nhận OTP, mất quyền reset password, mất email recovery**.
  + Một tài khoản ChatGPT sinh ra trên một Gmail không ổn định là tài sản suy thoái, sớm muộn cũng bị phế bỏ.

### 1.2. Phản Ứng RBA Của Google Khi Nhận OTP Đăng Ký Dịch Vụ Sớm
- Google không coi việc *"nhận mail OTP từ OpenAI"* là bằng chứng tăng trust.
- Ngược lại, Google nhận diện pattern: **Gmail vừa tạo xong 2–3 phút đã nhận ngay mail đăng ký dịch vụ AI/web từ thiết bị khác**. Đây là chữ ký điển hình của bot cày tài khoản hàng loạt (*account farming* / *credential harvesting*), đẩy rủi ro bị khóa lên mức cao nhất.

---

## 2. Kiến Trúc Chuẩn Hóa: Staged Maturation Pipeline

Hệ thống tuân thủ nghiêm ngặt 4 giai đoạn sinh trưởng của tài khoản:

```text
[Giai đoạn 1: Sinh ra]       [Giai đoạn 2: Sinh tồn]       [Giai đoạn 3: Kiểm tra]     [Giai đoạn 4: Đấu nối]
    S7 Reg Gmail          ──►   Ngâm tĩnh >= 7 ngày   ──►    Quét checkmail.live  ──►    Đưa lên GPM PC
  (Ghi sổ cái Excel)           (Không đụng web/GPM)           - DIE  -> Gỡ dọn S7         - Bật 2FA Auth
                                                             - LIVE -> Lên PC GPM        - Reg ChatGPT / Codex
```

1. **Phase 1 — Sinh ra (Ngày 0):** S7 chạy reg Gmail qua script chuẩn `run_parallel.ps1`, lưu thông tin vào `gmail_clean_v2.xlsx`, tuyệt đối không mở web, không gọi hook ChatGPT hay đăng ký dịch vụ thứ 3.
2. **Phase 2 — Sinh tồn (Ngày 1 đến 7):** Để nguyên tài khoản trên máy S7, ngâm tĩnh tối thiểu $\ge 7$ ngày. Chỉ để Google Play Services đồng bộ nền tự nhiên. Để thuật toán Google tự thanh lọc các acc yếu.
3. **Phase 3 — Kiểm tra & Phân loại (Ngày 8+):** Quét kiểm tra trạng thái qua `checkmail.live` (Mobile Proxy `mobi1`).
   - Tài khoản **DIE**: Đưa vào hàng đợi gỡ bỏ khỏi S7 để giải phóng slot.
   - Tài khoản **LIVE**: Chuyển sang Phase 4.
4. **Phase 4 — Đấu nối dịch vụ (Service Onboarding):**
   - Đưa tài khoản LIVE lên GPMLogin trên PC theo đúng proxy 4G tương ứng của máy S7.
   - Bật Google Authenticator (2FA) nâng trust level.
   - Đăng ký ChatGPT Web / Codex OAuth cấp cho AI pool của hệ thống.

---

## 3. Cơ Chế Dọn Dẹp Tài Khoản Gmail DIE Hiện Hữu (3 Tầng)

### 3.1. Tầng 1: Preflight Dọn Ngay Trước Ca Reg (14:30 hàng ngày)
- **Script điều phối:** `gmail_reg_v10.py` gọi `run_s7_rolling_cleanup_preflight()` từ `D:/Taadaa/GPM auto/scripts/preflight_s7_rolling_cleanup.py`.
- **Cơ chế:**
  1. Đọc `dumpsys account` để lấy danh sách tài khoản Google đang có trên máy S7.
  2. Quét nhanh trạng thái qua `checkmail.live`.
  3. **Nếu phát hiện có tài khoản DIE:** Script lập tức trả về `action = "REMOVE"`.
  4. Lệnh `remove_account_adb()` tự động mở `android.settings.SYNC_SETTINGS`, điều hướng đến tài khoản DIE và bấm **"XÓA TÀI KHOẢN"** ngay trên thiết bị để dọn sạch slot trước khi reg tài khoản mới.
  5. Ghi vết tài khoản đã xóa vào `D:/OneDrive/TaadaaData/kibe/gmail_die_tong.txt`.

### 3.2. Tầng 2: Watchdog Cuốn Chiếu Buổi Sáng (07:15 – 08:45)
- **Script điều phối:** `C:/Users/Kibe/AppData/Local/hermes/scripts/sync_gpm_lifecycle.py`.
- **Cơ chế:**
  1. Quét các tài khoản bị đánh dấu `DIE` trong `master_gmail_manager.xlsx` (sheet `Kibe_Farm_S7`).
  2. Đối soát thiết bị: Máy S7 phải online và **không nằm trong slot nuôi TikTok** (`is_machine_in_feed_slot == False`).
  3. Xin `device_lock` (non-blocking) và thực thi `remove_account_adb()` gỡ sạch tài khoản chết trên máy.

### 3.3. Tầng 3: Kỷ Luật Bảo Tồn Profile GPM PC (CẤM XÓA PROFILE DIE)
- **Chốt chặn an toàn:** Trong `sync_gpm_lifecycle.py`, hệ thống **BỎ QUA** việc xóa profile GPM gắn với Gmail DIE (`preserve_openai_codex_sessions`).
- **Lý do kỹ thuật:** Các profile GPM trên PC có thể đã liên kết session OpenAI / Codex đã tốn tiền thuê SIM ver số (`5sim`). Dù Gmail gốc bị Google khóa, cookie session của OpenAI/Codex trên trình duyệt đó vẫn có thể còn dùng được cho pool AI. Chỉ tắt toggle (`is_active = 0`) hoặc cô lập, tuyệt đối không xóa trắng profile GPM.

---

## 4. Công Cụ Quét Toàn Kho & Tự Động Dọn Dẹp Tập Trung (`gmail_farm_health_and_die_cleanup.py`)

- **Vị trí script:** `D:/Taadaa/tools/gmail_farm_health_and_die_cleanup.py`
- **Test suite focused:** `D:/Taadaa/tools/tests/test_gmail_farm_health_and_die_cleanup.py` (9/9 tests PASS in <0.7s, L0-digest zero-truncation).
- **Kiến trúc vận hành:**
  1. **Lọc ứng viên thông minh:** Đọc `D:/OneDrive/TaadaaData/kibe/gmail_clean_v2.xlsx`, tự động lọc các tài khoản đã ngâm $\ge 7$ ngày (hoặc dùng cờ `--force` để quét toàn bộ), ưu tiên các dòng Cột 11 (`trạng thái`) đang trống.
  2. **Quét live batch:** Gọi `checkmail.live` qua Mobile Proxy Farm (`http://test.taadaa.click:5101`) và GPM Chrome core 142.
  3. **Cập nhật Excel nguyên tử & Purge DIE (User Directive 2026-10-04 - HARD INVARIANT)**:
     - **Chính sách lưu trữ cốt lõi:** `gmail_clean_v2.xlsx` **TUYỆT ĐỐI CHỈ ĐƯỢC PHÉP LƯU GMAIL LIVE**.
     - **Cấm giữ dòng DIE trong kho:** Tuyệt đối KHÔNG được chỉ đổi Cột 11 (`trạng thái`) thành "DIE" rồi để lại dòng trong file `gmail_clean_v2.xlsx`.
     - **Xóa hoàn toàn tài khoản DIE:** Khi tài khoản được xác nhận `DIE` (bao gồm checkmail.live báo DIE hoặc Google challenge phone `challenge/iap` đòi số điện thoại), BẮT BUỘC phải **xóa hoàn toàn dòng tài khoản khỏi `gmail_clean_v2.xlsx`** (`ws.delete_rows(r, 1)`).
     - **Điểm lưu vết duy nhất:** Toàn bộ thông tin tài khoản DIE chỉ được phép lưu vết lịch sử tại `D:/OneDrive/TaadaaData/kibe/gmail_die_tong.txt`.
     - **Phân biệt SMTP Live vs App/Web Challenge Phone DIE:** Tool check SMTP (`checkmail.live`) báo LIVE chỉ là server còn nhận thư; nếu Google đã bật challenge phone (`challenge/iap`) chặn đăng nhập thì vẫn là DIE đối với automation farm vì cấm tự ý tốn phí thuê SIM -> Phải dọn ngay khỏi kho clean.
     - **Làm sạch slot trên Workbook Farm (`taikhoan_run_safe.xlsx`):** Khi tài khoản gắn với slot bị die, phải làm sạch trắng slot (`tiktok_id=""`, video count = None, created_date = None) thay vì để lại chuỗi `_DIE`, giúp tool `ensure_row_accounts.py` nhận diện chính xác slot trống cần reg bù.
     - **Kiểm chứng sau purge:** Đọc lại cả `taikhoan_run_safe.xlsx` và `taikhoan_dat_v2_updated .xlsx`; không chấp nhận `_DIE` còn sót trong slot/tracking. Khi kiểm tra backfill dùng cú pháp positional `python D:/Taadaa/tools/ensure_row_accounts.py <row> --machines <M> --dry-run` (không dùng `--row`). Nếu dry-run báo `Toan bo may da day du` trong khi slot trống, đó là lỗi đối soát và phải dừng, không báo sẵn sàng.
  4. **Dọn dẹp thiết bị S7:** Với các tài khoản được xác nhận `DIE` có gán số máy:
     - Tra cứu serial thiết bị qua `D:/OneDrive/TaadaaData/kibe/PROXYgandienthoai.xlsx`.
     - Kiểm tra kết nối `adb devices` online.
     - Xin non-blocking `acquire_device_lock` an toàn (bỏ qua nếu máy đang bận nuôi TikTok).
     - Kiểm tra `dumpsys account` xác nhận tài khoản còn trên máy.
     - Điều khiển ATX-Agent / Android UI Settings qua module `remove_device_google_account.py` (cấm uiautomator dump tránh OOM 137) bấm **"XÓA TÀI KHOẢN"**.
     - Ghi nhận lịch sử gỡ vào `D:/OneDrive/TaadaaData/kibe/gmail_die_tong.txt`.
  5. **Bảo mật Credentials & Observability (Chuẩn hóa Sol Auditor):**
     - **Bảo mật Secret:** Tuyệt đối CẤM hardcode password proxy làm default value trong mã nguồn. Bắt buộc đọc từ `os.environ` hoặc nạp động từ file bí mật `~/.hermes/.env` (`get_farm_proxy_credentials`).
     - **Dynamic Module Loading:** Ưu tiên import module nội bộ qua `Path(__file__).resolve().parent / "remove_device_google_account.py"` trước khi fallback đường dẫn tuyệt đối, phát telemetry logging cảnh báo khi thiếu dependency thay vì fallback im lặng.
     - **Structured Telemetry:** Bổ sung `log_telemetry_event(event_type, data, correlation_id)` phát JSON telemetry có cấu trúc cho toàn bộ các sự kiện vận hành: `CANDIDATES_LOADED`, `BATCH_CHECK_RESULT`, `DEVICE_CLEANUP_RESULT`, `ACCOUNT_REMOVED`, `ACCOUNT_SKIP_BUSY`, `ACCOUNT_SKIP_OFFLINE`.
  6. **CLI Flags hỗ trợ:**
     - `--dry-run`: Chạy mô phỏng, không ghi Excel, không gỡ thiết bị.
     - `--limit <N>`: Giới hạn số lượng tài khoản quét.
     - `--skip-device-cleanup`: Chỉ quét check live và cập nhật Excel, không đụng vào S7.
     - `--device-only`: Chỉ đọc các tài khoản đã có nhãn DIE trong Excel để dọn sạch trên S7.
     - `--force`: Bỏ qua thời gian ngâm 7 ngày, quét toàn bộ kho.
