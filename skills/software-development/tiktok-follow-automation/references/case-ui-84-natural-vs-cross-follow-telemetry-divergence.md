# Case UI-84: Phân Kỳ Đo Lường Follow Tự Nhiên (30 Lượt) vs Follow Chéo (0 Lượt) — Bản Chất Dương Tính Giả Của Tương Tác Video Overlay (Optimistic UI) & Cơ Chế Xác Thực Server-Verified (2026-10-02)

## 1. Hiện Tượng & Câu Hỏi Vận Hành
Trong báo cáo watchdog Ca 2 (Row 4) ngày 02/10/2026:
- **Lướt Feed:** 68/80 máy thành công, 1.285 video lướt.
  - Ghi nhận: **Follow tự nhiên = 30 lượt / 1.285 video (2.3%)**.
- **Follow Chéo:** 0 lượt hoàn thành.
  - Ghi nhận: **Nhả follow liền (0 lượt) trên 38 máy**.
  - Lý do: `FOLLOW_FAILED: anchor @... bị nhả sau vuốt — dừng session`.
- **Thắc mắc:** Tại sao cùng trên một dàn máy và trong cùng một ca chạy, Follow chéo thì 100% thất bại (0 lượt), trong khi Follow tự nhiên vẫn báo thành công tới 30 lượt? Có phải Dual Gate bị hở hay bot bị lỗi logic?

---

## 2. Bản Chất Kỹ Thuật: 2 Khâu Khác Nhau Dẫn Đến Phân Kỳ

### A. Về Điều Kiện Gating (Dual Gate: Tuổi >= 21d & Video >= 6)
- **Row 8 (Ca sáng):** Toàn bộ nick mới tạo ngày 16/09/2026 (16 ngày tuổi < 21 ngày).
  - Cả follow chéo và follow tự nhiên đều bị khóa cứng (`budget = 0` và `_follow_rate = 0`) theo bản vá commit `c120f24`.
- **Row 4 (Ca chiều):** Toàn bộ nick đều là nick già:
  - Tạo từ tháng 2 đến tháng 8/2026 (tuổi từ 38 đến 112 ngày), số video đã đăng từ 8 đến 11 video (ví dụ: M2 38 ngày tuổi, 10 video; M9 95 ngày tuổi, 9 video; M29 112 ngày tuổi, 11 video).
  - Do đó, các nick Row 4 **hoàn toàn thỏa mãn cả 2 điều kiện Dual Gate**.
  - Cả 2 luồng (tự nhiên và chéo) đều được cấp quyền tương tác bình thường.

### B. Về Cơ Chế Đo Lường: Client Optimistic UI vs Server-Verified
Điểm khác biệt cốt tử nằm ở khâu xác thực sau khi bấm nút follow:

| Tiêu chí | Follow Chéo (`tiktok-follow`) | Follow Tự Nhiên (`tiktok-luot nuoi acc`) |
| :--- | :--- | :--- |
| **Vị trí tương tác** | Profile Anchor (Mode 2) hoặc Profile Nick target (Mode 1 / Path B). | Overlay video trên tab Đề xuất / Bạn bè (`_maybe_follow_video`). |
| **Hành vi sau khi tap** | Bắt buộc **Kéo vuốt làm mới trang Profile (Pull-to-refresh, sleep 3.5s)** để phá vỡ cache UI client. | **Không có bước reload**. Chỉ gửi lệnh `input tap x y` vào nút Follow trên video overlay. |
| **Phản hồi của TikTok khi bị Throttling** | App client đổi màu nút (Optimistic UI), nhưng khi vuốt reload trang, server TikTok trả về trạng thái thật: **Nút nhảy ngược lại màu đỏ (`not_followed`)**. | App client tự động ẩn dấu `+` đỏ hoặc chuyển nút sang "Đang follow" cục bộ. |
| **Phán quyết của Script** | Phát hiện ngay server không nhận -> Báo lỗi `FOLLOW_FAILED` và dừng phiên ngay lập tức để bảo vệ tài khoản (Fail-closed). | Thấy lệnh tap không lỗi -> Ghi nhận ngay `result="success"`, tăng counter `follow_counts["for-you"]`. |
| **Bản chất số liệu** | **Số liệu thật 100%**: Server không nhận thì báo 0. | **Dương tính giả (False Positive) 100%**: App hiển thị ảo nhưng server TikTok đã shadow-revert. |

---

## 3. Thực Nghiệm Bằng Chứng Đối Soát Dữ Liệu (`tiktok_tracker.db`)

