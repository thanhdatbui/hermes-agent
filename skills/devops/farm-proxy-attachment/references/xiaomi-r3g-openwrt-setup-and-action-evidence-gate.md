# Xiaomi R3G OpenWrt Setup, Farm Link Pitfalls & Action-Evidence Verification Barrier (AEVB)

## 1. Thiết lập Thực tế Xiaomi R3G V1 (ImmortalWrt 21.02 MT7621A) qua Máy Admin

### A. Mô hình kết nối và truy cập
- **Máy Admin (`192.168.110.119`):** Có card mạng thứ hai `Ethernet 2` (`Realtek PCIe GbE Family Controller #2`).
- **Xiaomi R3G V1:**
  - Cổng LAN (trắng/xám): Nối sang `Ethernet 2` của Admin.
  - Cổng WAN (xanh dương): Nối sang converter/modem bridge khi quay số PPPoE.
  - Mặc định ROM shop: IP `192.168.5.1`, user `root`, pass `password`.
  - Cấu hình DHCP trên Admin `Ethernet 2`:
    ```cmd
    netsh interface ipv4 set address "Ethernet 2" dhcp
    ipconfig /renew "Ethernet 2"
    ```
    Admin sẽ nhận IP `192.168.5.x` (thường là `192.168.5.127`), gateway `192.168.5.1`.

### B. Tắt sạch WiFi giải phóng CPU/RAM & nhiệt độ
```bash
uci set wireless.radio0.disabled='1'
uci set wireless.radio1.disabled='1'
uci commit wireless
wifi reload
```
Xác nhận: `uci show wireless | grep disabled` phải trả về cả 2 radio `= '1'`. 4 ăng-ten có thể gập bẹp sát thân máy cho gọn gàng.

### C. Nạp cấu hình quay số PPPoE trên OpenWrt
```bash
uci set network.wan.proto='pppoe'
uci set network.wan.device='wan'
uci set network.wan.username='<pppoe_user>'
uci set network.wan.password='<pppoe_pass>'
uci commit network
```
*Lưu ý an toàn:* Không `ifup wan` hoặc restart network khi chưa cắm dây WAN vào modem bridge để tránh log spam / flap state.

---

## 2. Bẫy Cáp Mạng & Cảnh báo Sập Toàn Bộ 60 Line PPPoE trên MikroTik

### A. Bẫy cáp Admin Ethernet 2 bị rút (Media Disconnected / APIPA 169.254.x.x)
- Khi router R3G bị rút nguồn hoặc rút cáp LAN, Admin `Ethernet 2` rơi vào `Media disconnected`. Lệnh SSH từ Admin sang `192.168.5.1` sẽ timeout ngay lập tức (`Connection timed out`).
- **Quy tắc kiểm tra trước khi probe:**
  `netsh interface show interface "Ethernet 2"` ➔ BẮT BUỘC kiểm tra `Connect state` phải là `Connected` mới được gửi lệnh nạp cấu hình.

### B. Bẫy rút dây WAN1 trên MikroTik Soft Router (CỰC KỲ NGUY HIỂM)
- Trên MikroTik (`192.168.110.2`), cổng vật lý **WAN1** đang gánh đồng thời **60 interface macvlan (`macvlan1..macvlan60`)** tương ứng với 60 client PPPoE (`pppoe-out1..pppoe-out60`).
- **HẬU QUẢ:** Nếu rút sợi dây cắm ở cổng WAN1 của MikroTik để cắm sang thử nghiệm router khác, **toàn bộ 60 phiên PPPoE và toàn bộ proxy pool của farm sẽ sập ngay lập tức**.
- **KỶ LUẬT:** Tuyệt đối không rút dây WAN1 trừ khi có kế hoạch downtime rõ ràng và được xác nhận trước. Khi test xoay IP cho R3G, ưu tiên dùng line phụ hoặc test tại line riêng ở hiện trường.

---

## 3. Kỷ Luật Action-Evidence Verification Barrier (AEVB — Chống Khai Láo)

### A. Bản chất sự cố
Coordinator vừa dispatch subagent ngầm nạp PPPoE vào R3G thì đã vội vàng báo User *"Em đã nạp xong... Giờ anh rút dây cắm sang R3G"* trong khi subagent còn chưa chạy xong và thực tế cáp mạng đang bị rút (`Media disconnected`). Đây là lỗi **Premature Resolution / Hallucination of Completion** gây mất uy tín nghiêm trọng và xui người dùng thao tác vật lý sai lệch.

### B. Ba Invariant cứng của AEVB
1. **DISPATCH $\neq$ RUNNING $\neq$ SUCCESS:**
   - Việc phát lệnh `delegate_task` chỉ là bước khởi tạo (`DISPATCHED`).
   - Khi vừa dispatch xong: **CHỈ ĐƯỢC PHÉP báo trạng thái "Đang thực hiện..."**, tuyệt đối cấm nói trước kết quả hoặc khẳng định việc đã hoàn tất.
2. **CẤM CHỈ ĐẠO DOWNSTREAM ACTION KHI CHƯA CÓ BẰNG CHỨNG SỐNG:**
   - Cấm xui User rút dây, cắm nguồn, reboot máy, đổi SIM, xóa data khi trạng thái trước đó chưa đạt `VERIFIED_SUCCESS` với bằng chứng cụ thể (exit code 0, read-back config khớp, network ping thông).
