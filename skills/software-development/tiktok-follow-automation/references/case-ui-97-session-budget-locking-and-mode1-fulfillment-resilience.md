# Case UI-97: Session Budget Locking (Single Source of Truth) & Mode 1 Fulfillment Resilience

## 1. Context & Sự Cố Thực Tế (06/10/2026)

Trên các máy chạy follow thành công hôm nay (M17 `@hadang0725`, M18 `@trinh.trinh.dinh`, M23 `@.thanh.trc.ng`):
- Mode 2 chỉ follow được 1-2 nick nội bộ (do hầu hết nick trong following list của 3 anchor Tik1/Tik2 đã được farm follow từ các ngày trước).
- Mode 1 được kích hoạt để chạy bù budget nhưng chỉ follow thêm được 3-6 nick rồi dừng.
- Tổng số follow thực tế sau cả ca chỉ đạt 8-14 follow (5-8 follow/phiên), thấp hơn so với kỳ vọng ngân sách 10-20 follow/phiên của nick trưởng thành.

### Sai lầm điều phối (Coordinator Anti-Pattern):
Khi User hỏi tại sao các nick chạy được thực tế lại chạy ít như vậy:
- **Lỗi 1 (Đổ lỗi lệch đối tượng):** Thay vì phân tích nguyên nhân tại sao nick *thành công* lại dừng sớm, Coordinator đi giải thích về các nick bị `FOLLOW_FAILED` / nhả follow trên các máy khác.
- **Lỗi 2 (Ngụy biện budget):** Tự kết luận "budget cấu hình chỉ có 4-8 lượt/phiên" dựa trên số đếm thực tế của phiên, trong khi cấu hình chuẩn là `budget_per_session_min: 10`, `max: 20` (hoặc 3-5 cho nick dưới 10 video).

---

## 2. Nguyên Nhân Kỹ Thuật (Root Causes)

### A. Lệch Pha Ngân Sách Giữa Mode 2 và Mode 1 (Split Quota Accounting):
- Hàm `state.session_budget()` bốc số ngẫu nhiên `random.randint(min, max)` (ví dụ 10 đến 20 cho nick trưởng thành).
- Trước đây:
  1. `run_mode2()` gọi `state.session_budget()` $\rightarrow$ bốc ra số $B_1$ (ví dụ 18). Mode 2 follow được 2 nick, còn thiếu 16 nick.
  2. `follow_engine.py` kiểm tra fallback: gọi `state.session_budget()` lần 2 $\rightarrow$ bốc ra số $B_2$ (ví dụ 12). Tính `rem_budget = 12 - 2 = 10`.
  3. `run_mode1()` bắt đầu chạy bù: lại gọi `state.session_budget()` lần 3 $\rightarrow$ bốc ra số $B_3$ (ví dụ 10). Tính `budget = 10 - 2 = 8`!
- **Hậu quả:** Quota phiên bị thay đổi liên tục giữa chừng, Mode 1 không nhận được mục tiêu ngân sách nhất quán từ đầu phiên.

### B. Bẫy Soft Deadline Trong Mode 1 (`reserve_seconds=180.0`):
- Trong `mode1_search_follow.py`, vòng lặp kiểm tra:
  `has_time_for_next_action(reserve_seconds=180.0)`
- Mức dự phòng 180s (3 phút) là quá lớn. Khi một phiên lướt feed + Mode 2 kéo dài, Mode 1 chỉ cần còn dưới 180s là lập tức dừng sớm (`Session deadline approaching, completing mode1 gracefully`), bỏ qua các UID còn lại trong danh sách dù hoàn toàn đủ thời gian thực hiện thêm 3-5 lượt tìm kiếm và follow.

### C. Rào Cản Dual Gate (Video Count Gate):
- Nick M23 (`@.thanh.trc.ng`) có `video_count = 9` (< 10 video).
- Thuật toán Dual Gate trong `follow_state.py`:
  `elif account_age_days <= 30 or video_count < 10: budget = random.randint(3, 5)`
- Nick chưa đủ 10 video bị khóa cứng budget ở mức **3-5 lượt/phiên** (giai đoạn mồi an toàn). Đây là hành vi đúng theo thiết kế an toàn, không phải lỗi runner.

