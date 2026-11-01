# OpenWrt Multi-WAN PPPoE: CGNAT (100.x / 172.x) vs Missing MAC / Switch Port Conflict

## 1. Context & The False Attribution Trap
Khi router OpenWrt (như Xiaomi R3G chip MediaTek MT7621 / MT7530 DSA) kết nối nhiều đường cáp quang cùng nhà mạng (ví dụ 2 line Viettel):
- **Hiện tượng:** 
  - Line 0 (`lan1`, user `hyn_gftth_tamnhb0`): Quay PPPoE nhận đủ IP Public (`117.5.x.x`).
  - Line 1 (`lan2`, user `hyn_gftth_tamnhb1`): Quay PPPoE bị dính dải CGNAT (`100.77.x.x`) hoặc dải Private ISP (`172.17.x.x`).
- **Cạm bẫy:** Agent/Advisor vội vàng kết luận "100% do nhà mạng gán profile CGNAT trên OLT/BRAS" và bảo User gọi tổng đài, trong khi thực tế trên thiết bị phần cứng khác (ví dụ box MobiProxy 4 port card mạng riêng) cắm sợi dây đó lại quay ra IP Public bình thường!

## 2. Root Cause: OpenWrt Switch MAC Duplication
- **Bản chất phần cứng MT7530 switch trên OpenWrt:**
  - Cổng `lan1` được khai báo trong `/etc/config/network`:
    ```uci
    config device 'dev_lan1'
        option name 'lan1'
        option macaddr '02:11:22:33:44:10'
    ```
    Nhờ có MAC ảo riêng biệt, gói tin PPPoE Discovery (`PADI`) gửi lên BRAS có danh tính độc lập.
  - Cổng `lan2` (`WAN2`) bị thiếu khai báo `config device` chứa `macaddr` riêng -> Nó lấy MAC mặc định của router (hoặc MAC switch chung).
  - Khi 2 session PPPoE cùng gửi request lên trạm BRAS từ cùng 1 MAC hoặc xung đột bảng switch DSA, BRAS nhận diện phiên bất thường và tự động cô lập vào pool CGNAT hoặc trả về IP nội bộ.

## 3. Investigation Protocol (Cấm vội đổ lỗi nhà mạng)
1. **Audit MAC từng cổng PPPoE:**
   - Đọc trực tiếp `/etc/config/network`: mọi cổng vật lý làm WAN (`lan1`, `lan2`, `wan`) và MACVLAN (`mvl*`) BẮT BUỘC phải có `macaddr` duy nhất.
2. **Cross-Hardware Validation:**
   - Nếu cắm sợi cáp đó sang một thiết bị khác (MobiProxy, máy tính quay trực tiếp) mà nổ IP Public -> Khẳng định 100% lỗi do cấu hình MAC / Interface / DSA trên OpenWrt, tuyệt đối không bắt User gọi nhà mạng.
3. **Sửa cấu hình:**
   - Gán `macaddr` riêng cho `lan2`:
     ```bash
     uci set network.dev_lan2=device
     uci set network.dev_lan2.name='lan2'
     uci set network.dev_lan2.macaddr='02:11:22:33:44:20'
     uci commit network
     /etc/init.d/network restart
     ```
