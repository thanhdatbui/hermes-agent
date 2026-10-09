# Low Follow Count Triage & Warm-up vs Deadline Rules

## 1. Bản chất Follow 1–4 lượt trên Báo cáo Watchdog

Khi watchdog báo cáo nhóm `Success` chỉ đạt 1–4 lượt follow (thay vì 10–20 lượt):
1. **Trường hợp Bị Nhả (`status: FOLLOW_FAILED`):**
   - Đã được watchdog phân loại riêng vào mục `Nhả follow`.
   - Cơ chế fail-closed ngắt ngay lập tức khi phát hiện nút bị nhả về "Follow".
2. **Trường hợp Hoàn thành (`status: OK`):**
   - **Post-cooldown Warm-up (`is_post_cooldown_warmup`):** Nick vừa mãn hạn cooldown án phạt, hệ thống tự động bóp quota xuống ngẫu nhiên **3–5 lượt** để thăm dò/dưỡng sinh an toàn (`session_budget()` trong `follow_state.py`). Đạt 3–5 lượt là hoàn thành 100% quota thăm dò.
   - **Chặn Deadline Gate 180s (`has_time_for_next_action(180.0)`):** Sau khi Mode 2 lướt tệp Anchor và skip các nick trùng, nếu thời gian còn lại của session < 180s thì script dừng Mode 2 và **không chuyển sang Mode 1 để bù**, tránh bị timeout giữa chừng.
   - **Cạn nick mới:** Toàn bộ danh sách nick trong tệp Anchor đã được follow từ các phiên trước ➔ Safe-exit với trạng thái `OK`.
