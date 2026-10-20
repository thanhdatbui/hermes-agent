# Follow Dashboard Diagnostics & Health Ceiling Invariants

## 1. Dashboard Modal vs TikTok External Link Invariant
- **Vấn đề**: Người dùng bấm vào username tài khoản trong header "Sổ Bệnh Án" nhưng không bung ra kênh TikTok.
- **Nguyên nhân**: Trong `tools/dashboard/follow_detail_component.py`, danh sách các UID con được follow (`followed_list`) có gắn thẻ `<a href="https://www.tiktok.com/@${encodeURIComponent(item.uid)}" target="_blank">`. Tuy nhiên ở header modal (`fdModalTitle`), username `@username` lại được render dạng `<span style="color:#38bdf8;">` không có thẻ `<a>`, khiến nó chỉ đổi màu mà không thể click mở trang cá nhân.
- **Giải pháp chuẩn hóa**:
  * Tạo hàm helper `fdModalTitleHtml(username)`:
    ```javascript
    function fdModalTitleHtml(username) {
        if (!username || username === '-') return `📜 Sổ Bệnh Án: <span style="color:#38bdf8;">Chưa gán username</span>`;
        return `📜 Sổ Bệnh Án: <a href="https://www.tiktok.com/@${encodeURIComponent(username)}" target="_blank" rel="noopener" style="color:#38bdf8;text-decoration:none;">@${fdEsc(username)}</a>`;
    }
    ```
  * Áp dụng đồng bộ trong cả `loadFdDetail` (lúc bắt đầu nạp) và `renderFollowDetailModal` (sau khi có data API).

## 2. Cơ chế lưu và hiển thị "Gãy Gần Nhất" (Last Failed Ceiling)
- **Vấn đề**: Ở tab "Hồi phục 1" hoặc "Hồi phục 2", ô "Gãy Gần Nhất" thường hiển thị "Chưa từng" hoặc rỗng dù nick đang có `fail_streak > 0` và từng bị đưa vào cooldown.
- **Nguyên nhân cốt lõi trong code**:
  1. **Chỉ ghi nhận khi nick đã tốt nghiệp (`graduated`)**:
     Trong `tiktok-follow/follow_runner/core/follow_state.py` (hàm `set_follow_failed`), trường `last_failed_ceiling` chỉ được tính toán và lưu vào JSON khi nick đó có cờ `graduated: True` bị thu hồi (revoked):
     ```python
     if self._data.pop("graduated", None):
         failed_ceiling = attempted if attempted is not None else (used + 1)
         self._data["last_failed_ceiling"] = failed_ceiling
     ```
     Nếu tài khoản bị nhả khi đang ở diện Tân binh (rookie), Warmup, hoặc đang trong quá trình Hồi phục (probation clean days < 2), trường này không được ghi nhận trong file state JSON.
  2. **Giải pháp fallback mốc trần ca gãy (`follow_health_helper.py`)**:
     Trong `get_account_follow_detail(machine, row)`:
     ```python
     last_failed_ceiling = _to_int(d.get("last_failed_ceiling"))
     last_failed_date = d.get("last_failed_date") or (d.get("last_failed_at") or "")[:10] or None
     if not last_failed_date and isinstance(d.get("last_cooldown_decision"), dict):
         last_failed_date = (d["last_cooldown_decision"].get("decided_at") or "")[:10] or None
     if last_failed_ceiling is None and last_failed_date:
         last_b = d.get("last_budget_decision")
         if isinstance(last_b, dict) and last_b.get("budget") is not None:
             last_failed_ceiling = _to_int(last_b.get("budget"))
     ```
  3. **Hiển thị thông minh tại Frontend (`follow_detail_component.py`)**:
     ```javascript
     const hasCeiling = data.last_failed_ceiling !== null && data.last_failed_ceiling !== undefined && data.last_failed_ceiling !== '' && data.last_failed_ceiling !== '-';
     const failedDate = data.last_failed_date ? String(data.last_failed_date).slice(5) : '';
     let lastFailedText = 'Chưa từng (sạch)';
     if (hasCeiling) {
         lastFailedText = `${data.last_failed_ceiling} lượt` + (failedDate ? ` · ${failedDate}` : '');
     } else if (failedDate) {
         lastFailedText = `Gãy ${failedDate}`;
     } else if (data.fail_streak > 0) {
         lastFailedText = `Streak ${data.fail_streak}`;
     }
     document.getElementById('fdLastFailed').textContent = lastFailedText;
     ```

