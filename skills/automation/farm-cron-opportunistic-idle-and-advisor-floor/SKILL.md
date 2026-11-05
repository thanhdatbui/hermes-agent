---
name: farm-cron-opportunistic-idle-and-advisor-floor
description: "Quy chuẩn chuyển đổi Cron toàn Farm sang canh máy rảnh cuốn chiếu (Opportunistic Idle-Machine) và đồng bộ sàn 300s cho Advisor Sol."
---
# Farm Cron Opportunistic Idle-Machine & Advisor 300s Floor

## 1. Đồng Bộ Sàn Timeout 300s Cho Toàn Bộ Advisor & Planner
- **Bẫy lệch pha cấu hình:** Hệ thống đã ép sàn Worker và Planner lên 300s (`SOL_AGY_TIMEOUT_FLOOR = 360`, `DEFAULT_TIMEOUT_PER_TURN = 300`), nhưng nếu bỏ quên file `consult_advisor.py` ở ngưỡng cũ (`first_token_timeout=90s`, `max_total_timeout=200s`) thì mô hình suy luận sâu (`gpt-5.6-sol-high` qua :20129) sẽ bị ngắt socket giữa chừng (do reasoning mất 45s-85s) $\rightarrow$ báo lỗi `unavailable` giả tạo.
- **Quy chuẩn bắt buộc:** Trong `consult_advisor.py` bắt buộc đồng bộ `first_token_timeout=150.0s`, `max_total_timeout=300.0s`, default `timeout_sec=300.0s`.

## 2. Kiến Trúc Cron Farm: Giờ Cố Định -> Canh Máy Rảnh Cuốn Chiếu (Opportunistic Idle-Machine)
Khi chuyển các cron tác vụ phụ (cứu session login, 2FA, đổi biệt danh, upload avatar) từ khung giờ cố định sang quét liên tục cả ngày (`*/15 * * * *`):

### A. Hai Chốt Chặn An Toàn Bắt Buộc (Safety Invariants)
1. **Né Ca Nuôi Feed/Follow Cứng (Manifest Slot Buffer):**
   - Đọc file lịch `assignment-v1-*.json` mới nhất.
   - Bắt buộc: `now_dt + timedelta(minutes=15) < next_slot_time`. Nếu cách ca nuôi kế tiếp dưới 15 phút $\rightarrow$ BẮT BUỘC BỎ QUA (Safe-Skip) để tránh đè app và làm văng session nuôi TikTok.
2. **Device Lock State Check:**
   - Quét `~/.codex/device-locks/machine_<M>.lock.json`. Bắt buộc không có lock nào ở trạng thái active/running/queued.

### B. Cơ Chế Giải Quyết Tranh Chấp Lock (Priority Hierarchy & Backoff)
Khi nhiều cron cùng thấy một máy rảnh, áp dụng bảng phân tầng độ ưu tiên:
- **P0 (Critical / Sống còn):** Cứu login Gmail văng session (`is_relogin`), phục hồi nick bị checkpoint.
- **P1 (Doanh thu):** Đăng video TikTok theo giờ vàng (`cron_stale_upload`).
- **P2 (Lịch nuôi chính):** Feed session / Follow theo Manifest.
- **P3 (Dưỡng & Chuẩn hóa):** Bật 2FA TikTok, đổi biệt danh "user bình thường", bù avatar.
- **P4 (Hạ tầng):** Dọn cache, dọn dead locks.

**Nguyên tắc chống Starvation:**
- Các tác vụ P3/P4 kiểm tra cờ trạng thái: nếu máy đang nằm trong hàng đợi cần cứu session (P0) hoặc đăng video (P1) $\rightarrow$ Tự động lùi bước (Priority Backoff), nhường máy cho tác vụ bậc cao hơn.

### C. Case Study Thi Công Thực Tế: GPM Login Watchdog (`post_evening_gpm_login_watchdog.py`)
- **Trước nâng cấp:** Chặn cứng 3 ca (`09:30-11:20`, `15:30-17:20`, `21:30-23:45`).
- **Sau nâng cấp:** Chuyển sang cơ chế Rolling né 3 ca cao điểm nuôi feed (`05:15-09:30`, `11:45-15:30`, `17:45-21:30`) và dọn cache (`04:00-04:30`). Ngoài các khung này, cho phép chạy cả ngày mỗi 15 phút (`*/15 * * * *`). Hễ có máy S7 rảnh và có acc `NEEDS_LOGIN` là mở GPM phối hợp ADB cứu session ngay lập tức.

## 3. Kỷ Luật Điều Phối Của Coordinator (Anti-Context Amnesia)
- Khi User đưa ra định hướng kiến trúc lớn (như chuyển đổi toàn bộ cron sang canh máy rảnh) sau đó tiếp tục chỉ đạo các việc phụ (gọi Advisor, kiểm tra log): Coordinator BẮT BUỘC giữ vững mục tiêu kiến trúc cốt lõi trong đầu, không được để việc xử lý nhánh phụ làm "rơi" mất nhiệm vụ chính của User. Phải chủ động cập nhật tiến độ và hỏi xác nhận thi công dứt điểm.
