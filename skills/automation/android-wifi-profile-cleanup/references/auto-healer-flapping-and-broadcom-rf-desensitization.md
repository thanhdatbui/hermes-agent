# Bẫy Auto-Healer Flapping, Phân Quyền Knox và Suy Hao RF S7 Trên Kệ Sắt

## 1. Hiện Tượng Cronjob Tự Động Biến Thành "Kẻ Phá Hoại" (The Flapping Loop)
Khi thiết bị Android bị rớt mạng Wi-Fi hoặc mất IP, nếu một cronjob tự động (như `farm_wifi_auto_healer.py` chu kỳ 5 phút) liên tục dập nhả nguồn radio:
```bash
svc wifi disable
sleep 1
svc wifi enable
```
Nếu thiết bị chưa kịp nhận DHCP IP hoặc đang trong quá trình thương thảo WPA2:
1. **Chip Broadcom DHD PCIe rơi vào trạng thái ngủ sâu:** Bị dập tắt/bật liên tục khiến chip driver PCIe chuyển sang `state DORMANT / NO-CARRIER` hoặc `Supplicant state: UNINITIALIZED`.
2. **Aruba AP đưa vào blacklist:** AP Aruba ghi nhận trạm phát sóng dập nhả liên tục (flapping station) và kích hoạt cơ chế phòng vệ từ chối kết nối:
   ```text
   mNetworkSelectionDisableReason NETWORK_SELECTION_DISABLED_ASSOCIATION_REJECTION
   NETWORK_SELECTION_DISABLED_ASSOCIATION_REJECTION counter:8
   ```
3. **Quy tắc bắt buộc:** Mọi script cứu hộ tự động BẮT BUỘC phải cài đặt Circuit Breaker: tối đa 2 lần thử radio toggle trong 30 phút. Nếu không thành công, phải tạm dừng (pause/backoff) ít nhất 60 phút để phần cứng ổn định.

---

## 2. Bẫy Phân Quyền Knox Với Net ID Rác Trên Samsung S7
* **Lỗi phát sinh:** Khi nạp cấu hình qua intent `adbjoinwifi`:
  ```bash
  am start -S -n com.steinwurf.adbjoinwifi/.MainActivity --es ssid "kibe 1" --es password_type WPA --es password "23102025"
  ```
  App `adbjoinwifi` chạy dưới UID 10179. Nếu trong máy đã có sẵn cấu hình cũ do hệ thống UID 1000 tạo (ví dụ Net ID 0 `kibe` NONE), Android Knox sẽ chặn:
  ```text
  E WifiConfigManager: UID 10179 does not have permission to update configuration "kibe"NONE
  ```
* **Cách xử lý dứt điểm:** Bắt buộc dùng ADB shell (UID 2000) gọi Binder service xóa Net ID rác trước khi gọi `adbjoinwifi`:
  ```bash
  service call wifi 14 i32 <net_id>
  ```

---

## 3. Tại Sao CẤM Tăng Công Suất Aruba AP Trên Kệ Kim Loại?
Khi một máy trong farm (như M7) có tín hiệu yếu (-72 dBm), câu hỏi thường gặp là: "Có nên tăng công suất phát của AP không?"
* **Câu trả lời: TUYỆT ĐỐI KHÔNG.**
* **Lý do kỹ thuật (Near-field Saturation & Faraday Reflection):**
  1. Khoảng cách giữa AP-325 gắn trên kệ sắt tới 40 điện thoại chỉ từ **30cm – 80cm**.
  2. Hai máy nằm cạnh M7 là M6 (RSSI: -65 dBm, 351 Mbps) và M8 (RSSI: -63 dBm, 650 Mbps) đều đang bắt sóng hoàn hảo ở công suất tiêu chuẩn (6–9 dBm).
  3. Nếu tăng công suất lên 12–15 dBm: Kệ sắt tạo ra phản xạ sóng dữ dội, làm **bão hòa bộ thu (Receiver Desensitization)** trên 39 máy còn lại. AP Aruba sẽ kích hoạt kickout hàng loạt: `Wlan driver excessive tx fail quick kickout`, làm sập toàn bộ 40 máy Rack 1.

---

## 4. Tại Sao Farm 100% Dùng 5GHz, CẤM Bật 2.4GHz?
* Băng tần 2.4GHz chỉ có **3 kênh độc lập không chồng lấn** (1, 6, 11).
* Với mật độ 80–160 máy truyền nhận video song song, 2.4GHz sẽ lập tức sụp đổ do **can nhiễu đồng kênh (Co-Channel Interference / CCI)**.
* 100% AP farm tắt hoàn toàn radio 2.4GHz, chỉ chạy 5GHz (Kênh 36, 44, 149, 157) với độ rộng kênh hẹp **20 MHz**.

---

## 5. Hiện Tượng Tụt Sàn 6 Mbps Trên Samsung S7 Và Cách Khắc Phục
* **Triệu chứng:** WPA2 Supplicant đã `COMPLETED`, nhưng máy liên tục mất IP hoặc báo:
  ```text
  D WifiStateMachine: CMD_IP_REACHABILITY_LOST but disconnect disabled -- ignore
  ```
* **Bản chất:** RSSI -72 dBm trên băng tần 5GHz khiến chip Broadcom tụt link speed xuống **6 Mbps** (mức sàn 802.11a). Tỷ lệ rớt gói tin ARP/DHCP quá cao làm kernel thu hồi IP.
* **Khắc phục:** Thường do mặt lưng S7 tì sát vào thanh giằng kim loại của khay. Chỉ cần nhấc máy dịch chuyển 2–3 cm ra khỏi góc khuất khung sắt, link speed sẽ vọt lại 300–500 Mbps và giữ IP ổn định 100%.

---

## 6. Kỷ Luật Can Thiệp Máy Đơn Lẻ Mất Mạng Khi Farm Đang Chạy Ca
* **Không làm tê liệt việc sửa máy lẻ:** Khi một máy đơn lẻ bị rớt mạng Wi-Fi (`IP: none`, `wlan0 state DORMANT`), máy đó không thể chạy automation và không ảnh hưởng đến các máy khác đang hoạt động. CẤM Coordinator vin cớ "ca nuôi đang chạy sợ ảnh hưởng máy khác" để trì hoãn xử lý. Thao tác ADB qua `operator_device_lock(machine=N, force_preempt=True, bypass_proxy_readiness=True)` được thực thi độc lập trên máy đó.
* **Xử lý triệt để Stale ARP trên Router Gateway (MikroTik):**
  Khi máy Android đổi dải IP hoặc bị rớt DHCP nhiều lần, MikroTik có thể lưu entry ARP ở trạng thái `failed` hoặc giữ IP cũ dạng `stale`. Cần truy cập MikroTik REST API (`DELETE /rest/ip/arp/<id>`) để xóa bỏ entry stale, giúp việc bắt tay DHCP/ARP giữa Gateway và S7 diễn ra thông suốt ngay khi tín hiệu RF hồi phục.
