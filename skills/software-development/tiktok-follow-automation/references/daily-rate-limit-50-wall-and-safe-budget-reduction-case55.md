# TikTok 50 Follow/Ngày Hard Rate-Limit & Quy Tắc Giảm Trần Ngân Sách An Toàn (Case UI-55)

## 1. Bối Cảnh & Phân Tích Thực Tế (Đối Soát 140 State Files & 10 Ngày Farm)
Trong quá trình vận hành follow chéo trên farm (từ 27/08 đến 06/09/2026 trên 80 máy, cả Row 1 và Row 2):
- **Bức tường Rate-Limit 50 Follow/Ngày:** 100% không có bất kỳ tài khoản nào vượt qua được mốc 50 follow/ngày. Khi nick chạm mốc 48–50 lượt tích lũy trong ngày (thường rơi vào Phiên 3 của ca), TikTok lập tức kích hoạt rolling-window action block: nút Follow nảy ngược lại sau reload (`FOLLOW_FAILED: TikTok không nhận follow sau reload — dừng session`).
- **Phản biện mối lo ngại "Follow nhiều bị nhả ở chu kỳ sau":** Đối soát lịch sử chu kỳ $T \rightarrow T+1$ (sau 48h nghỉ theo lịch Chẵn/Lẻ) trên các máy đạt volume cao nhất (M45, M51, M58, M62, M26, M46, M72 đạt 45–50 lượt ở chu kỳ $T$):
  + Ở chu kỳ $T+1$, 100% các tài khoản này **KHÔNG hề bị nhả ở Turn 0**.
  + Chúng tiếp tục follow trơn tru từ 25 đến 46 lượt ở chu kỳ tiếp theo với `status: OK`.
  + **Bản chất:** Rate-limit 50 là giới hạn tần suất tích lũy theo ngày/phiên của TikTok, không phải hình phạt cộng dồn sang chu kỳ sau. Hạn mức được reset mới hoàn toàn sau 48h nghỉ ngơi.
  + Các tài khoản bị nhả Turn 0 thực chất là các nick vốn dĩ có trust score yếu từ trước (`fail_streak >= 2` hoặc dính IP bẩn/anchor lỗi).

## 2. Vì Sao Phải Hạ Trần Ngân Sách từ 60 Xuống 45?
- **Cấu hình cũ (trần 60):** `budget_per_day = 60`, `budget_per_session = 20`, random range `15–20`.
  + 1 Ca = 3 Phiên follow. Nick chạy Phiên 1 (~18–20 `OK`) và Phiên 2 (~18–20 `OK`) đã tích lũy ~36–40 lượt.
  + Sang Phiên 3, hệ thống tiếp tục ép nick chạy 15–20 lượt để cố đạt trần 60. Nick chạy được thêm 10–13 lượt thì đụng bức tường 50 của TikTok và bị cưỡng chế dừng lại (`FOLLOW_FAILED`), `fail_streak` tăng lên 1 và dính daily cooldown.
- **Cấu hình mới an toàn (trần 45 - Case UI-55):**
  + `budget_per_day = 45`
  + `budget_per_session = 15`
  + `budget_per_session_min = 12`
  + `budget_per_session_max = 15`
- **Hiệu quả:**
  + 3 phiên x 12–15 = 36–45 lượt/ngày, dừng chủ động dưới "radar" 50 của TikTok.
  + Cả 3 phiên trong ngày đều hoàn thành sạch sẽ (`status: OK`), `fail_streak = 0`.
  + Tránh mòn trust score do bị TikTok action-block cưỡng chế mỗi ngày.

## 3. Các File Cấu Hình & Code Bị Ảnh Hưởng
1. `follow_runner/core/config.py`: `FollowConfig` default `budget_per_day = 45`, `budget_per_session = 15`, `budget_per_session_min = 12`, `budget_per_session_max = 15`.
2. `follow_runner/core/follow_state.py`: `FollowState.session_budget()` fallback `base_min = 12`, `base_max = 15`.
3. `follow_runner/config.example.yaml`: Cập nhật cấu hình mẫu đồng bộ.
4. Unit test suite: `test_config.py`, `test_follow_state.py`, `test_mode1_search_follow.py` khớp assert trần 45.
