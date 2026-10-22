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

## 17. Đối Soát Lệch Follow (Script 0 Lượt vs Web +1) Khi Kích Hoạt Chốt Chặn Anchor
- **Hiện tượng**: Báo cáo watchdog ghi nhận `M<N> (@user): script 0 lượt - web 1 lượt - lệch (+1)`.
- **Nguyên nhân cốt lõi & Quy trình đối soát 3 điểm bắt buộc**:
  1. *Kiểm tra hiện trường follow của máy*:
     - Đọc `follow_result.json` tại `live/<date>/<run>/machines/machine_<N>/<run>/follow_result.json` và state file `runs/state/follow_state_<N>_row_<row>.json`.
     - Xác nhận cờ: `status: FOLLOW_FAILED`, `follow_failed: True`, `followed_count: 0`, `followed: []`, lý do `anchor @... bị nhả sau vuốt — dừng session`.
  2. *Kiểm tra log thực thi*:
     - Kiểm tra `log.jsonl` xác nhận không có bất kỳ lệnh tap nào được gửi sau khi anchor bị nhả (fail-closed bảo vệ fleet).
  3. *Đối soát snapshot database (`tiktok_tracker.db`)*:
     - Truy vấn `SELECT timestamp, following FROM snapshots WHERE LOWER(username) = LOWER(?) ORDER BY timestamp DESC LIMIT 5`.
     - Xác định mốc snapshot sáng (07:04) so với mốc snapshot sau ca (14:06).
  4. *Kỷ luật phân tích & Cấm quy chụp*:
     - CẤM võ đoán đổ lỗi cho "lỗi script", "timeout rớt log", hay "bot chạy ẩu" khi chưa kiểm tra hiện trường.
     - Khẳng định rõ: Runner đã xử lý hoàn toàn chuẩn xác theo Invariant Chốt Chặn Anchor (ngắt phiên ngay lập tức để bảo vệ tài khoản và proxy). Lượt tăng trên Web là biến động tự nhiên ngoài flow hoặc TikTok sync trễ từ phiên cũ trước mốc snapshot, không liên quan đến lỗi bot.

## 18. Tiêu Chí Phân Hạng "Nick Khỏe" (🟢 Khỏe / Healthy) & Triage Hiện Tượng Fl Đủ Budget Chưa Lên Khỏe
- **Tiêu chuẩn vào nhóm 🟢 Khỏe (`tier == 'healthy'`) trong `follow_health_helper.py`**:
  1. `is_in_cooldown == False`: Không có cờ `follow_failed: True` và không trong thời hạn Cooldown (`cooldown_until_date` / `cooldown_until_at`).
  2. **`fail_streak == 0`**: Bắt buộc sạch hoàn toàn án tích. Nếu `fail_streak > 0`, nick lập tức bị xếp vào diện Hồi phục (`probation_tier1` nếu `clean_days < 1`, `probation_tier2` nếu `clean_days >= 1`).
  3. **`is_graduated == True`**: Đã tốt nghiệp thử thách (hoặc acc cũ có bề dày $\ge 15$ follow an toàn và chưa từng có án tích).
- **Tại sao toàn farm chỉ có rất ít nick Khỏe (ví dụ 4 nick: M37 R1, M12 R1, M10 R1, M21 R3)**:
  * Qua các đợt quét và siết thuật toán của TikTok, phần lớn các tài khoản trong farm (>420/437 state files) đều từng có ít nhất 1 lần bị nhả follow dẫn tới `fail_streak > 0`. Do đó chỉ những nick cựu binh chưa từng gãy hoặc đã hoàn tất trọn vẹn chu trình tốt nghiệp mới nằm ở nhóm Khỏe.
