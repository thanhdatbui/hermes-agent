# Quy Trình Nghiệm Thu Proxy Farm 4 Bước (Anti-Blaming ISP & Persistence)

## 1. Bối Cảnh Sự Cố & Bài Học Xương Máu (02/11/2026)
- **Hiện tượng:** 29 máy Farm Admin báo `blocked-proxy-vpn` ở ca 12:00 trưa.
- **Sai lầm chết người của Agent:** Nhìn thấy vài port timeout vội vàng kết luận do mạng Viettel Thái Bình chập chờn / rớt cổng, gây ức chế tột độ cho User.
- **Sự thật kỹ thuật:** 100% các cổng R3G Thái Bình đều sống khỏe, nguyên nhân gốc do:
  1. Sing-box container trên MikroTik chưa trỏ outbound sang `tb.taadaa.click`, vẫn giữ IP PC Admin cũ `192.168.110.119`.
  2. File Excel và SQLite kẹt cờ `QUARANTINE_R3G_INVESTIGATION`.

---

## 2. Quy Trình 4 Bước Nghiệm Thu Proxy Bắt Buộc (Evidence-First)

Mỗi khi cấu hình, thay đổi hoặc lắp thêm box proxy mới, BẮT BUỘC thực thi tuần tự 4 bước sau trước khi đưa ra kết luận:

```
[Bước 1: Upstream Probe]
       │ Test trực tiếp: tb.taadaa.click:51xx -> api.ipify.org
       ▼ (Nếu LIVE -> CẤM đổ thừa do ISP/nhà mạng)
[Bước 2: Bridge Probe]
       │ Test qua MikroTik LAN: 192.168.110.2:202xx -> api.ipify.org
       ▼ (Nếu FAIL -> Kiểm tra Outbound Sing-box & restart container)
[Bước 3: Math Assert 1:1]
       │ assert IP_Singbox == IP_Upstream trên 100% máy
       ▼ (Bảo đảm không rò rỉ IP nhà FPT hoặc lẫn IP Đà Nẵng)
[Bước 4: Device ADB Verification]
       │ set_proxy_farm_admin_adb.py -> verify settings get global http_proxy
       ▼
[Nghiệm thu hoàn tất & Ghi lưu 4 nơi]
```

### Bước 1: Test Upstream Đích Trực Tiếp
```python
import urllib.request
req = urllib.request.Request('http://api.ipify.org')
h = urllib.request.ProxyHandler({'http': 'http://tb.taadaa.click:<port>'})
opener = urllib.request.build_opener(h)
ip = opener.open(req, timeout=4.0).read().decode().strip()
print(f"Direct Upstream IP: {ip}")
```
*Tiêu chuẩn:* Phải ra đúng IP Public của line mạng box proxy (ví dụ Viettel Thái Bình: `117.5.x.x` hoặc `116.104.x.x`).

### Bước 2: Test Bridge / Sing-box Trung Gian
```python
req = urllib.request.Request('http://api.ipify.org')
h = urllib.request.ProxyHandler({'http': 'http://192.168.110.2:<20000+m>'})
opener = urllib.request.build_opener(h)
ip = opener.open(req, timeout=4.0).read().decode().strip()
print(f"Sing-box Egress IP: {ip}")
```

### Bước 3: Đối Soát 1:1 Khớp Tuyệt Đối
So sánh trực tiếp kết quả Bước 1 và Bước 2. Toàn bộ máy phải khớp đúng IP của port upstream tương ứng theo tỷ lệ 1 proxy : 2 máy.

### Bước 4: Nạp & Xác Minh Trên Thiết Bị Android Thật
- Chạy script gán proxy ADB cho máy online:
  ```bash
  python D:/Taadaa/AI-Tools/scripts/set_proxy_farm_admin_adb.py
  ```
- Kiểm tra read-back:
  * `adb shell settings get global http_proxy` -> phải trả về `192.168.110.2:202xx`.
  * `adb shell dumpsys connectivity` -> Wi-Fi connected, captive portal = 0.

---

## 3. Quy Chuẩn Lưu Trữ Bền Vững 4 Nơi (Persistence Checklist)
Để chống tình trạng reboot máy hoặc chạy lại tool sinh config bị ghi đè mất:
1. **RouterOS Flash:** Nạp JSON minified vào `docker/config/config.json` và lưu bản backup `.bak_r3g` trên MikroTik.
2. **Code Generator:** Cập nhật script `scripts/generate_singbox_config.py` trong repo `AI-Tools` và chạy qua `unified_patch_pipeline.py` để Closeout Gate Approved.
3. **Sổ Cái SSOT:** Xóa sạch cờ QUARANTINE, ghi nhận cổng `202xx` trong `PROXYgandienthoai.xlsx` và `farm_master.db`, đồng bộ sang PC Admin.
4. **Điện thoại:** Nạp qua ADB, xác nhận thoát chế độ direct `:0`.
