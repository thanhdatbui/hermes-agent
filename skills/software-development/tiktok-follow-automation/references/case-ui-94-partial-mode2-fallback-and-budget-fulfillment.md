# Case UI-94: Partial Mode 2 Follow Fallback and Session Budget Fulfillment

## Context & User Correction

Previously (Case UI-93), `follow_engine.py` only triggered fallback to Mode 1 when Mode 2 resulted in exactly 0 follows (`len(res.mode2_followed) == 0`).
If Mode 2 followed a partial number of accounts (e.g. 4, 7, 12 follows) and then exhausted the 3 scanned anchors (or idle scroll reached limit) without filling the session's random budget (e.g. target 15-20), the engine prematurely halted the session.
The user corrected this assumption:
> "Cạn anchor là sao, cạn thì qua module 1 chạy cho đủ chứ? Chưa kể trong anchor toàn trên cả trăm follow k lẽ lướt cả cái tab following của anchor cũng k đủ"
> "Sửa đi. Budget thì ngẫu nhiên trong khoảng mỗi phiên r"

## Architectural Contract

1. **Partial Fallback Calculation:**
   Mode 2 fallback to Mode 1 must be governed by remaining session budget, NOT by a zero-count check:
   ```python
   rem_budget = (
       max(0, min(self.state.session_budget(getattr(self, "video_count", None), getattr(self, "account_age_days", None)), self.state.budget_remaining()) - len(res.followed))
       if self.state is not None
       else max(0, int(getattr(self.cfg, "budget_per_session", 20)) - len(res.followed))
   )
   if mode == "2" and rem_budget > 0 and not res.follow_failed:
       res.details["mode2_fallback_to_mode1"] = True
       res.details["mode2_fallback_reason"] = "anchors_exhausted" if len(res.mode2_followed) == 0 else "budget_unfilled"
       mode = "both"
   ```

2. **Safety Invariant Preserved:**
   - Fallback is strictly guarded by `not res.follow_failed` and `not self.state.follow_failed`.
   - If TikTok rejects/releases a follow (`FOLLOW_FAILED`), the session terminates immediately into cooldown; no fallback is permitted.

3. **Distinguishing "Cạn Anchor" in Reports:**
   - "Cạn anchor" trong Mode 2 không có nghĩa là tài khoản anchor hết sạch following trên TikTok, mà là trong phạm vi 3 anchor được chọn ngẫu nhiên ($\le 40$ scrolls/anchor), hệ thống không tìm thấy thêm UID nội bộ nào thuộc farm (`taikhoan_run_safe.xlsx`) chưa follow.
   - Khi Mode 2 kết thúc dở dang, Module 1 phải kích hoạt để tìm UID nội bộ trực tiếp qua Search, bù đủ ngân sách ngẫu nhiên của phiên.

4. **Bẫy `feed_timeout_seconds` vs `has_time_for_next_action` (Reserve Deadline Trap):**
   - Trước khi thực thi Module 1 sau Mode 2, `follow_engine.py` kiểm tra deadline bảo vệ:
     `has_time_for_next_action(reserve_seconds=120.0)`
     Tức là thời gian phiên còn lại (`feed_timeout_seconds - elapsed`) bắt buộc phải $> 120$ giây.
   - **Cạm bẫy:** Một số file config máy cũ (`config/machineXX.yaml`) để `feed_timeout_seconds: 90`. Do $90 \le 120$, điều kiện `has_time_for_next_action` LUÔN TRẢ VỀ FALSE ngay lập tức, khiến Module 1 bị bỏ qua êm ái (`skipping mode1 after mode2`) và không thể bù follow dù đã kích hoạt `mode2_fallback_to_mode1: true`.
   - **Khắc phục:** File config máy khi chạy follow bắt buộc đồng bộ `feed_timeout_seconds: 1200` (chuẩn 20 phút toàn farm theo `config.example.yaml`) hoặc tối thiểu $\ge 600$ giây để Module 1 có đủ quỹ thời gian mở search và follow bù.

5. **Anti-Pattern Báo Khống Canary Khi Zero Follow & Gửi Ảnh Màn Hình Home:**
   - **CẤM TUYỆT ĐỐI báo Canary PASS khi `followed_count == 0`:** Nếu mục tiêu canary là kiểm chứng follow hoặc fallback sang Module 1, việc exit code 0 với `mode1_followed_count: 0` là THẤT BẠI (starvation / no-op), cấm tuyệt đối thấy exit 0 mà vội báo thành công.
   - **CẤM GỬI ẢNH LAUNCHER HOME LÀM BẰNG CHỨNG:** Ảnh nghiệm thu BẮT BUỘC chụp trên màn hình TikTok thực tế (lúc đang ở Search, Profile, hoặc tab Following) TRƯỚC KHI teardown/đóng app. Gửi ảnh màn hình Home Launcher sau khi app đã đóng là vi phạm nghiêm trọng và hoàn toàn vô giá trị.
   - **Cạm bẫy Identity Switcher khi chạy Canary độc lập:**
     - Trong pipeline thật (`multi_machine_feed_session.py`), feed runner cha đã switch account từ trước nên luôn truyền `--skip-identity-verify`.
     - Khi chạy CLI độc lập `run_follow.py`, nếu không truyền `--skip-identity-verify`, runner sẽ cố mở Account Switcher để đối soát. Trên máy S7 chậm/lag, việc này dễ dính race condition với SplashActivity dẫn đến `VERIFY_IDENTITY fail`.
     - Để kiểm chứng hook/module follow độc lập, ưu tiên dùng `--canary-hook nav_search` kèm `--canary-screencap`, hoặc nếu tài khoản trên máy đã đúng thì thêm `--skip-identity-verify` để tránh gây nghẽn tại bước switcher.

## Unit Testing Requirement

Every fallback transition must be validated with offline unit tests in `test_follow_engine.py`:
1. `test_follow_engine_mode2_only_falls_back_to_mode1_when_anchors_exhausted`: Mode 2 có 0 follow $\rightarrow$ fallback với reason `anchors_exhausted`.
2. `test_follow_engine_mode2_partial_follow_falls_back_to_mode1_to_fulfill_budget`: Mode 2 có $N > 0$ follow nhưng chưa đủ budget $\rightarrow$ fallback với reason `budget_unfilled`, Module 1 tiếp tục follow $M$ lượt tiếp theo.
3. `test_follow_engine_mode2_does_not_fallback_when_budget_fulfilled`: Mode 2 đã đạt đủ quota phiên $\rightarrow$ không gọi Module 1.