- **Tại sao có nick follow đủ budget gần đây nhưng KHÔNG được vào nhóm Khỏe**:
  * **Trường hợp A: Follow đủ budget nhưng CUỐI PHIÊN dính Nhả Follow (Release / Action Block)**:
    - *Hiện trường thực tế*: `hadang0725` (M17 R2) và `.thanh.trc.ng` (M23 R2) ngày 20/10.
    - Cả 2 đều được cấp budget 13 và đã bấm thành công 14–15 lượt. Tuy nhiên, ở bước kiểm tra anchor hoặc post-follow sau vuốt của UID cuối, phát hiện bị nhả ➔ kích hoạt `set_follow_failed()`.
    - *Hậu quả cơ chế an toàn*: Ngay lập tức thu hồi cờ tốt nghiệp (`pop("graduated")`), tăng `fail_streak = 1`, phạt cách ly Cooldown 3 ngày. Dù số lượt follow tích lũy cao, nick rơi thẳng vào **🔴 Cooldown (Streak 1)**, không thể là Khỏe.
  * **Trường hợp B: Follow đủ budget và sạch sẽ 100%, nhưng ĐANG TRONG THỜI GIAN THỬ THÁCH (Probation Clean Days < 2)**:
    - *Hiện trường thực tế*: `thy.dung4581` (M33 R2, fl 6/6), `vantieu11` (M59 R4, fl 5/5), `minhan2473` (M8 R2, fl 3/3), `trinh.trinh.dinh` (M18 R2, fl 2/2).
    - Các nick này từng bị nhả trước đó nên đang mang `fail_streak > 0`. Sau khi hết Cooldown và chạy cữ đầu tiên sạch sẽ, hệ thống ghi nhận `recovered_date`.
    - Sau khi qua ngày (`_roll_day()`), nick mới chỉ tích lũy được **`probation_clean_days = 1`** ➔ xếp vào **🟡 Hồi phục 2** (chưa đủ điều kiện reset streak).
    - **Quy tắc 2 Ca Sạch Tốt Nghiệp (`probation_graduation_clean_days = 2`)**: Chỉ khi nick chạy tiếp **ca thứ 2 sạch sẽ** và qua ngày đạt `clean_days >= 2`, hệ thống mới:
      1. Reset `fail_streak = 0`.
      2. Cấp lại `graduated = True`.
      3. Giải phóng hoàn toàn probation và chính thức đưa nick trở lại nhóm **🟢 Khỏe (Full Quota)**.

## 19. Tương Quan Trần An Toàn & Tỉ Lệ Ăn Nhả Giữa Các Cohort (Thực Chiến Chu Kỳ 19–20/10)
- **Dữ liệu thực nghiệm trên 245 tài khoản tham gia**:
  * **🔴 Rookie (< 30 fl)**: Tỷ lệ ăn nhả **97.9% (190 / 194 nick)**.
    - Điểm gãy tức thì: 98.9% ăn nhả ngay mốc 0–1 lượt (`last_failed_ceiling = 1`), vừa bấm nick đầu tiên hoặc kiểm tra Anchor là bị TikTok nhả ngay.
    - Chỉ 4 nick sống sót sạch nhờ đang ở chế độ dưỡng bóp trần (2–5 fl).
    - *Trần an toàn thực tế*: Cực thấp, chỉ **1 – 3 follow/ca**. Cấp budget $\ge 4$ cho Rookie ở giai đoạn này kích hoạt bot detection 98% gãy.
  * **🟡 Mid (30 – 99 fl)**: Tỷ lệ ăn nhả **84.2% (16 / 19 nick)**.
    - Điểm gãy (Cliff Drop): Xuất hiện rõ rệt ở mốc **12 – 15 follow** (`M23 R2` gãy ở 15, `M16 R3` gãy ở 13).
    - *Trần an toàn tối ưu*: **5 – 6 follow/ca** (duy trì sạch 100% khi ở Hồi phục 2).
  * **🟢 Veteran ($\ge 100$ fl)**: Tỷ lệ ăn nhả **71.9% (23 / 32 nick)**.
    - Điểm gãy: Ngưỡng đỏ farm ở **$\ge 15$ follow** (`M17 R2` fl 15 lượt thì dính nhả lượt 15, `last_failed_ceiling = 16`).
    - *Trần an toàn*: Chỉ top 3 cựu binh cứng (`M37 R1`, `M12 R1`, `M10 R1`) duy trì được **10 – 14 follow/ca**. Veteran đang dưỡng trần an toàn là **3 – 5 follow/ca**.
- **Diễn biến tỷ lệ nhả qua các chu kỳ 4 ngày**:
  * Chu kỳ 11–12/10 (cũ): 18 nick chạy, 7 ăn nhả (**38.9%**), thu 58 follow.
  * Chu kỳ 15–16/10 (trước 4 ngày): 123 nick chạy, 84 ăn nhả (**68.3%**), thu 183 follow.
  * Chu kỳ 19–20/10 (hiện tại): 245 nick chạy, 228 ăn nhả (**93.1%**), thu 219 follow.
  * *Nguyên nhân nhảy vọt*: Dàn Rookie tham gia ồ ạt (194 nick, chiếm 79.2% fleet) đúng đợt TikTok siết mạnh + nhóm Mid/Veteran được cấp budget cao chạm ngưỡng đỏ 13–15 fl.

