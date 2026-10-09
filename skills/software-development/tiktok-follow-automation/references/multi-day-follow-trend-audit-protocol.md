# Quy Trình Đối Soát & Báo Cáo Follow Chéo Đa Ngày (Multi-Day Trend Audit)

## 1. Nguyên Tắc Cốt Lõi: Định Nghĩa "Gần Đây" (Recently)
- Khi User hỏi "kiểm tra tình hình follow chéo gần đây", **CẤM TUYỆT ĐỐI** chỉ báo cáo trong 1 ngày hoặc 24h gần nhất.
- "Gần đây" **bắt buộc** là bức tranh toàn cảnh đa ngày (**7 đến 14 ngày qua**), phân tách thành các giai đoạn / chu kỳ rõ ràng:
  1. **Giai đoạn khởi động / vận hành bình thường:** Nhịp follow ban đầu, số lượng máy tham gia.
  2. **Giai đoạn cao điểm & va chạm thuật toán:** Thời điểm TikTok kích hoạt Action Throttling / Silent Drop, số máy bị nhả follow, các bản vá selector/telemetry tương ứng (như Case UI-82, UI-84).
  3. **Giai đoạn phân hóa hiện tại:** Phân tách rõ rệt 3 nhóm tài khoản:
     - **Nhóm nick già (Row 1 / Row 2):** Đủ trust score, cắn follow đều đặn, gánh sản lượng chính.
     - **Nhóm nick trung (Row 3 / Row 4 / Row 5):** Đang chịu đợt siết Cooldown lũy tiến 3-5-7 ngày.
     - **Nhóm nick non (Row 7 / Row 8):** Bị chặn an toàn bởi Dual Gate (`age >= 21d` & `video >= 6`), 0 lượt bấm.

---

## 2. Phương Pháp Trích Xuất Dữ Liệu O(1) Nhanh Chóng (Không Cần Quét Đĩa Hay Viết Script Nặng)

Để tránh timeout và không phụ thuộc vào worker subagent hay terminal allowlist:
1. **Lịch sử tích lũy per-machine:**
   - Đọc trực tiếp các file state JSON tại `D:/Taadaa/tiktok-follow/runs/state/follow_state_<machine>_row_<row>.json`.
   - Các trường cốt lõi cần trích xuất:
     - `"followed"`: Danh sách `username: timestamp_iso` -> gom theo ngày để thấy sản lượng từng ca.
     - `"skipped"`: Các target bị skip do đã follow hoặc lỗi màn hình.
     - `"follow_failed"`: Cờ báo nick bị nhả follow.
     - `"fail_streak"` & `"cooldown_until_date"`: Trạng thái và thời hạn Cooldown (Streak 1: 3 ngày, Streak 2: 5 ngày, Streak 3+: 7 ngày).
2. **Báo cáo tổng hợp toàn farm mới nhất:**
   - Dùng `read_file` đọc thẳng `D:/Taadaa/reports/tiktok_tracker_report.xlsx` (công cụ tự động convert sang text).
   - Kiểm tra cột `Follower`, `Tăng Follow`, `Số Video`, `Avatar`, `Cắn Đề Xuất`.
3. **Nhịp vận hành chẵn / lẻ của Farm:**
   - **Ngày lẻ (01, 03, 05...):** Vận hành các hàng nick lẻ (**Row 1, Row 3, Row 5, Row 7**).
   - **Ngày chẵn (02, 04, 06...):** Vận hành các hàng nick chẵn (**Row 2, Row 4, Row 6, Row 8**).
   - Mỗi ngày chia 4 ca: Ca 1 (Sáng 06:00), Ca 2 (Trưa 12:00), Ca 3 (Tối 18:00), Ca 4 (Đêm 00:00).

---

## 3. Cấu Trúc Báo Cáo Chuẩn Cho User
1. **Bảng diễn biến qua các mốc thời gian:** Tóm tắt 3–4 giai đoạn biến động trong 7–14 ngày.
2. **Chi tiết từng nhóm tài khoản:** Số liệu các nick tăng trưởng tốt nhất, số lượng máy dính Cooldown và hạn mở lại.
3. **Các cải tiến / bản vá kỹ thuật đi kèm:** Báo cáo các cơ chế vừa triển khai (Khấu trừ follow tự nhiên, Idempotent staging, Dwell time 12-20s, lọc nhãn thống kê).
4. **Nhận định & Kế hoạch tiếp theo:** Thời điểm các đợt Cooldown kết thúc và lộ trình mở lại.

---

## 4. Cạm Bẫy Phân Tích Dữ Liệu Lịch Sử & Thiết Kế Sản Lượng (Pitfalls & Audit Traps)

