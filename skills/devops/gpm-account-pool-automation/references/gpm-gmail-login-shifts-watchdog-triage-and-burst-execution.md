# GPM Gmail Login Shifts Watchdog: Multi-Shift Triage & Burst Execution Mechanics

## 1. Bản Chất Vận Hành Đa Ca (Multi-Shift Schedule)
Watchdog `gpm-gmail-login-shifts-watchdog` (chạy script `post_evening_gpm_login_watchdog.py`, `no_agent: true`, cron `*/5 9,10,11,15,16,17,21,22,23 * * *`) vận hành so le vào các khung rảnh giữa các ca nuôi feed TikTok của Farm:
- **Ca Sáng:** 09:30 – 11:20 (sau Ca 1 nuôi feed kết thúc lúc 09:25).
- **Ca Chiều:** 15:30 – 17:20 (sau Ca 2 nuôi feed kết thúc lúc 15:25).
- **Ca Tối:** 21:30 – 23:45 (sau Ca 3 nuôi feed & avatar kết thúc lúc 21:25).

Ngoài 3 khung giờ trên, `is_within_time_window()` trả về `False`, script tự ngắt ngay lập tức để không chạm vào farm.

## 2. Cơ Chế Chạy Dồn (Burst Execution) vs Chờ Chốt Ca
Khi nhận câu hỏi: *"Chạy từ sáng đến giờ sao chỉ được 26-30 acc?"*:
1. **Thực tế thời gian chạy thật:**
   - Script chạy theo từng batch `MAX_WORKERS = 5` trên mỗi tick cron (mỗi 5 phút).
   - Với 30 tài khoản, script chỉ mất **6 batch × 5 workers ≈ 25 - 26 phút** (từ 09:30 đến ~09:56).
   - Tốc độ xử lý thực chiến: **~50s / acc**.
2. **Tại sao dừng giữa chừng khi chưa hết khung giờ?**
   - **Chốt chặn an toàn thiết bị (`is_machine_idle`):** Sau khi xử lý hết các máy rảnh, các tài khoản còn lại trong hàng đợi thuộc về máy đang dính device lock hoặc nằm trong khoảng đệm an toàn (`MIN_IDLE_BUFFER_MIN = 10` phút) trước ca nuôi TikTok tiếp theo.
   - **Chốt chặn proxy (`MAX_LOGINS_PER_PROXY = 2`):** Mỗi cổng proxy di động 4G chỉ được login tối đa 2 lần/ngày. Khi cổng chạm trần, script bỏ qua ứng viên đó.
   - **Chờ đến ngưỡng `is_late`:** Giữa 09:56 và 11:15, các tick cron 5 phút đều thấy `ready` rỗng và âm thầm chờ. Đến 11:15 (`now.minute >= 15`), ngưỡng `is_late` kích hoạt, script chính thức chốt `finished_shifts: ["SANG"]`, xuất báo cáo tổng kết duy nhất ra stdout và bàn giao máy cho ca trưa.

## 3. Quy Trình Đối Soát Nhanh Hiện Trường (Triage Runbook)
1. **Kiểm tra file state:** Đọc `D:/Taadaa/runtime/kibe/cron-state/post_evening_gpm_login_state.json`:
   - `mtime` của file: Xác định chính xác phút cuối cùng batch thực sự chạy (ví dụ 09:56).
   - `processed`: Danh sách acc đã chạy hôm nay.
   - `proxy_count`: Số lượt dùng trên từng cổng proxy.
   - `finished_shifts`: Đã hoàn tất các ca nào (`["SANG"]`, `["CHIEU"]`, `["TOI"]`).
2. **Kiểm tra cookie mtime:** Kiểm tra file `Default/Network/Cookies` của profile tương ứng trong `GPMLogin/profile/<ProfilePath>` để chứng minh session được nạp lúc mấy giờ.
3. **Phân loại thất bại (Fail Triage):**
   - **Google 2SV sensitive cooldown 7 days (`signin/rejected?rrk=77`):** Đưa về GroupId=11 cách ly, không cố thử lại.
   - **Timeout / Không bắt được session:** Thường do proxy lag cục bộ hoặc popup Google chưa bypass kịp. Giữ nguyên để ca sau hoặc watchdog nuôi tự động rà lại.