## 20. Phân Tích Cơ Chế Hồi Phục Ra Tù: Bài Toán 15 Fl vs Phễu S1/S2 & Fast-Track Veteran
- **Nguy cơ nếu thả ra tù nã ngay 15 fl**:
  * Khi nick bị nhả ở lượt 15, TikTok đưa tài khoản vào diện theo dõi đặc biệt (High-Risk Watchlist). Mãn hạn cooldown chỉ là mở khóa tạm thời.
  * Vừa ra tù mà bot nã ngay 15 fl dồn dập $\rightarrow$ AI TikTok kích hoạt Action Block lập tức do trùng pattern spammer cũ.
  * Tái phạm sẽ tăng `fail_streak` lên 2 (giam 5 ngày) hoặc 3 (giam 7 ngày) $\rightarrow$ Nick bị đóng băng dài hạn, sản lượng cả tuần = 0.
- **Bài toán sản lượng**:
  * Đi qua phễu S1 (4 fl) $\rightarrow$ S2 (6 fl) $\rightarrow$ Tốt nghiệp (12–14 fl) thu về tổng **24 follow thật**, giữ an toàn cho nick.
- **Quy chuẩn kiến nghị Veteran Fast-Track (Chống cào bằng với Rookie)**:
  * Không cào bằng Veteran với Rookie: Veteran có điểm gãy 15–16, trust cao.
  * Khi ra tù: Cho Veteran chạy Fast-Track **8 – 10 fl** (nằm an toàn dưới mốc gãy 15, đạt 60–70% sản lượng).
  * Chỉ cần hoàn thành 1 ca sạch 8–10 fl là tốt nghiệp thẳng lên mốc 12–14 fl, không cần ngâm 2 ngày S1/S2 như Tân binh.

## 21. Cải Cách Cơ Chế Fail Streak (Chống Phạt Oan Nick Đã Follow Được) & Chuẩn Thống Kê Chu Kỳ
- **Sai lầm thiết kế cũ của `fail_streak`**:
  * Mọi trường hợp `set_follow_failed()` đều tăng `fail_streak = curr_streak + 1` bất kể nick follow được 0 hay 15 lượt.
  * Hậu quả: Nick hoàn toàn khỏe mạnh, follow được 14–15 lượt (như M17 R2, M23 R2) chỉ bị chạm rate limit cuối phiên lại bị đối xử như nick tù nặng, bị tăng streak lên 2, 3, 4, 5, 6 và bị giam 5–15 ngày oan.
- **Chuẩn hóa Logic Fail Streak mới (`follow_state.py`)**:
  1. **Chỉ tăng `fail_streak` khi `budget_used == 0`**:
     * Bị nhả ngay phát đầu tiên (không follow được cái nào) $\rightarrow$ Chứng tỏ tài khoản đang bị cấm/IP dơ thật sự $\rightarrow$ Tăng progressive streak (Streak 1: 3 ngày, Streak 2: 5 ngày, Streak 3: 7 ngày, Streak $\ge 4$: 15 ngày).
  2. **KHÔNG tăng `fail_streak` khi `budget_used > 0`**:
     * Nick đã bấm được $\ge 1$ UID thành công rồi mới dính nhả (chạm trần phiên):
     * Giữ nguyên `fail_streak = max(1, curr_streak)`, tuyệt đối không tăng lũy tiến ngày tù.
     * Chỉ cách ly ngắn **1 ngày** (`today + timedelta(days=1)`) để xả cache phiên của TikTok.
     * Ghi nhận `last_failed_ceiling = max(1, min(40, att if att >= 0 else max(1, used + 1)))` để cơ chế trần động phiên sau tự động khóa cap an toàn dưới ngưỡng này.
- **Quy tắc Thống Kê Chu Kỳ 4 Ngày (Loại Trừ Nhiễu Bị Nhả Ngay Phát Đầu)**:
  * Khi báo cáo đối soát tỷ lệ ăn nhả giữa các chu kỳ 4 ngày, **bắt buộc bóc tách 2 nhóm**:
    1. *Nhóm Bị Nhả Ngay Phát Đầu (`fl = 0`)*: Đa phần là Rookie non hoặc nick đang bị tù nặng, không phản ánh năng lực thực chiến của farm.
    2. *Nhóm Nick Thực Chiến (`fl >= 1`)*: Chỉ tính tỷ lệ Sạch vs Ăn Nhả Đuôi trên tập tài khoản này.
  * *Số liệu đối soát mẫu*:
    - Chu kỳ 15–16/10: Nhả phát đầu 84 nick; Nhóm thực chiến 39 nick (100% sạch, 0% ăn nhả đuôi) do trần an toàn thấp (bình quân 4.7 fl/ca).
    - Chu kỳ 19–20/10: Nhả phát đầu 213 nick; Nhóm thực chiến 32 nick (17 sạch 53.1%, 15 ăn nhả đuôi 46.9%) do mở trần 12–15 fl va phải ngưỡng đỏ TikTok.

