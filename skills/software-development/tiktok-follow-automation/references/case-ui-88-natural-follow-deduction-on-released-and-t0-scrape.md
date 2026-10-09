# Case UI-88: Khấu Trừ Follow Tự Nhiên Khi Nick Bị Nhả Follow Chéo (Ghost Follow Deduct Contract) & Pre-Session T0 Scrape Truth (2026-10-03)

## 1. Bản Chất Quy Trình Thực Thi Farm
- **Dữ liệu Web được cào trước mỗi phiên (T0 Scrape):**
  - Trong `tiktok_runner.py`, ngay trước khi gọi subprocess chạy feed session, hệ thống luôn chạy lệnh:
    `python D:/Taadaa/tools/tiktok_account_tracker.py --usernames <uids> --workers 10` để chốt mốc Following $T_0$ sát giờ chạy.
  - Kết thúc phiên, watchdog cào mốc $T_1$ để lấy $\Delta = T_1 - T_0$. Do đó, đối soát Web là so sánh delta thực tế trước và sau phiên.

## 2. Nghịch Lý Phân Kỳ: Lướt Feed Chạy Trước, Follow Chéo Chạy Sau
- Trong 1 phiên nuôi:
  1. Máy mở app $\rightarrow$ **Lướt feed chạy trước**:
     - Bot tap follow trên video overlay $\rightarrow$ App đổi giao diện cục bộ (Optimistic UI) $\rightarrow$ Script feed ghi nhận `natural_follows`.
  2. **Follow chéo chạy sau**:
     - Bot vào profile Anchor kiểm tra và follow $\rightarrow$ Bắt buộc thực hiện thao tác kéo vuốt reload profile (Pull-to-refresh) phá cache.
     - Server TikTok trả về nút màu đỏ $\rightarrow$ Phát hiện nick bị chặn/nhả follow (`follow_failed = True` / `released`).
- **Hệ quả logic:**
  - Nếu ở bước follow chéo đã chứng minh server TikTok chặn/nhả follow trên nick đó (Action Block / Rate Limit), thì các lượt follow tự nhiên vừa tap ở video trước đó **chắc chắn cũng bị TikTok shadow-drop sạch (Ghost Follows)**.
  - Web TikTok cào sau phiên xác nhận `+0 Following thật`.

## 3. Contract Khấu Trừ Bắt Buộc Trong Watchdog (`feed_session_watchdog.py`)
- **Nguyên tắc phân định lượt đầu (User chỉ đạo 2026-10-03):**
  - **Lượt đầu follow chéo = 0 (`cnt == 0`)**: Nick bị chặn/nhả ngay từ đầu $\rightarrow$ bỏ hết follow tự nhiên và chéo (`reported = 0`, `dropped_tot` tăng), tránh tạo delta âm trên đối soát Web.
  - **Lượt đầu follow chéo thành công (`cnt > 0`)**: Nick vẫn sống bình thường trong suốt quá trình lướt tự nhiên và lượt đầu follow chéo $\rightarrow$ **tính hết 100% follow tự nhiên thành công** và đếm toàn bộ các lượt chéo bấm được cho tới khi bị nhả (`reported = cnt + natural_cnt`).

1. **Hàm tính toán độc lập `calculate_session_natural_follows`:**
   - Quét qua `all_machines` và `all_follows`.
   - Chỉ đưa vào danh sách drop (`released_machine_set`) nếu máy đó có `follow_failed = True` hoặc nằm trong `fl_released` **VÀ có số lượt follow chéo `cnt == 0`**:
     ```python
     for m in fl_released:
         f_data = all_follows.get(m) or all_follows.get(str(m)) or (all_follows.get(int(m)) if str(m).isdigit() else {})
         cnt = len(f_data.get("followed", [])) if isinstance(f_data, dict) else 0
         if cnt == 0:
             released_machine_set.add(str(m))
     ```
   - Tự động trừ số lượt follow tự nhiên (`for-you`, `following`, `friends`) của các máy trong `released_machine_set` ra khỏi tổng số hợp lệ.
   - Trả về `(valid_tot, valid_fy, valid_fl, valid_fr, dropped_tot)`.

2. **Hàm đối soát TikTok Web `reconcile_cluster_following`:**
   - Khi so sánh số báo cáo vs Web delta:
     ```python
     if failed and cnt == 0:
         m_to_reported[str(m)] = 0
         failed_reset_machines.append(str(m))
     else:
         m_to_reported[str(m)] = cnt + natural_cnt
     ```
   - Nếu `cnt > 0`, vẫn ghi nhận `daily_account_actions` cho các lượt chéo đã bấm thành công.
2. **Minh bạch Telemetry báo cáo:**
   - Nếu `dropped_tot > 0`:
     `+ Follow tự nhiên: X lượt / Y video (...) [Đề xuất: ... | Bạn bè: ...] (Đã tự trừ Z lượt do nick bị nhả/drop)`
3. **Làm sạch Database (`tiktok_tracker.db`):**
   - Chỉ lưu `valid_tot` vào `session_action_stats`, không lưu số counter tap mù chưa trừ để tránh làm bẩn dữ liệu lịch sử và Dashboard.

## 4. Nuance Phân Biệt: Nick Bị Nhả (FOLLOW_FAILED) vs Nick Bỏ Qua Follow Chéo (SKIPPED / Zero-Following)
- **Bản chất của `zero-following-skip-v2`:**
  - Không phải nick bị nhả hay lỗi script, mà là bot mở profile nick Anchor (mồi) trong Mode 2 nhưng phát hiện Anchor có 0 Following (`_is_zero_following_profile`). Danh sách rỗng nên bot skip an toàn, chưa từng bấm follow chéo cái nào (`followed: []`, `status: "OK"`, `follow_failed: false`).
- **Tình huống thực tế (Case M76):**
  - Máy lướt feed tap follow tự nhiên thành công (`natural_follows = 1`).
  - Đến bước follow chéo, máy không chạy hoặc bị bỏ qua hợp lệ (`status: "OK"`, `followed: []`, `follow_failed: false`, `mode2_zero_following_fix: "zero-following-skip-v2"`).
  - **Vì sao script vẫn giữ tự nhiên 1 dù chéo = 0:**
    - Watchdog chỉ khấu trừ `natural_follows` của các máy bị xác nhận nhả nick thật (`follow_failed is True` hoặc `status == "FOLLOW_FAILED"` kèm `cnt == 0`).
    - M76 không dính `follow_failed` (chỉ skip chéo hợp lệ), nên script vẫn bảo lưu 1 lượt follow tự nhiên đã tap trên feed.
  - **Hệ quả trên Đối soát Web:**
    - Nếu server TikTok âm thầm drop lượt follow tự nhiên đó trên feed mà không làm đổi số Following thật trên Web, Web delta sẽ là `+0`, dẫn tới báo lệch:
      `- M76 (@attet0870): script báo 1 (chéo 0, tự nhiên 1) | web tăng +0 (Lệch -1)`.
    - Đây là độ lệch giữa client tap telemetry và Web truth, không phải lỗi đếm follow chéo hay bug watchdog. Nếu sau này quy ước nghiệp vụ yêu cầu "hễ follow chéo = 0 thì khấu trừ toàn bộ follow tự nhiên bất kể lý do skip", contract của `calculate_session_natural_follows` mới cần mở rộng.