Để chứng minh 30 lượt follow tự nhiên hoàn toàn không hề được server TikTok ghi nhận:
- Trích xuất bảng `snapshots` từ `D:/Taadaa/data/tiktok_tracker.db` (dữ liệu cào độc lập qua Web scraper trước và sau ca chạy):
  - **M2 (`@lieuhoan03`):** Script feed ghi nhận `follow_counts["for-you"]: 1`. Nhưng snapshot lúc 07:03 là `following = 1`, sau ca chạy lúc 13:11 snapshot vẫn là `following = 1` (tăng +0).
  - **M14 (`@cjalves19`):** Script feed ghi nhận `follow_counts["for-you"]: 2`. Snapshot lúc 07:03 và 13:11 đều giữ nguyên `following = 1` (tăng +0).
  - **M22, M25, M27, M29, M39, M41, M45...:** Toàn bộ các nick báo có lượt follow tự nhiên đều có số following trên TikTok Web tăng **+0**.
- **Ý nghĩa:** Khi thiết bị hoặc dải IP bị dính hạn mức vận tốc (Device Action Throttling theo Case UI-83), mọi lượt follow phát sinh từ màn hình video đều bị TikTok âm thầm hủy bỏ (shadow-drop) mà không có bất kỳ thông báo lỗi nào trên giao diện app.

---

## 4. Lỗ Hổng Mặt Nạ Đối Soát Của Watchdog (Reconciliation Masking Defect)

### A. Nghịch Lý Báo Cáo ("Khớp 100%" Dù Lệch 30 Lượt)
Trong báo cáo watchdog Ca 2:
- Dòng trên: `+ Follow tự nhiên: 30 lượt / 1285 video (2.3%)`
- Dòng dưới: `• Follow chéo (0 lượt follow)`
- Dòng đối soát: `+ Đối soát TikTok Web (+0 Following thật - Khớp 100% so với script báo)`

Bất kỳ người vận hành nào đọc vào cũng sẽ thấy mâu thuẫn: **Script vừa bảo có 30 follow tự nhiên, web tăng 0, tại sao lại kết luận là "Khớp 100% so với script báo"? 30 lượt follow tự nhiên biến đi đâu?**

### B. Cơ Chế Lỗi Trong Code (`scripts/feed_session_watchdog.py`)
Nguyên nhân xuất phát từ logic xử lý trừ hao máy lỗi trong hàm `reconcile_cluster_following`:
```python
failed = bool((all_follows.get(m) or {}).get("follow_failed"))
# A machine that failed/released its follows must not create a
# negative web reconciliation delta from stale reported claims.
m_to_reported[str(m)] = 0 if failed else cnt + natural_cnt
```
1. Mục đích ban đầu: Khi một máy bị nhả follow ở luồng follow chéo (`follow_failed = True`), runner kết thúc với 0 lượt follow chéo (`cnt = 0`). Để tránh tính sai, code đặt `m_to_reported = 0`.
2. **Hệ quả ngoài ý muốn (Defect):** Phép gán `0 if failed else cnt + natural_cnt` đã **vô tình xóa sổ luôn cả `natural_cnt` (30 lượt follow tự nhiên)**!
3. Watchdog tính: `expected_delta = m_to_reported[m] = 0`.
4. Web cào về: `web_delta = 0`.
5. Độ lệch: `diff = web_delta - expected_delta = 0 - 0 = 0`!
6. Kết quả: Watchdog thấy `diff == 0` nên kết luận:
   `+ Đối soát TikTok Web (+0 Following thật - Khớp 100% so với script báo)`!
   Nó đã che giấu (mask) hoàn toàn việc 30 lượt follow tự nhiên bị TikTok drop sạch.

---

## 5. Quy Tắc Vận Hành & Khuyến Nghị

1. **Hiểu Đúng Bản Chất Báo Cáo:**
   - Khi thấy Follow chéo bị nhả hàng loạt (nhả chùm cùng máy do cờ thiết bị/IP) mà mục Follow tự nhiên vẫn có số nhảy (ví dụ 10–30 lượt), **KHÔNG ĐƯỢC ngộ nhận là follow tự nhiên vẫn hoạt động tốt còn follow chéo bị lỗi**.
   - Đó là do Follow chéo có cơ chế kiểm chứng chặt chẽ (Pull-to-refresh phá cache) nên đã phát hiện và chặn đứng kịp thời; còn Follow tự nhiên chỉ đang đếm số lần tap client trên video.
2. **Kỷ Luật Bóc Tách Khi Đọc Đối Soát Web:**
   - Khi thấy dòng trên có `Follow tự nhiên: N lượt` mà dòng đối soát web lại báo `+0 Following thật - Khớp 100%`:
   - Phải nhận diện ngay: Toàn bộ N lượt follow tự nhiên đó là **Ghost Follows (bị TikTok shadow-drop sạch, +0 trên web)**.
   - Chữ "Khớp 100%" ở đây là do Watchdog bị lỗi mặt nạ (zero hóa `expected_delta` khi follow chéo fail), chứ không phải tài khoản đã tăng được follow trên server.
