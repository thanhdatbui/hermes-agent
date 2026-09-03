# Network-Level Policy-Based Routing (PBR) & Transparent Proxy Gateway

Tài liệu thiết kế kiến trúc định tuyến và Kill Switch ở tầng mạng (RouterOS / MikroTik / Mini PC) cho phone farm 160 máy (80 Kibe + 80 Admin), thay thế dần cho việc gán proxy trên từng điện thoại S7 (ViChanger/VpnService).

---

## 1. So sánh 2 Tầng Xử lý Proxy / Mạng Farm

| Tiêu chí | Tầng Điện thoại S7 (App VPN / ViChanger) | Tầng Router (MikroTik RouterOS / Mini PC) |
| :--- | :--- | :--- |
| **Cơ chế** | S7 mở tunnel `tun0`, app ViChanger login proxy upstream. | MikroTik định tuyến Layer 3 (PBR/Mangle) hoặc Container Sing-box làm Transparent Gateway. |
| **Tải S7** | Nặng, nóng máy, Android 8 dễ kill service, nghẽn ADB. | S7 siêu nhẹ, chỉ bắt Wi-Fi thường, không chạy app proxy. |
| **Độ phức tạp phần mềm** | Cần Watcher, Central Locks (`machine_*.lock.json`), Live-IP Gate, recovery loop. | Không cần lock, không cần watcher; S7 reboot là có mạng ngay. |
| **Kill Switch (Chống leak)** | Chặn bằng code preflight (`verify_live_ip=True`) + Always-on VPN. | Chặn bằng phần cứng (Blackhole Route trên MikroTik): Proxy sập $\rightarrow$ S7 mất mạng 100%. |
| **Phù hợp nhất** | Proxy ở xa (nhà khác) khi chưa có hạ tầng trung gian. | Đường mạng đa phiên tại chỗ (Admin) hoặc Farm tập trung. |

---

## 2. Mô hình Hạ tầng Mạng Kết hợp (Ruijie + 4 Aruba + MikroTik)

```text
[Đường 1: FPT 1 Gbps] ────────► [Ruijie 3200] (IP: 192.168.1.1, DHCP chính)
                                       │
                                       ▼
[Đường 2: Viettel Đa phiên] ──► [Mini PC MikroTik RouterOS] (IP: 192.168.1.254)
                                       │ (1x Cat6 LAN)
                                       ▼
                                [Switch PoE 8P / 16P]
                                       │
         ┌──────────────┬──────────────┴──────────────┬──────────────┐
         ▼              ▼                             ▼              ▼
     [Aruba 1]      [Aruba 2]                     [Aruba 3]      [Aruba 4]
    (SSID 1: 5G)   (SSID 2: 5G)                  (SSID 3: 5G)   (SSID 4: 5G)
     (40 máy)       (40 máy)                      (40 máy)       (40 máy)
     └────── Dàn Kibe (01–80) ──────┘             └───── Dàn Admin (200+) ──────┘
```

* **Cắm dây:** 
  * Đường FPT cắm vào WAN Ruijie.
  * Đường Viettel Đa phiên cắm vào WAN Mini PC MikroTik.
  * Cắm 1 dây LAN từ cổng LAN MikroTik vào Switch chung của 4 Aruba (không cần cắm vòng qua Ruijie để tránh tải CPU Ruijie).
* **Phân luồng Gateway:**
  * **80 máy Kibe:** Nhận Gateway `192.168.1.1` (Ruijie $\rightarrow$ FPT) $\rightarrow$ Chạy app VPN ViChanger kết nối tới cụm proxy nhà ông anh.
  * **80 máy Admin:** Gán DHCP Static Lease với Gateway `192.168.1.254` (MikroTik) $\rightarrow$ MikroTik PBR ra các phiên PPPoE Viettel.

---

## 3. Cấu hình Định tuyến & Kill Switch trên RouterOS v7

