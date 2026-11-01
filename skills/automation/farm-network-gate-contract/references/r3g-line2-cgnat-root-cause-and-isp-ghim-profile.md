# Chẩn Đoán & Khắc Phục Nguyên Nhân Line 2 PPPoE (tamnhb1) Bị Dính CGNAT 100.77.x.x

## 1. Hiện Trường Kỹ Thuật (Evidence Dump 2026-11-01)
Khi kiểm tra 16 sub-interfaces quay số PPPoE trên router Xiaomi R3G (cụm Thái Bình) qua LuCI ubus RPC:
- **Line 1 (Cổng `lan1` - Cổng giữa):**
  - Username: `hyn_gftth_tamnhb0`
  - Giao diện: `wan` và `wan_sub11` đến `wan_sub17`.
  - Kết quả IP: **8 IP Public Viettel độc lập 100%** (`117.5.62.126`, `117.5.183.211`, `116.107.116.183`, `116.104.210.119`...).
- **Line 2 (Cổng `lan2` - Cổng ngoài):**
  - Username: `hyn_gftth_tamnhb1`
  - Giao diện: `WAN2` và `wan_sub1` đến `wan_sub8`.
  - Kết quả IP: **Toàn bộ 8 sub-interfaces đều bị cấp dải CGNAT `100.77.x.x`** (`WAN2`: `100.77.27.98`, `wan_sub2`: `100.77.97.108`... `wan_sub8`: `100.77.6.239`).

## 2. Vì Sao Session Cũ Đã Từng Có IP Public Nhưng Sau Reboot Lại Bị Lại?
- **Bản chất BRAS Viettel Thái Bình (`TBH8001BRA01`):**
  - Tài khoản thuê bao `hyn_gftth_tamnhb1` **chưa được ghim cứng profile Non-CGNAT (IP Public động) trên cổng OLT trạm**.
  - Mỗi khi kết nối PPPoE reconnect (do router reboot, cúp điện hoặc rút cắm nguồn):
    - Trạm BRAS sẽ bốc ngẫu nhiên IP từ pool cấp phát.
    - Lần trước khi test ban đầu, router may mắn bốc trúng pool IP Public sạch (`117.5.152.x`).
    - Lần reboot sau đó, BRAS điều hướng thuê bao vào pool CGNAT (`100.77.x.x` / `100.64.0.0/10`).
    - Khi đó, cả 8 session quay số MACVLAN trên cổng `lan2` đều bị dồn vào pool CGNAT này, đi ra ngoài Internet bằng chung một IP gateway NAT (`117.5.152.50`), gây dồn chùm IP toàn bộ máy gán vào Line 2.

## 3. Quy Trình Xử Lý & Phòng Ngừa Triệt Để
1. **Thao tác nhanh trên Router (Thử vận may reconnect):**
   - Thực hiện restart riêng interface `WAN2` và các sub `wan_sub1..8` để gửi lại gói PADI/PADR xin cấp lại IP mới, kiểm tra xem có bốc lại được IP Public ngoài dải `100.x` hay không.
2. **Khắc phục dứt điểm 100% từ nhà mạng (Root Fix):**
   - Gọi tổng đài kỹ thuật Viettel **18008119** (nhánh 2 - hỗ trợ kỹ thuật internet cáp quang).
   - Đọc account: `hyn_gftth_tamnhb1` (hoặc số điện thoại chủ hợp đồng).
   - Nội dung yêu cầu chuẩn kỹ thuật:
     > *"Em ơi, đường internet nhà anh lắp camera giám sát và máy chủ nội bộ cần truy cập từ xa, nhờ kỹ thuật trực trạm ghim bỏ CGNAT (nhả NAT về dải IP Public động) trên cổng thuê bao giúp anh."*
   - Kỹ thuật Viettel thao tác ghim profile trên OLT/BRAS mất ~1-2 phút.
   - Sau khi ghim thành công, router dù reboot hay quay số lại bao nhiêu lần cũng vĩnh viễn nhận IP Public thật (`117.5.x.x`, `171.224.x.x`, `116.107.x.x`), triệt tiêu hoàn toàn nguy cơ tái phát CGNAT.
