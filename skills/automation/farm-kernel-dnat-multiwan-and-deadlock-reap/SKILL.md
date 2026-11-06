---
name: farm-kernel-dnat-multiwan-and-deadlock-reap
description: "Kỷ luật vận hành Kernel DNAT trên MikroTik, cơ chế Dead Lock Reap cho pipeline, và xử lý Asymmetric Routing trên Multi-WAN OpenWrt (R3G & MobiProxy)."
version: 1.0.0
category: automation
tags: [mikrotik, routeros, kernel-dnat, mobiproxy, openwrt, r3g, pipeline-lock, dead-lock-reap, farm-safety]
---
# Farm Kernel DNAT, Multi-WAN Routing & Pipeline Lock Governance

## 1. Bản Chất Hạ Tầng Vật Lý Proxy Farm
- **MobiProxy:** Cắm 4 line mạng cáp quang vật lý (Lan1..Lan4), mỗi line quay đa phiên 8 PPPoE chia ra các port proxy 5101..5138.
  - Trên web quản trị v3.0.67, bảng danh sách `#proxies` có menu dấu 3 chấm `•••` -> `Cấu hình truy cập` -> modal HTML5 Dialog với nút `#access-save` để đổi chế độ xác thực từng port sang `none` (Không xác thực).
  - Tắt pass trên MobiProxy an toàn 100% nhờ lớp tường lửa Chống scan proxy (Scan Guard Whitelist IP) tại mục `#security`.
- **Xiaomi R3G:** Cắm 2 line mạng cáp quang vật lý, quay đa phiên 16 đường PPPoE con:
  - Line 1 (LAN2): Cổng 5141-5148 (`pppoe-WAN2`, `wan_sub2..sub8`).
  - Line 0 (LAN1): Cổng 5151-5158 (`pppoe-wan`, `wan_sub11..sub17`).
  - 16 port Tinyproxy trên R3G vốn dĩ **không hề cài mật khẩu** (`BasicAuth` = none), bảo vệ bằng whitelist `Allow <mikrotik_ip>`.
- **CẤM NHỚ NHẦM BẢN CHẤT PHẦN CỨNG:** MobiProxy cắm 4 line cáp quang quay PPPoE, KHÔNG PHẢI cắm SIM 4G. R3G cắm 2 line cáp quang quay 16 PPPoE.

## 2. Kernel DNAT trên MikroTik & Cơ chế Chống Nghẽn CPU
- Thay vì để gói tin proxy của farm chui vào container Singbox (L7) gây nghẽn CPU 96-98%, sử dụng trực tiếp rule Kernel DNAT phần cứng (`dstnat` -> `to-addresses` IP WAN đại diện proxy, `to-ports` tương ứng).
- Đẩy toàn bộ rule Kernel DNAT lên đứng trước rule Singbox `*30E` để bắt trọn gói tin, giảm tải CPU MikroTik từ 97.6% về 0.4% - 1.6% (wire-speed 0.4s).
- **Tự động hóa đồng bộ DDNS khi ISP đổi IP:** Khi nhà mạng Viettel tự động nhả lease và đổi IP WAN của MobiProxy/R3G, cronjob (`update_mikrotik_scan_guard.py` chạy 1 phút/lần) tự phân giải DNS và cập nhật `to-addresses` cho toàn bộ các rule DNAT tương ứng, chống rớt mạng toàn farm.
- **Xóa Cronjob Tự Reset Proxy:** Tuyệt đối không để các watchdog cũ tự động gọi API reset cổng/reboot MobiProxy (như `cron_mobiproxy_healer.py`) làm rớt kết nối đột ngột của farm.

## 3. Mangle Bypass trên MikroTik & Phân Luồng Singbox vs Kernel DNAT
- **Cạm bẫy Mangle ép cổng ra:** Các máy Admin (`192.168.10.x`) trên MikroTik bị gắn các rule Mangle ép đi ra qua các đường `WAN8..WAN35` (`mark-routing`). Khi DNAT sang R3G, R3G chỉ chấp nhận và trả lời cho cổng `WAN1` (`pppoe-out1`). Nếu thiếu rule bypass, gói tin bị ép ra sai cổng WAN dẫn đến gãy kết nối (Connection Refused / Timeout).
- **Rule Mangle Bypass (Top #0):** Bắt buộc nạp rule `chain=prerouting dst-port=20201-20280 protocol=tcp action=accept` đặt ở vị trí đầu tiên của bảng Mangle để các gói tin proxy đi thẳng ra cổng mạng chính `WAN1`.
- **Phân định chiến lược Proxy Farm:**
  - **80 máy Kibe:** Chạy thẳng **Kernel DNAT 100%** qua MobiProxy (vì MobiProxy có 1 WAN đại diện, xử lý luồng đồng nhất wire-speed).
  - **32 máy Admin non (R3G):** Giữ chạy qua **Singbox**. Vì Singbox đóng vai trò L7 proxy client trung chuyển, tự động xử lý trơn tru hiện tượng Asymmetric Routing của 16 PPPoE trên OpenWrt. Với 80 máy Kibe đã bốc ra ngoài, tải CPU MikroTik chỉ ăn 2%, Singbox gánh 32 máy cực kỳ nhẹ nhàng và đảm bảo 100% điện thoại không bao giờ bị dấu chấm than Wi-Fi.

## 4. Invariant Chống Gửi Ảnh Màn Hình Đen (Display Power State=OFF Trap)
- **Cạm bẫy màn hình tắt sinh ảnh đen kịt:** Khi chụp màn hình điện thoại Android qua ADB `screencap`, nếu màn hình máy đang ngủ (`Display Power: state=OFF`), framebuffer trả về toàn bộ pixel 0 (ảnh đen xì 100%, dung lượng file rất nhỏ ~12KB). Nếu Agent gửi thẻ `MEDIA:` kèm lời mô tả hoang tưởng mà không soi pixel thật thì sẽ bị ăn chửi nặng vì vi phạm quy chuẩn kiểm chứng thị giác.
- **Kỷ luật cơ học bắt buộc:**
  1. Luôn chạy lệnh đánh thức và giữ màn hình trước khi thao tác UI / screencap:
     `adb -s <serial> shell "input keyevent 224 && input keyevent 82 && svc power stayon true && settings put system screen_off_timeout 600000"`
  2. Kiểm tra `dumpsys power | grep -i 'Display Power'` phải là `state=ON`.
  3. Kiểm chứng pixel cơ học sau khi chụp: nếu `len(np.unique(r)) == 1 and np.unique(r)[0] == 0` (đen 100%) -> **CẤM TUYỆT ĐỐI GỬI THẺ MEDIA: CHO USER**. Phải bật màn hình và chụp lại ngay lập tức.


> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
