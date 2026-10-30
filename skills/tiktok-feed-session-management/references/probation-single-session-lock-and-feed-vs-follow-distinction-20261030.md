# Khế Ước Phân Biệt Feed Session Thành Công vs Follow Hook & Quy Tắc Khóa Cữ Probation (2026-10-30)

## 1. Bản Chất Tách Biệt: Feed Swipe Session vs Follow Hook Execution
- **Hai tiến trình hoàn toàn độc lập trong 1 Session nuôi acc:**
  1. **Feed Swipe Session (`feed-session-smoke`):** Lướt video For You / Following / Friends, tương tác thả tim, comment peek.
  2. **Follow Hook (`follow-hook` / `run_follow.py`):** Chỉ kích hoạt ở cuối session feed khi máy được chọn đi follow.
- **Bẫy ảo giác "Thấy máy chạy mượt là đã follow thành công":**
  - Một máy có thể lướt 19/19 video mượt mà (`final_status: success`), nhưng đến bước gọi `run_follow.py` thì bị chặn bởi Preflight Gate (ví dụ: `required Android VPN is not connected`).
  - Khi đó, tiến trình follow bị `BLOCKED` với `followed_count = 0` (chưa bấm lượt nào).
  - **Kỷ luật đối soát:** Không được nhìn vào số video hoàn thành của feed để kết luận số lượt follow; bắt buộc đọc trực tiếp `follow_result.json` hoặc cột `internal_follows` trong bảng `session_account_actions` của `tiktok_tracker.db`.

---

## 2. Quy Tắc Khóa Cữ Probation: `PROBATION_SINGLE_SESSION_LOCK`
- **Mục tiêu an toàn:** Bảo vệ tài khoản đang trong diện thử thách (Probation Tier 1 & Tier 2) sau khi mãn hạn Cooldown.
- **Cơ chế kích hoạt:**
  - Nếu trong ngày tài khoản Probation đã follow thành công $\ge 1$ lượt (`budget_used > 0`): Hệ thống tự động khóa cứng quota của các phiên tiếp theo trong cùng ngày (`budget = 0`).
  - Runner vẫn hoàn tất với `status: OK, followed: 0` để dưỡng nick, tránh bị thuật toán TikTok phát hiện dồn dập.
- **Trường hợp dồn cữ sang Phiên 2:**
  - Nếu ở Phiên 1, máy bị chặn trước khi bấm follow (`status: BLOCKED`, `budget_used == 0` do rớt VPN/mạng): Quota ngày vẫn còn nguyên.
  - Sang Phiên 2, khi mạng phục hồi, máy sẽ được cấp quota để đi cữ Hồi phục của ngày hôm đó.

---

## 3. Hệ Quả Khi Bị Nhả Ở Cữ Probation (Học Lại Từ Đầu)
- **Nếu đang đi Hồi phục 1 mà bị nhả ngay anchor đầu (`used == 0`):**
  - Bị xóa trắng biến tích lũy sạch (`probation_clean_days` bị xóa).
  - Tăng lũy tiến bậc phạt Cooldown theo bậc thang chuẩn (`streak += 1`, ví dụ streak 3 $\rightarrow$ 4 bị phạt 15 ngày).
  - Sau khi mãn hạn Cooldown, nick **bắt buộc phải quay lại Hồi phục 1 (Probation Tier 1, quota 2–4 lượt)** để rà mìn lại từ đầu; không có ngoại lệ nhảy cóc.