## 3. Bản chất 967 nick ở tab "Hồi phục 1" (Probation Tier 1)
- Trong `tools/follow_health_helper.py` (hàm `get_follow_health_data`):
  Hệ thống query toàn bộ tài khoản từ bảng `farm_account_info` trong `tiktok_tracker.db`. Các nick chưa từng chạy flow follow hoặc chưa có file `follow_state_<machine>_row_<row>.json` (khoảng 967 nick) sẽ được gán mặc định:
  ```python
  "tier": "probation_tier1",
  "tier_label": "🟠 Mới / Đang dưỡng",
  "fail_streak": 0
  ```
- Trên giao diện dashboard, nhóm `probation_tier1` được gán tab label là `🌱 Hồi phục 1`.
- Do phần lớn 967 nick này là nick mới hoặc đang dưỡng chưa chạy follow, fail streak = 0 và chưa từng bị fail, nên chỉ số "Gãy Gần Nhất" hiển thị "Chưa từng (sạch)" là hoàn toàn chính xác theo dữ liệu thực tế.

## 4. Quy trình nạp lại Dashboard sau khi sửa code UI/Helper
- Sau khi chỉnh sửa `dashboard/*.py` hoặc `follow_health_helper.py`, tiến trình dashboard trên port 1905 giữ template HTML cũ trong memory.
- Lệnh reload chuẩn:
  1. Dò và tắt PID cũ: `taskkill /PID <pid> /F`.
  2. Relaunch: `python D:/Taadaa/tools/tiktok_dashboard.py --port 1905` (hoặc qua hidden VBS).
  3. Kiểm chứng live:
     - `http://localhost:1905/api/follow-detail?machine=12&row=1`
     - Kiểm tra string `fdModalTitleHtml` và `lastFailedText` trong HTML root `/`.

## 5. Chuẩn Báo Cáo Tỷ Lệ Follow Theo Row (Recovered vs Healthy Cohort Triage)
Khi User yêu cầu báo cáo tình hình follow của một Row (ví dụ Row 1 theo chu kỳ Parity 4 ngày), **TUYỆT ĐỐI KHÔNG chỉ báo cáo số tổng follow macro** (như "127 follow, tăng 4%"). Bắt buộc phải phân tách 3 nhóm và trả về đúng tỷ lệ thực chiến:
1. **Nhóm Đang Trong Tù (Still in Jail Cooldown)**:
   - Các nick có `cooldown_until_date >= today` từ các đợt trước. Runner tự động skip, không phát sinh lệnh ADB.
2. **Nhóm Nick Phục Hồi (Recovered / Post-Cooldown Probation)**:
   - Các nick mãn hạn cooldown hoặc đang có `fail_streak > 0` quay lại cữ chạy.
   - Bắt buộc phân tích 3 kịch bản:
     * *Phục hồi sạch (Clean Success)*: Follow đủ quota warm-up (3-9 follow), không bị nhả, không tái phạm.
     * *Chạm trần nhả (Partial Follow then Released)*: Follow được 1-8 nick rồi bị TikTok chặn (`TikTok không nhận follow` hoặc `nhả sau vuốt`). Script dừng an toàn.
     * *Tái phạm nhả liền (Immediate Release - 0 follow)*: Bị TikTok nhả ngay nick đầu tiên. Chiếm tỷ lệ lớn ở nick trust yếu vừa ra tù.
3. **Nhóm Nick Khỏe Cựu Binh (Graduated Core Fleet)**:
   - Nick đã tốt nghiệp (`graduated == True`, `fail_streak == 0`), không dính án tích gần đây (như M12, M37).
   - Tỷ lệ thành công (thường đạt 100%), đóng vai trò đầu tàu gánh 30-50% tổng sản lượng cả Row.

## 6. Cơ Chế Dò Trần Động (Adaptive Probing Ceiling) & Bảo Hiểm Lùi 4 Sàn 15
Trong `follow_state.py`, runner tự động điều chỉnh trần follow cho các nick cựu binh khỏe theo thuật toán thích ứng:
- **Ngưỡng Trần Tuyệt Đối (`core_cap`) theo Cohort**:
  * `veteran` (Following > 100, Video > 25, Tuổi > 180 ngày): trần tối đa = **40 follow/ngày** (nâng từ 30 lên 40 theo lệnh Operator ngày 19/10/2026).
  * `mid`: trần tối đa = **22 follow/ngày**.
  * `rookie` (Following < 30 hoặc Video < 15 hoặc Tuổi < 60 ngày): trần tối đa = **16 follow/ngày**.
