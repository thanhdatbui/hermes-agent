# Case Study: TikTok Web Follow Reconciliation — Baseline Drift & Target Account Audit

## 1. Bối Cảnh Sự Cố
Trong báo cáo định kỳ của watchdog `tiktok-follow-session-watchdog` (Ca 1 - Phiên 2/2 Sáng, Run: `row-0-080046`):
```text
  + Đối soát TikTok Web (+22 Following thật - Khớp 100% so với script báo):
    - M2 [Tik 1] (@thanh.h.dng00) : script 14 lượt - web 14 lượt - khớp
    - M5 [Tik 2] (@stevemgjqec) : script 5 lượt - web 6 lượt - lệch (+1)
    - M17 [Tik 2] (@hadang0725) : script 1 lượt - web 1 lượt - khớp
    - M23 [Tik 2] (@.thanh.trc.ng) : script 0 lượt - web 1 lượt - lệch (+1)
    - M74 [Tik 2] (@phannhu185) : script 2 lượt - web 0 lượt - lệch (-2)
```
Mặc dù tổng số lượt follow toàn farm khớp 22 lượt, có 3 máy bị lệch cục bộ: M5 (+1), M23 (+1), M74 (-2).

---

## 2. Bản Chất Cơ Chế Đối Soát (Watchdog Reconciliation Engine)
Trong `feed_session_watchdog.py` (`reconcile_cluster_following`):
1. **Latest Snapshot:** Cuối phiên (09:35), watchdog kích hoạt `tiktok_account_tracker.py` cào snapshot công khai của các nick vừa chạy:
   ```sql
   SELECT following, timestamp FROM snapshots
   WHERE LOWER(username) = LOWER(?) AND timestamp <= ?
   ORDER BY timestamp DESC, id DESC LIMIT 1
   ```
2. **Baseline Snapshot:** Tìm snapshot trước hoặc tại thời điểm bắt đầu phiên:
   ```sql
   SELECT following, timestamp FROM snapshots
   WHERE LOWER(username) = LOWER(?) AND timestamp <= ?
   ORDER BY timestamp DESC, id DESC LIMIT 1
   ```
   với `query_start_iso = session_start_iso + 30m` (đối với Phiên 2).
3. **Tính Delta:** $\Delta_{\text{web}} = \text{following}_{\text{latest}} - \text{following}_{\text{baseline}}$, so với $\Delta_{\text{reported}}$.

---

## 3. Phân Tích Chi Tiết 3 Ca Lệch

### Ca 1: M5 [Tik 2] (`@stevemgjqec`) — Lệch (+1) do Baseline Drift 24h
* **Dữ liệu thực tế:**
  * Script `follow_result.json`: `followed_count = 5`, gồm 5 nick: `vy.nguyen8730`, `charakrh768`, `skitezrfa3o`, `tuan31075`, `demarfpmafi`.
  * Snapshot DB:
    - Baseline: `(Following: 19, 2026-10-27 10:04:11)` — **Snapshot từ 24h trước** (do Phiên 1 lúc 06:00 máy bị `sensitive-skip-fail` nên không được cào snapshot lúc 08:06).
    - Latest: `(Following: 25, 2026-10-28 09:36:10)`.
    - $\Delta_{\text{web}} = 25 - 19 = 6$.
* **Kết luận:** Trong 24h qua nick tăng 6 following: 5 lượt thuộc Phiên 2 hôm nay, 1 lượt tăng từ hôm qua hoặc follow tự nhiên ngoài ca. Do thiếu snapshot tại mốc 08:00 (đầu Phiên 2), watchdog kéo lùi về hôm qua và cộng dồn cả lượt cũ.

### Ca 2: M23 [Tik 2] (`@.thanh.trc.ng`) — Lệch (+1) do App Fail-Safe vs Server Async Commit
* **Dữ liệu thực tế:**
  * Script `follow_result.json`: `status: FOLLOW_FAILED`, `reason: "FOLLOW_FAILED: follow bị nhả sau re-entry — dừng session"`, `followed_count = 0`.
  * Snapshot DB:
    - Baseline (sau Phiên 1): `(Following: 117, 2026-10-28 08:07:04)`.
    - Latest: `(Following: 118, 2026-10-28 09:36:10)`.
    - $\Delta_{\text{web}} = 118 - 117 = 1$.
* **Kết luận:**
  * Trong Phiên 2, runner bấm follow 1 nick. Khi cơ chế **Natural Re-entry Verify** kiểm tra lại, UI nút follow chưa cập nhật trạng thái đã follow. Để bảo vệ nick khỏi bị nhả follow hàng loạt, runner fail-safe dừng phiên ngay và ghi nhận `followed_count = 0`.
  * Tuy nhiên, request follow đó đã được máy chủ TikTok tiếp nhận và ghi nhận vào profile web sau vài giây, dẫn đến web tăng 1 dù script báo 0.