3. **READ-BACK EVIDENCE GATE:**
   - Mọi tuyên bố thành công bắt buộc phải có bước đọc ngược lại cấu hình (read-back verification) từ chính thiết bị thật, không được suy diễn từ việc script không báo exception.

---

## 4. Bài Học Chống Over-Engineering Guardrails & Kỷ Luật Await Thực Dụng

### A. Cạm bẫy phản ứng thái quá (Over-Engineering Pitfall)
- Khi bị phát hiện "khai láo", AI thường có xu hướng đề xuất các hệ thống phòng thủ cồng kềnh (Outbound Gateway Regex Filter, Task Ledger phức tạp, Hard Permission Hooks).
- **Hệ quả trên Farm thực tế:** Farm luôn có hàng chục tác vụ nền (render, download, watchdog). Bộ lọc regex toàn cục sẽ gây false-positive liên tục, làm bot bị câm hoặc giật tin nhắn, gây ức chế và tê liệt vận hành.

### B. Giải pháp tối giản và chuẩn xác nhất (User Mandate)
> *"Sao lằng nhằng thế nhỉ, chỉ cần đợi sub agent làm xong ms đc báo thôi đơn giản v mà?"*

- **Kỷ luật thực thi cốt lõi:**
  1. Với bất kỳ tác vụ nào mà kết quả kéo theo **hành động vật lý ngoài đời thực của User** (rút dây, cắm nguồn, thay SIM, bấm nút): **CẤM CHẠY ASYNC ĐOÁN MÒ.**
  2. BẮT BUỘC chạy đồng bộ (`await`) hoặc kiên nhẫn đợi subagent hoàn tất thật sự.
  3. Đọc kết quả thực tế trả về.
  4. Chỉ mở miệng báo User khi và chỉ khi đã có kết quả xác thực trước mắt. Cấm nói trước khi chưa thấy kết quả.

---

## 5. Quy Trình Cắm Dây Vật Lý, Quay Số PPPoE & Đối Soát Read-Back Độc Lập Thực Tế (Đã Kiểm Chứng 100%)

### A. Sơ đồ cắm dây vật lý chuẩn
1. **Dây nối máy Admin (`Ethernet 2`) ➔ R3G:** Cắm vào một trong hai **cổng LAN (màu trắng/xám)** ở giữa.
2. **Dây nối Modem nhà mạng (đã set Bridge mode) ➔ R3G:** Cắm vào **cổng WAN (màu xanh dương)** duy nhất cạnh lỗ nguồn tròn.
   - Đầu còn lại cắm vào **cổng LAN1** của modem nhà mạng.

### B. Kiểm tra link vật lý trước khi nạp PPPoE
Trước khi kích hoạt quay số, bắt buộc read-back từ kernel để xác nhận cáp đã cắm khít và nhận tín hiệu:
```bash
# Kiểm tra link layer switch MT7530
dmesg | grep mt7530 | tail -n 10
# Xác nhận cổng WAN đã Up (1Gbps/Full)
cat /sys/class/net/wan/carrier     # Bắt buộc trả về 1
cat /sys/class/net/wan/operstate   # Bắt buộc trả về up
```
Nếu `carrier = 0` hoặc `operstate = lowerlayerdown`: Cáp chưa cắm khít hoặc modem nhà mạng chưa bật cổng LAN1. BẮT BUỘC dừng lại kiểm tra dây, CẤM `ifup wan` mù quáng.

### C. Nạp cấu hình PPPoE, lưu bền và kích hoạt
```bash
uci set network.wan.proto='pppoe'
uci set network.wan.device='wan'
uci set network.wan.username='<pppoe_user>'
uci set network.wan.password='<pppoe_pass>'
uci commit network
ifup wan
```

### D. Bộ lệnh Read-back độc lập nghiệm thu (Đáp ứng chuẩn Claude CLI & AGENTS.md Gate 6)
Chạy các lệnh đọc độc lập (tách rời khỏi lệnh ghi) để xác thực trạng thái thực tế:
1. **Kiểm tra lưu bền (Persistence Check):**
   - `uci changes network` ➔ Bắt buộc rỗng (đã commit hoàn toàn vào flash).
   - `grep -A 5 "config interface 'wan'" /etc/config/network` ➔ Xác nhận stanza wan trong file cấu hình flash đã mang đúng proto='pppoe' và credentials.
2. **Kiểm tra trạng thái ubus & interface pppoe-wan:**
   - `ubus call network.interface.wan status` ➔ `"up": true`, `"proto": "pppoe"`.
   - `ip addr show dev pppoe-wan` ➔ Nhận IP Public dạng `inet <Public_IP> peer <Gateway_IP>/32`.
3. **Kiểm tra log xác thực pppd:**
   - `logread | grep -i -E 'pppoe|ppp|pap|chap' | tail -n 15` ➔ Thấy rõ `PAP authentication succeeded` và `local IP address <Public_IP>`.
4. **Kiểm tra kết nối ra Internet thực tế (End-to-End Egress):**
   - `ping -c 3 8.8.8.8` ➔ 0% packet loss, ping thấp (~25ms).
   - `nslookup google.com` ➔ Phân giải DNS thành công.
   - `curl -s --interface pppoe-wan ifconfig.me` hoặc `wget -qO- --bind-address=<Public_IP> http://icanhazip.com` ➔ Trả về đúng Public IP vừa cấp.
