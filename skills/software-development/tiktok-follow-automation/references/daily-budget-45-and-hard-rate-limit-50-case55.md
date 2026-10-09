# Case UI-55: Hạ Trần Follow An Toàn 45 Lượt/Ngày (12–15 Lượt/Phiên) Chống Nhả Follow Ở Phiên 3 Do Chạm Trần Rate-Limit 50 Của TikTok

## 1. Hiện tượng & Dữ liệu thực tế 10 ngày (27/08 – 06/09/2026)
- **Triệu chứng:** Các tài khoản khỏe nhất farm (M26, M46, M72 ở Ca Row 2) chạy trơn tru ở Phiên 1 (follow 18–20 `OK`) và Phiên 2 (follow 18–20 `OK`), tích lũy được ~36–40 follow. Tuy nhiên sang Phiên 3, sau khi follow được 10–13 lượt và chạm **mốc 49–50 lượt follow tích lũy trong ngày**, TikTok lập tức kích hoạt action-block:
  `FOLLOW_FAILED: TikTok không nhận follow sau reload — dừng session`.
- **Hậu quả:** Phiên 3 bị gán thất bại, tài khoản dính daily cooldown và tăng `fail_streak = 1` một cách không cần thiết dù nick rất khỏe.
- **Bản chất kỹ thuật:** 
  1. TikTok áp dụng trần cứng rolling-window ~50 follow/ngày cho mỗi tài khoản. Trong suốt 10 ngày đối soát trên 80 máy, **100% không có bất kỳ nick nào vượt qua được mốc 50 follow/ngày**.
  2. Mức trần cũ `budget_per_day = 60` (với `budget_per_session = 20`, random `15..20`) là "trần ảo" không thể chạm tới, vô tình ép các nick khỏe phải húc đầu vào bức tường rate-limit 50 ở phiên 3.
  3. Cơ chế của TikTok là rate-limit trong ngày chứ không cộng dồn phạt sang chu kỳ sau: tài khoản follow 45–50 lượt ở chu kỳ T hoàn toàn không bị nhả Turn 0 ở chu kỳ T+1 (sau 48h).

## 2. Giải pháp chuẩn hóa (Case Fix UI-55)
Hạ trần ngân sách follow toàn hệ thống để dừng chủ động dưới "radar" 50 của TikTok:
- `budget_per_day`: **45** (từ 60).
- `budget_per_session`: **15** (từ 20).
- `budget_per_session_min`: **12** (từ 15).
- `budget_per_session_max`: **15** (từ 20).

Với cấu hình 12–15 lượt/phiên qua 3 phiên:
- 3 phiên x 12–15 = 36–45 lượt/ngày.
- Cả 3 phiên đều kết thúc sạch sẽ (`status: OK`), duy trì trust score cao và `fail_streak = 0`.
- Không có rủi ro bị TikTok cưỡng chế dừng bằng action-block ở phiên 3.

## 3. Các vị trí mã nguồn đã cập nhật
- `follow_runner/core/config.py`: Default `FollowConfig` set `budget_per_day = 45`, `budget_per_session = 15`, `budget_per_session_min = 12`, `budget_per_session_max = 15`.
- `follow_runner/core/follow_state.py`: Fallback mặc định trong `session_budget()` set `base_min = 12`, `base_max = 15`.
- `follow_runner/config.example.yaml`: Cập nhật config mẫu.
- `follow_runner/tests/`: Cập nhật assertions trong `test_config.py`, `test_follow_state.py`, `test_mode1_search_follow.py`.
