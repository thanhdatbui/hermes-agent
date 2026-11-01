# Kiến Trúc L2 MAC Device OpenWrt & Sự Khác Biệt Giữa R3G vs MobiProxy

## 1. Bản Chất Sự Khác Biệt Phần Cứng Lớp 2 (Data Link Layer)

Khi chạy đa phiên PPPoE trên cùng một đường cáp quang Viettel:
- **Cục MobiProxy (Box Linux chuẩn công nghiệp)**:
  - Cung cấp 4 cổng LAN/WAN vật lý riêng biệt (`Lan1`..`Lan4`) với 4 card mạng phần cứng và 4 địa chỉ MAC phần cứng thật (OUI chuẩn).
  - Khi cắm vào modem bridge Viettel, BRAS nhận diện ngay đây là các thiết bị vật lý độc lập, cấp phát IP Public bình thường mà không bị kích hoạt cơ chế containment.
- **Router Xiaomi R3G (Switch DSA nhúng OpenWrt)**:
  - Con R3G chỉ có 1 switch chip tích hợp MediaTek MT7621. Các cổng `lan1`, `lan2` chia sẻ cấu trúc chuyển mạch nội bộ.
  - Khi cấu hình quay số PPPoE trên `lan1` (Line 0): Đã khai báo tường minh `device 'dev_lan1'` kèm MAC ảo `02:11:22:33:44:10` $\rightarrow$ BRAS Viettel nhận diện phiên riêng biệt, cấp đủ 8 IP Public.
  - Cổng `lan2` (Line 1): Trong file `/etc/config/network`, `lan2` dùng mục ẩn danh `cfg090f15` **KHÔNG CÓ DÒNG MACADDR**. Router fallback dùng MAC gốc của router/switch.
  - Khi các sub-interface `macvlan` `mvl1..mvl8` quay số trên một parent device không có MAC độc lập hoặc xung đột bảng CAM của switch chip, các gói tin PADI/PADR bị trạm Viettel coi là hành vi multi-session bất thường và tự động gán vào pool cô lập CGNAT (`100.77.x.x`).

## 2. Quy Chuẩn Khai Báo MAC Device Độc Lập Cho Mọi Cổng WAN Trên OpenWrt

Mọi cổng WAN vật lý trên OpenWrt dùng để quay PPPoE BẮT BUỘC phải được khai báo thành một `device` tường minh có `macaddr` riêng:
```sh
# Line 0 (lan1)
uci set network.dev_lan1=device
uci set network.dev_lan1.name='lan1'
uci set network.dev_lan1.macaddr='02:11:22:33:44:10'
uci set network.dev_lan1.mtu='1500'

# Line 1 (lan2) - BẮT BUỘC KHAI BÁO TƯƠNG TỰ
uci set network.dev_lan2=device
uci set network.dev_lan2.name='lan2'
uci set network.dev_lan2.macaddr='02:11:22:33:44:20'
uci set network.dev_lan2.mtu='1500'

uci set network.WAN2.device='lan2'
uci commit network
```

## 3. Quy Tắc Bảo Toàn Kết Nối Khi Thi Công Router Nhúng Từ Xa
1. **CẤM restart bừa bãi toàn bộ service network**: Lệnh `/etc/init.d/network restart` có thể làm rớt cả LAN, drop session Web/SSH và làm treo router nếu có lỗi cú pháp.
2. **Chỉ can thiệp cục bộ**: Dùng `ifdown WAN2` / `ifup WAN2` để tái thiết lập riêng interface cần sửa. Đường `wan` (Line 0) đang giữ kết nối Internet và Dropbear SSH phải được giữ nguyên vẹn 100%.
3. **Luôn kiểm tra TCP Handshake trước và sau thao tác**: Đối soát `Test-NetConnection` port 22 và port 80 từ xa để đảm bảo router luôn reachable.