- **Cơ chế Dò Trần Tăng Động (`_roll_day()`)**:
  * Khi nick `graduated` hoàn thành cữ chạy sạch sẽ (`last_session_clean == True`, `follow_failed == False`) và số follow đạt $\ge base\_max$ (mặc định 15):
    $$proven\_safe\_ceiling = \min(40, \max(curr\_proven, prev\_used))$$
    $$active\_ceiling = \min(core\_cap, \max(0, proven\_safe\_ceiling + 2))$$
  * *Ví dụ thực tế*: Nick M37 đạt 25 follow sạch hôm nay $\rightarrow$ Mốc chứng minh `proven` nâng lên 25 $\rightarrow$ Kỳ tiếp theo tự động mở trần `active_ceiling` lên **27 follow** (`min(40, 25 + 2)`). Nếu tiếp tục sạch sẽ dò tiếp +2 mỗi kỳ lên kịch trần **40 follow**.
- **Cơ chế Bảo Hiểm Gãy (Lùi 4 Sàn 15)**:
  * Khi đang dò trần mà bị TikTok nhả nút:
    $$proven\_safe\_ceiling = \min(40, \max(0, \max(base\_max, curr\_proven - 4)))$$
  * Lùi ngay 4 nấc an toàn nhưng **khóa sàn không dưới 15**, thu hồi cờ `graduated`, đưa vào cooldown dưỡng sinh theo số lần tái phạm (Streak 1: 3 ngày, Streak 2: 5 ngày, Streak 3: 7 ngày, Streak $\ge 4$: 15 ngày).

## 7. Cơ Chế Hồi Phục 1 (Tier 1) vs Hồi Phục 2 (Tier 2) & Hiện Tượng Nhả Ở Lượt 7-8
- **Hồi phục 1 (Probation Tier 1 - `clean_days = 0`)**:
  * Áp dụng khi nick vừa hết hạn cooldown ra chạy cữ đầu tiên (chưa có ngày sạch nào tích lũy).
  * Ngân sách bị bóp nghẹt nghiêm ngặt: **2 – 5 follow/ngày** (Rookie/Mid trần 4, Veteran trần 5).
- **Hồi phục 2 (Probation Tier 2 - `clean_days = 1`)**:
  * Áp dụng khi nick ở cữ trước đã chạy follow sạch sẽ không bị nhả, qua ngày `_roll_day()` tự động tăng `probation_clean_days = 1`.
  * Ngân sách được nới rộng: **6 – 8 follow/ngày** (Veteran trần 9).
- **Tại sao nick hồi phục có nick follow được tới 8 lượt rồi mới bị nhả**:
  * Các nick như M29, M38, M39, M71, M16 đã có 1 ngày sạch từ kỳ trước (15/10) nên hôm nay (19/10) chạy ở **Tier 2**.
  * Ở **Phiên 1 (06:00)**: Nick chạy hoàn thành 6–7 follow sạch sẽ.
  * Ở **Phiên 2 (08:00)**: Hệ thống tính ngân sách còn lại trong ngày (`cap 8 - used 7 = 1 follow`), nick tiếp tục follow thêm 1 lượt nữa ➔ Đạt tổng **8 follow**.
  * Đến lượt tiếp theo (hoặc kiểm tra post-follow sau vuốt), nick chạm ngưỡng trần chịu đựng của tài khoản đang trong diện bị TikTok gắn cờ theo dõi ➔ TikTok kích hoạt Action Block (`TikTok không nhận follow` hoặc `nhả sau vuốt`).
  * Script phát hiện nhả nút lập tức ngắt phiên an toàn (`FOLLOW_FAILED`), thu hồi trạng thái thử thách và đưa nick vào chu kỳ cooldown tiếp theo.