### A. Cấm Nhầm Lẫn "Tổng Following Lũy Kế" vs "Sản Lượng Tăng Trong Tháng"
- **Cạm bẫy:** Lấy số Following hiện tại của nick già (ví dụ 250 – 380) rồi kết luận đó là số follow ăn được trong tháng vừa qua.
- **Quy tắc:**
  - Nếu không có baseline snapshot đầu tháng (T0 Web Scrape), **TUYỆT ĐỐI KHÔNG ĐOÁN MÒ SẢN LƯỢNG THÁNG CŨ**.
  - Dữ liệu log script trước ngày 02/10/2026 bị báo khống nặng nề do Optimistic UI + nhãn thống kê profile (`id/t_q`), hoàn toàn **KHÔNG ĐÁNG TIN**.
  - Chỉ công nhận số liệu sạch được đối soát 2 pha (Script khớp Web) từ ngày **02/10/2026 trở đi**.

### B. Đối Soát Tỉ Lệ Following Thực Tế vs Thiết Kế Chuẩn (`follow_state.py`)
- **Cấp độ nick riêng lẻ:**
  - Thiết kế: Nick già (`age > 30d` & `video >= 10`) được cấp `10–20 follow/phiên`, tối đa `40 follow/ngày` (`budget_per_day: 40`).
  - Thực tế: Các nick già sạch thoát nhả (M9, M16, M37, M39) chạy đúng chuẩn thiết kế (ăn 16–29 follow/ngày).
- **Cấp độ toàn ca (Tổng 80 máy):**
  - Lý thuyết: ~54 máy không dưỡng sinh $\times$ 15–20 follow $\rightarrow$ 800 – 1.000 follow/ca.
  - Thực tế hụt nặng (<10% lý thuyết, ~76–95 follow) do 4 nguyên nhân:
    1. Dưỡng sinh chiếm 36–45% (vượt trần 33%).
    2. TikTok siết nhả diện rộng (~40% máy bị nhả).
    3. Cơ chế Fail-Closed ngắt phiên ngay lượt đầu để bảo vệ nick già.
    4. Máy kẹt Cooldown 3–5–7 ngày từ các phiên trước.

### C. Cơ Chế Phạt Của TikTok: Phạt Theo Nick, KHÔNG Phạt All Nick Theo Máy
- **Bằng chứng thực nghiệm (03/10/2026):**
  - Cùng 1 máy Samsung S7 (ví dụ M9 hoặc M16):
    - Nick Row 1 (`age >= 210d, video >= 25`) chạy Ca 1 ăn 10–29 follow bình thường, `follow_failed: false`.
    - Nick Row 5 (`age ~39d, video ~6`) chạy Ca 3 trên chính máy đó bị nhả ngay anchor đầu tiên, `follow_failed: true`, đưa vào Cooldown 3 ngày.
- **Kết luận vận hành:**
  - TikTok phạt Action Restricting theo **Account Trust Score** của từng nick, **KHÔNG PHẠT THEO THIẾT BỊ (DEVICE BAN)**.
  - Nick hàng dưới (Row 3/Row 5) bị nhả **hoàn toàn không lây nhiễm án phạt sang nick già (Row 1/Row 2) nằm cùng trên máy**. CẤM hoang mang dừng chạy cả máy khi chỉ có 1 nick bị nhả.

### D. Cạm Bẫy Delta Following Ảo Trên Dashboard Do Mismatch Coverage (Smoothing Artifact)
- **Hiện tượng:** User thấy Dashboard báo tăng following (ví dụ +26) trong khi dàn nick đang bị khóa follow hoặc không có ca chạy nào từ nửa đêm.
- **Cơ chế gây ảo giác:**
  - Ngày hôm trước ($D_{-1}$) cào thiếu (ví dụ chỉ quét được 1.019 / 1.254 nick $\rightarrow$ tổng following ghi nhận 14.763, thiếu 235 nick có tổng 26 following tích lũy từ xưa).
  - Ngày hôm nay ($D_0$) đợt cào đang diễn ra dở dang (ví dụ mới cào 363 nick). Hàm `get_farm_history()` trong `tiktok_dashboard.py` kích hoạt fallback: thấy ngày hôm nay thiếu mẫu nên lấy tổng full farm 1.254 nick (14.789) đè vào để đồ thị không sụt.
  - Phép tính delta: $\Delta = 14.789 - 14.763 = \mathbf{+26}$ (bản chất là tổng following tích lũy của 235 nick bị quét sót hôm qua, không phải follow mới).
