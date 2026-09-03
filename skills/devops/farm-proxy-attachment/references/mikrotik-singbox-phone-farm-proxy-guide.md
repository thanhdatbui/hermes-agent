# Sổ Tay Vận Hành MikroTik RouterOS & Sing-box Proxy Farm (Cập nhật: 2026-08-31)

## 1. Thông Tin Quản Trị & API
- **LAN API:** `192.168.110.2:9090` (RouterOS REST API).
- **WAN Host:** `mirotik1.taadaa.click` (`116.110.211.231`).
- **User / Pass:** `admin` / `N0spam@@`.
- **PPPoE Dashboard:** `https://mikrotik-tool.pages.dev`.

## 2. Quy Hoạch 80 Cổng Proxy Sing-box
- **Container Sing-box:** `172.17.0.2` trên MikroTik.
- **Port Mapping:** `20000 + Machine_ID` (Máy 1 -> 20001, Máy 80 -> 20080).
- **Upstream Mapping:** `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx`.
- **Hardware Kill-Switch:** DROP toàn bộ traffic từ `192.168.10.0/24` không đi qua Sing-box mixed proxy.

## 3. Lệnh Vận Hành Nhanh
```bash
# Kiểm tra MikroTik
python D:\Taadaa\AI-Tools\scripts\mikrotik_manager.py --check

# Tự động fix lỗi / restart container
python D:\Taadaa\AI-Tools\scripts\mikrotik_manager.py --fix

# Gán proxy ADB cho máy farm
python D:\Taadaa\AI-Tools\scripts\set_proxy_farm_adb.py --machines 41,64,65,66
```

## 4. Quy Tắc Báo Cáo Lỗi Gửi Bên Ngoài
- Chỉ báo cáo: Host, Port, hiện tượng / mã lỗi socket.
- Cấm tự ý đính kèm giải pháp / hướng dẫn kỹ thuật khi chưa được hỏi.
