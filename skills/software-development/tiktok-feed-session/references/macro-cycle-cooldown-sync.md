# Lịch Vận Hành Vĩ Mô & Khôi Phục Cooldown Phạt Nhả (Feed Session)

## 1. Chu kỳ 3 ngày (4-4-Nghỉ) vs Lịch chạy 2 ngày cũ
- **Điểm yếu của lịch cũ:** Chạy xoay tua chẵn/lẻ không có ngày nghỉ khiến anomaly score tích lũy liên tục.
- **Lịch 3 ngày chuẩn:**
  - Ngày 1: Chạy 4 slot (Slot 1, 3, 5, 7 hoặc 1-4) — 2 phiên follow (10-15 follow/phiên) + kẹp 1 phiên up video.
  - Ngày 2: Chạy 4 slot còn lại (Slot 2, 4, 6, 8 hoặc 5-8).
  - Ngày 3: Toàn farm nghỉ follow 100% — Chuyển toàn bộ các ca sang thuần lướt feed nuôi tự nhiên (0 follow chéo, chỉ 5% organic follow tab For You nếu acc sạch).
  - Ngày 4: Lặp lại Ngày 1 (mỗi slot được nghỉ trọn vẹn 48h thực tế).

## 2. Đồng bộ State Machine trong `feed_swipe_smoke.py` (`is_account_in_follow_cooldown`)
- **Auto-sync expiry:** Khi `now_utc >= cooldown_until_at`, hàm kiểm tra phải tự dọn dẹp sạch cờ `follow_failed = False`, reset `fail_streak = 0`, xóa `cooldown_until_*` và atomic write (`.tmp` -> `os.replace`).
- **UTC normalization:** Dùng `datetime.now(timezone.utc)` và `until_dt.astimezone(timezone.utc)` đồng bộ toàn diện.
- **Row isolation:** Tuyệt đối không fallback sang `follow_state_{machine}.json` chung của máy để tránh đóng băng nhầm các slot khỏe mạnh.
