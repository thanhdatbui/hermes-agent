# No-Agent Cron Silent Watchdog & Telegram Chunking Spam Pitfall

> 📌 **Bối cảnh thực tế (02/10/2026):**  
> Người dùng nhận 5 tin nhắn spam dồn dập trên Telegram chứa toàn bộ log thô từng giây xem YouTube, CDP kết nối, telemetry JSON, kết thúc bằng:  
> `========== Tất cả tiến trình nuôi trong lượt này đã hoàn tất ========== (4/5) ?`  
> Người dùng bức xúc phản ánh: *"tao cấm bắn spam ra như v r mà"*.

---

## 1. Bản Chất Kỹ Thuật Của Sự Cố

### 1.1 Con số `(4/5)` là gì?
* **Không phải là tỷ lệ tài khoản (4/5 acc thành công)**: Thực tế đợt nuôi hoàn thành 100% (5/5 profile OK).
* **Đó là Telegram Chunking Pagination**: Telegram giới hạn mỗi tin nhắn tối đa 4.096 ký tự. Khi stdout của script vượt quá giới hạn (ở đây là hơn 15.000 ký tự), Telegram Platform Adapter của Hermes tự động xé nhỏ thành **5 tin nhắn liên tiếp**: `(1/5)`, `(2/5)`, `(3/5)`, `(4/5)`, `(5/5)` và bắn dồn dập vào kênh người dùng.

### 1.2 Bẫy Semantics của Hermes `no_agent: true`
* Khi một cron job được khai báo `no_agent: true`:
  * **Stdout không rỗng (non-empty stdout)**: Hermes lấy toàn bộ `sys.stdout` làm nội dung tin nhắn và tự động gửi verbatim tới đích (`deliver: telegram:...`).
  * **Stdout rỗng (empty stdout)**: Hermes xem đây là **SILENT** (không có gì để báo cáo, watchdog bình yên) và **hoàn toàn không gửi tin nhắn nào**.
  * **Non-zero exit code (`sys.exit(1)`)**: Hermes coi đây là script crash và **bắt buộc bắn alert đỏ** kèm traceback lên Telegram, bất kể stdout rỗng hay không!
* Khi script khai báo:
  ```python
  logging.basicConfig(
      handlers=[
          RotatingFileHandler(LOG_FILE, ...),
          logging.StreamHandler(sys.stdout),  # ❌ BẪY CHÍ MẠNG
      ]
  )
  ```
  Mọi dòng `logger.info()`, `logger.warning()`, Playwright navigation log và telemetry JSON đều tuồn ra `sys.stdout` $\rightarrow$ Hermes nuốt 15KB log thô và bắn spam thành 5 tin nhắn Telegram.

### 1.3 Bẫy Non-Zero Exit Code Khi Nền Tảng Offline (GPM Tắt)
* Khi GPMLogin bị tắt (do người dùng tắt, restart máy hoặc crash), cổng Local API `19995` từ chối kết nối (`WinError 10061`).
* Nếu script bắt lỗi này rồi gọi `sys.exit(1)`, Hermes cron engine sẽ bắn cảnh báo `⚠️ Cron '<job>' failed: Script exited with code 1...` mỗi chu kỳ chạy (ví dụ mỗi tiếng), gây hoang mang và spam Telegram ("clgt ????").

---

## 2. Quy Chuẩn Bất Biến Cho Toàn Bộ Script Cron `no_agent: true`

### 2.1 CẤM `StreamHandler(sys.stdout)` — Chuyển sang `sys.stderr`
```python
# ❌ SAI: Rò rỉ log chi tiết vào Telegram delivery channel
logging.StreamHandler(sys.stdout)

# ✅ ĐÚNG: Ghi log console ra stderr; Hermes no_agent chỉ capture stdout để gửi tin
import sys
from logging.handlers import RotatingFileHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        RotatingFileHandler(LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"),
        logging.StreamHandler(sys.stderr),  # Log console cho debug thủ công, KHÔNG leak vào Telegram
    ]
)
```

### 2.2 Triệt Để Mẫu "Silent Watchdog On Success"
* Khi toàn bộ tác vụ thành công bình thường: **`sys.stdout` BẮT BUỘC RỖNG**.
* Khi có lỗi thực sự: In đúng **1 dòng alert duy nhất $\le$ 160 ký tự**.

```python
# Cuối hàm main() của cron runner / supervisor:
success_count = sum(1 for r in results if r.get("ok"))
total_count = len(results)

if success_count < total_count:
    failed_items = [f"{r['email']}: {r['status']}" for r in results if not r.get("ok")]
    err_detail = "; ".join(failed_items)[:100]
    # In cảnh báo ngắn gọn ra stdout để Hermes gửi duy nhất 1 tin Telegram khẩn cấp
    print(f"❌ [GPM Nurture Alert] Lỗi {total_count - success_count}/{total_count} profile: {err_detail}", flush=True)
else:
    # Thành công 100% -> CHỈ ghi vào logger.info (lưu file log), KHÔNG print ra stdout
    logger.info(f"✓ Hoàn tất nuôi {success_count}/{total_count} profile thành công (Silent Watchdog).")
```