## 8. Tử Huyệt Phiên 2 của Probation Tier 2 (Velocity Window & Quota Exhaustion)
- **Hiện tượng**: Nick M29, M38, M39 ở P1 chạy 6–7 follow sạch sẽ 100%. Sang P2 (cách 2h), nick vẫn bấm thành công 1 người, nhưng do script cấp `budget = 2, 3` để vét trần ngày 8–9 follow, nick bấm tiếp người thứ 2 thì chạm trần Quota tổng / Rate-limit của TikTok ➔ dính `FOLLOW_FAILED`, mất sạch `clean_days` và bị giam 3 ngày oan.
- **Nguyên nhân cốt lõi**: TikTok tính Quota trong cửa sổ trượt 24h kết hợp velocity. Khoảng nghỉ 2h giữa P1 (06:00) và P2 (08:00) quá ngắn. Với nick probation, quota TikTok cấp chỉ khoảng 7–8 follow/ngày. Sau P1, dư địa chỉ còn đúng 1 follow; nếu ráng vét lượt thứ 2 chắc chắn bị chặn.
- **Nguyên tắc bảo vệ**:
  * Mọi nick đang probation (Tier 1 và Tier 2) chỉ nên chạy ở Phiên 1 (06:00) với budget 5-6 follow rồi dừng luôn.
  * Nếu chạy P2, bắt buộc clamp `budget = min(remaining, 1)`, tuyệt đối không cấp `budget >= 2` ở P2.

## 9. Nguyên Lý Phân Tầng Cầu Dao IP (Tier-Aware Circuit Breaker)
- **Quy tắc**: Cầu dao IP (`trip_ip_breaker()`) CHỈ kích hoạt khi nick **ĐÃ TỐT NGHIỆP (Graduated / Cựu binh, `was_graduated == True`)** bị nhả follow.
- **Nick Probation bị nhả**: Bỏ qua cầu dao IP, chỉ phạt Cooldown tầng account (3–15 ngày).
- **Trạng thái Dashboard**: Dashboard báo `🛡️ IP Circuit Breaker: Active 100% - Tất cả các cổng proxy đều sạch sẽ` là hoàn toàn chính xác khi các nick bị nhả đều là probation/tân binh, đảm bảo không ngắt proxy oan làm giam nick khỏe 48 tiếng.

## 10. Quy Tắc Khóa Độc Quyền Phiên 1 Cho Hạng Hồi Phục (Probation Single-Session Cap Invariant)
- **Nghịch lý chia phiên**: Tổng daily quota của nick Tier 1 (3–4 follow) và Tier 2 (5–6 follow) thậm chí còn ít hơn một nửa của một phiên đơn lẻ của nick cựu binh (10–15 follow/phiên). Việc chia mỏng 5–6 follow thành 2 phiên (cách nhau 2 tiếng lúc 06:00 và 08:00) tạo ra pattern spammer nhân tạo: vừa bấm 4–5 follow lúc 06:00 lại thức giấc bấm tiếp 1 follow lúc 08:00, kích hoạt bot detection rate-limit của TikTok.
- **Cơ chế phân bổ Greedy Daily Quota (`budget_used`)**:
  - Script không chia tỷ lệ % cố định trước, mà chạy theo cơ chế "nuốt trần ngày": P1 cấp `random_target` từ `t2_range`. Nếu P1 bốc trúng số thấp (ví dụ 4-5), `budget_used = 4-5`, dẫn tới `remaining = cap - budget_used > 0` ➔ P2 bị ép lôi nick ra bấm nốt phần dư 1 lượt.
  - **Quy chuẩn Single-Session Lock**: Nếu `budget_used > 0` (P1 đã chạy có follow), hàm `_probation_budget()` tại P2 bắt buộc trả về `budget = 0`. Toàn bộ ngân sách Tier 1 (3–4 lượt) và Tier 2 (5–6 lượt) được dồn chạy 1 cữ duy nhất trong Phiên 1, sau đó cho nick nghỉ ngơi làm nguội, triệt tiêu hoàn toàn rủi ro bị nhả ở P2. P2 chỉ đóng vai trò dự phòng khi P1 bị offline hoặc lỗi mạng (`budget_used == 0`).