- **Quy trình Verify O(1) trong SQLite (`D:/Taadaa/data/tiktok_tracker.db`):**
  1. Kiểm tra event tăng following gần nhất:
     ```sql
     WITH Ranked AS (
         SELECT username, following, timestamp,
                ROW_NUMBER() OVER (PARTITION BY username ORDER BY timestamp DESC) as rn
         FROM snapshots WHERE status != 'ERROR'
     )
     SELECT r1.username, r2.following, r1.following, r1.timestamp
     FROM Ranked r1 JOIN Ranked r2 ON r1.username = r2.username AND r2.rn = 2
     WHERE r1.rn = 1 AND r1.following > r2.following
     ORDER BY r1.timestamp DESC LIMIT 5;
     ```
     Nếu timestamp mới nhất cách xa thời điểm nghi vấn (ví dụ từ hôm trước), khẳng định ngay: **0 nick nào đi follow ngầm**.
  2. Kiểm tra độ phủ mẫu giữa 2 ngày:
     `SELECT substr(timestamp,1,10) as dt, count(distinct username) FROM snapshots GROUP BY dt ORDER BY dt DESC LIMIT 2;`
  3. Tính tổng following của nhóm nick bị sót hôm trước:
     `WHERE username NOT IN (SELECT username FROM snapshots WHERE substr(timestamp,1,10) = 'hôm_trước')` $\rightarrow$ So khớp chính xác số $\Delta$ ảo.

### F. Phân Tích Trust Score & Nguyên Nhân Nhả Follow (xem `references/nick-trust-score-drop-analysis.md`)

Khi User hỏi "tại sao có nick không bị nhả, còn nick dễ bị nhả?", quy trình trả lời chuẩn:

1. **Quét toàn bộ state files** (không chỉ 7 ngày): phân loại `ever_failed` = `fail_streak > 0 OR last_failed_at OR last_cooldown_decision`.
2. **Tỷ lệ theo Row** — Row 1: ~84%, Row 2-3: ~95%, Row 4-8: 100%. Số video và follower KHÔNG phải yếu tố phân biệt trong cùng Row.
3. **Join với SQLite (`account_mapping` + `snapshots`)** để so sánh profile DB giữa nhóm sạch và nhóm bị nhả.
4. **3 nguyên nhân cốt lõi:** (a) Cadence / bão siết diện rộng, (b) Rolling Rate-Limit per account, (c) Thiếu organic feed depth.
5. **Post-cooldown recovery:** Nick già KHÔNG "ngọng" vĩnh viễn. Chu kỳ Cày 3–4 ngày → Nghỉ 3 ngày → Cày tiếp. Phiên đầu sau cooldown cấp 3–5 follow, sau đó reset về full budget nếu không bị nhả lại.

Chi tiết đầy đủ: `references/nick-trust-score-drop-analysis.md`

---

### G. Dual Gate Tuning — Khuyến Nghị Nâng Lên age≥30 & video≥10 (xem `references/dual-gate-tuning-age30-video10.md`)

Empirical evidence từ 06/10/2026:
- **185 quyết định** cấp budget cho nick `age <= 30 OR video < 10` → **182/185 (98.4%) bị nhả ngay** → đốt vía vô nghĩa.
- Nâng gate lên `age >= 30 AND video >= 10` sẽ block ~200 nick Row 5–8, giữ Row 3–4 còn đủ nguồn.
- Không nên merge "warmup mồi cho nick non" và "warmup hồi phục sau cooldown" vào cùng điều kiện.

Chi tiết diff đề xuất + anchor code: `references/dual-gate-tuning-age30-video10.md`

---

### E. Phân Tích Lịch Sử Nhả vs Khả Năng Hồi Phục Sau Cooldown (Drop History & Recovery Audit)
- **Bài toán:** Khi kiểm tra các nick đang đi follow được gần đây (7 ngày qua), xác định xem trước đó chúng có từng bị nhả follow không.
- **Phương pháp trích xuất O(1) từ `runs/state/follow_state_*.json`:**
  - Lọc các state file có timestamp trong dict `"followed"` nằm trong khoảng 7 ngày qua (`>= now_utc - timedelta(days=7)`).
  - Phân loại thành 2 nhóm dựa trên lịch sử lỗi:
    1. **Nhóm Sạch (Never Dropped):** `fail_streak == 0`, không có `last_failed_at`, `last_failed_date`, và `last_cooldown_decision is None`. Đây là nhóm core trust (ví dụ M9 R1, M16 R1, M17 R2, M18 R2, M39 R1) gánh sản lượng ổn định nhất farm.
    2. **Nhóm Từng Bị Nhả (Cooldown Cycle / Post-Cooldown):** Có `fail_streak > 0` hoặc có `last_failed_at`/`last_cooldown_decision`.