### 2.3 Auto-Heal & Safe Skip Khi Nền Tảng Offline (Tránh Crash Alert)
Khi script phụ thuộc vào phần mềm nền tảng cục bộ (như GPMLogin API port 19995):
1. **Auto-Heal:** Trước khi từ bỏ, tự kiểm tra và khởi động ứng dụng nếu chưa chạy:
   ```python
   gpm_exe = Path(r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\GPMLogin.exe")
   if gpm_exe.exists():
       try:
           subprocess.Popen([str(gpm_exe)])
           time.sleep(5)
       except Exception as e:
           logger.warning(f"Không thể tự khởi động GPMLogin: {e}")
   ```
2. **Safe Skip (Bỏ qua an toàn):** Nếu sau khi thử kết nối lại mà API vẫn offline (người dùng cố tình tắt app để dùng máy hoặc giải phóng RAM):
   - CHỈ ghi warning vào `logger.warning()` (stderr/file).
   - Thoát êm bằng **`sys.exit(0)`** (hoặc `return`).
   - **CẤM `sys.exit(1)`**: Thoát mã lỗi non-zero sẽ kích hoạt Hermes cron engine bắn alert đỏ về Telegram, vi phạm nguyên tắc Silent Watchdog.
3. **Lệnh Bật Lại GPMLogin Chuẩn Từ Terminal:**
   ```bash
   # Khởi chạy ứng dụng vào interactive desktop session:
   powershell.exe -NoProfile -Command "Start-Process 'C:\Users\Kibe\AppData\Local\Programs\GPMLogin\GPMLogin.exe'"
   # Kiểm tra tiến trình & Local API v3:
   tasklist /fi "imagename eq GPMLogin.exe"
   curl -s -m 5 http://127.0.0.1:19995/api/v3/profiles?page=1&per_page=1
   ```

---

## 3. Checklist Tự Động Hóa & Kiểm Thử Unit Test Bắt Buộc

Khi phát triển hoặc review bất kỳ cron script nào thuộc danh mục `no_agent: true`, bắt buộc có 2 unit test:

1. **`test_silent_on_full_success`**:
   ```python
   def test_main_silent_watchdog_on_full_success(tmp_path, monkeypatch, capsys):
       # Mock toàn bộ runner hoàn thành OK
       ...
       main()
       out = capsys.readouterr().out
       assert out.strip() == "", f"Expected completely silent stdout on success, got: {out}"
   ```

2. **`test_alert_on_partial_failure`**:
   ```python
   def test_main_alert_on_partial_failure(tmp_path, monkeypatch, capsys):
       # Mock ít nhất 1 profile fail
       ...
       main()
       out = capsys.readouterr().out
       assert "❌ [Alert]" in out
       assert len(out.strip()) <= 160  # Tuân thủ nghiêm ngặt memory rule
   ```

3. **Đồng bộ 3 kho bắt buộc**:
   Sau khi vá script cron, phải copy đồng bộ sang cả 3 thư mục:
   - `D:/Taadaa/Hermes/deploy/hermes-home/scripts/`
   - `C:/Users/Kibe/AppData/Local/hermes/scripts/`
   - `D:/OneDrive/Taadaa_Sync_Shared/hermes-cron/scripts/`

---

## 4. Kỷ Luật Báo Cáo Ca & Hiển Thị "Bỏ Qua An Toàn" Khi Nhường Cron Khác (Safe Skip Transparency)

> 📌 **Chỉ thị cốt lõi của User:**  
> *"Cập nhật báo cáo đó cho all script khi phải nhường cho cron khác đi"*

### 4.1 Bối Cảnh & Vấn Đề
Khi các watchdog chạy theo ca hoặc báo cáo định kỳ (`post_evening_gpm_login_watchdog`, `post_noon_chain_watchdog`, `post_morning_gmail_2fa_watchdog`, `post_evening_avatar_watchdog`, `cron_clear_tiktok_cache`), các thiết bị/tài khoản có thể bị hoãn lại do:
1. Máy đang bận ca nuôi TikTok (`is_machine_idle == False` theo slot manifest).
2. Máy đang có active device lock (`~/.codex/device-locks/machine_<mid>.*`).
3. Khung giờ ca kết thúc (`is_late`) nhưng máy chưa rảnh kịp.

Nếu script im lặng thoát hoặc gộp các máy này vào danh sách lỗi (❌), User sẽ tưởng cron bị lỗi hoặc bị treo đứng im.

### 4.2 Định Dạng Báo Cáo Chuẩn 3 Cột
Báo cáo gửi về Telegram BẮT BUỘC phải phân tách rạch ròi:
- `• Đã hoàn tất: <N> máy / acc`
- `• Bỏ qua an toàn: <M> máy / acc (nhường lịch nuôi TikTok / lock tiến trình khác)`
- `• Lỗi thực tế: <K> máy` (tách rõ lỗi nền tảng vs lỗi script)

### 4.3 Date Drift Guard Trong Cron State File
- Trong cron feeder/reporter, khi sang ngày mới (`data.get("date") != today`), BẮT BUỘC ghi ngay state mới xuống đĩa (`save_daily_state`), cấm chỉ reset trong RAM rồi thoát sớm khi pool cạn ứng viên.
- Script báo cáo BẮT BUỘC kiểm tra `state.get("date") == today` trước khi lấy `used_proxies` và `success_emails` để triệt tiêu hiện tượng in lặp số liệu ngày cũ ("3 IPs used", "0 accounts").

