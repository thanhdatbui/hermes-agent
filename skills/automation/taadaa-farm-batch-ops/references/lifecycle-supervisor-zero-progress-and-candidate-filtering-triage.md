# Chẩn Đoán O(1) Khi Batch Lifecycle / Supervisor Báo Biến Động 0 (+0)

## Hiện Tượng
Trong báo cáo định kỳ 6h (`cron_hotmail_gpm_lifecycle_6h_report.py`) hoặc watchdog giám sát vòng đời tài khoản (Hotmail -> GPM -> ChatGPT -> Change Info), một farm hoặc giai đoạn hiển thị biến động `+0` (ví dụ: Farm Kibe 0 tài khoản được xử lý trong 6h qua) dù trong state vẫn còn hàng trăm tài khoản `PENDING` hoặc `WAIT_7D`.

## Cạm Bẫy Tư Duy (Anti-Pattern)
- **CẤM** vội vã kết luận supervisor bị treo, crash, dừng chạy hay lỗi hạ tầng khi chỉ nhìn vào số liệu `+0`.
- **CẤM** tự ý restart service, xóa state hoặc can thiệp cưỡng chế khi chưa kiểm tra logic chọn ứng viên (`select_candidates`).

## 4 Bộ Lọc Cơ Học Trong `select_candidates` Cần Kiểm Tra
Khi `batch_gpm_5profiles_supervisor.py` trả về `CANDIDATES=0 DISTINCT_PROXY_PORTS=0`, nguyên nhân bắt buộc nằm trong 5 bộ lọc sau:

### 1. Giãn Cách IP MobiProxy 24h (`ip_history_cooldown < 24h`)
- **Cơ chế**: Để chống checkpoint và quét hàng loạt từ Microsoft, mỗi cổng MobiProxy LAN (`proxy_port` từ 5101–5180 tương ứng với từng máy) bị khóa cứng tối đa 1 hành động `HOTMAIL_LOGIN` trong vòng 24 giờ:
  ```python
  last_time_str = ip_history.get(port, {}).get(stage)
  if last_time_str and (now_dt - parse_time(last_time_str)).total_seconds() < 24 * 3600:
      continue
  ```
- **Hệ quả**: Nếu toàn bộ 80 máy của cụm vừa thực hiện login trong đợt trước (ví dụ cách đây 19 giờ), toàn bộ hàng trăm tài khoản PENDING trên cụm đó sẽ đồng loạt bị bỏ qua trong ~5 giờ tiếp theo. Đây là trạng thái chờ an toàn, không phải lỗi.

### 2. Điều Kiện Tiên Quyết Cho `WAIT_7D` & `CHANGE_INFO` (`missing_tiktok_or_chatgpt`)
- **Cơ chế**: Dù tài khoản đã ngâm đủ 7 ngày (`now - anchor >= 7 * 86400`), supervisor bắt buộc tài khoản phải có đủ cả ChatGPT lẫn TikTok (`has_tiktok` hoặc `username` + `password`):
  ```python
  if stage in ("WAIT_7D", "CHANGE_INFO"):
      has_tik = bool(info.get("has_tiktok") or (info.get("username") and info.get("password")))
      has_cg = bool(info.get("has_chatgpt") or info.get("chatgpt_registered_at"))
      if not (has_tik and has_cg):
          continue
  ```
- **Hệ quả**: Nếu nick ngâm đủ 7 ngày nhưng thiếu thông tin nick TikTok tương ứng trên farm, tài khoản sẽ tiếp tục nằm ở `WAIT_7D` và không bao giờ được bốc sang `CHANGE_INFO` để đổi mật khẩu Hotmail, nhằm tránh mất dấu tài khoản chưa gắn nick.

### 3. Cooldown Lỗi (48h) và Cách Ly Vĩnh Viễn (`QUARANTINE`)
- **Cooldown 48h**: Tài khoản login thất bại (`BLOCKED`, `FAILED`, `ERROR`) chỉ được tự động mở khóa thử lại sau 48 giờ.
- **Quarantine ($\ge 3$ lần)**: Khi `login_retry_count >= 3`, tài khoản bị chuyển sang `QUARANTINE` và không bao giờ được supervisor tự động bốc lại trừ khi có can thiệp thủ công.

### 4. Cooldown Cục Bộ Profile & Giới Hạn Tiến Trình GPM
- **Scheduler Cooldown**: Khoảng cách tối thiểu giữa 2 lần xử lý cùng một profile là 1.800 giây (30 phút).
- **Concurrency Cap**: Nếu có $\ge 5$ tiến trình browser GPM (`gpm_browser`) đang chạy đồng thời trên máy, supervisor tự động bỏ qua tick đó để chống quá tải CPU/RAM.

## Quy Trình Triage Nhanh O(1)
Chạy script kiểm tra lý do skip trực tiếp trên file state (thay thế mọi phỏng đoán):
```bash
python -c "
import json
from pathlib import Path
from datetime import datetime, timezone

p = Path('D:/Taadaa/runtime/kibe/cron-state/batch_gpm_5profiles_supervisor_state.json')
d = json.loads(p.read_text(encoding='utf-8'))
profiles = d['profiles']
ip_hist = d.get('ip_action_history', {})
now_dt = datetime.now(timezone.utc)

for k, v in list(profiles.items())[:10]:
    port = str(v.get('proxy_port') or '')
    last_ip = ip_hist.get(port, {}).get(v.get('stage'))
    if last_ip:
        diff_h = (now_dt - datetime.fromisoformat(last_ip.replace('Z', '+00:00'))).total_seconds() / 3600
        print(f'{k} | port {port} | stage {v.get(\"stage\")} | IP cooldown: {diff_h:.1f}h / 24h')
"
```
