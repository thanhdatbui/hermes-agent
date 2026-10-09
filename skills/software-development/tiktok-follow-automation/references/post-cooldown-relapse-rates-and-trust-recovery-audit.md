# Post-Cooldown Relapse Rates & Trust Recovery Empirical Audit (07/10/2026)

## 1. Bối cảnh & Khảo Sát Thực Tế
Khảo sát đối soát 411 state files (`runs/state/follow_state_*.json`) trên toàn bộ 80 máy farm (`D:/Taadaa/tiktok-follow`):

- **Tổng số tài khoản trong hệ thống theo dõi follow:** 411 accounts.
- **Nick chưa từng dính phạt (Streak = 0):** 22 accounts (~5.4%).
- **Nick mới bị dính phạt lần đầu (Streak = 1):** 174 accounts (~42.3%).
- **Nick đã từng mãn hạn cooldown (ra tù) hoặc tái phạm >= 2 lần:** 215 accounts (~52.3%).

---

## 2. Phân Bổ Tỉ Lệ Khi Ra Tù (Trên 215 Nick Mãn Hạn Cooldown)

| Nhóm hành vi sau khi ra tù | Số lượng nick | Tỉ lệ trên tập ra tù (215 nick) | Tỉ lệ trên toàn farm (411 nick) |
| :--- | :---: | :---: | :---: |
| **1. Cứ ra tù là dính nhả liền liên tục** *(Fail ngay 1-2 lượt đầu / 0 follow được / Streak leo lên 2, 3, 4, 5, 6)* | **184 - 200 nick** | **85.6% - 93.0%** | **44.8% - 48.7%** |
| **2. Ra tù follow được vài cái (1-5 cái) rồi bị lại** *(Ăn 1-3 lượt warm-up rồi phiên sau bị nhả tiếp)* | **15 - 29 nick** | **7.0% - 13.5%** | **3.6% - 7.1%** |
| **3. Ra tù follow lại bình thường / phục hồi hoàn toàn** *(Follow ổn định >10-50+ cái, giữ streak 0)* | **2 - 17 nick** | **0.9% - 7.9%** | **0.5% - 4.1%** |

---

## 3. Phân Phối Lũy Tiến Cooldown Streak (Progressive Backoff)
- **Streak 1 (Phạt 3 ngày):** 174 nick.
- **Streak 2 (Phạt 5 ngày):** 152 nick.
- **Streak 3 (Phạt 7 ngày):** 42 nick.
- **Streak >= 4 (Phạt 15 ngày):** 21 nick (có tài khoản lên đến Streak 6).

---

## 4. Kết Luận Vận Hành & Kiến Trúc
1. **Feed Trust và Follow Trust tách biệt hoàn toàn:**
   - Việc chỉ cho nick nghỉ follow 7+ ngày và lướt feed đơn thuần **KHÔNG** tự động hồi phục Follow Trust.
2. **Nguyên nhân tái phạt chiếm áp đảo (>85%):**
   - Tài khoản bị TikTok đánh cờ hành vi spam hoặc chưa tích lũy đủ Inbound Trust (thiếu video chất lượng / tương tác 2 chiều). Khi hết cooldown, TikTok kích hoạt Action Drop ngay khi phát sinh lượt bấm follow mới.
3. **Tiêu chuẩn tài khoản phục hồi thành công:**
   - Các nick thoát khỏi vòng lặp nhả follow thành công (0.9% - 7.9%) đều là những nick có tuổi đời cao (>60 - 120 ngày) và đã có sẵn số lượng video đăng (>15 - 20 video).