### A. Dàn Admin: Native PBR ra từng phiên PPPoE
1. **Quay PPPoE:** Tạo `pppoe-out1`, `pppoe-out2`... trên interface WAN Viettel.
2. **Cố định IP S7:** Đặt DHCP Static cho 80 máy (ví dụ `192.168.1.201` – `192.168.1.280`).
3. **Mangle Marking:**
   ```routeros
   /ip firewall mangle
   add chain=prerouting src-address=192.168.1.201 action=mark-routing new-routing-mark=TO_PPPOE_01 passthrough=no
   add chain=prerouting src-address=192.168.1.202 action=mark-routing new-routing-mark=TO_PPPOE_02 passthrough=no
   ```
4. **Routing Table & Kill Switch (Blackhole):**
   ```routeros
   /routing table add name=TO_PPPOE_01 fib
   /ip route
   add dst-address=0.0.0.0/0 gateway=pppoe-out1 routing-table=TO_PPPOE_01 distance=1 check-gateway=ping
   add dst-address=0.0.0.0/0 type=blackhole routing-table=TO_PPPOE_01 distance=2
   ```
   *Khi `pppoe-out1` down hoặc mất ping gateway, route distance 1 bị disable $\rightarrow$ route distance 2 (blackhole) kích hoạt $\rightarrow$ Máy 201 mất mạng hoàn toàn, không thể lọt ra FPT hay phiên khác.*

---

### B. Dàn Kibe: Chuyển tiếp Proxy Từ Xa (Remote HTTP/SOCKS5) qua RouterOS Container
Nếu muốn bỏ ViChanger cho cả dàn Kibe (proxy đặt ở nhà khác):
1. **RouterOS v7 Container (Docker):** Bật tính năng Container trên RouterOS x86.
2. **Sing-box / Redsocks Container:** Chạy container Sing-box làm Transparent Proxy Gateway:
   * Map Source IP của từng máy S7 Kibe $\rightarrow$ Forward ra đúng Outbound Proxy (User:Pass@Host:Port nhà ông anh).
   * Nếu Outbound Proxy chết $\rightarrow$ Sing-box drop connection $\rightarrow$ S7 mất mạng, fail-closed an toàn.

---

## 4. Kiểm tra Thực tế Cụm Proxy Gateway 192.168.10.254 (Dàn Kibe)

* **Subnet & Gateway:** Mạng Wi-Fi dàn Kibe chạy dải `192.168.10.0/24`, Gateway nội bộ `192.168.10.254`.
* **Cổng Proxy Cục bộ:** Cụm proxy gateway lắng nghe trên các cổng `192.168.10.254:20001..20080` tương ứng từng máy (Máy $N \rightarrow$ Cổng $20000 + N$).
* **Hành vi Direct Wi-Fi (Khi không có ViChanger / chưa gán global proxy):**
  * Subnet Wi-Fi được cô lập, **KHÔNG có Transparent NAT trực tiếp** ra WAN.
  * Direct Ping (8.8.8.8) và Direct TCP Connect (104.26.12.205) từ shell Android bị Timeout / Block 100%.
* **Probe kiểm tra Proxy Gateway trực tiếp từ Android S7 (không cần curl/wget):**
  ```bash
  printf 'GET http://api.ipify.org/ HTTP/1.1\r\nHost: api.ipify.org\r\nProxy-Connection: close\r\n\r\n' | toybox nc -w 3 -W 3 -q 1 192.168.10.254 <PORT>
  ```
  *(Trả về `HTTP/1.1 200 OK` kèm Public IP proxy thành công).*
* **Kết luận vận hành:** Nếu không chạy ViChanger VpnService, điện thoại bắt buộc phải gán `settings put global http_proxy 192.168.10.254:<PORT>` hoặc cấu hình Wi-Fi Manual Proxy mới có mạng; Wi-Fi không tự động đi qua proxy nếu để mặc định.

