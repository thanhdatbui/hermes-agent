# Cơ Chế Dò Trần Tăng Tiến Có Bộ Nhớ & Khóa Trần Ca Hồi Phục (Adaptive Progressive Ceiling)

## 1. Bối cảnh & Vấn đề Thực tế

- **Hạn mức tĩnh 15–16 lượt làm nghẽn dàn nick khỏe:** Các farm nuôi tài khoản già có thể đạt 20–30 follow/ca. Nếu hệ thống đóng đinh trần tĩnh ở 15–16 thì nick dù khỏe cũng không bao giờ bung được hết năng suất.
- **Nghịch lý chia nhiều Tier tĩnh:** Nếu chia 5–6 bậc cứng nhắc với điều kiện ngặt nghèo (50, 100, 180 fl, tuổi 150d...) mà khi dính nhả 1 lần lại văng vào tù và reset về vạch xuất phát, nick sẽ liên tục bị "xóa trí nhớ" và không bao giờ tìm được trần an toàn thật.
- **Nguyên nhân cốt lõi khiến Phiên 2 bấm người thứ 2 là bị nhả:**
  - Ở nick Hồi phục (Tier 1 và Tier 2), trần chịu đựng trong ngày của TikTok chỉ từ 4–8 lượt.
  - Ở Phiên 1 (06:00), nick đã follow 3–4 người (ăn hết trần sinh tồn).
  - Sang Phiên 2 (08:00, cách 2 tiếng), runner lại cấp tiếp 3–4 lượt mới mà không kiểm tra số lượt P1 đã tiêu thụ.
  - Kết quả: Nick bấm được đúng 1 lượt ở P2 (chạm trần), sang lượt thứ 2 bị TikTok từ chối ngay (`FOLLOW_FAILED`), dính án phạt tăng streak và bị giam cooldown 3–5 ngày oan uổng.

---

## 2. Giải Pháp 1: Khóa Trần Theo Ca (Shift Cap) Cho Nick Hồi Phục

Áp dụng trong `_determine_budget_tier()` của `FollowState`:
- **Hồi phục Tier 1 (`probation_tier1` — clean_days = 0):** Trần cứng tối đa **4 lượt / ca**.
  - P1: Bốc 2–4 lượt. Nếu P1 đã ăn hết 4 lượt $\rightarrow$ P2 tự động **Safe-Skip (budget = 0)**, nick chỉ lướt feed xem video, bảo toàn ngày sạch (`clean_days`).
  - Nếu P1 chỉ ăn 2 lượt $\rightarrow$ P2 cấp tiếp tối đa 2 lượt để đủ trần 4.
- **Hồi phục Tier 2 (`probation_tier2` — clean_days = 1):** Trần cứng tối đa **8 lượt / ca** (P1 ăn 4, P2 ăn 4, tổng ngày không quá 8).

---

## 3. Giải Pháp 2: Cơ Chế Dò Trần Tăng Tiến Có Bộ Nhớ (Adaptive Progressive Ceiling)

Bỏ toàn bộ các bậc thang tĩnh rườm rà. Hệ thống quản lý bằng 3 biến số trong file state của từng nick:
1. `proven_safe_ceiling`: Trần an toàn cao nhất mà nick đã vượt qua sạch sẽ (mặc định khởi tạo = 15 khi tốt nghiệp).
2. `active_ceiling`: Trần mở rộng cho chu kỳ tiếp theo (`= min(30, proven_safe_ceiling + 2)`).
3. `last_failed_ceiling`: Ngưỡng chết mà nick vừa bị TikTok nhả.

### Vòng đời thăng tiến & Khôi phục:
- **Dò trần tăng tiến (+2 mỗi ca sạch, kịch trần 30 lượt):**
  - Khi nick chạy sạch $\ge 15$ lượt $\rightarrow$ Sang ca tiếp theo, `active_ceiling` tự động mở rộng thêm `+2`:
    $$15 \xrightarrow{+2} 17 \xrightarrow{+2} 19 \xrightarrow{+2} 21 \dots \xrightarrow{+2} 25 \dots \xrightarrow{+2} \mathbf{30\text{ lượt}}$$
- **Kỷ luật khi bị TikTok nhả (Giữ nguyên Invariant Farm):**
  - Khi gặp `FOLLOW_FAILED`: Nick vẫn bắt buộc vào Cooldown (nghỉ 3–5 ngày) và khi ra tù phải đi Hồi phục 1 $\rightarrow$ Hồi phục 2.
  - **Nhưng State ghi nhớ điểm an toàn:** Hệ thống tự động lùi trần an toàn lại 4 bước đệm:
    $$\text{proven\_safe\_ceiling} = \max(15, \;\text{curr\_proven} - 4)$$
    $$\text{active\_ceiling} = \text{proven\_safe\_ceiling}$$
    Đồng thời lưu `last_failed_ceiling = budget_used + 1`.
- **Khôi phục thông minh sau tốt nghiệp:**
  - Sau khi hoàn thành Hồi phục 1 & 2 và tốt nghiệp lại (`graduated = True, fail_streak = 0`), hệ thống đọc `proven_safe_ceiling = 20` $\rightarrow$ **Cấp ngay trần 20 lượt**, nick tiếp tục cày từ mốc an toàn đã được chứng minh, không bị đè về đáy 10–15.

---

## 4. Cạm Bẫy Kỹ Thuật (Implementation Pitfalls)

1. **Bẫy Đệ Quy Vô Hạn trong `_roll_day()`:**
   - Trong `FollowState._roll_day()`, tuyệt đối KHÔNG được gọi `self.is_graduated` hoặc `self.follow_failed` vì cả hai property này đều gọi ngược lại `self._roll_day()`, gây `RecursionError: maximum recursion depth exceeded`.
   - **Khắc phục:** Đọc trực tiếp từ dictionary nội bộ: `self._data.get("graduated") is True and not self._data.get("follow_failed")`.
2. **Bẫy `session_budget()` Không Clamp Daily Remaining:**
   - Spec yêu cầu `session_budget()` độc lập tạo budget cho phiên đó dựa trên trần phiên (`active_cap`), không tự trừ `budget_used` vào dải random của phiên mới, tránh làm gãy contract và test suite cũ.
3. **Phân biệt Hành Vi Tài Khoản vs Thiết Bị:**
   - Từng tài khoản chỉ on app 30–40 phút/ca rồi nghỉ 96h (rất an toàn).
   - Nhưng thiết bị chạy 3–4 ca/ngày đổi nick liên tục thì mang rủi ro liên đới phần cứng/IP (Hardware Correlation). Không mở ồ ạt ca đêm cho cả 160 máy mà phải canary nhóm nhỏ (5–10 máy) trước.
