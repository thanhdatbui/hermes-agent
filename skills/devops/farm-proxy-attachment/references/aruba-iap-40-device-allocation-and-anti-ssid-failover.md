# Aruba IAP 40-Device Hard Allocation & Anti-SSID Failover Discipline (2026-10-09)

## 🛑 BẢO VỆ QUY HOẠCH PHÂN BỔ 40 MÁY / AP (USER MANDATE 2026-10-09)
Khi gặp sự cố máy farm kết nối Wi-Fi bị từ chối (`ASSOCIATION_REJECTION`), Coordinator:
- **CẤM TUYỆT ĐỐI GỢI Ý HOẶC TỰ ĐỘNG CHUYỂN MÁY SANG AP KHÁC:**
  + Quy hoạch phần cứng: Cụm Aruba được tính toán chịu tải tối ưu **40 máy / AP** (M1–M40 ➔ `kibe 1` trên AP `.253`, M41–M80 ➔ `kibe 2` trên AP `.252`).
  + Việc tự ý ép máy cụm 1 nhảy sang `kibe 2` (hoặc ngược lại) để "chữa cháy tạm" là hành vi **tự phá vỡ quy hoạch dung lượng**, gây quá tải domino cho AP còn lại và làm hỏng tính cô lập của từng cụm máy.
- **CẤM TUYỆT ĐỐI FALLBACK SANG SSID VÃNG LAI / NGOÀI LUỒNG (NHƯ SSID 'DAT'):**
  + **Bản chất nguy hiểm:** SSID `Dat` phát dải mạng `192.168.10.x` (thay vì dải Farm chuẩn `192.168.110.x`). Khi điện thoại bắt sang SSID này, định tuyến gateway bị lệch, các kết nối vào proxy nội bộ Singbox trên MikroTik (`192.168.110.2:20000+N`) bị timeout hoặc connection refused.
  + **Nguy cơ Direct IP Leak:** Nếu máy bị rớt cấu hình proxy hoặc gặp kẽ hở trong preflight, máy sẽ đi thẳng ra IP FPT nhà của user.
  + **Quy tắc Fail-Closed:** Máy không kết nối được SSID chính của nó thì **bắt buộc dừng lại và báo cáo hiện trường** (qua watchdog), tuyệt đối không tự chế tầng fallback sang SSID ngoài.

---

## KIẾN TRÚC ARUBA INSTANT AP (IAP) CLUSTER
Cụm 4 AP Aruba (`192.168.110.250` .. `.253`) hoạt động theo mô hình Virtual Controller (IAP Cluster):
- **Master AP (Virtual Controller):** Hiện tại là `192.168.110.251`.
  + **Quyền hạn cấu hình:** CHỈ Master AP mới nhận lệnh cấu hình `conf t` (sửa profile ARM, SSID, VLAN, v.v.).
  + **Lỗi trên Slave AP:** Khi SSH vào các slave AP (`.250`, `.252`, `.253`) và gõ `conf t`, AP sẽ chặn và báo:
    `WARNING: CLI is not supported on slave.`
  + Khi cần đổi cấu hình toàn cụm (ví dụ: tắt `client-match` gây đá máy: `conf t` ➔ `arm` ➔ `no client-match` ➔ `end` ➔ `commit apply`), **bắt buộc SSH vào Master AP `.251`**.
- **Slave APs (.250, .252, .253):**
  + Không nhận `conf t`, nhưng hỗ trợ đầy đủ các lệnh vận hành (operational commands) cục bộ:
    * `reload` (xác nhận `y`): Khởi động lại riêng lẻ AP đó để xóa sạch bảng BSSID và session kẹt phần cứng.
    * `show clients`: Xem danh sách client đang kết nối trên radio của AP đó.
    * `show ap debug mgmt-frames`: Xem trace gói tin quản lý 802.11 thời gian thực (auth, assoc-req, assoc-resp, deauth).
    * `show ap debug auth-trace-buf`: Xem vết bắt tay WPA2 4-way handshake.
- **Lệnh Deauth / Kick Client chuẩn trên Aruba IAP:**
  + Cú pháp: `disconnect-user mac <MAC_ADDRESS>` (ví dụ: `disconnect-user mac ac:5f:3e:60:59:1b`).
  + Không được gõ thiếu từ khóa `mac` (nếu gõ `disconnect-user <MAC>` sẽ bị `% Parse error`).

---

## BẪY ANDROID 8 'NETWORK_SELECTION_DISABLED_ASSOCIATION_REJECTION'
1. **Cơ chế bẫy:**
   Khi AP Aruba gửi gói 802.11 `status 1: UNSPECIFIED_FAILURE` liên tiếp nhiều lần, Android Wi-Fi Framework sẽ tự động khóa mạng đó:
   ```text
   Disabled saved networks: "kibe 1": reason=NETWORK_SELECTION_DISABLED_ASSOCIATION_REJECTION
   Networks filtered out due to blacklist: kibe 1:<BSSID>
   ```
2. **Cách mở khóa triệt để:**
   - Lệnh `svc wifi disable` ➔ `svc wifi enable` **KHÔNG XÓA ĐƯỢC CỜ NÀY**.
   - Cần vào Android UI: `Cài đặt` ➔ `Kết nối` ➔ `Wi-Fi` ➔ `Nâng cao` ➔ `Quản lý mạng` (Manage networks) ➔ Chọn SSID ➔ Bấm **QUÊN (Forget)** để xóa hoàn toàn file profile trong `WifiConfigStore.xml`.
   - Sau đó kết nối lại một phiên fresh hoàn toàn với đúng mật khẩu.

---

## BẢNG QUY HOẠCH SSID & MẬT KHẨU FARM CHUẨN
- **Máy 01 – 40:** SSID `"kibe 1"` — **Mật khẩu: `23102025`** (AP `.253`).
- **Máy 41 – 80:** SSID `"kibe 2"` — **Mật khẩu: `19051995`** (AP `.252`).
- **Máy 201 – 240:** SSID `"admin 1"` — **Mật khẩu: `19051995`** (AP `.251`).
- **Máy 241 – 280:** SSID `"admin 2"` — **Mật khẩu: `19051995`** (AP `.250`).
*(CẤM TUYỆT ĐỐI nhập nhầm pass `kibe 1` thành `19051995` vì sẽ gây lỗi bắt tay 4-way handshake AUTHENTICATION_FAILURE).*
