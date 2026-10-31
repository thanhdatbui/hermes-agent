# Triage Sự Cố: Cụm Proxy tb.taadaa.click Mất Kết Nối & Giải Mã Hiện Tượng Song Thị Lỗi Preflight (31/10/2026)

## 1. Hiện Tượng & Phản Xạ "Lảm Nhảm" Cần Tuyệt Đối Tránh
- **Bối cảnh:** Batch Nuôi Feed cụm Farm Admin (M201–M280, 79 máy) bị gãy diện rộng (34/79 máy fail, tỷ lệ 43%).
- **Lỗi phổ biến của Coordinator (Anti-Pattern):**
  * Chỉ chạy lệnh kiểm tra canary đại diện (`inspect_machine.py M203`, `M208`), thấy máy hiện tại đã lên Wi-Fi (`192.168.110.x`) và pin >90%, kèm theo việc chạy `mobiproxy_auto_healer.py` thấy báo "All 32 ports HEALTHY" -> Vội vàng kết luận "lỗi transient do race condition lúc bật máy đồng loạt, đủ điều kiện mở lại fleet".
  * Bị User mắng thẳng: *"Tao cần dò chính xác lỗi đéo phải lảm nhảm"*.
- **Kỷ luật điều phối:**
  * CẤM TUYỆT ĐỐI dựa vào trạng thái hiện tại (sau ca chạy) của máy để phủi tay kết luận lỗi thoáng qua.
  * Khi batch lỗi diện rộng (>20-40%), BẮT BUỘC phải mở file log chi tiết của đợt chạy (`runtime/admin/live/<date>/row-X-<timestamp>/log.jsonl`) để đối soát phân bố lỗi và tra cứu tận gốc nguyên nhân hạ tầng.

---

## 2. Bản Chất Gốc Rễ: Phân Bổ Proxy Hai Cụm Trên Farm Admin & Đứt Node tb.taadaa.click
- **Cấu trúc phân bổ Proxy cụm Admin trong `D:/OneDrive/TaadaaData/admin/PROXYgandienthoai.xlsx`:**
  * **Cụm 1 (48 máy):** M192.168.110.2:10008..10035 (Container Sing-box nội bộ). Nhóm này chạy **100% SUCCESS**.
  * **Cụm 2 (32 máy):** `tb.taadaa.click:5141..5158` (Modem 4G quản lý qua Tailscale IP `100.115.94.49`).
    Gồm danh sách: `M203, M204, M208, M211, M213, M217, M220, M223, M227, M230, M233, M235, M238, M241, M243, M246, M251, M253, M255, M260, M261, M262, M263, M264, M265, M266, M267, M268, M269, M270, M271, M272`.
- **Nguyên nhân cốt lõi (Truy vết Session đêm 30/10):**
  * Lúc 23:24 ngày 30/10, file `PROXYgandienthoai.xlsx` của Admin đã bị sửa vội vã 32 máy từ `192.168.110.2:202xx` sang `tb.taadaa.click:5141..5158`.
  * **Sai lầm kiến trúc 1 (Route Blackhole):** `tb.taadaa.click` trỏ về IP Tailscale `100.115.94.49`. Điện thoại S7 chỉ nằm trong LAN nội bộ `192.168.110.x`, không có Tailscale nên hoàn toàn không thể route tới `100.x` trực tiếp, văng ngay lỗi `network is unreachable` hoặc bị Android ngắt kết nối Wi-Fi.
  * **Sai lầm kiến trúc 2 (Đi trước hạ tầng):** Kỹ sư mới chỉ bàn lý thuyết mở Direct WAN cho R3G, trên thực tế router R3G cổng WAN vẫn DROP 100%, chưa cấu hình mở firewall hay DDNS.
  * **Sự cố daemon Tailscale:** Trên R3G bị cấu hình đồng thời cả `/etc/init.d/tailscale` (procd) và `/etc/rc.local` cùng chạy `tailscaled --port=41641`. Xung đột binding và state khiến lúc 00:43 rạng sáng 31/10 (17:43 UTC), `r3g-thaibinh` bị văng khỏi Tailnet (`Online: False`), làm toàn bộ 32 port gãy hoàn toàn.
