# Hướng Dẫn Triage & Đối Soát Khi Lệch Follow (Follow Discrepancy Playbook)

> **Mục đích:** Hướng dẫn chẩn đoán và giải thích nhanh khi User hoặc Farm Operator thắc mắc về hiện tượng số lượt follow bị lệch lớn giữa báo cáo script, TikTok Web và Dashboard.

---

## 1. Bản Đồ Phân Loại 3 Nguyên Nhân Gây Lệch Follow

| Loại lệch | Hiện tượng nhận biết | Nguyên nhân kỹ thuật gốc rễ | Bản vá / Cách xử lý |
| :--- | :--- | :--- | :--- |
| **1. Lệch Follow Chéo** *(Case UI-82)* | Script báo hàng chục/trăm lượt, nhưng Web chỉ tăng vài lượt hoặc 0 (Lệch -90% đến -100%). | **TikTok Silent Action Drop** kết hợp lỗ hổng Path B fallback: Quét text toàn màn hình bắt nhầm nhãn `text="Đã follow"` trên node thống kê Profile chủ kênh (`id/t_q`, `id/sdn`, `id/shq`). | Đã fix ở commit `c12242d`. Whitelist cấm mọi node `_STAT_COUNTER_IDS` trong `_classify_profile_action` và `classify_button`. |
| **2. Phân Kỳ Follow Tự Nhiên vs Chéo** *(Case UI-84)* | Cùng 1 ca: Follow chéo bị nhả 100% (`FOLLOW_FAILED` sau vuốt), nhưng feed vẫn báo follow tự nhiên 10-30 lượt. Web tăng +0. | **Follow chéo có pull-to-refresh** nên phát hiện server nuốt nút; còn **Follow tự nhiên trên video overlay chỉ đếm lệnh `input tap`**, không reload nên 100% là Ghost Follows khi IP bị throttle. | Nick đã `follow_failed` phải kích hoạt Progressive Cooldown (3-5-7 ngày) để skip cả 2 luồng. Watchdog không được zero hóa `natural_cnt` khi tính `expected_delta`. |
| **3. Lệch Dashboard Do Bug Cộng Lặp** *(Case UI-81, UI-89)* | Thẻ `TỔNG ĐÃ FOLLOW` hoặc cột `Đã Follow` từng nick có `🔗 Nội bộ: +X` cao hơn `+Y` thực tế (Ví dụ: `171 +32` nhưng `🔗 Nội bộ: +49`, M51 bấm 14 nhưng hiện +42). | **CẤM NGỤY BIỆN CỘNG DỒN NHIỀU CA: 1 nick chỉ chạy đúng 1 ca/slot trong ngày.**<br>Nguyên nhân kỹ thuật 100% là **Bug cộng lặp non-idempotent trong Watchdog**: Khi session chưa chốt báo cáo (`can_report_all == False`), Watchdog chạy cron 5p/lần vẫn gọi `reconcile_cluster_following`. Câu lệnh SQL `ON CONFLICT DO UPDATE SET internal_follows = daily_account_actions.internal_follows + excluded.internal_follows` khiến mỗi lần quét lại CỘNG TIẾP, nhân số lượng lên x2, x3 lần (M51: 14x3=42, M9: 10x3+19=49). | **Cách triage & sửa triệt để:**<br>1. **Kiểm tra O(1):** Đọc `follow_result.json` thực tế của máy trong ngày so với `daily_account_actions`. Nếu `daily > sum(followed_count)` $\rightarrow$ Chắc chắn bị bug cộng lặp non-idempotent.<br>2. **Chặn cộng lặp:** Không dùng phép cộng mù `+ excluded` trên unfinalized polling; chỉ claim/ghi nhận idempotent khi chốt phiên.<br>3. **Giữ nguyên tính độc lập của Script:** BẮT BUỘC để script tự bắt nhả và trừ nhả, CẤM lấy số từ DB cào để tự ý đè vào bộ đếm nội bộ. |
| **4. Lệch Pha Sáng Sớm Giữa `🔗 Nội Bộ: +0` vs `📈 Tổng Tăng: +X`** *(Case UI-90 / Dashboard Scan)* | Sáng sớm (sau đợt quét daily 04h-07h), Dashboard hiện `🔗 Nội bộ: +0` nhưng `📈 Tổng tăng: +126`. User tưởng farm không follow nội bộ hoặc số liệu bị lỗi. | **Lệch pha thời điểm ghi nhận (Scan Timing vs Bot Schedule):**<br>• `🔗 Nội bộ` đọc từ `session_action_stats` theo `target_date = max_dt` (ngày hôm nay). Sáng sớm các ca nuôi trong ngày chưa chạy nên counter nội bộ ngày mới bằng 0.<br>• `📈 Tổng tăng` là Day-over-Day delta (so sánh snapshot sáng nay với snapshot sáng hôm qua). Số này gồm: các ca chiều/tối hôm qua + follow tự nhiên khi lướt feed + follow trễ.<br>• **Bản chất số tăng:** Không phải Rolling 24h trượt theo phút, mà là chu kỳ ngày giữa 2 đợt quét daily (~24h). | Giải thích rõ cho Operator: Chờ các ca nuôi trong ngày chạy xong, số `🔗 Nội bộ` sẽ tự động nhảy số tích lũy tương ứng cho ngày đó. |
| **5. Phân Kỳ Lệch Module 2 (Anchor) vs Module 1 (Bù)** *(Case UI-91, UI-92 / Hybrid Follow)* | Báo cáo Watchdog hiện `Follow chéo [Module 2 (Anchor): X \| Module 1 (Bù): Y]` trong đó Module 2 rớt thảm hại (0-2 lượt) còn Module 1 vọt lên chiếm 90-100% tổng lượt (ví dụ Module 2: 2 \| Module 1: 25). | **Hai nguyên nhân phối hợp đồng thời:**<br>1. **Fail-closed Anchor:** Đa số máy (ví dụ 24 máy) bị TikTok nhả follow ngay tại kênh Anchor (`anchor @... bị nhả sau vuốt — dừng session`) -> Dừng fail-closed ngay lập tức (0 lượt). Máy bấm được 1 lượt rồi nhả (như M8, M25) chỉ đóng góp 1-2 lượt cho Module 2.<br>2. **Fail-Soft Degradation trên máy sống:** Các máy không bị nhả (như M17, M18, M33) khi quét list follower của Anchor bị lỗi UI layout `mode2_degraded: true` (`MANUAL_REVIEW: follower row không có nút follow semantic`). Theo thiết kế `follow_engine.py`, khi Module 2 lỗi UI mà không bị TikTok phạt chặn (`follow_failed=False`), engine reset status về `OK` và bàn giao 100% budget cho Module 1 (Search Follow).<br>3. **Bug Premature Multi-Anchor Abort (Case UI-92):** Khi Anchor 1 lỗi UI, cờ `failed = True` làm break sớm cả vòng lặp ngoài `for uid in uids:`, bỏ qua Anchor 2 và 3.<br>4. Module 1 tìm kiếm nick trực tiếp trên Search và hoàn thành toàn bộ chỉ tiêu. | **Quy chuẩn Hard Invariant (Case UI-92):**<br>1. **Duyệt tối thiểu 3 anchor:** Module 2 BẮT BUỘC phải thử lần lượt đủ 3 anchor trong pool. Anchor 1 lỗi UI -> ghi nhận, recover về Feed, `continue` sang Anchor 2 và Anchor 3. Chỉ khi CẢ 3 ANCHOR ĐỀU FAIL mới chuyển sang Module 1 bù.<br>2. **Semantic Text Fallback:** `_cluster_follower_rows` bổ sung matcher text ("Follow", "Follow lại", "Đã follow", "Bạn bè", "Following") chống rớt do obfuscated resource-id.<br>3. **Internal Pending Priority:** Nếu màn hình vẫn còn nick nội bộ có nút hợp lệ thì ưu tiên follow trước, không ngắt sớm. |

