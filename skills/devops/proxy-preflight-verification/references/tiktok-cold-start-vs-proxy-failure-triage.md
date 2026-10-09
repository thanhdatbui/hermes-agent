# Triage Phân Định: Sập Proxy Thực Sự vs Màn Hình Lỗi Mạng Cold-Start TikTok (id/dd9)

## 1. Hiện tượng gây nhầm lẫn
Khi chạy automation nuôi nick / lướt feed TikTok (feed-session-smoke / multi-machine-feed-session):
- Runner dừng khẩn cấp báo lỗi: `[ALERT] [MÁY N] Dừng: manual-needed | Lý do: network/error/retry marker detected`
- Màn hình thiết bị hiện:
  - Thông báo: *"Không có kết nối Internet. Hãy nhấn để thử lại."* (`resource-id="com.ss.android.ugc.trill:id/ze3"`)
  - Chữ phụ: *"Kết nối với internet và thử lại."* (`resource-id="com.ss.android.ugc.trill:id/message_tv"`)
  - Nút bấm: *"Thử lại"* (`resource-id="com.ss.android.ugc.trill:id/dd9"`).

Khi nhìn thấy màn hình này, người vận hành thường đặt câu hỏi: **"Có phải proxy bị lỗi không?"**

---

## 2. Quy trình Kiểm chứng O(1) Phân tầng Bản chất

| Tầng kiểm tra | Lệnh thực thi | Kết quả Sống 100% | Dấu hiệu Proxy Sập Thật |
| :--- | :--- | :--- | :--- |
| **1. Host Probe Proxy** | `curl -x http://192.168.110.2:2000N http://api.ipify.org` | HTTP 200 (IP Viettel) | 502 Bad Gateway / Connection Refused / Timeout |
| **2. Host Probe Captive** | `curl -x http://192.168.110.2:2000N http://connectivitycheck.gstatic.com/generate_204` | HTTP 204 No Content | Timeout / 502 |
| **3. Host Probe TikTok** | `curl -x http://192.168.110.2:2000N https://www.tiktok.com` | HTTP 200 OK | Socket reset / TLS handshake fail |
| **4. Device TCP Socket** | `adb -s <serial> shell "echo \| toybox nc -w 3 192.168.110.2 2000N"` | Exit code 0 (cổng mở) | Exit code 1 (kẹt/đóng port) |
| **5. Device HTTP Stream** | `adb -s <serial> shell 'printf "GET http://api.ipify.org/ HTTP/1.1\r\nHost: api.ipify.org\r\nProxy-Connection: close\r\n\r\n" \| toybox nc -w 5 -W 5 192.168.110.2 2000N'` | `HTTP/1.1 200 OK` + Egress IP | Trống / Connection closed |
| **6. Android Wi-Fi State** | `adb -s <serial> shell "dumpsys connectivity \| grep -E 'NetworkAgentInfo.*WIFI\|lastValidated'"` | `Score: 60`, `lastValidated: true` | `Score: 20`, `lastValidated: false` (chấm than) |

👉 **Quy tắc vàng**: Nếu cả 6 bước trên đều PASS, **hạ tầng mạng và proxy hoàn toàn bình thường 100%**. Lỗi hiển thị trên app chỉ là hiện tượng **Cold-Start Transient Lag** của TikTok khi app vừa khởi động chưa kịp nạp video đầu tiên.

---

## 3. Cạm bẫy trong Script Automation khi gặp hiện tượng này
1. **Bẫy Tap Mù & Báo Thành Công Ảo:**
   - Trong `_dismiss_network_error_retry`, nếu không bắt trúng `dd9` mà tap mù tọa độ giữa màn hình `(w*0.5, h*0.5)`, tap sẽ không trúng nút "Thử lại".
   - Nếu sau khi tap không dump UI XML hậu kiểm mà đã vội trả về `dismissed=True`, các bước sau đọc lại màn hình thấy lỗi mạng sẽ kích hoạt cascade fail.
2. **Bẫy Swipe Recovery trên Network Screen:**
   - Script feed session thấy kẹt baseline liền chạy `_swipe_recovery_on_stuck` (vuốt feed từ y=1400 lên y=400).
   - Trên giao diện lỗi mạng, vuốt cuộn không kích hoạt reload. Vuốt 2 lần vô ích sẽ làm session ngắt với cảnh báo sai lệch.
3. **Giải pháp chuẩn:**
   - Bắt buộc tap đúng node allowlist `id/dd9`.
   - Hậu kiểm XML: nếu còn marker `dd9`/`ze3` ➔ báo postcondition failed, không nhận vơ thành công.
   - Nếu retry không hết lỗi ➔ dùng force-stop + relaunch (`_network_force_stop_recovery`), cấm vuốt feed mù.
