# Viettel FTTH CGNAT Profile Root Cause & Technical Support Dispatch Protocol

## 1. Bản Chất Kỹ Thuật: CGNAT (100.64.0.0/10) trên BRAS / RADIUS
Khi 2 đường cáp quang Viettel kéo vào cùng một địa điểm (cùng nhà/phòng), cắm chung 1 router OpenWrt / MikroTik:
- **Line 0 (`tamnhb0`):** Quay PPPoE nhận dải IP Public động thật (`117.5.x.x`), Gateway PTP (`27.68.x.x`).
- **Line 1 (`tamnhb1`):** Quay PPPoE nhận dải CGNAT (`100.77.x.x` / `100.64.0.0/10`), Gateway PTP (`100.77.0.2`).
- **Khẳng định nguyên nhân:**
  * **0% do cấu hình Router:** OpenWrt / MikroTik chỉ là PPPoE client gửi gói `PADI/PADR` chứa User/Pass. Sau khi xác thực, BRAS của ISP hoàn toàn quyết định cấp IP nào qua giao thức `IPCP`.
  * **100% do Profile trên hệ thống OLT/BRAS/RADIUS:** Nhà mạng Viettel gán mặc định thuê bao cá nhân mới vào pool CGNAT chung để tiết kiệm IPv4. Tài khoản nào được kỹ thuật chọn profile không NAT thì mới được cấp IP Public động.
  * **CẤM AI ảo giác "do lúc restart bốc nhầm":** Profile gán cứng trên hệ thống trạm, khởi động lại bao nhiêu lần vẫn rơi vào CGNAT trừ khi nhà mạng đổi profile thuê bao.

## 2. Giao Thức Nhắn Tin / Báo Hỏng Kỹ Thuật Viettel (Ngắn Gọn & Đanh Thép)
Tuyệt đối không giải thích dông dài hay bịa chuyện camera nếu user không muốn. Nhắn thẳng vào vấn đề kỹ thuật mạng:

```text
Anh ơi, kiểm tra giúp em line hyn_gftth_tamnhb1 với. Line này đang bị dính NAT (ra dải IP 100.77.x.x), trong khi line kia (hyn_gftth_tamnhb0) thì ra IP chuẩn bình thường rồi.
Anh nhờ trạm đổi profile nhả NAT sang IP Public động cho nick tamnhb1 giống line tamnhb0 giúp em với nhé!
```

- **Điểm mấu chốt kỹ thuật:**
  1. Nêu đúng mã hợp đồng/user PPPoE: `hyn_gftth_tamnhb1`.
  2. Nêu rõ dải IP dính NAT: `100.77.x.x`.
  3. Đưa ra đối chứng thực tế cùng trạm: `hyn_gftth_tamnhb0` đã ra IP chuẩn.
  4. Nêu đúng hành động cần trạm xử lý: "Đổi profile nhả NAT sang IP Public động".
