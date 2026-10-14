# GPM Supervisor Proxy Port Cooldown Bottleneck Triage

## 1. Hiện tượng & Triệu chứng
- User hoặc telemetry báo cáo: Tiến độ login Hotmail/Gmail trên GPM quá chậm hoặc số lượng tài khoản đăng nhập thành công rất ít so với tổng queue (ví dụ: chỉ 10-20% queue chạy được, còn lại đứng im).
- Trạng thái profile phần lớn ở `PENDING` nhưng mỗi tick 5 phút supervisor chỉ bốc được 0-2 candidate hoặc không bốc được tài khoản mới nào.

## 2. Nguyên nhân kỹ thuật cốt lõi (Root Cause)

### 2.1. Cơ chế Cooldown 24h theo Proxy Port (`ip_action_history`)
- Trong `batch_gpm_5profiles_supervisor.py`:
  - Mỗi khi 1 profile thực thi stage `HOTMAIL_LOGIN` trên port proxy, timestamp được lưu vào `data["ip_action_history"][port]["HOTMAIL_LOGIN"]`.
  - Bộ lọc `select_candidates()` bắt buộc khoảng cách giữa 2 lần thực thi cùng stage trên cùng port proxy phải $\ge 24\text{ giờ}$ (`(now_dt - last_dt).total_seconds() < 24 * 3600`).
- **Nghẽn số lượng (Port Starvation):**
  - Nếu farm có 409 tài khoản nhưng chỉ có 39-80 port proxy (mỗi máy 1 port), trung bình 5-10 tài khoản dùng chung 1 port proxy.
  - Khi 1 tài khoản vừa chạy (dù thành công hay thất bại), 4-9 tài khoản còn lại trên port đó **buộc phải chờ 24h** mới được tới lượt.
  - Tối đa throughput lý thuyết của toàn cụm: $\le N_{\text{ports}}$ tài khoản/ngày.

### 2.2. Cơ chế cách ly 48h khi lỗi (`BLOCKED: Hotmail login that bai`)
- Tài khoản gặp lỗi login (sai mật khẩu mail, checkpoint, captcha khó, lỗi mạng) bị gán status `BLOCKED`.
- Logic tự phục hồi yêu cầu ngâm đủ 48 tiếng (`(now_dt - fail_time).total_seconds() >= 2 * 86400`) mới auto-unblock về `PENDING` để retry (tối đa 3 lần trước khi vào `QUARANTINE`).

## 3. Quy trình chẩn đoán O(1) trạng thái Queue

Thay vì quét đĩa hay đoán mò, đọc trực tiếp file state:
`D:\Taadaa\runtime\<farm>\cron-state\batch_gpm_5profiles_supervisor_state.json`

```python
import json
from pathlib import Path
from datetime import datetime, timezone

state_path = Path(r"D:\Taadaa\runtime\kibe\cron-state\batch_gpm_5profiles_supervisor_state.json")
data = json.loads(state_path.read_text(encoding="utf-8"))
now_dt = datetime.now(timezone.utc)
ip_history = data.get("ip_action_history", {})

# 1. Đếm port đang bị khóa 24h
locked_ports = sum(
    1 for port, stages in ip_history.items()
    if stages.get("HOTMAIL_LOGIN") and (now_dt - datetime.fromisoformat(stages["HOTMAIL_LOGIN"].replace("Z", "+00:00"))).total_seconds() < 86400
)

# 2. Phân loại lý do tài khoản PENDING bị skip
profiles = data.get("profiles", {})
reasons = {"port_cooldown_24h": 0, "cooldown_expired": 0}
for k, p in profiles.items():
    if p.get("status") == "PENDING" and p.get("stage") == "HOTMAIL_LOGIN":
        port = str(p.get("proxy_port") or "")
        t_str = ip_history.get(port, {}).get("HOTMAIL_LOGIN")
        if t_str and (now_dt - datetime.fromisoformat(t_str.replace("Z", "+00:00"))).total_seconds() < 86400:
            reasons["port_cooldown_24h"] += 1
        else:
            reasons["cooldown_expired"] += 1
```

## 4. Giải pháp điều chỉnh khi cần tăng tốc
1. **Kiểm tra loại Proxy:**
   - Nếu là **Proxy tĩnh (Static Residential / Datacenter):** BẮT BUỘC giữ nguyên cooldown 24h để bảo vệ tài khoản khỏi checkpoint của Microsoft.
   - Nếu là **Proxy xoay 4G (MobiProxy / Dongle xoay IP):** Cổng đổi IP sau mỗi lần ngắt/xoay, có thể giảm trần cooldown từ 24h xuống 6h-12h sau khi đã xác minh IP đã được xoay sạch.
2. **Khuyến nghị vận hành:**
   - Báo cáo rõ cho User số tài khoản đang PENDING là do cơ chế an toàn chống trảm acc của Microsoft, không phải do script bị đứng hay supervisor bị crash.