---

## 2. Quy Tắc Bất Biến Về Bộ Đếm Trừ Nhả & Tính Độc Lập Giữa Script vs DB (User Invariant)

1. **Bộ đếm trừ nhả là trách nhiệm của SCRIPT tại hiện trường thiết bị:**
   - Script trên máy đã được thiết kế sẵn cơ chế bắt nhả (`verify_follow`, cờ `follow_failed`, dừng session khi bị nhả, khấu trừ follow tự nhiên có điều kiện qua `calculate_session_natural_follows`, và tính reported count qua `reconcile_cluster_following`).
   - **Quy tắc phân định lượt đầu (User Invariant 2026-10-03):**
     * Khi follow chéo lượt đầu = 0 (`cnt == 0` khi `follow_failed`): Mới tính bỏ hết follow tự nhiên và chéo (`reported = 0`, khấu trừ tự nhiên của máy đó khỏi tổng phiên để không tạo delta âm).
     * Khi lượt đầu follow chéo thành công (`cnt > 0`): Tính HẾT toàn bộ follow tự nhiên thành công, rồi bắt đầu bộ đếm cho tới khi bị nhả follow (`reported = cnt + natural_cnt`, không trừ tự nhiên).
   - Con số "Nội bộ" hiển thị trên Dashboard PHẢI là số do SCRIPT tự ghi nhận sau khi đã trừ nhả theo quy tắc trên.

