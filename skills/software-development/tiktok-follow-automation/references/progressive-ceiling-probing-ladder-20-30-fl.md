# Progressive Ceiling Probing Ladder (Dò Trần Tăng Tiến Lên 20-30 Follow)

## Bối cảnh & Yêu cầu thực chiến
- CẤM cố định cứng trần 15-16 follow cho nhóm nick khỏe (Core).
- Các farm quy mô lớn (chu kỳ 4 ngày / 96h) chạy thực tế đạt 20–30 follow/ca cho nick có trust dày.
- Để không bị vỡ trận diện rộng, runner áp dụng cơ chế **Dò Trần Tăng Tiến Động (Dynamic Progressive Ceiling)** tự động nâng bậc dựa trên dữ liệu tích lũy của từng tài khoản.

## 6 Bậc Thang Tăng Tiến (Progressive Ladder)

| Bậc (Tier) | Điều kiện Nick (State / DB) | Trần Ca (Shift Cap) | Phân bổ P1 & P2 | Cơ chế an toàn |
| :---: | :--- | :---: | :---: | :--- |
| **Bậc 1 (S1)** | Vừa dính nhả / hết cooldown (`clean_days = 0`) | **4 lượt** | P1: 2–4, P2: bù đủ 4 | Dưỡng bệnh. P1 đạt 4 thì P2 Safe-Skip. |
| **Bậc 2 (S2)** | Đã có 1 ngày sạch hoàn toàn (`clean_days = 1`) | **8 lượt** | P1: 4, P2: 4 | Hồi phục chuẩn. P2 bù đủ trần 8. |
| **Bậc 3 (Base Core)** | Tốt nghiệp (`clean_days >= 2`), Follow $< 50$ | **12 – 16 lượt** | P1: 6–8, P2: 6–8 | Bước đệm sau tốt nghiệp. |
| **Bậc 4 (Probing 1)** | `Follow tích lũy >= 50`, `Video >= 15`, `Age >= 45d` | **18 – 22 lượt** | P1: 9–11, P2: 9–11 | Vượt ngưỡng 20 an toàn. |
| **Bậc 5 (Probing 2)** | `Follow tích lũy >= 100`, `Video >= 20`, `Age >= 90d` | **22 – 26 lượt** | P1: 11–13, P2: 11–13 | Khai thác năng suất cao. |
| **Bậc 6 (Elite Peak)** | `Follow tích lũy >= 180`, `Video >= 25`, `Age >= 150d` | **26 – 30 lượt** | P1: 13–15, P2: 13–15 | Đạt trần 30 follow/ca (M37, M39). |

## Nguyên tắc Vận hành & Phanh Khẩn Cấp
1. **Chia nhịp P1 và P2 (Decay Window 2h):**
   - Không dồn toàn bộ 25-30 follow vào 1 phiên duy nhất (dễ kích hoạt hourly rate limit của TikTok).
   - Chia làm 2 cữ (P1 lúc 6h/12h/18h và P2 lúc 8h/14h/20h) để TikTok kịp reset cửa sổ trượt.
2. **Shift Budget Cap (Khóa trần ca):**
   - Đọc `budget_used` trong ngày: `remaining = max(0, cap - budget_used)`.
   - Nếu P1 đã dùng hết trần ca $\rightarrow$ P2 trả `budget = 0` (Safe-Skip follow, chỉ lướt feed dưỡng).
3. **Rollback tự động khi dính nhả (Circuit Breaker):**
   - Nếu nick ở Bậc 5 (26 fl) hoặc Bậc 6 (30 fl) bị TikTok nhả giữa chừng $\rightarrow$ Dừng phiên ngay lập tức (`FOLLOW_FAILED`), hạ 1 bậc ở ca sau, tránh bị phạt chuỗi streak $\ge 4$ giam 15 ngày.
