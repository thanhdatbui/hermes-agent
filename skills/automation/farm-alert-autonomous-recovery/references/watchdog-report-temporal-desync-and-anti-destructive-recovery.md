# Watchdog Report Temporal Desync & Anti-Destructive Network Recovery

## Bối cảnh & Hiện tượng
- Telegram nhận được thông báo từ `tiktok-feed-session-watchdog`:
  `📊 [TIKTOK NUÔI ACC] Ca 1 - Phiên 1/2 (Sáng) hoàn tất (Row X) ... Fail: M7 - Mất kết nối Wi-Fi (AP)`
- Operator thắc mắc: *"Ủa tao fix wifi m7 r mà?"* hoặc *"Là sao tóm lại mạng máy 7 ổn chưa sao report cron nuôi acc báo lỗi"*.
- **Sai lầm thường gặp của Coordinator:**
  1. Không kiểm tra mốc thời gian của báo cáo, ngộ nhận lỗi đang diễn ra theo thời gian thực.
  2. Tự ý kích hoạt quy trình cứu hộ phá hủy (`farm_network_gate.py --force-preempt`), chạy `_forget_all_networks()` xóa sạch toàn bộ profile Wi-Fi đã lưu trên máy (bao gồm cả mạng `Dat` mà operator vừa cấu hình cứu hộ thành công trước đó).
  3. Cố ép máy vào SSID theo bảng config cứng (`farm_wifi_profiles.json`) dẫn tới bị AP từ chối (`ASSOC_REJECT status 1`), làm máy mất mạng hoàn toàn.
  4. Đưa ra giải thích lan man và sai bảo operator đi rút cắm nguồn POE hay vào Web UI router (vi phạm nguyên tắc bất biến `cấm sai bảo user`).

---

## 3 Bước Điều Phối Chuẩn Khi Nhận Phản Hồi Về Báo Cáo Watchdog

### Bước 1: Đối soát thời gian thực thi (Temporal Desync Check)
- Xem tiêu đề ca và mã run: `Ca 2 - Phiên 2/2 (Chiều)` kèm `(Run: row-0-140039)` chạy lúc **14:03 PM**.
- **Hiện tượng Báo muộn sau khi vá Watchdog (Late Backlog Trigger):**
  + Khi watchdog vừa được sửa logic quét (ví dụ: vá lỗi quét đa cụm, thêm live dir), watchdog sẽ quét thấy các phiên cũ chưa từng được report trong `feed_session_reported.json` và bắn cảnh báo muộn.
  + **Quy tắc đối soát mốc thời gian Git vs Run:** So sánh timestamp của Git commit bản fix (`git log -n 1 --format="%ci"`) với thư mục phiên chạy (`row-0-HHMMSS`). Nếu commit fix diễn ra SAU khi phiên chạy kết thúc, đây là cảnh báo "hàng tồn" của phiên quá khứ, KHÔNG PHẢI lỗi mới lặp lại sau khi fix!
- Kiểm tra file `runtime/<cluster>/live/YYYY-MM-DD/row-X-.../run_manifest.json`:
  + Đọc `start_time` và `stop_reason` của máy trong manifest.
  + Xác định rõ: Báo cáo watchdog tổng kết kết quả của ca chạy trong quá khứ, không phải trạng thái thời gian thực lúc nhận tin nhắn.
  + Nếu operator/agent đã can thiệp fix sau thời điểm ca chạy, báo cáo cũ hiển thị lỗi là tất yếu.

### Bước 2: Kiểm tra hiện trường O(1) trước khi can thiệp (Read-Only Inspection First)
- **CẤM TUYỆT ĐỐI** chạy ngay các lệnh can thiệp phá hủy (`--force-preempt`, `_forget_all_networks`, reboot) khi chưa đọc hiện trạng thực tế.
- Chạy lệnh kiểm tra nhanh:
  ```bash
  python D:/Taadaa/tools/inspect_machine.py <N>
  ```
- Kiểm tra 3 thông số then chốt:
  1. `Wi-Fi IP`: Có IP nội bộ dải farm (`192.168.110.x`) không?
  2. `Proxy`: Có đúng cổng `192.168.110.2:2000X` không?
  3. `Current Focus` / `Màn hình`: Đang ở Home Launcher hay app?

### Bước 3: Cấu trúc câu trả lời trực diện (Direct 2-Part Answer)
Khi operator hỏi *"Mạng máy X ổn chưa sao report báo lỗi?"*, trả lời ngắn gọn, trực diện theo đúng 2 phần:
1. **Tại sao report báo lỗi:** Giải thích rõ báo cáo thuộc Ca nào, khởi chạy lúc mấy giờ (ví dụ: Ca 1 chạy lúc 06:03 sáng ghi nhận máy mất mạng tại thời điểm đó).
2. **Hiện tại máy ổn chưa:** Nêu rõ tình trạng thực tế đọc được từ `inspect_machine.py` (IP, Proxy, Wi-Fi) kèm bằng chứng rõ ràng. Tuyệt đối không suy diễn, không đổ lỗi phần cứng, không yêu cầu operator thao tác tay khi chưa có lệnh.