### D. Nghịch Lý Mỏ Neo Rỗng Trong Mode 2 (Empty Anchor Mine Trap):
- Thiết kế ban đầu của Mode 2 kỳ vọng Anchor Tik1/Tik2 có danh sách Following dày đặc để khai thác follow chéo nội bộ.
- Tuy nhiên, hàm chọn anchor `anchor_uids()` trong `follow_engine.py` chỉ lọc theo `row_uids <= 2`, `video_count >= 10`, `machine <= 80` mà **hoàn toàn không kiểm tra số lượng Following thực tế của Anchor**.
- Phân tích hiện trường database ngày 06/10/2026 cho thấy trong 145 anchor Tik1/Tik2, có tới **47 anchor có Following < 10**, nhiều nick có Following = 0, 1, 3, 4 (`@shirldlpbkg` = 0, `@masyctsyy02` = 1, `@tooanh2604` = 3, `@crystal.1.15` = 4).
- Khi bốc ngẫu nhiên 3 anchor (`uids = uids[:3]`), Mode 2 bốc trúng các mỏ neo rỗng này:
  1. Thấy chưa follow anchor $\rightarrow$ bấm follow bản thân anchor (tính 1 lượt).
  2. Mở tab "Đang follow" của anchor ra $\rightarrow$ danh sách rỗng hoặc chỉ có 1-3 nick mà máy đã follow từ trước.
  3. Cuộn 5 lần (`idle_scrolls >= 5`) không thấy nick farm mới $\rightarrow$ break khỏi anchor.
  4. Hết 3 anchor $\rightarrow$ Mode 2 kết thúc sớm chỉ với đúng 1-2 lượt follow (chính là follow bản thân 2 anchor rỗng đó) và phải nhả quyền cho Mode 1 bù.

---

## 3. Kiến Trúc Sửa Đổi Chuẩn (Architectural Fix)

### 1. Khóa Cứng Budget Phiên (Single Source of Truth Quota):
Thêm phương thức `effective_session_budget()` trên `FollowEngine`:
```python
self._effective_session_budget: int | None = None

def effective_session_budget(self) -> int:
    """Resolve and lock the random session budget once for the entire session.

    Guarantees Mode 2 and Mode 1 (fallback) share the EXACT same session quota
    without re-rolling random numbers mid-session.
    """
    if getattr(self, "_effective_session_budget", None) is not None:
        return self._effective_session_budget
    if self.state is None:
        budget = int(getattr(self.cfg, "budget_per_session", 20))
    else:
        budget = self.state.session_budget(
            getattr(self, "video_count", None),
            getattr(self, "account_age_days", None),
        )
    self._effective_session_budget = budget
    return budget
```
- Cả `run_mode2()`, điều kiện fallback `rem_budget` trên engine, và `run_mode1()` đều đọc quota từ `engine.effective_session_budget()`.
- Quota chỉ bốc ngẫu nhiên đúng 1 lần khi phiên bắt đầu; Mode 1 bù chuẩn xác $100\%$ lượng follow còn thiếu:
  `rem_budget = effective_session_budget() - len(res.followed)`

### 2. Tinh Chỉnh Soft Deadline Buffer Của Mode 1:
- Hạ `reserve_seconds` trong vòng lặp Mode 1 từ `180.0`s xuống `90.0`s.
- 90 giây là biên độ an toàn lý tưởng: đủ cho 1 thao tác follow cuối + recovery + cleanup app về Home và in `FOLLOW_RESULT` JSON ra stdout trước hard deadline 1200s, đồng thời không ngắt sớm tiến trình bù của Mode 1.

### 3. Khử Bẫy Mỏ Neo Rỗng (Anchor Following Density Requirement):
- Khi chọn Anchor trong `anchor_uids()` hoặc khi Mode 2 duyệt danh sách:
  * Không thể chỉ dựa vào `account_row_index <= 2` vì nhiều nick Tik1/Tik2 mới hoặc ít follow chỉ có 0-4 following.
  * Cần sàng lọc mật độ Following của Anchor (yêu cầu Following >= 30 hoặc >= 50 từ snapshot/mapping), hoặc cơ chế Mode 2 phải tự nhận diện anchor có `following < 5` để skip nhanh mà không tính vào giới hạn 3 anchor (`uids[:3]`).

---

## 4. Quy Tắc Điều Phối Cho Coordinator (Non-Negotiable)

1. **Tách biệt hiện trường:** Khi User hỏi về tài khoản thành công/chạy ít, TUYỆT ĐỐI KHÔNG đem số liệu máy bị lỗi/nhả follow (`FOLLOW_FAILED`) ra làm bình phong.
2. **Kiểm tra State JSON:** Luôn đọc `last_budget_decision` trong `follow_state_<m>_row_<row>.json` để biết chính xác nick đó bị giới hạn bởi Dual Gate (`video_count < 10` $\rightarrow$ 3-5) hay do runner dừng sớm.
3. **Phân tích danh tính nick Mode 2 follow:** Khi `mode2_followed_count` là 1-2, phải kiểm tra ngay xem nick được follow có phải chính là bản thân Anchor hay không. Nếu chỉ follow đúng 2 Anchor thì 100% là dính bẫy Mỏ Neo Rỗng (Anchor có 0-4 following).
4. **Kiểm chứng Offline:** Sau khi patch, chạy test suite với Python chuẩn của automation env:
   `PYTHONPATH=. /d/Taadaa/python-envs/automation/Scripts/python -m pytest follow_runner/tests/test_follow_engine.py follow_runner/tests/test_follow_state.py follow_runner/tests/test_config.py`