## 11. Cơ Chế Tính Toán Động Cho Tier 1 & Tier 2 (Né Mốc Gãy Cũ & Bóp Trần Theo Án Tích)
- **Vấn đề**: Trước đây Tier 1 (2–4 follow) và Tier 2 (5–6 follow) cấp theo dải ngẫu nhiên tĩnh, chưa bám sát lịch sử thất bại cá nhân của từng nick. Nếu một nick từng bị gãy ở mốc 3 lượt mà hệ thống random cấp 4 lượt, nick sẽ chạm trần cũ và bị phạt tù tiếp.
- **Giải pháp cơ giới hóa trong `_probation_budget()` (`follow_state.py`)**:
  1. *Ghi nhận `last_failed_ceiling` toàn diện*: Khi `set_follow_failed()` kích hoạt, lưu `failed_ceiling = attempted or (used + 1)` cho 100% tài khoản (thay vì chỉ lưu cho nick graduated bị thu hồi cờ như trước).
  2. *Né mốc gãy cũ (`last_failed_ceiling >= 2`)*:
     $$cap = \min(cap, \max(1, last\_failed\_ceiling - 1))$$
     Nick từng gãy ở mốc $N$ thì khi ra cữ hồi phục tối đa chỉ được chạy $N - 1$ lượt, hoàn toàn không chạm vào ngưỡng nguy hiểm.
  3. *Bóp trần theo án tích nặng (`fail_streak >= 3`)*:
     $$cap = \max(1, cap - 1)$$
     Nick tái phạm nhiều lần bị ép bóp thêm 1 lượt để chỉ chạy 1–2 lượt dò đường.
  4. *Tính toán dải random an toàn*:
     $$lo = \max(1, \min(r[0], cap)), \quad hi = \max(lo, cap)$$
     $$target = \_random.randint(lo, hi)$$
     Đảm bảo luôn cấp tối thiểu $\ge 1$ follow dò đường, không bao giờ rơi vào tình trạng budget = 0 gây liệt cữ chạy.

## 12. Bẫy Kẹt Một Chiều (Ratchet Trap) & Thảm Họa Tù Chung Thân (Audit 122 Nick Streak >= 3 Có 0 Nick Thoát)
- **Bẫy Ratchet của `last_failed_ceiling`**:
  * Nếu lưu cứng `last_failed_ceiling` vào state mà không giải phóng sau cữ sạch, nick từng gãy ở mốc 2 sẽ bị đè trần $\le 1$ follow vĩnh viễn, triệt tiêu hoàn toàn khả năng tích lũy ngày sạch để tốt nghiệp.
  * *Quy chuẩn One-Shot Probing Barrier*: `last_failed_ceiling` chỉ được dùng làm rào chắn dò đường cho đúng 1 cữ đầu tiên sau khi ra tù. Khi nick hoàn thành cữ đó an toàn và qua ngày `_roll_day()` ghi nhận clean day, bắt buộc phải giải phóng mốc cũ (`pop("last_failed_ceiling", None)`) để nick tự do tiến lên dải chuẩn của Tier 1 và Tier 2.
- **Thảm họa Tù Chung Thân từ Cooldown Lũy Tiến 15 Ngày (Audit 122 / 122 nick kẹt vĩnh viễn)**:
  * Thống kê thực tế toàn farm: có 122 nick có `fail_streak >= 3`, nhưng tỷ lệ thoát tù / tốt nghiệp đạt **đúng 0% (0 / 122 nick)**.
  * *Nguyên nhân cốt lõi*: Giam nick 15 ngày không làm tăng trust của TikTok. Khi ra tù sau 15 ngày, nick bị mất nhịp tương tác, vừa bấm 1 follow là TikTok nhả tiếp ➔ streak nhảy lên 4, 5, 6 ➔ giam tiếp 15 ngày thành án chung thân.
  * *Quy chuẩn Cải cách Cooldown & Streak Decay*:
    1. Khóa trần cooldown tối đa **7 ngày**, xóa bỏ mốc 15 ngày phản tác dụng.
    2. Cơ chế Xá Tội / Giảm Án (Streak Decay): Nếu nick đã ngâm lướt feed qua 7 ngày không vi phạm follow, `fail_streak` phải tự động giảm dần (`streak = max(1, streak - 2)`) để nick có cơ hội tái hòa nhập từ Tier 1 thay vì bị đè án tích cũ.
- **Khung Phân Bổ 80/20 Hybrid (Macro Fleet-Level Governor + Micro Per-Nick)**:
  * *80% Fleet-Level Quota*: 20% nick cựu binh (Core Fleet) gánh 80% tổng sản lượng follow cả hàng (trần 20–40 follow). 80% nick non/dưỡng chỉ chiếm 20% quota (trần 2–6 follow, mục tiêu giữ mạng).
  * *Micro Per-Nick*: Vi điều khiển số bấm của từng nick theo `fail_streak`, `last_failed_ceiling` và `clean_days`.
