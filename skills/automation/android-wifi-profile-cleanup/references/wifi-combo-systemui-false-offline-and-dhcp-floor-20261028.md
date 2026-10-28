# SystemUI wifi_combo False Offline & S7 DHCP Lease Timing Settle Floor

## Bối cảnh Hiện Trường (Incident 2026-10-28)
Trong phiên chạy sáng đầu ca (`06:00:49`), Farm Alert báo 4 máy Admin (M216, M229, M268, M277) bị lỗi "Mất kết nối Wi-Fi (AP)". Tuy nhiên đến ca 08:00 cả 4 máy đều tự động chạy thành công 100% mà không hề reboot phần cứng hay động vào dây cáp.

## 2 Nguyên Nhân Gốc Rễ Đã Phân Lập

### 1. Bẫy Bắt Nhầm Thanh Trạng Thái Android (`wifi_combo status`)
- **Triệu chứng**: M216, M277 dừng ca với lỗi:
  `manual-needed:network-offline: Wi-Fi has no internet connection (wifi_combo status)`
- **Cơ chế**:
  - Máy kết nối Wi-Fi farm và cấu hình HTTP Proxy (`settings put global http_proxy 192.168.110.2:100xx`).
  - Gói tin kiểm tra captive portal của Android OS (`generate_204`) không đi qua hoặc bị trễ qua proxy, khiến icon Wi-Fi trên đỉnh màn hình (`com.android.systemui:id/wifi_combo`) mang nhãn `content-desc="Tín hiệu Wi-Fi đủ.,Không có Internet."`.
  - Trong `feed_swipe_smoke.py`, hàm `_switcher_offline_reason(popup_xml)` quét chuỗi `"khong co internet"` trên toàn bộ dump XML (bao gồm cả SystemUI).
  - Thấy chuỗi này, runner lập tức `break` abort toàn bộ tiến trình chuyển tài khoản dù tài khoản đích (`account_element`) đã xuất hiện rõ ràng trên danh sách switcher của TikTok.
- **Biện pháp chuẩn hóa**:
  - Bóc tách / loại bỏ các node thuộc `com.android.systemui` hoặc `wifi_combo` trước khi kiểm tra marker offline.
  - Luôn kiểm tra `if offline_reason is not None and account_element is None:`. Nếu tài khoản mục tiêu đã tìm thấy, BẮT BUỘC tap chuyển tài khoản thay vì huỷ sớm.
  - Cơ giới hóa rào chắn trong `rules.json`: `case_invariant_prohibit_abort_switcher_offline_without_account_check`.

### 2. Lệch Pha DHCP Lease Lúc Thức Dậy Đầu Ca
- **Triệu chứng**: M229, M268 dừng ca với lỗi:
  `required router proxy is unreachable ... dumpsys connectivity: Wi-Fi not connected`
- **Cơ chế**:
  - Lúc 06:00 sáng sau cả đêm ngủ sâu, 80 máy đồng loạt thức dậy và gửi request kết nối lại AP Aruba.
  - Trên Samsung S7 (Android 8), quá trình bắt tay WPA2 và xin cấp phát IP DHCP mất trung bình 5–7 giây.
  - Trong `vpn_preflight.py`, sau khi toggle Wi-Fi (`svc wifi enable`), code chỉ chờ `time.sleep(2.0)` rồi thăm dò `check_android_vpn` ngay. Chưa kịp gán IP inet nên bị fail-closed oan.
- **Biện pháp chuẩn hóa**:
  - Nâng sàn thời gian chờ lắng đọng DHCP (Stage 1 sau Wi-Fi enable) từ `2.0s` lên `6.0s`.
  - Nâng sàn thời gian sau `adbjoinwifi` (Stage 2) từ `2.0s` lên `5.0s`.

## Kỷ Luật Sửa Code & GuardGate
1. **Hard Gate #3 cấm `delegate_task` cho task sửa code**: Mọi thao tác sửa code phải chạy qua `python D:/Taadaa/tools/dispatch_worker.py --workdir ... --file ... "<prompt>"`.
2. **Kỷ luật cấu trúc phân bước (`check_step_by_step_structure`)**: Diffs thêm mới >= 15 dòng bắt buộc phải có comment định danh bước (`# Bước X: ...` hoặc `# Step X: ...`) để GuardGate chấp thuận (ALLOW).
