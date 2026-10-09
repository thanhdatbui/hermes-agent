# Viettel PPPoE Outage, Sing-box Default Route Loss, and Farm Topology Reference (2026-10-09)

## 1. Sơ Đồ Đấu Nối Cáp Vật Lý Thực Tế (Phân Biệt Viettel vs FPT)

Trên thiết bị MikroTik x86 Mini PC (`PROXY` / `192.168.110.2`):
- **Cổng WAN 1 (`ether1`):** Cắm trực tiếp vào modem / converter cáp quang của **VIETTEL** (tài khoản FTTH `d511_gftth_khoind5`). Dùng để quay 60 phiên PPPoE (`pppoe-out1` đến `pppoe-out60` qua `macvlan1..60`) phục vụ dải proxy nội bộ `10001..10035`.
- **Cổng WAN 2 (`ether2`):** **TRỐNG** (không cắm dây).
- **Cổng WAN 3 (`ether3`):** Cắm vào switch **Ruijie của FPT** (mạng gia đình, dải IP `192.168.110.x`, gateway Ruijie `192.168.110.1`, IP WAN FPT `1.55.80.51`). Dùng làm cổng LAN nội bộ cho PC Kibe, điện thoại farm và web quản trị.
- **Cổng WAN 4 (`ether4`):** Cổng vật lý phụ cho macvlan dải cao (`macvlan46..60`).

---

## 2. Bản Chất Sự Cố: Tại Sao Viettel Rớt Lại Làm Liệt Cả Cụm Sing-box (MobiProxy 4G)?

### Câu hỏi phản xạ của người vận hành:
> *"Nhưng mà cục Viettel lỗi thì mất proxy mikrotik thôi, còn dây từ switch Ruijie cắm vào mini PC làm sing-box liên quan gì?"*

### Cơ chế kỹ thuật tầng Routing RouterOS & Container:
1. **Sing-box chạy bên trong Mini PC:** Container `sing-box` chạy dưới dạng RouterOS Container (`veth-singbox` gắn vào bridge `dockers_app`, IP `172.17.0.2`, gateway `172.17.0.1`).
2. **Sing-box Inbound vs Outbound:**
   - Inbound: Lắng nghe các cổng `20001..20080` trên IP LAN `192.168.110.2`.
   - Outbound: Đa số các cổng (ví dụ Máy 16 / port `20016`) được cấu hình chuyển tiếp ra server 4G MobiProxy ở ngoài (`test.taadaa.click:5118`, auth `mobi18`).
3. **Mắt xích chí mạng ở bảng định tuyến `main`:**
   - Cổng `ether3` (Ruijie/FPT) **chỉ được gán IP tĩnh LAN `192.168.110.2/24`**, hoàn toàn **KHÔNG có default route `0.0.0.0/0 gateway=192.168.110.1`**.
   - Tuyến đường ra Internet duy nhất của bảng định tuyến `main` phụ thuộc vào cờ `add-default-route=true` của interface `pppoe-out1` (trên line Viettel).
4. **Hệ quả khi đường truyền Viettel bị gián đoạn:**
   - Khi cục Viettel bị lỗi / mất quang (đèn LOS đỏ / RX=0 bytes / `LCP lowerdown`), toàn bộ các interface `pppoe-out1..60` chuyển sang trạng thái `down` / `disconnected`.
   - RouterOS tự động thu hồi và xóa sạch Default Route `0.0.0.0/0` trong bảng định tuyến `main`.
   - Toàn bộ lưu lượng xuất phát từ chính Mini PC và từ container Sing-box (`172.17.0.2`) khi gửi gói tin TCP ra Internet (`test.taadaa.click:5118` / `171.253.74.159`) bị RouterOS drop do **không có route ra ngoài** (`No route to host` / `network unreachable`).
   - Kết quả: Cổng `192.168.110.2:20016` từ phía PC/điện thoại vẫn connect TCP được (vì cùng mạng LAN Ruijie), nhưng bất kỳ HTTP proxy request nào cũng bị treo cứng và văng `context deadline exceeded` (Timeout).

---

## 3. Quy Trình Chẩn Đoán Phân Tầng O(1)

1. **Kiểm tra cổng Sing-box cục bộ:**
   ```python
   # TCP connect PASS nhưng HTTP GET timeout
   s.connect(('192.168.110.2', 20016)) # -> OK (cổng LAN mở)
   # Nhưng curl qua proxy bị timed out do Mini PC mất egress
   ```
2. **Kiểm tra Default Route trên MikroTik:**
   ```bash
   GET /ip/route?dst-address=0.0.0.0/0
   # Kiểm tra xem có route nào active=true trong routing-table=main không
   ```
3. **Phân biệt lỗi Viettel vs FPT:**
   - Mạng PC / Telegram / Wi-Fi nhà vẫn chạy bình thường: Tuyến FPT Ruijie trên `ether3` sống 100%.
   - Toàn bộ PPPoE trên web manager `kibe:2310` báo `DOWN (0/34 running)`: Tuyến Viettel trên `WAN1` bị đứt/treo converter.
