# Triage Sự Cố: Dấu Chấm Than Wi-Fi ("Không Có Internet") & Lỗi Switcher Giả Mạo Khi MikroTik Uptime > 7 Ngày

**Ngày ghi nhận:** 17/10/2026  
**Ngữ cảnh:** Farm Alert báo diện rộng `[ACCOUNT_SWITCHER_FAILED] ACCOUNT_READY verify failed: ACCOUNT_VERIFY_MISMATCH: Profile did not show the expected account` hoặc `profile username still mismatched after switch (expected='...', found='...')`.
Operator thắc mắc: *"Ủa mà khoan máy trong hình bị chấm than là mạng lỗi mà? Vấn đề proxy trên web quản trị kibe:2310 vẫn online hơn 7 ngày rồi mà?"*

---

## 1. Cơ Chế Lỗi Gốc Rễ (Root Cause & Dây Chuyền Sự Cố)

1. **Hiện tượng trên UI thiết bị:**
   - Trên thanh Status Bar: Icon Wi-Fi xuất hiện **dấu chấm than (!)**.
   - Trích xuất UI hierarchy XML:
     ```xml
     <node resource-id="com.android.systemui:id/wifi_combo" 
           content-desc="Tín hiệu Wi-Fi ba vạch.,Không có Internet." bounds="[734,14][781,56]" />
     <node resource-id="com.ss.android.ugc.trill:id/tux_loading_hud" 
           class="android.widget.ProgressBar" bounds="[420,825][660,1065]" />
     ```
   - Trong quá trình đổi tài khoản: Runner mở Account Switcher thành công, tìm thấy dòng tài khoản mục tiêu và phát lệnh tap. Tuy nhiên, TikTok bắt buộc phải gửi API request lên server máy chủ để xác thực và cấp token phiên mới. Do mạng bị mất kết nối ra Internet, app hiện vòng xoay loading `tux_loading_hud` giữa màn hình rồi tự hủy thao tác chuyển tài khoản, giữ nguyên phiên của nick cũ.
   - Khi runner chuyển sang bước `ACCOUNT_READY` verify lại username, màn hình vẫn hiển thị username nick cũ, dẫn đến ném lỗi `ACCOUNT_VERIFY_MISMATCH`.

2. **Bản chất nghịch lý "Web MikroTik kibe:2310 Uptime > 7 ngày":**
   - **Tầng Layer 3 (MikroTik PPPoE Interface `pppoe-out17..35`):** Bảng quản trị web tại `kibe:2310` chỉ đo thời gian duy trì kết nối PPPoE vật lý với ISP Viettel (`1w11h30m`). Đường cáp quang chính hoàn toàn không rớt mạng.
   - **Tầng Layer 7 & Bẫy Gán Proxy Domain `mirotik1.taadaa.click` vs IP LAN:**
     * Trên 10 máy dính lỗi (`M33, M34, M35, M36, M38, M71, M72, M75, M77, M78`), proxy được gán qua `settings get global http_proxy` là dạng tên miền: `mirotik1.taadaa.click:1000x`.
     * **Trên Host PC:** Tên miền được map nội bộ trong `hosts` trỏ về IP LAN `192.168.110.2` $\rightarrow$ probe hay test từ PC luôn thành công `HTTP 200 OK`.
     * **Trên Điện Thoại Android:** Điện thoại hỏi DNS ngoài (`8.8.8.8`) phân giải domain về **IP Public WAN Viettel** (`116.99.168.85`).
     * **Bẫy Firewall MikroTik (`DROP_EXTERNAL_PROXY_PORTS`):** Khi gói tin từ Wi-Fi LAN (`192.168.110.x`) kết nối vòng ra WAN IP port 1000x, Firewall MikroTik chặn đứng toàn bộ (`NC_EXIT: 1`).
     * Thực nghiệm so sánh trực tiếp từ shell Android qua `toybox nc`:
       - `toybox nc -w 3 mirotik1.taadaa.click 10002` $\rightarrow$ `NC_EXIT: 1` (Chết cứng / Timeout vĩnh viễn).
       - `toybox nc -w 3 192.168.110.2 10002` $\rightarrow$ `NC_EXIT: 0` (Thành công `HTTP/1.1 200 OK`, IP `27.79.42.241`).
     * **Kết luận người vận hành:** Khi điện thoại đang bị dấu chấm than do bẫy tên miền này thì **chắc chắn có chờ bao nhiêu giây cũng không thể load được TikTok**. Bắt buộc phải chuyển cài đặt proxy trên máy sang IP LAN nội bộ `192.168.110.2:1000x` (hoặc dải Singbox `192.168.110.2:200xx`).