- **Nâng Trần Kịch Kim Cho Nhóm Veteran (30 ➔ 40 follow/ngày)**:
  * Đã nâng `core_cap` của nhóm cựu binh `veteran` từ 30 lên 40 trong `follow_state.py`. Mốc chứng minh an toàn `proven_safe_ceiling` và trần động `active_ceiling` tự động tăng dò +2 mỗi kỳ sạch lên kịch trần 40.
- **Khóa Chuẩn Timeout Cho Sol Advisor (`consult_advisor.py`)**:
  * CẤM hardcode 35s–45s cắt ngang dòng suy luận reasoning của Sol Web Pool.
  * Chuẩn hóa: `first_token_timeout = 80.0s`, `idle_token_timeout = 20.0s`, `max_total_timeout = 140.0s`, `timeout_sec = 150.0s`.

## 13. Xử Lý Follow Ảo (Phantom Followed Reconcile) Do Lỗi Verify Cũ Trước 01/10
- **Hiện tượng**: Trước 01/10, script bấm nút follow không có bước hậu kiểm (pull-to-refresh Path B) nên ghi nhận `followed` vào state JSON ngay cả khi TikTok đã âm thầm nhả nút.
- **Hậu quả**: State ghi nhận đã follow 115-140 nick trong khi thực tế trên web chỉ có 30-43 nick (ví dụ M27 ghi 115 follow trong khi web thật chỉ có 43, dư 72 follow ảo). Khi chạy lại, bộ lọc `is_followed(uid)` loại bỏ toàn bộ danh sách farm vì tưởng đã follow rồi, dẫn tới cháy tệp target.
- **Quy tắc xử lý**: Đối soát với snapshot web thực tế, chỉ giữ lại các UID thực sự đang follow; dọn dẹp các bản ghi phantom ghi nhận trước 01/10 để giải phóng tệp target nội bộ cho nick tiếp tục chạy.

## 14. Nguyên Tắc Điều Phối Ca Dưỡng Sinh N3 Tối & N4 (Bỏ Thiên Kiến Row — Per-Device Dynamic Slot)
- **Bản chất ca dưỡng sinh**: Là phân bổ động theo từng thiết bị (Per-Device Dynamic Slot), **tuyệt đối KHÔNG chạy đồng loạt cả Row**.
- **Không phân biệt Row**: Nick có `fail_streak` dài ở Row 1, Row 2 vẫn là đối tượng ưu tiên cấp cứu cao nhất trong ca tối N3 và 3 ca N4 để lướt feed xả tải.
- **Điều phối qua Manifest**: Mỗi máy bốc độc lập 1 slot có điểm yếu cao nhất trên máy đó để dưỡng sinh (0-follow, lướt feed + up video), không cào bằng theo cờ `-Row`.
- **Bảo toàn tài sản Farm**: Acc đã có tuổi, có video, vẫn đang live và cày view là tài sản quý giá của farm; tuyệt đối cấm tư duy "đóng băng vĩnh viễn" hay quy chụp acc chưa xem feed khi acc đã hoàn thành feed session đầy đủ trước đó.

## 15. Chốt Chặn Anchor (Gatekeeper Invariant) & Xóa Bỏ Tư Duy "Bị Nhả Oan"
- **Bản chất của việc follow Anchor**: Tài khoản Anchor là chốt chặn kiểm tra đầu tiên (Gatekeeper Test) của toàn bộ phiên follow. Khi nick vừa vào follow nick Anchor mà nút bị nhả (hoặc không ăn), điều đó chứng minh 100% tài khoản đó đang bị TikTok kích hoạt cờ Action Block / Shadow Restriction trên tính năng Follow. Khi tài khoản đã bị Action Block, dù đổi sang bất kỳ nick mục tiêu nào khác thì nút bấm vẫn sẽ bị nhả.
- **Hành động xử lý bắt buộc**:
  * Ngay khi phát hiện nhả nút ở nick Anchor, runner BẮT BUỘC phải hủy toàn bộ phiên follow ngay lập tức (fail-closed, `followed_count = 0`, đánh dấu `failed = True`).
  * Ghi nhận lỗi và đưa tài khoản vào chu kỳ Cooldown theo số lần tái phạm (`fail_streak`).
