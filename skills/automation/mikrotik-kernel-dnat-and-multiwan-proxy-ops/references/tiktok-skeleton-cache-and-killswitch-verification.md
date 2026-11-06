# TikTok Skeleton Loading vs Disk/RAM Cache & Killswitch Verification Discipline

## 1. Hiện Tượng & Điểm Mù Khi Nghiệm Thu Fail-Closed Trên S7
- **Hiện tượng gây hoang mang cho Operator:** Khi ngắt upstream proxy hoặc kích hoạt Killswitch, Operator mở app TikTok thấy:
  1. Video vẫn chạy trôi 1-2 video đầu tiên -> Nghi ngờ bị lọt IP Direct cáp quang gốc (Fail-Open).
  2. Máy 02 / Máy 204 dù Wi-Fi có hoặc không có dấu chấm than, vào tìm kiếm hoặc Cửa hàng (Shop) thấy hiện các khung xám.
- **Bản chất kỹ thuật (Ground Truth):**
  - **ExoPlayer / TTNet Buffer:** App TikTok luôn nạp sẵn (prefetch) 1-3 video vào RAM/ROM từ phiên lướt trước. Khi mở app, nó phát trực tiếp từ cache offline, hoàn toàn KHÔNG phát sinh network request mới.
  - **Cold-Boot vs Warm-Boot Verification:** Nếu kiểm tra trong lúc app đang chạy ngầm (warm state), app sẽ dùng dữ liệu cache cũ. BẮT BUỘC phải dập tắt triệt để (`am force-stop com.ss.android.ugc.trill com.zhiliaoapp.musically`) rồi mới mở lại (`am start`) để quan sát cold-start UI.
  - **Dấu hiệu nhận diện mất mạng thật (Skeleton Loading Cards):** Khi vào tab Shop/Cửa hàng hoặc Search:
    * Toàn bộ lưới sản phẩm biến thành các khung chữ nhật màu xám rỗng (`Skeleton Loading Placeholder`), không bung ảnh, không bung giá tiền, không có review.
    * Màn hình Home hiện thông báo chào mừng rỗng: `"Chào mừng bạn trở lại! Tìm kiếm video, chủ đề hoặc nhà sáng tạo bất cứ lúc nào"` kèm icon loading quay tròn `com.ss.android.ugc.trill:id/tux_status_view_default_loading`.
    * Socket kết nối gửi tới proxy nội bộ `192.168.110.2:200xx` kẹt cứng ở trạng thái `SYN_SENT` (0 packet ra ngoài).

## 2. Kỷ Luật Tường Lửa 3 Tầng Bảo Vệ Cứng
1. **Tầng Filter Forward:**
   - Rule `*D` (`chain=forward action=drop src-address=192.168.0.0/16 out-interface-list=WAN comment=KILLSWITCH_BLOCK_FARM_DIRECT_WAN`) BẮT BUỘC nằm ở vị trí số [0] đỉnh bảng Filter.
   - BẮT BUỘC drop UDP 443 (`*9`) để chặn ByteDance TTNet lách QUIC HTTP/3.
   - BẮT BUỘC drop UDP 53 (`*8`) ra WAN để chặn DNS Leak.
2. **Tầng Mangle Prerouting Bypass (Quan trọng):**
   - Khi có nhiều line WAN (35 line PPPoE) và chạy Policy-Based Routing (PBR / Mangle):
   - Mangle PREROUTING duyệt TRƯỚC Filter FORWARD. Các gói tin từ điện thoại Farm gửi tới các port proxy DNAT (`20001..20080` của Kibe và `20201..20280` của Admin) BẮT BUỘC phải có rule `action=accept` nằm ngay ở đỉnh bảng Mangle (`*174` và `*175`).
   - Nếu thiếu rule bypass ở đầu bảng, gói tin sẽ bị Mangle phía dưới gán cờ `mark-routing=WANx`, làm sai lệch đích đến và gây lỗi Asymmetric Routing.
3. **Đồng bộ IP WAN Đích Trong NAT Rules:**
   - Khi IP WAN của MobiProxy (`test.taadaa.click`) hoặc R3G (`tb.taadaa.click`) thay đổi (do Viettel quay số PPPoE đổi IP):
   - BẮT BUỘC cập nhật ngay `to-addresses` trong các rule `/ip firewall nat` tương ứng trên MikroTik, nếu không kết nối DNAT sẽ gửi vào IP chết và gây timeout toàn bộ dải máy.
