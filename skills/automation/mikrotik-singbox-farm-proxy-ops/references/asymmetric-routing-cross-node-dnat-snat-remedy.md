# Asymmetric Routing Trap in Cross-Node Kernel DNAT & SNAT Remedy

## 1. Hiện Tượng Sự Cố (The Asymmetric Routing Pitfall)
Khi định tuyến gói tin proxy từ router trung tâm (MikroTik Đà Nẵng) sang router proxy biên (Xiaomi R3G OpenWrt Thái Bình) bằng cơ chế Kernel DNAT:
```routeros
/ip firewall nat add chain=dstnat protocol=tcp dst-port=20203 action=dst-nat to-addresses=116.107.114.137 to-ports=5141
```
Gói tin gửi từ client (điện thoại S7 / PC Kibe) tới cổng `20203` bị **`timed out` (100% rớt kết nối)** mặc dù port `5141` trên OpenWrt vẫn `LISTEN`.

## 2. Nguyên Nhân Gốc Rễ (Root Cause)
1. **Lệch đường trả về (Asymmetric Path):** 
   - MikroTik thực hiện `dst-nat` chỉ đổi IP đích thành IP WAN của R3G, nhưng **giữ nguyên IP nguồn là IP gốc của Client**.
   - Gói tin đến R3G qua cổng WAN cáp quang chính (`116.107.114.137`), tiến trình Tinyproxy trên R3G tiếp nhận và xử lý.
   - Nhưng khi Tinyproxy phát gói tin trả lời (TCP SYN-ACK / response): Do Tinyproxy được bind vào card mạng con PPPoE (`pppoe-WAN2` mang dải IP `100.123.x.x`), nhân Linux của R3G nhìn vào default route của bảng định tuyến PPPoE và **đẩy gói tin trả lời đi ra ngoài bằng đường PPPoE con thay vì trả ngược lại cổng WAN cáp quang đã nhận**!
   - Kết quả: Client hoặc MikroTik đang chờ câu trả lời từ IP `116.107.114.137` không bao giờ nhận được gói tin $\rightarrow$ Timeout.

## 3. Phác Đồ Xử Lý Chuẩn (Kernel Hairpin SNAT)
Không cần cấu hình bảng định tuyến phức tạp (`ip rule / ip route`) trên R3G. Xử lý triệt để ngay tại MikroTik bằng cách bổ sung một rule **Source NAT (Masquerade)** song hành với DNAT:

```routeros
# Rule 1: Chuyển tiếp cổng đích (DNAT)
/ip firewall nat add chain=dstnat protocol=tcp dst-port=20203 action=dst-nat to-addresses=116.107.114.137 to-ports=5141 comment="DNAT_M203_TO_R3G"

# Rule 2: Ép đổi IP nguồn thành IP của MikroTik (Hairpin SNAT)
/ip firewall nat add chain=srcnat protocol=tcp dst-address=116.107.114.137 dst-port=5141 action=masquerade comment="SNAT_OUT_TO_R3G"
```

### Cơ chế hoạt động:
- Khi gói tin bay sang R3G, R3G thấy IP nguồn gửi đến chính là **IP WAN của MikroTik** (đã nằm trong danh sách Allow của Tinyproxy).
- R3G bắt buộc phải trả ngược câu trả lời về đúng IP MikroTik qua đường WAN kết nối.
- MikroTik nhận lại gói tin, hoàn tác SNAT và trả về cho Client $\rightarrow$ Kết nối thông suốt 100%, độ trễ thấp và CPU MikroTik tiêu tốn < 2%.