## 22. Quy Trình Giải Cứu & Đối Soát Nick Bị Giam Oan Toàn Farm (`reconcile_unfair_streaks.py`)
- **Nguyên nhân phát sinh 90 nick bị giam oan**: Do cơ chế cũ tự động cộng dồn `fail_streak` mỗi lần chạm trần cuối phiên, 90 nick cựu binh/nòng cốt (tích lũy từ 50 đến 254 follow) bị tích tụ streak 3-6 và dính cooldown dài hạn tới cuối tháng 10 hoặc tháng 11 dù hoàn toàn đủ sức cày tiếp.
- **Bộ tiêu chí 2 lớp để phân loại nick được giải cứu**:
  * *Nhánh A (`A_CEILING_DROP`)*: Có $\ge 1$ follow vào ngày báo lỗi (`fl_on_fail_day >= 1` hoặc `budget_used >= 1`).
  * *Nhánh B (`B_TRAPPED_HIGH_TRUST`)*: Đã tích lũy $\ge 10$ follow thực tế (`total_followed >= 10`) và đang kẹt `fail_streak >= 2` hoặc có `cooldown_until_date > today`.
- **Đơn thuốc phục hồi chuẩn hóa**:
  1. Đặt lại `fail_streak = 1`.
  2. Xóa bỏ cờ giam giữ: `cooldown_until_date = None`, `cooldown_until_at = None`, `follow_failed = False`.
  3. Cấp cờ thăng hạng: `probation_clean_days = 1` $\rightarrow$ Đưa thẳng lên nhóm **🟡 Hồi phục 2 (0/1 ca)**, chỉ cần chạy sạch đúng 1 ca tiếp theo là lập tức tốt nghiệp lên **🟢 Khỏe**.
  4. Khóa mốc gãy bảo vệ: `last_failed_ceiling = max(1, fl_on_fail_day + 1)` để phiên sau tự động chạy trần an toàn thấp hơn điểm gãy.
- **Kết quả nghiệm thu**: 90 nick được giải thoát ngay lập tức; nhóm Hồi phục 2 nhảy vọt từ 4 lên 94 nick; số nick Cooldown toàn farm giảm mạnh từ 358 xuống 272 nick.

## 23. Tích Hợp Báo Cáo Chu Kỳ 4 Ngày Lên Dashboard Sổ Bệnh Án (`:1905`)
- **Backend Metric Layer (`follow_health_helper.py`)**:
  * Hàm `get_follow_health_data()` trả về cấu trúc `cycle_comparison`:
    - `current_cycle` (19–20/10) vs `previous_cycle` (15–16/10) vs `old_cycle` (11–12/10).
    - Tính toán: `total_active`, `immediate_drop` (`fl = 0`), `eligible_accounts` (`fl >= 1`), `clean_accounts` (không lỗi), `clean_pct`, `drop_after_fl` (chạm trần), `drop_pct`, `total_follows`, và `by_cohort` (veteran/mid/rookie).
- **Frontend Visualization Layer (`dashboard/follow_detail_component.py`)**:
  * Thêm khối container `#fdCycleComparisonContainer` ngay trên 4 card trần động.
  * Render card so sánh song song với màu sắc chuẩn mực:
    - Xanh lá (`#4ade80`): Tỉ lệ chạy SẠCH 100%.
    - Vàng hổ phách (`#fbbf24`): Tỉ lệ ăn nhả đuôi (chạm trần phiên).
    - Đỏ nhạt (`#fca5a5`): Số nick tù nặng / Rookie non bị nhả ngay phát đầu.
- **Kỷ Luật Nạp Lại RAM Dashboard & Tự Phục Hồi Qua Watchdog**:
  * Sửa code Python/JS không tự nạp vào tiến trình đang chạy do `sys.modules` cache.
  * Supervisor `tiktok_dashboard_watchdog.ps1` (PID kiểm tra mỗi 60s qua `/api/data`).
  * Khi tiến trình cũ trên cổng 1905 bị tắt, Watchdog tự động kích hoạt `start_tiktok_dashboard_hidden.vbs` để dựng lại server trong vòng <=60s với mã nguồn mới nhất.

## 24. Bản Chất Ăn Nhả Đuôi (Account Ceiling) vs Cháy Proxy (IP Circuit Breaker 48h) & Thảm Họa Tê Liệt Máy Partner Cùng IP
- **Hiện tượng**: Nick chạy được 5–15 follow rồi mới bị nhả ở lượt cuối (ăn nhả đuôi). Operator đặt câu hỏi: *Tại sao ăn nhả nhiều mà cầu dao IP 48h không kích hoạt, và trong lịch sử có nick nào bị nhả đuôi xong nick khác cùng IP bị phạt oan theo không?*
- **Bản chất kỹ thuật**:
  * Ăn nhả đuôi (`used > 0`): Nick đã follow thành công 5–15 người liên tục chứng minh **100% IP proxy hoàn toàn sạch và thông suốt**. Việc bị nhả ở lượt cuối là do **tài khoản chạm trần bảo vệ phiên (Account-level Rate Limit)** của riêng nick đó trên TikTok, hoàn toàn không phải do proxy bị chết hay IP bị dơ.
  * Cháy proxy / IP bẩn thật sự: Nick bị chặn ngay từ phát bấm đầu tiên (`fl = 0`) và các nick khác trên cùng proxy đều bị chặn đồng loạt.
