# Ruijie Static IP DHCP Starvation Incident & Enforcement (2026-10-18)

## 1. Sự cố hiện trường (Incident Context)
- **Thiết bị:** Máy 7 (Serial `9885f63030454d3055`, MAC `ac:5f:3e:60:59:1b`, Cluster Kibe Local).
- **Hiện tượng:** Sau khi kết nối thành công Wi-Fi `kibe 1` (L2 WPA2 state UP, không có MIC/auth fail), thiết bị bị kẹt hoàn toàn ở tầng L3 (`L3_NO_IP`). Interface `wlan0` chỉ có IPv6 link-local (`fe80::...`), không nhận được IPv4 từ router Ruijie (`192.168.110.1`). Bảng ARP của mạng báo `192.168.110.124 -> 00:00:00:00:00:00` (Incomplete).
- **Nguyên nhân gốc rễ:** Trên router Ruijie Gateway (`EW3200GX-PRO`), Máy 7 đã bị gán IP tĩnh thủ công `192.168.110.124` trong mục **Static IP Addresses**. Trong bảng **DHCP Clients**, Ruijie chuyển trạng thái lease của thiết bị sang **`Converted to Static IP`** và ngậm chặt bản ghi. Khi thiết bị Android 8 reset stack mạng hoặc xin lease mới, DHCP server của Ruijie không cấp phát động IP mới từ pool, dẫn đến tình trạng treo DHCP vô thời hạn.

## 2. Kỷ luật nghiêm cấm (Operator Mandate)
- **User chỉ thị dứt khoát:** *"Cập nhất vào guard gate gì đó lỗi này luôn sau đừng có tự tiện vào gán bậy"*.
- **Quy tắc tuyệt đối:**
  * Toàn bộ 80 máy farm client (`1 <= machine_id <= 80`) BẮT BUỘC hoạt động 100% trên cơ chế **DHCP động** (Dynamic DHCP Pool).
  * Mục Static IP trên Ruijie CHỈ dành riêng cho thiết bị hạ tầng: 4 AP Aruba (`192.168.110.250-253`) và Admin PC (`192.168.110.119`).
  * CẤM TUYỆT ĐỐI agent hoặc operator tự tiện gán Static IP trên Ruijie hoặc viết code fallback gán tĩnh IP cho bất kỳ máy farm nào (M1-M80).

## 3. Cơ chế chốt chặn bằng Code (Gate Enforcement)
Module `D:/Taadaa/tools/farm_network_gate.py` đã được chốt chặn cơ học:
```python
FARM_DHCP_MACHINE_MAX = 80
STATIC_IP_POLICY_ERROR = "STATIC_IP_RESERVATION_FORBIDDEN"

def validate_dynamic_dhcp_policy(machine_id: int, static_ip: str | None = None) -> None:
    """Farm phones M1-M80 must remain on dynamic DHCP; reject static reservations."""
    if static_ip is not None and isinstance(machine_id, int) and not isinstance(machine_id, bool):
        if 1 <= machine_id <= FARM_DHCP_MACHINE_MAX:
            raise ValueError(STATIC_IP_POLICY_ERROR)
```
- **Hành vi:** Bất kỳ yêu cầu nào cố tình truyền `static_ip` hoặc fallback IP tĩnh cho các máy `1 <= machine_id <= 80` đều lập tức bị quăng lỗi `STATIC_IP_RESERVATION_FORBIDDEN` (fail-closed).
- **Ngoại lệ an toàn:** Các máy ngoài dải farm (như Admin 201) hoặc máy chạy direct proxy (M67, M69) khi không có `static_ip` vẫn hoạt động bình thường.
- **Kiểm thử hồi quy:** Được bảo vệ bởi unit test `test_static_ip_reservation_policy()` trong `D:/Taadaa/tools/tests/test_farm_network_gate.py` (41/41 tests pass).

## 4. Quy trình xử lý dọn dẹp khi bị kẹt lease Static IP
Nếu một máy farm bị lỡ gán tĩnh trên Ruijie:
1. Đăng nhập Ruijie Gateway (`http://192.168.110.1/cgi-bin/luci/`).
2. Vào **More -> Basics -> LAN -> Static IP Addresses**.
3. Tìm bản ghi chứa IP/MAC của máy farm và bấm **Delete**.
4. Kiểm tra tab **DHCP Clients**, xác nhận bản ghi không còn cờ `Converted to Static IP`.
5. Thực hiện reboot nóng thiết bị qua `python D:/Taadaa/tools/recover_stuck_s7.py --machine <N> --reboot` để Android khởi động lại network daemon và broadcast gói `DHCP Discover` sạch lên Ruijie.