- **Bẫy mù của `mobiproxy_auto_healer.py`:**
  * Script `mobiproxy_auto_healer.py` hiện tại chỉ giám sát dải port `5101..5138` trên host **`test.taadaa.click`** (phục vụ cụm Farm Kibe M1–M80).
  * Do đó, khi cụm `tb.taadaa.click` của Admin bị chết hoàn toàn, script auto-healer vẫn ngây thơ báo "All 32 ports HEALTHY".

---

## 3. Cơ Chế Song Thị Lỗi: Vì Sao Cùng 1 Sự Cố Lại Báo 2 Signature Khác Nhau?
Trong báo cáo batch alert, 31 máy lỗi bị phân thành 2 cụm:
1. **Signature A — `dumpsys connectivity: Wi-Fi not connected` (25 máy):**
   * Các máy này đã nạp proxy `tb.taadaa.click`. Khi Android 8 (Samsung S7) cố gắng thực hiện cơ chế NetworkMonitor kiểm tra mạng ngầm (HTTP Captive Portal Generate 204 qua proxy) nhưng proxy chết, Android đánh dấu kết nối Wi-Fi là `Không có Internet` (chấm than).
   * Trong nhiều trường hợp, ConnectivityService của Android chuyển trạng thái mạng sang DISCONNECTED hoặc ngắt hẳn kết nối Wi-Fi. Khi runner chạy preflight, regex `_WIFI_CONNECTED_RE` trên `dumpsys connectivity` không tìm thấy cờ `CONNECTED/CONNECTED` -> Fail-closed ngay tại Step 3.
2. **Signature B — `dial tcp 192.168.110.2:202xx: connect: network is unreachable` (6 máy M213, M230, M238, M261, M262, M269):**
   * Trên thiết bị, `settings get global http_proxy` vẫn còn lưu dải port nội bộ cũ `192.168.110.2:202xx`.
   * Khi preflight lọt qua Step 3 và chạy Step 4 (`_probe_atx_curl_public_ip`), tiến trình `atx-agent curl` cố mở TCP socket tới `192.168.110.2:202xx`. Lúc này card `wlan0` đã bị kernel rớt route do mất kết nối hoặc port không phản hồi -> kernel trả về POSIX error `ENETUNREACH` (`network is unreachable`).
   * Batch aggregator tự động normalize IP/Port `192.168.110.2:202xx` thành token `<serial>` trong template alert.

---

## 4. Quy Chuẩn Triage Cho Các Ca Farm Alert Tiếp Theo
1. **Tra chéo Mapping Proxy O(1):**
   Khi có alert hàng loạt máy lỗi mạng (`blocked-proxy-vpn`), việc đầu tiên là trích xuất danh sách máy lỗi và map với cột `proXy` trong `PROXYgandienthoai.xlsx` của cụm tương ứng (`kibe` hoặc `admin`). Nếu tỷ lệ lỗi tập trung 100% vào một endpoint proxy cụ thể (như `tb.taadaa.click`), nguyên nhân chắc chắn là hạ tầng proxy đó, không phải lỗi máy lẻ hay race condition.
2. **Kiểm tra liveness endpoint độc lập:**
   Probe trực tiếp TCP socket từ host tới domain/IP của proxy đó bằng Python timeout 2-3s trước khi đưa ra bất kỳ kết luận nào cho User.
3. **Phương án cứu nguy tức thời khi cụm proxy phụ (TB) chết:**
   Chuyển tạm mapping của các máy sang cụm proxy nội bộ `192.168.110.2:10008..10035` hoặc dải proxy chính `test.taadaa.click` để không làm gián đoạn các ca chạy tiếp theo của farm.
