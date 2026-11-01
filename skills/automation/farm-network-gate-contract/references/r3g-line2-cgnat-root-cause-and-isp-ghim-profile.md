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

## 2. Bản Chất Gốc Rễ: Profile Thuê Bao Trên BRAS/Radius Viettel (Không Phụ Thuộc Khởi Động Lại)
- **Sự Thật Kỹ Thuật (Ground Truth):**
  - Cấu hình OpenWrt hoàn toàn giống nhau giữa 2 cổng (`lan1` và `lan2`), cùng chạy giao thức `proto=pppoe`. OpenWrt chỉ gửi gói xác thực, không có quyền tự chọn IP Public hay IP CGNAT.
  - Việc cấp dải IP nào là **100% do profile tài khoản thuê bao được gán cố định trên trạm OLT/BRAS/Radius của Viettel**:
    * `hyn_gftth_tamnhb0`: Được gán profile Non-CGNAT (ra IP Public `117.5.x.x` với Gateway `27.68.227.150`).
    * `hyn_gftth_tamnhb1`: Bị gán profile CGNAT (`100.77.x.x` với Gateway `100.77.0.2`).
  - **Phản Bác Luận Điểm Sai Lệch:** Hoàn toàn KHÔNG CÓ chuyện "tùy lúc khởi động lại mà lúc Public lúc CGNAT" hay do OpenWrt cấu hình sai. Khi chưa ghim profile Non-CGNAT trên trạm, tài khoản này sẽ luôn luôn bị cấp dải `100.77.x.x`.

## 3. Quy Trình Làm Việc Với Kỹ Thuật Viettel (Ngắn Gọn & Chuẩn Chuyên Môn)
- Nhắn trực tiếp kỹ thuật trạm / tổng đài 18008119 với nội dung kỹ thuật đanh thép (bỏ qua văn mẫu suy diễn camera rườm rà):
  > *"Anh ơi, kiểm tra giúp em line `hyn_gftth_tamnhb1` với. Line này đang bị dính NAT (ra dải IP `100.77.x.x`), trong khi line kia (`hyn_gftth_tamnhb0`) thì ra IP chuẩn bình thường rồi. Anh nhờ trạm đổi profile nhả NAT sang IP Public động cho nick `tamnhb1` giống line `tamnhb0` giúp em với nhé!"*
- Kỹ thuật Viettel đổi profile trên hệ thống xong là line `tamnhb1` sẽ nổ đủ 8 IP Public sạch vĩnh viễn.