3. **Định Hướng Khắc Phục Code Watchdog (Đã chuẩn hóa tại Case UI-88):**
   - Khi pha follow chéo phát hiện `failed = True` (bị nhả follow), điều đó chứng minh nick/máy đã dính Silent Action Block từ server TikTok.
   - Toàn bộ các lượt follow tự nhiên phát sinh từ pha nuôi feed trước đó trên nick này cũng bị server drop sạch (Ghost Follows).
   - Watchdog BẮT BUỘC tự động khấu trừ các lượt follow tự nhiên của các nick bị nhả ra khỏi tổng số follow tự nhiên hợp lệ (`valid_tot_nat = tot_nat_follows - dropped_tot_nat`), hiển thị chú thích `(Đã tự trừ X lượt do nick bị nhả/drop)` trên Telegram và chỉ lưu số đã khấu trừ vào database `session_action_stats` (Chi tiết xem `references/case-ui-88-auto-deduct-natural-follows-on-released-accounts.md`).
4. **Định Hướng Kiến Trúc Tương Lai Cho Follow Tự Nhiên:**
   - Nếu muốn triệt tiêu dương tính giả ở luồng nuôi feed: Trong các phiên có nghi vấn drop follow, sau khi kết thúc ca lướt feed, script có thể đọc số following trên Profile thật của chính nick đó (`ui.xml` profile header) để đối chiếu delta thay vì chỉ đếm số lần tap video overlay.

---

## 6. Chu Kỳ Cooldown Tương Hỗ: Follow Chéo Bị Nhả Thì Ngày Sau Chạy Lại Follow Tự Nhiên Có Tự Động Bỏ Qua Không?

### A. Cơ Chế Liên Kết Giữa 2 Repo (`tiktok-follow` ↔ `tiktok-luot nuoi acc`)
- Khi Follow chéo phát hiện TikTok nhả follow (ở hàm `_ensure_anchor_followed`), nó gọi `state.set_follow_failed()`, ghi trạng thái vào file `D:/Taadaa/tiktok-follow/runs/state/follow_state_{machine}_row_{row}.json`:
  - `follow_failed = True`
  - `cooldown_until_at = <ISO timestamp UTC>`
  - `cooldown_until_date = <YYYY-MM-DD local>`
- Ở luồng Nuôi Feed (`feed_swipe_smoke.py`), hàm `_maybe_follow_video` **bắt buộc kiểm tra chốt chặn Cooldown đầu tiên**:
  ```python
  if is_account_in_follow_cooldown(ctx):
      ctx.logger.log(
          step="swipe_after/follow",
          action="follow_video",
          result="skipped",
          error="account is in follow cooldown (imprisoned)",
      )
      return False
  ```
  Hàm `is_account_in_follow_cooldown` đọc trực tiếp file state của chính nick đó (`follow_state_{m}_row_{r}.json`). Nếu `now < cooldown_until_at` hoặc `today <= cooldown_until_date`, lệnh tap follow trên video bị hủy bỏ ngay lập tức.

### B. Hành Vi Vận Hành Các Ngày Kế Tiếp Theo Rule Streak Mới (Case UI-83)
- Theo quy tắc Progressive Backoff Cooldown (3-5-7 ngày):
  - **Streak 1 (Lần đầu bị nhả):** Tự động khóa nghỉ **3 ngày** liên tiếp.
  - **Streak 2 (2 cữ liên tiếp bị nhả):** Tự động khóa nghỉ **5 ngày**.
  - **Streak >= 3 (Tái phạm nhiều lần):** Tự động khóa nghỉ **7 ngày (1 tuần)**.
- **Trong suốt 3 đến 7 ngày này, khi máy chạy lại ca nuôi:**
  1. Máy **vẫn mở app, lướt feed 15–20 video, xem đủ thời lượng và thả tim bình thường** để nuôi dưỡng sinh (làm ấm tài khoản và hạ điểm nghi vấn của thiết bị).
  2. Khi lướt feed: **Follow tự nhiên = 0 lượt** (tự động skip do `is_account_in_follow_cooldown`).
  3. Hết phiên feed: **Follow chéo = Bỏ qua an toàn** (`status: skipped, reason: follow-released-daily-cooldown`).

### C. Vì Sao Ca Đầu Tiên Vẫn Lòi Ra 30 Lượt Follow Tự Nhiên?
- **Thứ tự thực thi trong 1 phiên:** App mở lên -> **Lướt feed (kèm follow tự nhiên) chạy TRƯỚC** -> Hết feed mới gọi subprocess **Follow chéo chạy SAU**.
- Lúc đầu phiên, nick chưa có án phạt trong file state nên vẫn roll trúng follow tự nhiên khi lướt feed.
- Đến cuối phiên, khi Follow chéo chạy vào kiểm tra mới phát hiện server TikTok nuốt/nhả follow và **chính thức đóng dấu phạt (`set_follow_failed`)**.
- ➔ **Kể từ thời điểm đó trở đi (các ca tiếp theo và 3 đến 7 ngày tới): 100% các nick này khi chạy lại sẽ TỰ ĐỘNG BỎ QUA cả follow tự nhiên lẫn follow chéo!**