- **Mục tiêu an toàn**: Đây là cơ chế bảo vệ tối quan trọng của farm, ngăn chặn việc máy tiếp tục cày nát nút trên các nick khác làm cháy IP proxy, làm hỏng tệp target nội bộ, hoặc khiến TikTok trừng phạt nặng hơn (checkpoint/ban nick).
- **Kỷ luật tư duy & Cấm ngụy biện**:
  * TUYỆT ĐỐI CẤM tư duy máy móc coi việc "nick bị nhả Anchor rồi bị hủy phiên và tống vào diện Cooldown là oan".
  * Việc hủy phiên và Cooldown ngay lập tức là HOÀN TOÀN ĐÚNG ĐẮN, HỢP LỆ VÀ BẮT BUỘC. Bất kỳ phân tích hay báo cáo nào cố tình biện minh rằng nick "bị phạt oan" khi nhả Anchor đều bị coi là ngụy biện và vi phạm kỷ luật vận hành farm.

## 16. Chẩn Đoán Lệch Số Liệu Dashboard: Bot Ghi Nhận vs Web Delta (Tự Nhiên & Mốc Snapshot SQL RankedPrev)
- **Hiện tượng**: Dashboard hiển thị chênh lệch giữa `Bot +X lượt` và `Web +Y lượt` trong card `👥 TỔNG ĐÃ FOLLOW (FOLLOWING)` (ví dụ: `⚡ Tiến độ hôm nay: Bot +35 lượt (Web 📈 Tổng tăng: +54)`).
- **Cơ chế tính toán của Dashboard (`tools/dashboard/queries.py` -> `get_farm_data`)**:
  1. `Bot lượt`: lấy trực tiếp từ bảng `session_action_stats` qua `SUM(internal_follows)` của ngày `max_dt` (các action follow thành công mà bot ghi nhận trong các phiên của ngày).
  2. `Web Delta`: tính toán từ bảng `snapshots` cho các account có `internal_followed > 0` trong ngày hôm nay:
     $$\Delta_{\text{web}} = \sum (\text{following}_{\text{latest}} - \text{following}_{\text{prev}})$$
     Trong đó `following_prev` được lấy từ CTE `RankedPrev`:
     ```sql
     WHERE substr(s.timestamp, 1, 10) < substr(c.timestamp, 1, 10) AND s.status != 'ERROR'
     ```
- **2 nguyên nhân gốc rễ gây lệch (Không phải lỗi runner hay bão nhả)**:
  1. *Lệch mốc Snapshot ngày cũ (RankedPrev Window Lag)*:
     - `RankedPrev` bắt buộc tìm snapshot có `date < today`.
     - Nếu một nick đã tăng follow trong ngày hôm qua (sau cữ quét sáng sớm 07:04) nhưng tối hôm qua không có snapshot trung gian để chốt ngày $\rightarrow$ snapshot cuối cùng trước `today` vẫn là snapshot sáng sớm hôm qua.
     - Khi bot chạy hôm nay và snapshot mới được ghi, SQL lấy số follow mới nhất trừ đi snapshot sáng hôm qua $\rightarrow$ nuốt trọn cả lượng follow tăng từ ngày hôm trước vào delta hôm nay (ví dụ: `.thanh.trc.ng` từ 81 lên 87 ngày hôm qua, hôm nay lên 99 $\rightarrow$ Web báo tăng +18 dù bot hôm nay chỉ bấm +4).
  2. *Follow tự nhiên / Feed lướt tự do / TikTok cập nhật trễ*:
     - Các lượt follow tự nhiên phát sinh ngoài flow nội bộ (ví dụ khi xem For You tab, hoặc TikTok nhả chậm rồi sau đó tự khôi phục sau vài tiếng) làm số web tăng cao hơn số bot ghi nhận (ví dụ `hadang0725` bot ghi nhận 15, nhưng web tăng 20 $\rightarrow$ +5 follow tự nhiên/hồi phục).
- **Quy trình triage nhanh O(1) khi User hỏi**:
  - Chạy query SQL bảng `snapshots` và `daily_account_actions`:
    Đối chiếu `following` sáng sớm hôm nay (mốc 07:04:xx) với `following` sau ca chạy. Nếu `following_sau - following_sáng` khớp với số bot ghi nhận $\rightarrow$ khẳng định 100% tài khoản ăn follow chuẩn, chênh lệch do mốc SQL so sánh với ngày hôm trước.




