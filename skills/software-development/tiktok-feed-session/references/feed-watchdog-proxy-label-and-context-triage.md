# Phân Biệt Context Đang Chạy Khi User Báo Lỗi Proxy / Ca Nuôi (2026-10-10)

## 1. Sự Cố Nhận Định Nhầm Ngữ Cảnh (Context Misidentification Pitfall)
- **Triệu chứng:** Người dùng nhắn ngắn gọn: *"Lỗi cấu hình proxy clgt"* hoặc *"sao lỗi proxy thế này"*.
- **Cạm bẫy:** Agent vội vàng liên hệ tới hệ thống LLM Gateway / Proxy Router (`9Router :20128`, `OmniRoute :20129`) trên PC vì các phiên trước vừa cấu hình model pool / proxy pool, trong khi thực tế người dùng đang nhắc tới **kết quả ca chạy Phone Farm (TikTok feed session, upload, follow...)**.
- **Hậu quả:** Báo cáo sai toàn bộ hiện trường (phân tích API 20129 thay vì thiết bị Android), gây ức chế nghiêm trọng cho người dùng (*"Gì thế đang ns ca chạy mà?? Omni gì ở đây"*).

## 2. Quy Tắc Khoanh Vùng Ưu Tiên (Triage Order Invariant)
Khi nhận câu hỏi ngắn về "lỗi proxy" mà không nói rõ hệ thống:
1. **Kiểm tra ngay Báo Cáo / Cronjob mới nhất của Farm:**
   - Đọc các run gần nhất trong ngày tại `D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>/` và `D:/Taadaa/runtime/admin/live/<YYYY-MM-DD>/`.
   - Xem thông báo gần nhất từ cronjob `tiktok-feed-session-watchdog` hoặc `tiktok-follow-watchdog`.
   - Nếu có ca chạy vừa kết thúc với danh mục `Fail: Lỗi cấu hình Proxy` -> **100% ngữ cảnh là PHONE FARM**.
2. **Chỉ kiểm tra LLM Proxy (20128/20129) khi:**
   - Người dùng nhắc đích danh: "OmniRoute", "9Router", "Antigravity", "Codex", "ChatGPT Web", "OAuth", "token".

## 3. Bản Chất Nhãn "Lỗi Cấu Hình Proxy" Trên Báo Cáo Feed Session Watchdog
- **Watchdog Regex Categorization:** Script watchdog gom tất cả các máy bị chặn ở chốt an toàn `vpn_preflight` (mã trạng thái `blocked-proxy-vpn`) vào cùng một nhãn hiển thị là `Lỗi cấu hình Proxy`.
- **Thực tế gồm 3 phân nhóm hoàn toàn khác nhau:**
  1. **Lỗi Lệch Dải Cổng Proxy (Port Boundary Desync):** Máy bị gán dải port không tồn tại trên router (ví dụ dải `10041..10080` trên cụm Admin khi MikroTik chỉ có tối đa 40 port PPPoE). Socket TCP bị từ chối (`closed/refused`). Khắc phục: Phủ lại dải port chuẩn `10008..10035` bằng `set_proxy_farm_admin_adb.py`.
  2. **Lỗi Mất Wi-Fi / Chớp Sóng:** Máy bị rớt sóng AP lúc batch quét qua, `dumpsys connectivity` báo `Wi-Fi not connected` hoặc kẹt ở app `adbjoinwifi`. Khắc phục: Toggle radio Wi-Fi hoặc re-join SSID chuẩn theo `farm-wifi-governance`.
  3. **Lỗi Phần Cứng / Cáp USB (ADB Disconnected):** Máy bị `device not found` hoặc `device offline`. Preflight fail-closed để chống lộ IP direct. Khắc phục: Kiểm tra cáp USB vật lý / hub sạc, không phải lỗi mạng.

## 4. Xử Lý Máy Đang Nằm Trong Ca Chạy Kế Tiếp (Lock Queued / Running)
- Khi user bảo kiểm tra / sửa một máy cụ thể (ví dụ: *"fix máy 7 đi"*):
- BẮT BUỘC kiểm tra xem tiến trình ca tiếp theo (ví dụ `run_tiktok.py` phiên 2) có đang giữ lock máy đó không (`C:/Users/Kibe/.codex/device-locks/machine_N.lock.json`).
- Nếu lock đang ở trạng thái `queued_v2` hoặc `running`: Runner ca mới đã tự động bốc máy vào hàng đợi xử lý. Không cưỡng chế tranh chấp lock (contention) mà kiểm tra `log.jsonl` / `summary.txt` của ca mới để theo dõi kết quả thực tế.