- **Đặc trưng vận hành thực tế:**
  - Phần lớn (~70%) số nick đang active tuần qua đều từng có lịch sử nhả ít nhất 1 lần.
  - Cơ chế lũy tiến (Streak 1: 3 ngày, Streak 2: 5 ngày, Streak 3+: 7 ngày) giúp tài khoản hồi phục Trust Score: sau khi mãn hạn cooldown, nick chuyển sang trạng thái `is_post_cooldown_warmup` và tiếp tục follow được các ca sau.
  - Cần chú ý mốc `cooldown_until_date` (so khớp với 17:00 UTC = 00:00 VN) để dự đoán nhóm nick sắp mãn hạn và tái gia nhập ca chạy tiếp theo.

---

### H. Bóc Tách 3 Nhóm Hành Vi Nhả Follow & Truy Vết Lịch Sử Hồi Phục (Recovery Audit)

Khi User hoặc Operator đặt câu hỏi: *"Các nick này có phải fl 1 cái bị nhả luôn không?"* hoặc *"Mấy nick này có lịch sử từng nhả rồi hồi phục chưa?"*:

1. **Tránh bẫy ngộ nhận "Tất cả đều fl 1 cái bị nhả luôn":**
   Báo cáo tổng kết session chỉ ghi `Nhả follow (N máy)` khiến người xem dễ tưởng cả N máy đều yếu ớt fail ngay lượt đầu. BẮT BUỘC tra cứu `follow_result.json` và `daily_account_actions` để phân loại chính xác 3 nhóm hành vi:
   - **Nhóm 1 — Đạt trần tải rồi mới nhả (Redline / Ceiling Drop):** Đã follow thành công nhiều lượt trong ca/ngày (ví dụ M39 ăn 14 follow Ca 1, 1 follow Ca 2 = 15 follow), đến lượt thứ 16 mới chạm trần rate-limit của TikTok và bị nhả. Đây là nick rất khỏe, nhả do chạm ngưỡng trần chứ không phải yếu.
   - **Nhóm 2 — Ăn vài follow rồi nhả (Mid-Session Drop):** Follow thành công 1–3 target (ví dụ M2, M52 ăn 1 target), sang target kế tiếp mới bị TikTok từ chối $\rightarrow$ fail-closed ngắt an toàn.
   - **Nhóm 3 — Nhả ngay anchor đầu (Immediate Drop):** Bấm target đầu tiên đã bị TikTok nuốt/nhả nút sau vuốt (ví dụ M1, M9, M14) $\rightarrow$ 0 lượt thành công.

2. **Quy trình truy vết lịch sử hồi phục của Nick Nòng Cốt:**
   - **Tại sao nick đang ở Nhóm Khỏe lại có `fail_streak = 1` mà không thấy lịch sử án tích cũ trong JSON?**
     Theo cơ chế `Graduated Probation Ladder`, khi nick vượt qua 6 ngày chạy sạch (`clean_days >= 6`) và tích lũy $\ge 15$ follow an toàn, hệ thống kích hoạt tốt nghiệp: gán `graduated = True`, xóa sạch `fail_streak = 0` và xóa trường `probation_clean_days` để cấp Full Quota. Do đó, state JSON hiện tại chỉ lưu trạng thái sau tốt nghiệp.
   - **Truy vết lịch sử đa tầng O(1) (CẤM quét đĩa diện rộng tránh trigger GUARD):**
     * **Tầng 1 (SQLite `tiktok_tracker.db`):** Chạy query `daily_account_actions` theo `may` và `username`. Nhìn vào chuỗi ngày hoạt động sẽ thấy rõ: giai đoạn cày follow $\rightarrow$ giai đoạn gián đoạn (Cooldown cách ly 3-5 ngày) $\rightarrow$ giai đoạn tái xuất hiện và cày tiếp hàng chục/hàng trăm follow.
     * **Tầng 2 (`runs/state/follow_state_<M>_row_<R>.json`):** Đọc dict `"followed"` để thống kê dải ngày active (`active_dates`), tổng follow tích lũy (ví dụ M2, M39 tích lũy 240 follows; M1 tích lũy 126 follows).
     * **Tầng 3 (`runtime/kibe/live/...`):** Đối soát log hiện trường các đợt sự cố lớn trong quá khứ (như đợt 19/08 verify profile nhả hàng loạt, đợt 03/09 nghẽn USB timeout).
   - **Kết luận bản chất:** Nick nòng cốt bị nhả không đồng nghĩa nick hỏng vĩnh viễn; hầu hết các nick trụ cột đều đã trải qua các chu kỳ: *Dính nhả $\rightarrow$ Cooldown 3 ngày $\rightarrow$ Hồi phục 1 (3-5) $\rightarrow$ Hồi phục 2 (7-9) $\rightarrow$ Tốt nghiệp nhóm Khỏe (Full Quota)*. Khi nhận Full Quota trong ngày TikTok siết thuật toán, việc chạm trần trust là bình thường và hệ thống tự động đưa lại vào chu kỳ hồi phục an toàn.