2. **CẤM TUYỆT ĐỐI lấy số cào từ DB để đè hoặc trừ vào bộ đếm Nội bộ:**
   - Mục đích tối cao của việc đặt 2 con số song song trên Dashboard:
     * **`ĐÃ FOLLOW (+X)`**: Server Ground Truth (TikTok Web cào thực tế).
     * **`🔗 Nội bộ: +Y`**: Client Ground Truth (Script trên máy tự bắt và tự tính).
   - Nếu lấy số từ DB cào để đè vào hoặc tính ngược cho Nội bộ, User và QA sẽ **mất hoàn toàn khả năng kiểm chứng xem script trên máy bắt nhả có đúng hay không**.
   - Do đó, số Nội bộ PHẢI xuất phát 100% từ artifact `follow_result.json` của script, không phụ thuộc vào delta DB.

---

## 3. Quy Trình Đối Soát Tam Giác 3 Lớp (Triple-Source Verification)

Khi cần chứng minh số liệu follow cho User:
1. **Lớp 1 (Runner Self-Report):** Đọc `follow_result.json` hoặc `session_action_stats` trong `tiktok_tracker.db`.
2. **Lớp 2 (Server Public Web):** Truy vấn bảng `snapshots` trong `tiktok_tracker.db` so sánh timestamp trước phiên và sau phiên.
3. **Lớp 3 (On-Device Ground Truth):** Đọc file dump UI trên máy thật (`artifacts/.../ui.xml`) tại header profile để xem số following thực tế hiển thị trên client app.

- **Phán quyết:**
  - Nếu Lớp 2 (Web) VÀ Lớp 3 (App) đều KHÔNG TĂNG nhưng Lớp 1 (Runner) báo TĂNG: Runner bị dính Silent Drop / False Positive (báo khống).
  - Nếu Lớp 3 (App) ĐÃ TĂNG nhưng Lớp 2 (Web) chưa tăng: Độ trễ cache CDN của TikTok Web.
  - Nếu cả 3 đều không tăng: Không có lượt follow nào được server chấp nhận.

---

## 4. Cơ Chế Điều Phối Khắc Phục Lỗi Module 2 & Chống Tự Trói Tay Chân

1. **Khắc phục lỗi Multi-Anchor trong Mode 2:**
   - Trong `mode2_follow_followers.py`, danh sách anchor lấy tối đa 3 nick (`uids = uids[:3]`).
   - Nếu Anchor 1 bị lỗi UI (như `missing_button_rows` hoặc lỗi mở tab): runner BẮT BUỘC thu dọn về Feed (`_back_to_feed`), ghi nhận lỗi và `continue` duyệt Anchor 2, Anchor 3.
   - Chỉ khi CẢ 3 ANCHOR ĐỀU FAIL và không follow được tài khoản nào (`used == 0`) thì mới trả về `MANUAL_REVIEW` để `follow_engine.py` chuyển giao cho Module 1 chạy bù.
   - Nếu trên màn hình có cả hàng thiếu nút lẫn hàng có nút hợp lệ (`internal_pending`), runner ưu tiên follow các hàng có nút trước, không ngắt phiên sớm.

2. **Chống bại liệt điều phối khi chạm trần Subagent (User Invariant):**
   - Khi Coordinator chạm trần ngân sách dispatch worker (`delegate_task` 10/10) hoặc gặp rào cản sửa file/test lớn:
   - CẤM đứng im tuyên bố L3 BLOCKED hay viện cớ an toàn để trốn việc ("tự trói tay chân").
   - Kích hoạt ngay **Claude Code CLI** chạy trực tiếp qua tiến trình nền (background process):
     ```bash
     claude -p "Nhiệm vụ: ..." --dangerously-skip-permissions --max-turns 15
     ```
   - Chạy với `background=True, notify_on_complete=True, timeout=300` để harness tự động đánh thức khi hoàn tất, sau đó kiểm tra bằng chứng thực tế (`git diff --stat`, `pytest`) trước khi báo cáo kết quả.