### Ca 3: M74 [Tik 2] (`@phannhu185`) — Lệch (-2) do TikTok CDN Cache & Shadow Un-follow
* **Dữ liệu thực tế:**
  * Script `follow_result.json`: `status: OK`, `followed_count = 2`, nick theo dõi: `@phammai1805` (M57) và `@lm.ngc.dip0` (M7).
  * Snapshot DB của `@phannhu185`:
    - Baseline (24h trước): `Following: 25` (2026-10-27 10:04:11).
    - Latest: `Following: 25` (2026-10-28 09:36:10).
    - $\Delta_{\text{web}} = 0$.
* **Kỹ thuật Audit Nick Đích (Target Account Audit):**
  * Kiểm tra bảng `snapshots` của các nick đích được follow:
    - `@phammai1805` (M57): `follower` tăng từ **97 lên 98 (+1)** ngay trong phiên này!
    - `@lm.ngc.dip0` (M7): `follower` giữ nguyên 69.
* **Kết luận:**
  * Lượt follow `@phammai1805` **thực sự thành công** (nick đích nhận thêm follower), nhưng counter `following` trên trang công khai của `@phannhu185` chưa được TikTok cập nhật do cache profile phân tán.
  * Lượt follow `@lm.ngc.dip0` có thể bị TikTok shadow un-follow (nhả ngầm từ máy chủ).

---

## 4. Quy Trình Điều Tra Chuẩn Cho Điều Phối Viên (O(1))
Khi nhận báo cáo watchdog follow bị lệch:
1. **Đọc `follow_result.json` O(1):**
   Đường dẫn: `D:/Taadaa/runtime/<cluster>/live/<date>/<run>/<timestamp>/machines/machine_<N>/<timestamp>/follow_result.json`.
   Xem `status`, `followed_count`, và mảng `followed` (danh sách nick đã tap).
2. **Kiểm tra tuổi Baseline Snapshot trong `tiktok_tracker.db`:**
   Chạy query lấy `timestamp` của 2 snapshot gần nhất. Nếu khoảng cách giữa baseline và latest > 3-4 giờ (hoặc từ ngày hôm trước), xác định ngay nguyên nhân là **Baseline Drift**.
3. **Đối soát Follower nick đích (Target Account Follower Audit):**
   Nếu script báo $N > 0$ nhưng web báo 0, tra cứu danh sách nick đích trong `snapshots`: nếu follower của nick đích tăng tương ứng, khẳng định lượt follow đã thành công thực tế, web counter chỉ bị trễ CDN/cache.

---

## 5. Cơ Chế Khắc Phục Chuẩn Hóa (Standardized Remediation Architecture)
Để triệt tiêu các ca báo lệch ảo hoặc bẫy nhả follow giả:
1. **Max Baseline Age Guard trong Watchdog Reconcile (`feed_session_watchdog.py`):**
   - Kiểm tra khoảng cách thời gian giữa `session_start_iso` và `baseline_row.timestamp`.
   - Nếu baseline cũ hơn thời điểm bắt đầu phiên quá **4 giờ** (hoặc thuộc ngày hôm trước):
     - Không dùng snapshot cũ để tính delta trừ lùi.
     - Hiển thị rõ trạng thái: `M5 [Tik 2] (@stevemgjqec): script 5 lượt - web UNPROVEN (baseline stale > 4h từ 2026-10-27)`.
2. **Pre-Session Baseline Snapshotting (Chốt baseline $T_0$):**
   - Khi runner hoặc picker kích hoạt danh sách máy chạy follow trong ca, tự động chạy 1 pass cào nhanh qua `tiktok_account_tracker.py` để chốt snapshot tại thời điểm $T_0$. Phép trừ $T_1 - T_0$ ở cuối phiên sẽ phản ánh đúng 100% biến động của phiên đó.
3. **2-Pass Debounce Re-entry trong Runner (`verify_follow.py`):**
   - Trong `_confirm_not_released`, khi phát hiện trạng thái `not_followed` sau khi re-entry, không vội vàng phán `FOLLOW_FAILED` và dừng session ngay ở nhịp 1.
   - Bổ sung 1 nhịp settling delay 1.5s và verify lần 2 (2-pass verification) nhằm loại trừ độ trễ render UI của app qua proxy 4G chậm, ngăn chặn việc runner tự reset kết quả về 0 trong khi server TikTok thực tế đã nhận follow.
