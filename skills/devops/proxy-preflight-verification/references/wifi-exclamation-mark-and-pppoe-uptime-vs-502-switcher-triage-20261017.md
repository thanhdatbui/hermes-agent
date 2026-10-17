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
   - Trong quá trình đổi tài khoản: Runner mở Account Switcher thành công, tìm thấy dòng tài khoản mục tiêu và phát lệnh tap. Tuy nhiên, TikTok bắt buộc phải gửi API request lên server máy chủ để xác thực và cấp token phiên mới. Do mạng bị 502/mất kết nối ra Internet, app hiện vòng xoay loading `tux_loading_hud` giữa màn hình rồi tự hủy thao tác chuyển tài khoản, giữ nguyên phiên của nick cũ.
   - Khi runner chuyển sang bước `ACCOUNT_READY` verify lại username, màn hình vẫn hiển thị username nick cũ, dẫn đến ném lỗi `ACCOUNT_VERIFY_MISMATCH`.

2. **Bản chất nghịch lý "Web MikroTik kibe:2310 Uptime > 7 ngày":**
   - **Tầng Layer 3 (MikroTik PPPoE Interface `pppoe-out17..35`):** Bảng quản trị web tại `kibe:2310` chỉ đo thời gian duy trì kết nối PPPoE vật lý với ISP Viettel (`1w11h30m`). Đường cáp quang chính hoàn toàn không rớt mạng.
   - **Tầng Layer 7 (Sing-box 200xx -> MobiProxy 4G 51xx):** Cụm 80 máy Kibe được gán proxy trỏ vào container Sing-box nội bộ (`192.168.110.2:20001..20080`), forward ra modem 4G MobiProxy (`test.taadaa.click:51xx`). Khi batch chạy đồng loạt hàng chục máy lướt feed/upload, tải TCP bùng nổ tức thời làm service proxy trên modem 4G bị crash hoặc trả về `502 Bad Gateway` / `Connection Reset` trong 20–60 giây.
   - Android gửi gói kiểm tra mạng ngầm (`captive portal generate_204`) gặp 502 nên cắm ngay dấu chấm than vào icon Wi-Fi (`Không có Internet`).

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

1. **Cấm sửa mã nguồn Switcher khi nguyên nhân là mạng:**
   - Sửa tọa độ tap hoặc nới lỏng verify profile trong tình huống này sẽ phá vỡ logic chuẩn và gây regression nghiêm trọng cho các ca chạy bình thường.
2. **Kế hoạch phục hồi 2 bước:**
   - *Bước 1:* Chờ đợt nghẽn socket tức thời đi qua hoặc gọi auto-healer `mobiproxy_auto_healer.py` recreate modem.
   - *Bước 2:* Sau khi cổng proxy thông lại, kiểm tra device lock được giải phóng rồi mới cho retry ca chạy.
