# TikTok Cold-Start Network Retry (id/dd9) & Postcondition Guard

## 1. Hiện tượng & Triệu chứng
Khi chạy `run-feed-session.ps1` hoặc `multi-machine-feed-session`:
- Session dừng khẩn cấp ở bước `baseline` hoặc `baseline_stuck_recovery` với lý do:
  `[ALERT] [MÁY N] Dừng: manual-needed | Lý do: network/error/retry marker detected; swipe recovery (2 swipes) still stuck`
- Đọc UI XML dump tại `artifacts/.../feed-session-smoke/baseline/attempt_N/ui.xml` ghi nhận:
  - `com.ss.android.ugc.trill:id/ze3`: text *"Không có kết nối Internet. Hãy nhấn để thử lại."*
  - `com.ss.android.ugc.trill:id/message_tv`: text *"Kết nối với internet và thử lại."*
  - `com.ss.android.ugc.trill:id/dd9`: Button text *"Thử lại"*, bounds `[144,1329][936,1485]`.

---

## 2. Cạm bẫy Triage: Ngộ nhận lỗi Proxy / Sập Wi-Fi
Khi gặp màn hình trên, phản xạ đầu tiên của người vận hành là nghi ngờ Proxy chết hoặc máy rớt Wi-Fi.

### Kiểm chứng nhanh O(1) để phân định:
1. **Probe từ Host qua port Proxy của máy (`192.168.110.2:20000+N`):**
   - `curl -x http://192.168.110.2:2000N http://api.ipify.org` ➔ HTTP 200 (trả Egress IP hợp lệ).
   - `curl -x http://192.168.110.2:2000N http://connectivitycheck.gstatic.com/generate_204` ➔ HTTP 204.
   - `curl -x http://192.168.110.2:2000N https://www.tiktok.com` ➔ HTTP 200.
2. **Socket Probe từ chính thiết bị qua ADB:**
   - `adb -s <serial> shell "echo | toybox nc -w 3 192.168.110.2 2000N"` ➔ exit code 0 (cổng mở).
   - `adb -s <serial> shell 'printf "GET http://api.ipify.org/ HTTP/1.1\r\nHost: api.ipify.org\r\nProxy-Connection: close\r\n\r\n" | toybox nc -w 5 -W 5 192.168.110.2 2000N'` ➔ HTTP 200.
3. **Trạng thái Wi-Fi Android:**
   - `dumpsys connectivity` báo `CONNECTED/CONNECTED`, `Score: 60`, `lastValidated: true`.

👉 **Kết luận**: Wi-Fi và Proxy sống 100%. Đây là lỗi **Cold-Start Transient Lag** của TikTok khi khởi động: Các request mạng ban đầu bị trễ 1-2 giây khiến app hiển thị màn hình fallback lỗi mạng tạm thời.

---

## 3. Bản chất 2 lỗ hổng trong Code Handler cũ

### Lỗ hổng 1: Handler nhận vơ thành công & Tap mù (`benign_popup_registry.py`)
- Code cũ trong `_dismiss_network_error_retry`:
  - Tìm node retry hoặc fallback tap mù `(w*0.5, h*0.5)`.
  - Bấm xong thì lập tức trả về `dismissed=True` mà **KHÔNG dump lại XML để kiểm tra**.
- Kết quả: Khi nút "Thử lại" chưa kịp load xong hoặc bấm trượt, handler đã tự báo là giải cứu thành công (`dismissed=True`). Các bước tiếp theo đọc lại màn hình vẫn thấy lỗi mạng, kích hoạt vòng lặp lỗi giả.

### Lỗ hổng 2: Swipe Recovery vuốt mù vô ích (`feed_swipe_smoke.py`)
- Khi baseline bị đánh dấu `manual-needed:network`, script rơi vào cơ chế `_swipe_recovery_on_stuck`.
- Thao tác thực hiện: Bắn 2 lệnh `input swipe 540 1400 540 400 300`.
- **Thực tế giao diện**: Trên màn hình mất mạng của TikTok (`ze3`/`dd9`), thao tác vuốt cuộn không kích hoạt reload hay chuyển video. Sau 2 lần vuốt vô ích, hệ thống dừng phiên và báo lỗi oan.

---

## 4. Chuẩn hóa Code Handler & Patch Contract
1. **Loại bỏ hoàn toàn Tap mù:**
   - Chỉ click khi tìm thấy node allowlist (`res_id` chứa `dd9`, `retry`, `reload` hoặc text/desc "Thử lại", "Retry").
   - Nếu không có node hợp lệ hoặc không trích xuất được bounds: trả ngay `network_retry_target_not_found`, tuyệt đối không tap tọa độ trung tâm.
2. **Bắt buộc Hậu kiểm UI (Postcondition Hierarchy Verification):**
   - Sau khi tap target và chờ delay (1.5s): gọi `_safe_capture_hierarchy(ctx)` dump lại XML.
   - Kiểm tra các markers: `("dd9", "ze3", "message_tv", "không có kết nối internet", "kết nối với internet", "no internet connection", "network error")`.
   - Nếu còn bất kỳ marker nào: trả `dismissed=False`, `popup_closed=False`, reason `network_retry_postcondition_failed_network_markers_still_present`.
   - Chỉ công nhận `dismissed=True` khi XML sau bấm đã sạch hoàn toàn marker lỗi mạng.
3. **Cơ chế Phục hồi Thay thế Vuốt Mù:**
   - Với màn hình `NETWORK_RETRY_SCREENS`, cấm dùng `_swipe_recovery_on_stuck`.
   - Nếu bấm "Thử lại" không hết lỗi mạng sau hậu kiểm: kích hoạt `_network_force_stop_recovery` (force-stop và relaunch app TikTok sạch) để reset kết nối app.
