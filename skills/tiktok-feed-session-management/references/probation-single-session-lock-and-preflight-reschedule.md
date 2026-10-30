# Cơ Chế Khóa Đơn Phiên Hồi Phục (Probation Single Session Lock) & Điều Phối Bù Lượt Khi Dính Preflight Block

## 1. Bản Chất `PROBATION_SINGLE_SESSION_LOCK` Trong Code (`follow_state.py`)
- **Đối tượng áp dụng:**
  - Tất cả các tài khoản đang trong diện Dưỡng / Thử thách (**Probation Tier 1 & Tier 2 / Hồi phục 1 & 2**, tức `is_graduated == False`).
- **Nguyên tắc kỹ thuật:**
  ```python
  if _safe_int(self._data.get("budget_used", 0), 0) > 0:
      logger.info("[PROBATION_SINGLE_SESSION_LOCK] machine=%s row=%s tier=%s", self.machine, self.account_row_index, tier)
      return 0, tier
  ```
  - **Mỗi ngày chỉ được phép bấm follow trong 1 phiên duy nhất.**
  - Ngay khi nick đã hoàn thành follow ở Phiên 1 của ca (`budget_used > 0`), khi sang Phiên 2 của cùng ca, hàm `session_budget` lập tức trả về `budget = 0`.
  - Runner kết thúc với `status: OK, followed: 0` (an toàn tuyệt đối, không phải lỗi).
  - Mục đích: Chống dồn dập thao tác trên nick đang yếu/vừa hết cooldown, tránh kích hoạt lại thuật toán theo dõi bất thường của TikTok.

---

## 2. Cơ Chế Bù Lượt Khi Dính Preflight VPN / Lỗi Ngoại Cảnh Ở Phiên 1
- **Hiện tượng:**
  - Ở Phiên 1, máy vẫn có thể lướt Feed hoàn tất (ví dụ lướt 19/19 video For You).
  - Tuy nhiên, khi chuyển sang bước `follow-hook`, nếu Preflight VPN Gate phát hiện rớt VPN hoặc lỗi proxy (`tun_up=False`, `egress IP verification failed`), hệ thống lập tức ngắt fail-closed (`status: BLOCKED`).
- **Hệ quả đối với Quota:**
  - Vì bị chặn trước khi app thực hiện bấm follow, số follow thực tế là `0` và `budget_used` vẫn là `0`.
  - Tài khoản **CHƯA bị dính `PROBATION_SINGLE_SESSION_LOCK`**.
  - Do đó, khi sang Phiên 2 và mạng đã ổn định trở lại, tài khoản vẫn còn nguyên hạn ngạch đi follow của ngày hôm đó và sẽ được cấp quota để chạy Hồi phục.

---

## 3. Quy Tắc Giáng Cấp & Lặp Lại Vòng Hồi Phục (Probation Reset)
- **Nếu bị nhả ngay phát đầu (`used == 0`):**
  - Hệ thống xác định nick vẫn đang bị TikTok phạt Action Block tại chỗ (`FOLLOW_FAILED: anchor bị nhả sau vuốt`).
  - Toàn bộ điểm tích lũy ngày sạch bị xóa trắng (`pop("probation_clean_days")`).
  - Lũy tiến bậc phạt `fail_streak` theo ladder: Streak 1: 24h, Streak 2: 3d, Streak 3: 5d, Streak 4+: 15d.
  - **Kỳ sau mãn hạn cooldown:** Nick bắt buộc phải thi hành án lại từ đầu tại **Hồi phục 1 (Probation Tier 1, quota 2–4 lượt)**, không được phép bảo lưu sang Hồi phục 2 hay tốt nghiệp.
