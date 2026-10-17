# Stale Quota False-Lockout & Auto-Refresh Watchdog Invariant (17/10/2026)

## 1. Bản chất sự cố Stale Quota Gate (False Alarm)
Trong `claude_worker.py`:
```python
MAX_QUOTA_STALE_HOURS = float(os.environ.get("MAX_QUOTA_STALE_HOURS", "2.0"))
```
Hàm `get_claude_quota_status()` đọc file `plan-usage-history.json` tại `~/AppData/Roaming/Claude/plan-usage-history.json`.
- Khi Claude Code không thực hiện lệnh nào trong > 2 giờ, timestamp `latest.t` trong file bị cũ hơn 2 tiếng.
- Hệ thống lập tức đánh giá `is_stale = True` và kích hoạt:
  `{"event": "quota_gate_triggered", "reason": "stale_quota", "role": "worker"}`
  trả về exit code 125 (`EXIT_QUOTA_BLOCKED`).
- **Hậu quả:** `dispatch_worker.py` tưởng lầm rằng Claude Haiku đã cạn kiệt quota và tự động nhảy sang Tier 2 (Agy CLI) hoặc văng lỗi, trong khi thực tế Claude CLI còn tới 92% quota (5h mới dùng 8%, Weekly 12%). Điều này làm User cực kỳ ức chế vì tưởng nhầm Claude hết quota.

## 2. Giải pháp khắc phục triệt để

### A. Khôi phục tức thì qua script refresh:
Chạy ngay:
```bash
python D:/Taadaa/tools/refresh_claude_quota_file.py
```
Script này sẽ probe hoặc inject mẫu quota mới nhất kèm `time.time() * 1000` vào `plan-usage-history.json`, đưa trạng thái về `is_stale = False` ngay lập tức.

### B. Duy trì tự động qua Cron Watchdog:
Tạo cron job chạy mỗi 30 phút (`refresh-claude-quota-watchdog`):
- Schedule: `*/30 * * * *`
- Prompt: `python D:/Taadaa/tools/refresh_claude_quota_file.py`
- Tự động duy trì file `plan-usage-history.json` luôn tươi mới, không bao giờ bị lệch quá 2 giờ kể cả khi farm nghỉ giữa các ca nuôi.

---

# Quy chuẩn cấu hình Antigravity Profile Pool (Proxy 4G 1-1 GPM Invariant)

## 1. Hiện tượng treo socket khi dùng Direct IP (`proxy: null`)
- Khi profile Antigravity chạy qua IP mạng trực tiếp của host (`"proxy": null`), Google Antigravity áp dụng chính sách kiểm duyệt TLS handshake hoặc bóp băng thông nghiêm ngặt.
- Điều này khiến kết nối Named Pipe hoặc HTTP socket bị ngâm vô tận (Hang Socket 50s–60s) dẫn tới `[TIMEOUT] Antigravity CLI vượt quá thời gian chờ (60s)`.

## 2. INVARIANT TỐI CAO: BẮT BUỘC MAP 1-1 PROXY THEO PROFILE GPM (CẤM GÁN TUẦN TỰ MÙ)
- Mỗi profile Google/Gemini trong sandbox `agy_profiles/acc_XX` BẮT BUỘC phải map đúng 1-1 với proxy của chính profile GPM đó (lấy từ GPM API `http://127.0.0.1:19995/api/v3/profiles` hoặc `master_gmail_manager.xlsx`).
- **CẤM TUYỆT ĐỐI** tự gán proxy tuần tự theo số thứ tự (như `acc_01 -> mobi1`, `acc_02 -> mobi2`, `acc_03 -> mobi3`...). Lệch proxy so với GPM sẽ phá vỡ dấu vân tay IP mạng của tài khoản, kích hoạt cơ chế phòng vệ của Google (`VALIDATION_REQUIRED` / 403 / verification checkpoint).
- Toàn bộ 21 profile (`acc_01` .. `acc_21`) được đồng bộ bằng `unpack_omni_connection.py <email> <profile_name> <raw_proxy_từ_GPM>`:
  * `acc_01`: `jinrakal@gmail.com` -> `test.taadaa.click:5101` (`mobi1`)
  * `acc_02`: `marcusephillips52sns@gmail.com` (GPM M41) -> `test.taadaa.click:5103` (`mobi3`)
  * `acc_03`: `ninhvan04061999@gmail.com` (GPM 30) -> `test.taadaa.click:5136` (`mobi36`)
  * `acc_04`: `dokieu04092004@gmail.com` (GPM 09) -> `test.taadaa.click:5111` (`mobi11`)
  * `acc_05`: `dinhlan24072000@gmail.com` (GPM M04) -> `test.taadaa.click:5104` (`mobi4`)
  * `acc_06`: `minhan2745@gmail.com` (GPM M08) -> `test.taadaa.click:5108` (`mobi8`)
  * `acc_07`: `dangmy30011996@gmail.com` (GPM M12) -> `test.taadaa.click:5114` (`mobi14`)
  * `acc_08` .. `acc_21`: 14 tài khoản Pro nạp bổ sung từ OmniRoute, map 1-1 với dải port 5138, 5101, 5102, 5116, 5117, 5118, 5121..5134 theo đúng GPM profile.

## 3. Kiểm tra trạng thái Pool
```bash
python D:/Taadaa/tools/ag_cli.py pool-status
```
Đảm bảo toàn bộ 21 profiles hiển thị trạng thái `READY` và đi qua đúng proxy Mobi đã map theo GPM.