---

## 2. Quy Trình Chẩn Đoán Phân Định O(1)

1. **Soi mắt hiện trường (Visual & Hierarchy Check):**
   - Mở XML snapshot lúc lỗi (`popup_before.xml` hoặc `ui.xml`): kiểm tra xem có node `wifi_combo` mang `content-desc` chứa `"Không có Internet"` hoặc node `tux_loading_hud` hay không.
   - Tuyệt đối KHÔNG vội kết luận lỗi tọa độ tap anchor hay đổi code Switcher khi UI có chỉ dấu mất mạng.

2. **Probe phân tầng Proxy (Không dựa vào Uptime PPPoE):**
   - CẤM chỉ nhìn vào `kibe:2310` hay web dashboard để kết luận proxy còn sống.
   - Probe HTTP handshake thực tế từ host qua cổng proxy của máy (ví dụ port 20033):
     ```python
     import urllib.request
     opener = urllib.request.build_opener(urllib.request.ProxyHandler({'http': 'http://192.168.110.2:20033'}))
     # Nếu trả về HTTP 200 kèm IP -> Proxy đã hồi phục
     # Nếu trả về 502 / timeout -> Proxy upstream đang nghẽn
     ```

3. **Kiểm tra va chạm tiến trình song song (Concurrent Collision Check):**
   - Trước khi can thiệp thiết bị, kiểm tra xem có session khác hoặc tiến trình khác đang giữ lock:
     - Đọc thư mục device locks: `C:/Users/Kibe/.codex/device-locks/machine_<N>.lock.json`.
     - Chạy `session_search` để phát hiện session song song đang cùng khảo sát.

---

## 3. Kỷ Luật Điều Phối & Phục Hồi

1. **Cấm sửa logic tọa độ Switcher khi nguyên nhân là mạng:**
   - Sửa tọa độ tap hoặc nới lỏng verify profile trong tình huống này sẽ phá vỡ logic chuẩn và gây regression nghiêm trọng cho các ca chạy bình thường.

2. **Vá chốt chặn phòng thủ trong code runner (`feed_swipe_smoke.py`):**
   - **Chặn đứng vòng lặp mù:** Trước khi tap chọn nick trong Switcher, kiểm tra ngay XML hierarchy. Nếu node `wifi_combo` có `"không có internet"` $\rightarrow$ fail-fast ngay với `manual-needed:network-offline`, tuyệt đối không bấm tài khoản để tránh bị kẹt loading ngầm.
   - **Chống lag nhịp:** Khi mạng lag nhẹ có vòng xoay `tux_loading_hud`, runner chờ tối đa 5 giây cho vòng xoay biến mất hoàn toàn rồi mới tiến hành đọc Profile Identity.

3. **Kế hoạch phục hồi 2 bước:**
   - *Bước 1:* Chuyển đổi toàn bộ cài đặt proxy của các máy từ dạng domain `mirotik1.taadaa.click:1000x` sang IP LAN nội bộ `192.168.110.2:1000x` (hoặc dải Singbox `192.168.110.2:200xx`).
   - *Bước 2:* Sau khi cổng proxy thông suốt và dấu chấm than biến mất, kiểm tra device lock được giải phóng rồi mới cho retry ca chạy.
