# GPM Start Failed & Proxy Timeout Triage Guide

## 1. Triệu chứng nhận diện (Symptom)
- Cronjob nuôi Gmail (`gpm-gmail-nurture-watchdog`) hoặc automation worker báo lỗi đồng loạt:
  ```text
  ✓ [GPM Nurture] Hoàn tất nuôi 0/6 profile Gmail:
  - user1@gmail.com: FAIL (START_FAILED, 66.2s)
  - user2@gmail.com: FAIL (START_FAILED, 66.3s)
  ```
- File log (`D:\Taadaa\GPM auto\logs\cron_gpm_gmail_nurture.log`) ghi nhận:
  ```text
  [WARNING] Thử 1: Start <profile_id> thất bại: Không thể kết nối tới proxy
  [WARNING] Thử 2: Start <profile_id> thất bại: Không thể kết nối tới proxy
  [WARNING] Thử 3: Start <profile_id> thất bại: Không thể kết nối tới proxy
  [ERROR] [<email>] Không thể khởi động profile GPM!
  ```
- Thời lượng mỗi profile ~66s (do 3 lần retry x timeout kết nối proxy ~22s).

## 2. Bản chất kỹ thuật & Cơ chế Fail-Closed của GPM
- Khi gọi endpoint `GET /api/v3/profiles/start/{id}`, GPMLogin luôn kiểm tra tính thông suốt của proxy gán trong `raw_proxy` trước khi cấp port CDP / mở trình duyệt Chromium.
- Nếu proxy upstream không phản hồi (Connection Timed Out hoặc Connection Refused), GPM kích hoạt cơ chế an toàn **fail-closed** từ chối khởi động browser để tránh rò rỉ IP Direct/Wi-Fi của máy chủ.

## 3. Quy trình chẩn đoán O(1) (Fast Triage Checklist)

### Bước 1: Trích xuất `raw_proxy` của profile lỗi từ GPM API
```python
import requests
res = requests.get("http://127.0.0.1:19995/api/v3/profiles/<profile_id>").json()
raw_proxy = res.get("data", {}).get("raw_proxy")
print("Raw proxy:", raw_proxy)  # Ví dụ: test.taadaa.click:5116:mobi16:TaadaaMobi#2026!
```

### Bước 2: Kiểm tra TCP socket tới proxy upstream
```python
import socket
host, port = "test.taadaa.click", 5116
s = socket.socket()
s.settimeout(2.0)
code = s.connect_ex((host, int(port)))
s.close()
print("Proxy status:", "OPEN" if code == 0 else f"DEAD (code {code})")
```

### Bước 3: Phân loại cụm Proxy tại Farm
1. **Cụm MobiProxy (`test.taadaa.click` - 32 ports `5101..5138`):**
   - Thiết bị phần cứng MT7621 đặt ngoài farm (nhà Khoa Lee), quản trị qua Web UI cổng 80.
   - Nếu cả cụm chết (DNS trả về IP cũ nhưng ping/socket port 80 & các port 51xx đều timed out) -> Box mất nguồn, rớt mạng hoặc mất điện.
2. **Cụm MikroTik (`mirotik1.taadaa.click` / `192.168.110.2` - 35 line PPPoE ports `10001..10035`):**
   - Thiết bị Router MikroTik nội bộ tại Farm Kibe.
   - Thường có độ ổn định cao hơn, nằm trên mạng LAN `192.168.110.2`.

### Bước 4: Kiểm tra mức độ ảnh hưởng trong Group Profile
```python
import requests
profiles = requests.get("http://127.0.0.1:19995/api/v3/profiles?group_id=10").json().get("data", [])
hosts = {}
for p in profiles:
    h = p.get("raw_proxy", "").split(":")[0] if p.get("raw_proxy") else "none"
    hosts[h] = hosts.get(h, 0) + 1
print("Phân bổ proxy Group 10:", hosts)
```

## 4. Giải pháp xử lý (Remediation)
1. **Khôi phục Upstream Box (Ưu tiên số 1):**
   - Báo kiểm tra nguồn điện, dây mạng, hoặc rút cắm lại nguồn Box MobiProxy tại vị trí đặt box.
   - Chờ box boot và modem redial (sau 1-2 phút kiểm tra lại bằng `python D:/Taadaa/AI-Tools/scripts/mobiproxy_auto_healer.py --check-only`).
2. **Chữa cháy tạm thời (Failover sang MikroTik):**
   - Nếu cần nuôi gấp hoặc box MobiProxy hỏng lâu dài, chuyển tạm các profile GPM sang dải port MikroTik (`mirotik1.taadaa.click:10001..10035`).
   - Cập nhật proxy profile qua GPM API:
     `POST http://127.0.0.1:19995/api/v3/profiles/update/{id}` với payload `{"raw_proxy": "mirotik1.taadaa.click:100xx:..."}`.
