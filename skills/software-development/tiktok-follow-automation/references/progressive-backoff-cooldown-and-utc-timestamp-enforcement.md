# Case UI-37: Progressive Backoff Cooldown & UTC Timestamp Enforcement

## 1. Problem & Context
Tài khoản bị TikTok nhả follow (shadowban / rate-limit drop) chia làm 2 nhóm rõ rệt:
- **Nhóm nhả do chạm ngưỡng tạm thời (25% – 50%):** Hồi phục hoàn toàn sau 48 giờ nghỉ ngơi và có thể tiếp tục follow 15–40 target/ngày.
- **Nhóm nhả dai dẳng / lì đòn (5% – 10%):** Bị TikTok áp cờ phạt sâu. Nếu tiếp tục thử lại sau mỗi 48h sẽ liên tục chạm vào cờ phạt khiến nick không bao giờ được gỡ shadowban.

## 2. Progressive Backoff Policy
Quy tắc lũy tiến thời gian nghỉ dựa trên số chu kỳ nhả liên tiếp (`fail_streak`):

| Fail Streak | Trạng thái | Thời gian Cooldown | Mục đích |
| :--- | :--- | :--- | :--- |
| **Streak = 1** | Bị nhả lần đầu | **+48 giờ** | Mở lại đúng sau 48h để dò tìm và vớt 25% – 50% nick hồi phục sớm. |
| **Streak = 2** | Nhả 2 chu kỳ liên tiếp | **+96 giờ (4 ngày)** | Bỏ qua 1 ca chạy của nick để tăng thời gian giải trừ rate-limit. |
| **Streak >= 3** | Nhả >= 3 chu kỳ (lì đòn) | **+168 giờ (7 ngày / 1 tuần)** | Cho nick nghỉ hẳn follow 1 tuần để TikTok xóa sạch shadowban penalty score. |

## 3. Technical Design & Contracts (`follow_runner/core/follow_state.py`)

### A. Timestamp Tuyệt Đối (UTC Offset-Aware)
- Quản lý cooldown bằng timestamp UTC tuyệt đối (`cooldown_until_at` dạng `YYYY-MM-DDTHH:MM:SS+00:00`), chuẩn hóa microsecond = 0.
- Tuyệt đối không dùng so sánh ngày lịch thuần túy (`YYYY-MM-DD`) vì sẽ gây lỗi mất cooldown nếu lỗi xảy ra sát nửa đêm (ví dụ fail lúc 23:59 sang 00:01 hôm sau bị mở sớm).
- Strict parsing: Yêu cầu chuỗi timestamp phải có định dạng ISO và chứa timezone offset rõ ràng. Date-only hoặc naive datetime bị từ chối và kích hoạt chế độ **Fail-Closed** (tiếp tục khóa follow để bảo vệ tài khoản).

### B. Idempotent Failure Callbacks
- Nếu `set_follow_failed()` được gọi khi tài khoản đang trong thời gian cooldown còn hiệu lực (`now_utc < active_cooldown_dt`), hệ thống giữ nguyên `cooldown_until_at` và `fail_streak` gốc, không tăng streak oan do duplicate/delayed worker callbacks.
- Streak chỉ tăng khi lỗi mới xảy ra sau khi cooldown trước đã hết hạn và nằm trong cửa sổ gia hạn hợp lệ (`prior_cooldown_hours + 48h grace window`).
- Nếu lỗi xảy ra sau khi đã vượt quá grace window, streak tự động reset về `1`.

### C. Causal Success Resets
- Trong `mark(uid, 'followed')`, chỉ xóa cooldown và reset `fail_streak = 0` khi và chỉ khi thời điểm thành công diễn ra **sau** thời điểm lỗi gần nhất (`now_utc >= last_failed_at`).
- Ngăn chặn triệt để tình trạng một worker callback thành công bị trễ/stale vô tình xóa mất cờ cooldown của một đợt nhả follow mới hơn.

### D. Di Trú Dữ Liệu Cũ An Toàn (Legacy Migration)
- Tự động nhận diện các bản ghi state cũ chỉ có `follow_failed_date` (chưa có `last_failed_at`).
- Di trú an toàn sang mốc UTC bảo thủ: `end_of_day (23:59:59 local) + 48h`, ngăn ngừa việc roll-day sang ngày mới mở khóa sớm cho tài khoản.
- Tách biệt logic di trú thành `_migrate_legacy_cooldown` để đảm bảo đơn nhiệm và không tái kích hoạt sau khi cooldown mới đã hết hạn.

### E. Bảo Toàn Hard Block (`follow_blocked`)
- Mọi nhánh kiểm tra và hết hạn cooldown trong `_check_and_sync_cooldown_expiry()` đều phải bảo toàn cờ khóa vĩnh viễn `follow_blocked`. Hết hạn cooldown tạm thời tuyệt đối không làm mở khóa tài khoản đang bị hard-blocked.
