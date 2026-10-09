# Quy Chuẩn Phân Bổ Proxy Pool & Chống Kẹt Timeout Cục Bộ Cho Batch Download Video

## Bối Cảnh Sự Cố (2026-09-11)
Khi khởi chạy batch download video cho Slot 7 & Slot 8 (`download_by_niche.py`), script được truyền file master `PROXYgandienthoai.xlsx`.
Trong file master này chứa cả:
1. 64 proxy MobiProxy (`test.taadaa.click:5101..5132`).
2. 14 proxy MikroTik (`mirotik1.taadaa.click:10001..10007`).

Dải MikroTik ngoài WAN đang bị timeout kết nối (`ConnectTimeoutError`, port 10005, 10007 do firewall DROP chặn WAN hoặc thiếu Hairpin NAT). Khi `ThreadPoolExecutor` (5-20 workers) chạy, các thread bốc trúng cổng chết dẫn đến dồn cục, liên tục retry và xuất hiện hàng loạt lỗi:
`Unable to download API page: ('Unable to connect to proxy', ConnectTimeoutError(... 'Connection to mirotik1.taadaa.click timed out.'))`
Hệ quả: User phát hiện và nhắc nhở nghiêm khắc: *"batch download đã thiết kế pool proxy để xoay trải ra nhiều port rồi mày lại đâm đầu all in 1 port?"*.

---

## Nguyên Tắc Vận Hành Proxy Bắt Buộc

### 1. CẤM NẠP FILE PROXY MASTER CHƯA QUA SÀNG LỌC
- Tuyệt đối không truyền trực tiếp file master Excel (`PROXYgandienthoai.xlsx`) vào `--proxy-pool` nếu chưa lọc các cổng đang LIVE.
- Phải tách riêng danh sách proxy theo hạ tầng:
  - **MobiProxy Pool (`test.taadaa.click`)**: 32 cổng live 100%, phản hồi ~0.6s, xoay IP 4G di động sạch.
  - **MikroTik LAN / Direct (`10001..10035`)**: Cổng MikroTik WAN bị DROP từ ngoài mạng; muốn dùng từ PC Kibe phải đi qua IP LAN `192.168.110.1` hoặc cấu hình Hairpin NAT trên router.
- **CẤM suy diễn lan man về vai trò proxy**: Cả MobiProxy lẫn MikroTik đều cùng phục vụ nuôi điện thoại như nhau. Không được suy diễn "cổng này chỉ dành cho máy, cổng kia để tải" hay vội vã đổ lỗi do quá tải máy. Lỗi thuần túy do **Network Route / Firewall Drop** trên cổng WAN của router.

### 2. PREFLIGHT HEALTH CHECK TRƯỚC KHI KHỞI CHẠY BATCH DOWNLOAD
Trước khi nạp danh sách proxy vào file pool text, bắt buộc chạy đoạn probe O(1) kiểm tra độ trễ và tính khả dụng:
```python
import urllib.request, urllib.parse, time
from pathlib import Path

raw_proxies = [...] # Trích xuất từ config / excel
live_proxies = []
for p in raw_proxies:
    host, port, user, pwd = p.split(":")[:4]
    proxy_url = f"http://{urllib.parse.quote(user)}:{urllib.parse.quote(pwd)}@{host}:{port}"
    handler = urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
    opener = urllib.request.build_opener(handler)
    try:
        req = urllib.request.Request("https://api.ipify.org", headers={"User-Agent": "curl/7.88.1"})
        with opener.open(req, timeout=3) as resp:
            ip = resp.read().decode("utf-8").strip()
            live_proxies.append(p)
    except Exception:
        continue

Path("D:/Taadaa/Tiktok-video/live_mobi_proxies.txt").write_text("\n".join(live_proxies), encoding="utf-8")
```

### 3. CƠ CHẾ XOAY TRÒN ROUND-ROBIN QUA TẤT CẢ CÁC CỔNG
- Trong `download_by_niche.py`, hàm `next_proxy()` sử dụng biến toàn cục `_PROXY_IDX` xoay vòng qua toàn bộ `len(_PROXY_POOL)` trên từng request.
- Khi có $N$ cổng live (ví dụ 32 cổng MobiProxy 5101..5132), tải song song với `--parallel 5` đến `--parallel 16` sẽ phân bổ đều $1/N$ tải cho từng cổng, ngăn ngừa triệt để hiện tượng dồn cục vào 1 cổng gây rate limit hoặc sập NAT box MobiProxy.
- Cờ gọi canonical:
  `--proxy-pool "D:/Taadaa/Tiktok-video/live_mobi_proxies.txt"`