- **Bài học từ 2 sự cố lịch sử có thật (Tê liệt máy Partner 48h)**:
  * *Sự cố ngày 10/10 (M18 kéo sập Top 3 toàn farm M56)*: M18 R1 chạy mượt 12 lượt (`internal_follows = 12`), đến lượt 13 bị nhả. Do nick mang cờ `was_graduated = True`, hệ thống gọi `trip_ip_breaker(18)` ➔ Khóa cứng proxy 5122 trong 48h. Hậu quả: Máy partner **M56** (chứa nick cựu binh 🥉 **#3 toàn farm `@tuantuannguyen56`** 247 fl / gần 5.000 tim) **bị treo giò hoàn toàn 48 tiếng**, mất sạch ca chạy ngày 10 và 11/10.
  * *Sự cố ngày 15/10 (M17 làm khóa Cựu binh M55)*: M17 R1 chạy được 5 follow rồi nhả ➔ kích hoạt `trip_ip_breaker(17)` lúc 06:51 ➔ Cựu binh **`anh.le0052` (M55 R1, 106 follow)** ở máy partner bị dừng chạy trọn vẹn 2 ngày 15 và 16/10.
- **Tác hại của việc giật cầu dao IP sai đối tượng**:
  * Dù `run_follow.py` trả về `CIRCUIT_BREAKER_SKIPPED` với `failed: False` (không bị tăng `fail_streak`), nhưng nick ở máy partner bị:
    1. Đứt chuỗi dưỡng ấm (streak warming broken).
    2. Nguội cache tài khoản sau 48h ngừng chạy.
    3. Mất sản lượng follow của cả cụm máy.
- **Quy chuẩn bảo vệ**:
  * Cầu dao IP (`trip_ip_breaker()`) TUYỆT ĐỐI KHÔNG được kích hoạt khi nick ăn nhả đuôi (`used > 0`). Khi `used > 0`, chỉ phạt cooldown riêng nick đó 1 ngày xả cache, giữ nguyên proxy cho các máy partner chạy bình thường.
  * Cầu dao IP chỉ kích hoạt khi có dấu hiệu bẩn IP thực sự từ nick Khỏe (`used == 0` và `was_graduated is True`).

## 25. Nâng Cấp Báo Cáo 4 Chu Kỳ & Bóc Tách Theo Từng Nhóm Cohort Trên Sổ Bệnh Án
- **Mở rộng 4 chu kỳ liên tiếp**: 19–20/10 (Hiện tại), 15–16/10 (Kỳ trước), 11–12/10 (Kỳ cũ), 07–08/10 (Kỳ xưa).
- **Phân tách 3 nhóm Cohort bắt buộc (Cohort Breakdown)**:
  * 🟢 **Cựu binh (Veteran)**: Thực chiến | Sạch % | Nhả đuôi % | Follows.
  * 🟡 **Trung cấp (Mid)**: Thực chiến | Sạch % | Nhả đuôi % | Follows.
  * 🔴 **Tân binh (Rookie)**: Thực chiến | Sạch % | Nhả đuôi % | Follows.
- **Cạm bẫy tính toán lịch sử `has_drop` khi nick đã được giải cứu**:
  * *Lỗi*: Nếu dùng `has_drop = is_in_cooldown and (drop_day in c_dates)`, khi chạy script giải cứu (`reconcile_unfair_streaks.py`) xóa cờ `is_in_cooldown`, hệ thống sẽ tính nhầm là chu kỳ quá khứ có 0% nhả đuôi (sai lệch hoàn toàn với thực tế).
  * *Chuẩn hóa*: Tính drop lịch sử phải độc lập với cờ cooldown hiện tại:
    `has_drop = (a.get("last_failed_date") in c_dates) or (a.get("drop_day") in c_dates)`
    đảm bảo sau khi giải cứu tài khoản, số liệu đối soát chu kỳ lịch sử trên Dashboard vẫn bảo toàn chính xác 100%.

## 26. Tính Độc Lập Giữa Các Nick Cùng IP & Quy Chuẩn Ngắt Cầu Dao Nâng Cao (Smart Breaker: >= 2 Cựu Binh fl=0)
- **Bằng chứng đối soát hiện trường chứng minh Ăn Nhả Đuôi KHÔNG làm sập nick khác cùng IP/cùng máy**:
  * *Hiện trường 1 (Máy 21 ngày 19/10)*: Slot 1 (`labaozmh1x8`) ăn nhả đuôi sau 1 fl. Ngay sau đó Slot 3 (`cao.m.phng7`) cùng máy 21 vào ca nã tới 33 follow sạch sẽ (kỷ lục toàn farm).
  * *Hiện trường 2 (Máy 16 ngày 19/10)*: Slot 1 (`nhuphuong458934`) nhả sau 2 fl. Slot 3 (`lenhi09116`) cùng máy 16 vào ca follow trơn tru 13 lượt.
  * *Hiện trường 3 (Máy 59 ngày 19/10)*: Slot 3 (`carlosfwagne2`) nhả sau 1 fl. Slot 1 (`ngocanh.34589`) cùng máy vẫn follow 5 lượt.
  * *Cặp máy partner M21 & M59 (chung proxy 5125)*: M21 có nick nhả đuôi ngày 19/10, nhưng M59 cùng proxy vẫn chạy bình thường 7 follow qua 2 ngày (19–20/10).
  * *Kết luận bản chất*: Ăn nhả đuôi (`used > 0`) là giới hạn phiên cá nhân của tài khoản (Account Rolling Limit) do TikTok áp đặt khi nick hoạt động năng nổ, hoàn toàn không làm bẩn đường truyền IP proxy bên dưới. Các nick khác vào ca sau vẫn mang session/token riêng và được TikTok đối xử như người dùng mới bình thường.
- **Phân định chiến lược: Xóa bỏ hoàn toàn vs Giữ lại có chốt chặn thông minh**:
  * *Nếu xóa bỏ hoàn toàn (Kill Breaker)*: Khi nhà mạng xoay trúng dải IP độc hoặc bị TikTok blacklist cứng, các nick tiếp theo sẽ lao vào chạy và bị quét trảm hàng loạt (5–10 nick chết chùm trong 1 buổi sáng).
  * *Chuẩn hóa Cầu Dao Thông Minh (Smart Breaker Invariant)*:
    1. **Tuyệt đối cấm ngắt cầu dao IP khi `used > 0`**: Đã follow được $\ge 1$ lượt thì 100% IP sạch, chỉ phạt cooldown 1 ngày trên cá nhân nick đó để xả cache phiên, giữ nguyên proxy cho các máy partner sản xuất.
    2. **Chỉ ngắt cầu dao 48h khi có bằng chứng bẩn IP diện rộng**: Bắt buộc thỏa mãn điều kiện kép: **$\ge 2$ nick Cựu Binh (hoặc 2 máy độc lập dùng chung proxy) cùng bị nhả ngay phát bấm đầu tiên (`used == 0`) trong cùng một ngày**. Khi đó 99.9% là do IP bị gắn cờ, ngắt 48h để bảo vệ dàn nick còn lại là hoàn toàn chính xác.

## 27. Chế Độ Quan Sát Tích Lũy Báo Cáo Đối Soát IP (Accumulated IP Risk Audit Log & Verification Protocol)
- **Bối cảnh & Nhu cầu Operator**:
  * Khi đứng trước quyết định kỹ thuật nhạy cảm (như giữ nguyên không ngắt vs nâng cấp tự động ngắt khi $\ge 2$ cựu binh $fl=0$), Operator chọn giữ nguyên theo dõi (Phương án 1) nhưng **yêu cầu bắt buộc phải có cơ chế tích lũy report qua từng chu kỳ để sau này nhớ nhắc kiểm tra đối soát trước khi chốt nâng cấp**.
  * Nếu không lưu vết tích lũy, sau vài chu kỳ cả Operator và AI đều sẽ quên bối cảnh hiện trường, mất đi dữ liệu thực chứng để đánh giá an toàn.
- **Cơ chế Tích Lũy Báo Cáo Lịch Sử (`data/ip_risk_audit_log.json` / SQLite `ip_risk_audit_log`)**:
  * Mỗi khi kết thúc một chu kỳ 4 ngày (hoặc phiên quét ca ngày N4), hệ thống tự động trích xuất và lưu vết 1 bản ghi:
    ```json
    {
      "cycle": "19-20/10/2026",
      "total_runs": 245,
      "eligible_runs": 32,
      "isolated_tail_drops": 15,
      "immediate_drops_total": 213,
      "suspicious_ip_clusters": [
        {
          "proxy": "5125",
          "machines": ["M21", "M59"],
          "veteran_fl0_count": 0,
          "rookie_fl0_count": 2,
          "verdict": "SAFE_ISOLATED"
        }
      ],
      "would_trip_under_opt2": false
    }
    ```
- **3 Điểm Chạm Hiển Thị Trên Dashboard & Report**:
  1. *Dòng Cảm Biến Cụm IP Trong Bảng So Sánh Chu Kỳ 4 Ngày*:
     - Thêm dòng: `📡 Cụm IP nghi vấn (≥2 cựu binh fl=0 cùng IP)` ngay dưới các chỉ số follow.
     - Hiển thị: `🟢 0 cụm (100% Sạch)` khi an toàn, hoặc `🟡 X cụm nghi vấn` khi có biến động.
  2. *Thẻ Radar Giám Sát IP (Observation Mode) Trên Sổ Bệnh Án*:
     - Phân loại trực quan: 🟢 Xanh (Sạch) / 🟡 Vàng (Theo dõi 1 nick $fl=0$) / 🔴 Đỏ (Nghi vấn $\ge 2$ nick $fl=0$).
     - Ghi chú minh bạch: "Chế độ Quan Sát Tích Lũy: Không tự động ngắt proxy. Dữ liệu được lưu vết để đối soát và xác nhận thủ công."
  3. *Quy Trình Nhắc Nhở & Lệnh Đối Soát Nhanh Cho Operator*:
     - **Khẩu lệnh đối soát**: Khi Operator hỏi `"kiểm tra report ip"` hoặc `"đối soát ip"`, Coordinator lập tức chạy công cụ đối soát:
       ```bash
       python D:/Taadaa/tools/ip_risk_audit.py
       ```
       Công cụ tự động đọc mapping `PROXYgandienthoai.xlsx`, truy vấn `daily_account_actions` + state files, phân loại 3 cấp độ (SAFE / WARNING / CRITICAL), nạp vào `D:/Taadaa/data/ip_risk_audit_log.json` và in báo cáo từng chu kỳ ra màn hình.
     - **Tiêu chuẩn nghiệm thu đối soát**:
       + Số cụm proxy nghi vấn xuất hiện (CRITICAL: $\ge 2$ cựu binh $fl=0$ cùng IP).
       + Có trường hợp nào $\ge 2$ Cựu Binh cùng bị nhả phát đầu trên 1 proxy không?
       + Đánh giá xem đã đủ cơ sở thực tế tin cậy để chính thức kích hoạt Phương án 2 (tự động ngắt khi $\ge 2$ cựu binh $fl=0$) hay chưa.
     - **Tự động báo cáo cuối chu kỳ 4 ngày (N4)**: Trong bản tin chốt ca N4, Coordinator bắt buộc đính kèm 1 dòng đối soát:
       `📡 Đối soát IP chu kỳ này: X cụm nghi vấn / Y cựu binh dính chùm (Đã ghi nhận vào Sổ Audit Log).`

## 28. Bẫy Đóng Băng Mãn Hạn Cooldown (Stale `follow_failed: True`) & Công Cụ Reconcile O(1) (`reconcile_expired_cooldowns.py`)
- **Nghịch lý "Tù chung thân trên giấy tờ"**:
  * File state JSON trên đĩa (`runs/state/follow_state_*.json`) là dữ liệu tĩnh. Khi mốc thời gian `cooldown_until_at` đã trôi qua (`cooldown_until_at <= now_utc`), file trên đĩa **KHÔNG tự động biến `follow_failed: True` thành `False`**.
  * Nếu tài khoản chưa được cron bốc trúng để chạy ca follow mới (để runner gọi `_roll_day()` / `_check_and_sync_cooldown_expiry()`), cờ `follow_failed: True` vẫn nằm im vĩnh viễn trên đĩa.
  * Hậu quả: Dashboard / Sổ bệnh án đọc `is_failed = bool(d.get("follow_failed"))` sẽ tiếp tục xếp tài khoản vào **🔴 Cooldown**, khiến Operator nhìn vào tưởng tài khoản bị giam mãi mãi dù thực tế đã mãn hạn từ nhiều ngày trước (thực tế kiểm tra farm có tới 48 tài khoản kẹt tình trạng này).
- **Cấm tư duy "chờ cron quét tới mới mở"**:
  * Tuyệt đối không trả lời Operator là "phải chờ cron chạy qua từng máy mới hạ cờ".
  * BẮT BUỘC dùng công cụ giải phóng hàng loạt O(1):
    ```bash
    python D:/Taadaa/tools/reconcile_expired_cooldowns.py
    ```
  * **Cơ chế an toàn của `reconcile_expired_cooldowns.py`**:
    1. Quét toàn bộ `runs/state/follow_state_*.json`.
    2. Chỉ can thiệp các file có `follow_failed == True` VÀ `cooldown_until_at <= now_utc` (hoặc `cooldown_until_date < today_str`).
    3. Đặt lại `follow_failed = False`, xóa bỏ `follow_failed_date`, `cooldown_until_at`, `cooldown_until_date`.
    4. **BẢO TOÀN NGUYÊN VẸN**: `fail_streak`, `history`, `proven_safe_ceiling`, `last_failed_ceiling` để khi vào ca mới, tài khoản bước vào đúng chu trình thử thách Hồi phục 1 / Hồi phục 2 (Probation Clean Days) chứ không bị mất dấu vết lịch sử.
  * Sau khi chạy, 48 tài khoản lập tức thoát khỏi nhóm Cooldown và chuyển sang **🟠 Hồi phục 1 (Sẵn sàng chạy)** trên Dashboard ngay trong 1 giây.

## 29. Cạm Bẫy Phán Đoán Khống Nick Ngoại Farm (`priority_targets.txt` vs 0 Snapshot DB)
- **Hiện tượng**: Agent / Sub-agent khi điều tra nguyên nhân fail streak cao thấy nick ngoài farm (như `@bangtam2311`) trong `config/priority_targets.txt` truy vấn `tiktok_tracker.db` ra 0 dòng snapshots ➔ Vội vàng kết luận: *"Nick bangtam không tồn tại / chết làm bot search không ra ➔ coi là lỗi phiên rồi phạt streak dồn toa"*.
- **Bản chất kỹ thuật**:
  * Nick cá nhân ngoài farm được đưa vào để buff chéo, hệ thống tracker nội bộ KHÔNG crawl định kỳ nên đương nhiên bảng `snapshots` không có dữ liệu.
  * Trong Mode 1 (`mode1_search_follow.py`): Khi tìm kiếm nick không thấy hoặc TikTok trả anti-bot, kết quả trả về là `skipped` với lý do `ID không khớp` hoặc `không tìm thấy`.
  * Luồng `skipped` chỉ tăng `consecutive_not_found` và thêm vào `res.failed_ids` để báo cáo; **TUYỆT ĐỐI KHÔNG GỌI `set_follow_failed()`, KHÔNG PHẠT STREAK, KHÔNG GÂY COOLDOWN**.
  * Bằng chứng đối soát: Kiểm tra 450 state files, số file bị `failed` do nick ngoài farm là **đúng 0 file**; chỉ có 3 file ghi nhận `skipped`.
- **Quy tắc kỷ luật**: CẤM quy chụp lỗi cho nick trong `priority_targets.txt` nếu không tìm thấy key username đó trong `failed: {}` của file state.

## 30. Chuẩn Remediation Vượt Closeout Gate Cho Follow Runner (Sol Auditor >= 85 Scorecard)
- **Bối cảnh**: Khi sửa follow logic (gỡ IP breaker khỏi account mutation, chặn duplicate streak), Sol Auditor có thể từ chối ở Strike 1 & 2 (điểm 70–76) do các thiếu sót về regression coverage.
- **Checklist 5 điểm bắt buộc để đạt APPROVED (>= 85/100)**:
  1. *Giữ nguyên chốt chặn an toàn tại CLI Startup*:
     Gỡ `trip_ip_breaker()` khỏi mutation của từng nick, nhưng BẮT BUỘC giữ lại `check_ip_breaker()` ở đầu `run_follow.py`. Nếu proxy máy đã bị ngắt từ trước, runner phải chủ động bỏ qua an toàn với status `CIRCUIT_BREAKER_SKIPPED`, `failed = False`.
  2. *Hợp đồng Exit Code của `CIRCUIT_BREAKER_SKIPPED`*:
     Trong `_result_exit_code()` và `_result_payload()`, khi `status == "CIRCUIT_BREAKER_SKIPPED"` và `failed == False`, exit code BẮT BUỘC trả về `0` (không coi là crash/lỗi hệ thống để orchestrator không kích hoạt retry vòng lặp).
  3. *Test CLI hồi quy cho Breaker Skipping*:
     Trong `test_cli.py`, khôi phục test `test_live_path_circuit_breaker_tripped_skips` mock `check_ip_breaker` trả về `(True, "msg")` và assert exit code == 0, `failed: false`.
  4. *Test Phủ Định Cho Account Mutation*:
     Trong `test_follow_state.py`, thêm test `test_set_follow_failed_never_calls_trip_ip_breaker` assert rằng `set_follow_failed()` không bao giờ gọi `trip_ip_breaker`.
  5. *Mock `time.sleep` khi test Mode 2 Anchor Follow*:
     Trong `test_mode2_follow_followers.py`, khi viết test cho `_ensure_anchor_followed`, BẮT BUỘC monkeypatch `flow.time.sleep` thành no-op. Nếu không mock, các đoạn sleep random (2–4s) và pull-to-refresh (3.5s) sẽ làm test runner chạm timeout 35s của test suite.









