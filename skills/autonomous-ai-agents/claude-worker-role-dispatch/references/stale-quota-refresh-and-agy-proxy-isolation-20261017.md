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

# Quy chuẩn cấu hình Antigravity Profile Pool (Proxy 4G 1-1 Invariant)

## 1. Hiện tượng treo socket khi dùng Direct IP (`proxy: null`)
- Khi profile Antigravity chạy qua IP mạng trực tiếp của host (`"proxy": null`), Google Antigravity áp dụng chính sách kiểm duyệt TLS handshake hoặc bóp băng thông nghiêm ngặt.
- Điều này khiến kết nối Named Pipe hoặc HTTP socket bị ngâm vô tận (Hang Socket 50s–60s) dẫn tới `[TIMEOUT] Antigravity CLI vượt quá thời gian chờ (60s)`.

## 2. Quy chuẩn gán Proxy 4G độc lập trong `profiles_config.json`
Toàn bộ các profile trong `D:/Taadaa/agy_profiles/profiles_config.json` **BẮT BUỘC gán Proxy 4G Mobi riêng biệt 1-1**:
```json
{
  "profiles": [
    {
      "name": "acc_01",
      "path": "D:/Taadaa/agy_profiles/acc_01",
      "proxy": "http://mobi1:TaadaaMobi%232026%21@test.taadaa.click:5101",
      "enabled": true
    },
    {
      "name": "acc_02",
      "path": "D:/Taadaa/agy_profiles/acc_02",
      "proxy": "http://mobi2:TaadaaMobi%232026%21@test.taadaa.click:5102",
      "enabled": true
    },
    {
      "name": "acc_03",
      "path": "D:/Taadaa/agy_profiles/acc_03",
      "proxy": "http://mobi3:TaadaaMobi%232026%21@test.taadaa.click:5103",
      "enabled": true
    },
    {
      "name": "acc_04",
      "path": "D:/Taadaa/agy_profiles/acc_04",
      "proxy": "http://mobi4:TaadaaMobi%232026%21@test.taadaa.click:5104",
      "enabled": true
    },
    {
      "name": "acc_05",
      "path": "D:/Taadaa/agy_profiles/acc_05",
      "proxy": "http://mobi5:TaadaaMobi%232026%21@test.taadaa.click:5105",
      "enabled": true
    },
    {
      "name": "acc_06",
      "path": "D:/Taadaa/agy_profiles/acc_06",
      "proxy": "http://mobi6:TaadaaMobi%232026%21@test.taadaa.click:5106",
      "enabled": true
    },
    {
      "name": "acc_07",
      "path": "D:/Taadaa/agy_profiles/acc_07",
      "proxy": "http://mobi7:TaadaaMobi%232026%21@test.taadaa.click:5107",
      "enabled": true
    }
  ]
}
```

## 3. Kiểm tra trạng thái Pool
```bash
python D:/Taadaa/tools/ag_cli.py pool-status
```
Đảm bảo toàn bộ profile hiển thị trạng thái `READY` và đi qua đúng proxy Mobi được phân công.
