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

### 2.3. Bẫy False-Positive "Bảo vệ tài khoản" trên Microsoft Account Landing Page (CHÍ MẠNG)
- **Hiện tượng:** Nick đã login thành công vào tới trang chủ `account.microsoft.com` nhưng script vẫn phán `FAILED / BLOCKED: Hotmail login that bai`.
- **Nguyên nhân gốc:**
  - Trên trang chủ `account.microsoft.com` giao diện tiếng Việt, Microsoft có sẵn card bảo mật chứa dòng chữ: *"Cập nhật thông tin để giúp bảo vệ tài khoản của bạn"*.
  - Nếu script đăng nhập (`batch_gpm_hotmail_password_login.py`) quét `page.inner_text("body")` tìm chuỗi `"bảo vệ tài khoản"` hoặc `"help us protect your account"` mà KHÔNG kiểm tra domain hiện tại, nó sẽ tưởng nhầm là checkpoint bảo vệ tài khoản (Challenge/OTP).
  - Không có Graph token để bypass OTP -> script tự đánh rớt thành `BLOCKED`.
- **Hậu quả kép:**
  1. Tài khoản đã login thành công bị đánh trượt và ngâm cooldown 48 tiếng.
  2. Cổng proxy của máy đó bị ghi nhận vừa chạy lỗi và bị khóa cứng 24 tiếng, khiến tất cả các nick `PENDING` khác trên cùng máy bị đóng băng hàng loạt.
- **Quy tắc bất biến:** BẮT BUỘC kiểm tra `is_auth = urlparse(cur_url).netloc.lower() in ["account.microsoft.com", "outlook.live.com", "privacynotice.account.microsoft.com"]`. Khi đã vào các domain này, XÁC NHẬN LOGIN THÀNH CÔNG NGAY, CẤM quét chuỗi challenge trên trang đã authenticated!

### 2.4. Cấm "Ngâm Ảo 7 Ngày" (WAIT_7D) khi chưa login session thật trên GPM
- **Sai lầm kiến trúc:** Thấy tài khoản có OAuth Refresh Token (Graph API) liền tự ý nhảy cóc qua mặt bước `HOTMAIL_LOGIN`, đẩy thẳng sang reg ChatGPT rồi đưa vào `WAIT_7D`.
- **Hậu quả:** Profile GPM không hề có session/cookie đăng nhập Hotmail thật bằng mật khẩu. Sau 7 ngày ngâm, khi chuyển sang bước đổi mật khẩu (`CHANGE_INFO` / `gpm_change_hotmail_security.py`), script mở profile lên sẽ thấy màn hình trắng hoặc bắt đăng nhập lại từ đầu -> Fail 100%!
- **Quy tắc bất biến:** 100% tài khoản Hotmail BẮT BUỘC phải chạy qua `HOTMAIL_LOGIN` trên GPM để lưu session sống trong trình duyệt.
- **Cơ chế Fast-track:** Sau khi `HOTMAIL_LOGIN` thành công, nếu tài khoản đã có sẵn cờ `chatgpt_registered_at` (đã reg ChatGPT trước đó), hệ thống lập tức chuyển thẳng sang `WAIT_7D` thật cùng session GPM sống, bỏ qua việc gọi lại script reg ChatGPT.

### 2.5. Đối soát Port Proxy Kibe vs Admin (Chống ngộ nhận)
- **Kibe (M1–80):** Có **39 port proxy** khả dụng (dải port `5101`–`5180` trong `D:/OneDrive/TaadaaData/kibe/PROXYgandienthoai.xlsx`).
- **Admin (M201–280):** Chỉ có **28 port proxy** khả dụng (dải port `10008`–`10035` trong `D:/OneDrive/TaadaaData/admin/PROXYgandienthoai.xlsx`).
- **CẤM TUYỆT ĐỐI** ngộ nhận Admin nhiều port hơn Kibe khi phân tích tốc độ hoặc tỷ lệ throughput.

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
