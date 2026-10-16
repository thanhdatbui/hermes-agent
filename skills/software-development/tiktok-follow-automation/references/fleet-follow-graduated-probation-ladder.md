# Fleet Follow Graduated Probation Ladder & Health-Tiered Reporting

## 1. Bản Chất Kỹ Thuật: Cơ Chế Bậc Thang Thử Thách (Graduated Probation)

### Đơn vị vòng đời cốt lõi: (Máy, Row) là Account độc lập
- **CẤM TUYỆT ĐỐI GỘP QUOTA THEO MÁY:** Mỗi máy chạy nhiều ca (ví dụ ca sáng Row 1, ca chiều Row 2...). Mỗi `(máy, row)` là một nick độc lập có state, lịch sử và trust score riêng. Không bao giờ cộng dồn quota theo máy hoặc đặt trần ngày theo máy.

### Tại sao nick ra tù hay bị dính nhả lại?
1. **Lỗi spike quota ngay sau khi ra tù:**
   - Khi hết hạn cooldown, tài khoản ra tù vẫn đang nằm trong danh sách giám sát (probation) của TikTok server.
   - Nếu vừa chạy xong 1 phiên nhẹ (3-5 lượt) mà hệ thống xóa ngay `fail_streak = 0` thì phiên kế tiếp trong ngày hoặc ngày hôm sau sẽ cấp ngay Full Budget (10-20 lượt/phiên, tức 20-30+ lượt/ngày).
   - TikTok server phát hiện đột biến follow từ nick vừa ra tù -> Đập gậy trừng phạt và tăng mức phạt lên các streak cao hơn (3, 5, 7, 15 ngày).
2. **Ngưỡng tải thực tế (Trust Ceiling):**
   - Mức **1 - 3 follow/ngày:** Dành cho nick vừa dứt cữ phạt (ra tù).
   - Mức **7 - 10 follow/ngày:** Vùng an toàn cao nhất (~90% an toàn theo số liệu thực tế farm).
   - Mức **12 - 15+ follow/ngày:** Bắt đầu chạm ngưỡng đỏ của TikTok đối với các nick chưa tích lũy đủ trust. Chỉ nhóm nick nòng cốt (>215 ngày, >25 video, có tương tác tự nhiên) mới chịu được mức này an toàn.

---

## 2. Quy Chuẩn 3 Nấc Thang Thử Thách (Graduated Probation Ladder)

### Nhóm 1: Nick Khỏe / Nòng Cốt (Đã tốt nghiệp: `>= 15` follows an toàn HOẶC `graduated == True`, `fail_streak == 0`)
- Budget chuẩn: 10 - 15 follows/phiên (hạ từ 10-20 xuống 10-15 theo quyết định vận hành 12/10/2026, ngày 2 phiên tích lũy 20 - 30 follow).
- Tuyệt đối không tự ý hạ trần vô lý của nhóm này làm giảm hiệu suất chung của farm.

### Nhóm 2: Tân Binh & Nick Có Tiền Án (Lộ trình rút gọn thích ứng chu kỳ 4 ngày: 1 ca sạch / nấc)
- **Quy tắc Tân Binh (USER INVARIANT):** Nick mới đủ Dual Gate (`age >= 21d`, `video >= 6`) nhưng chưa từng đi follow hoặc chưa tích lũy đủ follow an toàn (`< 15` follows, chưa có cờ `graduated`) đi dò với Quota 2–4 lượt. Bị nhả chỉ phạt cá nhân (tăng fail_streak, cooldown 3-14 ngày dưỡng sinh), **CẤM TUYỆT ĐỐI GIẬT CẦU DAO IP** (xem chi tiết `references/tier-aware-circuit-breaker-and-accelerated-probation.md`).
- **Quy tắc Nick Ra Tù:** Nick vừa hết hạn cooldown quay lại thử thách với Quota 2–4 lượt.

Áp dụng lộ trình 2 nấc thang tính theo số ca/phiên chạy sạch (`probation_clean_days` - ĐÚNG 1 CA SẠCH / NẤC; mỗi stage chỉ đúng 1 lần chạy sạch hoàn thành là thăng cấp):

* **HỒI PHỤC 1 (Probation Tier 1 - Tân binh khởi động & Nick mới ra tù, `clean_days < 1`):**
  - **Quota:** 2 – 4 follows / ca (đồng nhất cho cả tân binh và nick ra tù; điều chỉnh tối ưu theo chu kỳ 4 ngày).
  - **Tiến độ thực tế:** Cần đúng 1 ca/phiên chạy sạch hoàn thành để thăng lên Hồi phục 2 (`sessions_needed = max(1, 1 - clean_days)`).
  - **Hiển thị Badge Thận trọng:** Tối đa 1 ca (`🛡️ Thận trọng (1 ca)`).

* **HỒI PHỤC 2 (Probation Tier 2 - Tăng tải an toàn, `1 <= clean_days < 2`):**
  - **Quota:** 6 – 8 follows / ca (chuẩn hóa tải đệm).
  - **Tiến độ thực tế:** Cần thêm đúng 1 ca/phiên chạy sạch tiếp theo để tốt nghiệp (`sessions_needed = max(1, 2 - clean_days)`).
  - **Hiển thị Badge Thận trọng:** Tối đa 1 ca (`🛡️ Thận trọng (1 ca)`).

* **NẤC 3 (Tốt nghiệp - Graduation, `clean_days >= 2`):**
  - Sau tổng cộng 2 ca/phiên chạy sạch (~2 chu kỳ xoay tua = 8 ngày ngoài đời thực, thay vì 4 ca sạch mất tới 17 ngày trong workflow 4 ngày).
  - Hệ thống chính thức tốt nghiệp (`graduated = True`, `fail_streak = 0`, xóa `probation_clean_days`), thăng hạng lên Nhóm Nick Khỏe (Full Budget 10 - 15 lượt).
  - **Cầu Dao IP (Tier-Aware Breaker):** CHỈ KHI NICK ĐÃ TỐT NGHIỆP (`was_graduated is True`) BỊ NHẢ mới kích hoạt ngắt Cầu dao IP 48h (`trip_ip_breaker`). Nick chưa tốt nghiệp (Tân binh, Hồi phục 1 & 2) bị nhả chỉ phạt Cooldown account, KHÔNG ngắt IP breaker (`[IP_BREAKER_SKIPPED_TIER]`).

* **CHỐT AN TOÀN FAIL-CLOSED & PROGRESSIVE BACKOFF STREAK:**
  - Nếu ở bất kỳ nấc nào (`Hồi phục 1` hay `Hồi phục 2`) mà bị TikTok nhả follow (`set_follow_failed()`) hoặc không follow được:
  - Lập tức xóa `probation_clean_days = 0`, tăng `fail_streak` (Streak 1 -> Streak 2 -> Streak 3+).
  - Đưa vào Cooldown theo Progressive Backoff:
    * `fail_streak = 1`: Giam 3 ngày (quota = 0).
    * `fail_streak = 2`: Giam 5 ngày (quota = 0).
    * `fail_streak = 3`: Giam 7 ngày (quota = 0).
    * `fail_streak >= 4`: Giam 15 ngày (quota = 0).
  - Khi mãn hạn Cooldown: Bắt buộc quay lại từ vạch xuất phát `Hồi phục 1` (2 - 4 lượt/ca). Nếu chạy sạch 1 phiên -> lên `Hồi phục 2` (6 - 8 lượt/ca) -> chạy sạch thêm 1 phiên -> tốt nghiệp lên `Khỏe` (10 - 15 lượt/ca). Nếu tại bất kỳ nấc nào bị nhả tiếp thì tiếp tục tăng `fail_streak` và quay lại Cooldown dài hơn.
  - **Chống bẫy thống kê Simpson:** Thống kê tỷ lệ giữ follow phải phân tầng độc lập (tỷ lệ của riêng Hồi phục 1, Hồi phục 2, Khỏe), CẤM gộp phẳng toàn farm khiến mức 15+ của nick Khỏe bị hiểu nhầm là an toàn nhất trong khi mức 1-4 của nick sau phạt bị kéo tụt tỷ lệ.
  - **Tương tác giữa Cooldown (Đi tù) vs Cầu Dao IP (Circuit Breaker) vs Ngày sạch:**
    * **Ngày đi tù (Cooldown) chạy theo Calendar Time:** Án phạt chốt theo ISO UTC timestamp (`cooldown_until_at`) và ngày kết thúc (`cooldown_until_date`). Dù ngày đó trùng ngày IP bị giật cầu dao hoặc máy không chạy, đồng hồ thụ án vẫn trôi tự nhiên và nick mãn hạn ra tù đúng hẹn.
    * **Mãn hạn đúng ngày IP bị ngắt:** Hệ thống kích hoạt Safe-Skip (`CIRCUIT_BREAKER_SKIPPED`), không cho nick bấm follow trên IP bẩn (tránh bị nhả dắt dây), bảo vệ nick an toàn chờ IP sạch mới vào Hồi phục 1.
    * **Phân biệt với Ngày sạch (`probation_clean_days`):** Ngày sạch để tốt nghiệp chỉ được tính khi có phiên follow thực tế thành công (`recovered_date < today`). Ngày bị ngắt cầu dao chỉ lướt feed dưỡng sinh thì KHÔNG được cộng ngày sạch, nhưng cũng tuyệt đối KHÔNG bị tính lỗi hay tăng streak.

---

## 3. Quy Chuẩn Đồng Bộ Múi Giờ & Báo Cáo Sức Khỏe (Health-Tiered Reporting)

### A. Bắt buộc đồng bộ múi giờ Việt Nam (GMT+7 / Asia/Ho_Chi_Minh):
- Timestamp trong file state JSON lưu dạng ISO UTC (`...Z` hoặc `+00:00`).
- Mọi thống kê, phân nhóm ngày, so sánh lịch chẵn/lẻ **BẮT BUỘC PHẢI convert sang Asia/Ho_Chi_Minh** trước khi tính toán.
- Tuyệt đối cấm lấy substring `ts[:10]` trực tiếp từ chuỗi UTC, tránh nhầm lẫn tai hại (ví dụ 06:30 sáng VN ngày 3 bị đọc nhầm thành 23:30 đêm ngày 2).

### B. Format báo cáo sức khỏe follow theo tầng (Ghi range lượt nhóm, %, và Danh Sách Máy trong ngoặc):
- **QUY TẮC CỐT LÕI (USER CORRECTION):**
  - Trong báo cáo Telegram theo nhóm, **BẮT BUỘC ghi rõ range lượt của nhóm** (ví dụ `(10+ lượt)`, `(5 - 9 lượt)`, `(1 - 4 lượt)`, `(0 lượt)`) kèm **tỷ lệ %** và **danh sách máy đặt trong ngoặc đơn `(M1, M2...)`**.
  - **TUYỆT ĐỐI CẤM ghi chi tiết số lượt của từng máy riêng lẻ `(M1 (4 lượt), M2 (17 lượt))`** gây rườm rà, rối mắt.
- **Cấu trúc chuẩn:**
  ```markdown
  • Follow chéo (35 lượt follow) [Module 2 (Anchor): 28 | Module 1 (Bù): 7]:
    + Thành công (7 máy | 70.0%):
      💪 Nhóm Khỏe (10+ lượt | 28.6%): (M2, M39)
      🌱 Hồi phục 2 (5 - 9 lượt | 28.6%): (M18, M28)
      🌱 Hồi phục 1 (1 - 4 lượt | 42.8%): (M1, M52, M16)
    + Nhả follow (3 máy | 30.0%):
      - Nhả liền (0 lượt | 66.7%): (M26, M32)
      - Nhả ở Hồi phục 1 (1 - 4 lượt | 33.3%): (M4)
  ```

---

## 4. Tích Hợp Web Dashboard (`D:/Taadaa/tools/tiktok_dashboard.py` :1905)
- **Module tính toán:** `D:/Taadaa/tools/follow_health_helper.py` trích xuất nhanh O(1) từ 411 file `runs/state/follow_state_*.json` và database `tiktok_tracker.db` (`daily_account_actions`).
- **Endpoint API:** `/api/follow-health` cung cấp cấu trúc JSON gồm:
  - `summary`: Tổng nick theo dõi, số lượng & tỷ lệ % cho 4 tầng (Khỏe, Nấc 2, Nấc 1, Cooldown kèm phân tách Streak 1 / Streak 2-3 / Streak 4+).
  - `weekly_stats` & `daily_stats`: Thống kê tổng lượt follow và số nick hoạt động theo từng tuần / ngày.
  - `accounts` & `grouped`: Danh sách chi tiết ánh xạ Máy, Row, Username, Tier, số ngày sạch, và ngày hết hạn Cooldown, kèm theo phân nhóm sẵn theo từng danh mục.
- **Quy tắc hiển thị Dashboard (Chống đổ tràng dài 400 dòng trên mobile & Tối ưu UI/UX tương tác):**
  - **CẤM TUYỆT ĐỐI render bảng cuộn 400 dòng lẫn lộn một tràng từ trên xuống dưới:** Khiến trên điện thoại bung thành hàng trăm card dọc dài vô tận, không thể nắm bắt được tình hình.
  - **Dùng 4 thẻ KPI lớn làm nút chọn nhóm chính (Interactive KPI Filter Cards — thay thế hàng nút dư thừa):**
    * 4 thẻ KPI trên cùng (`💪 Khỏe`, `🌱 Hồi phục 1`, `🌱 Hồi phục 2`, `⚠️ Đang Cooldown`) là các thẻ bấm được (`.fleet-kpi.clickable`).
    * BẮT BUỘC hiển thị cả **số lượng máy + tỷ lệ %** ngay trong thẻ: ví dụ `20 máy (4.9%)`, `29 máy (7.1%)`.
    * **Hiệu ứng bấm thẻ trực quan (Micro-interaction & Active Feedback):**
      - Thẻ KPI khi hover/click phải có hiệu ứng tương tác như các thẻ KPI khác (`:hover { transform: translateY(-3px); box-shadow: ... }`, `:active { transform: translateY(-1px); }`).
      - Thẻ được chọn BẮT BUỘC có class `.active` với background gradient highlight, viền rực màu neon accent, và hiệu ứng chấm tròn active (`::after`) để người dùng nhận biết ngay thẻ nào đang kích hoạt.
    * **CẤM tạo thêm hàng nút chọn nhóm lặp lại ở phía dưới (loại bỏ redundancy):** Khi 4 thẻ KPI đã có đủ chức năng và số liệu, việc tạo thêm một hàng nút chọn nhóm phía dưới là dư thừa và làm rối mắt. Nếu giao diện có hàng nút lọc nhanh cho Ma Trận, BẮT BUỘC phải có đủ cả 4 tầng: `[Tất Cả]`, `[Khỏe]`, `[Hồi phục 1]`, `[Hồi phục 2]`, `[Cooldown]`; CẤM TUYỆT ĐỐI bỏ sót `Hồi phục 1` và `Hồi phục 2`.
    * **Chỉ số và bộ lọc Follow Gần Đây (Recent Follows Invariant):** Dashboard BẮT BUỘC hiển thị chỉ số follow thực tế tích lũy trong 12 ngày gần nhất (`recent_followed` / `Gần đây (+X)`) trên mỗi thẻ và bảng, kèm tính năng sort `Gần đây ↕` để operator theo dõi ngay các nick đang cày follow tốt nhất thay vì bị che khuất bởi dàn nick 0 follow.
    * Bấm vào thẻ KPI nào là lập tức kích hoạt lọc và **tự động cuộn mượt (`scrollIntoView`)** xuống thẳng danh sách máy của nhóm đó, không bắt người dùng phải kéo tay tìm kiếm.
    * Có highlight trực quan (`.active`) trên thẻ KPI đang được chọn.
  - Mặc định khi mở tab phải chọn ngay nhóm **`[💪 Khỏe]`** để hiển thị ngay dàn nick nòng cốt sạch đẹp.
  - Hiển thị danh sách dạng **Lưới thẻ gọn gàng (Compact Cards Grid)**: Mỗi thẻ ghi rõ Máy & Row (`M1 (Row 1)`), `@username`, Trạng thái sức khỏe, và Hạn ra tù / Ngày sạch.
  - **Link trực tiếp đến profile TikTok (USER INVARIANT):** Trên mỗi thẻ nick, `@username` BẮT BUỘC phải là link `<a>` (`href="https://www.tiktok.com/@username" target="_blank"`) kèm icon `↗` và `📈` để người dùng chạm vào là bung ngay ra trang cá nhân của nick đó trên TikTok, giống như ngoài Dashboard chính. Tuyệt đối cấm để username dạng text tĩnh không click được.
  - Tích hợp ô tìm kiếm nhanh (theo số máy `m1`, `18` hoặc `username`).
  - **Deduplication:** Tự động lọc bỏ các file state legacy không có `_row_` (như `follow_state_1.json`) để không bị duplicate dòng hiển thị trên Dashboard.
  - **Quy chuẩn Adaptive Recovery Badge (USER INVARIANT - 1 Ca / Stage theo chu kỳ 4 ngày):**
    * Thẻ hiển thị huy hiệu `recBadge`:
      - `⚡ Ưu tiên (1 ca)`: Cho nick điểm tín nhiệm cao ($\ge 60$đ).
      - `🎯 Cần 1 ca sạch`: Cho nick đang trong nấc Hồi phục 1 hoặc Hồi phục 2 (`sessions_needed = 1`).
    * **Công thức `sessions_needed` & Nhãn tiến độ:**
      - Hồi phục 1 (`clean_days < 1`): nhãn `🟠 Hồi phục 1 (0/1 ca)`, `sessions_needed = max(1, 1 - clean_days) = 1 ca sạch` để lên Hồi phục 2.
      - Hồi phục 2 (`1 <= clean_days < 2`): nhãn `🟡 Hồi phục 2 (0/1 ca)`, `sessions_needed = max(1, 2 - clean_days) = 1 ca sạch` để tốt nghiệp lên Khỏe.
      - Fallback record (`farm_account_info`): BẮT BUỘC để `sessions_needed = 1` và `(0/1 ca)`. CẤM TUYỆT ĐỐI để fallback 2 ca cũ gây mâu thuẫn giữa thực tế runner và giao diện.

---

## 6. Kiến Trúc Chuẩn Hóa: Tách Biệt Cấp Bậc (Stage) vs Lộ Trình (Path) vs Tiến Độ (Progress)

### A. Nguyên nhân gây lú lẫn cho Operator:
- Lỗi UX: **Biến bộ đếm tiến độ / đếm ngược (Countdown) thành nhãn phân cấp (Classification Badge)**.
- Khi hiển thị `🛡️ Thận trọng (2 ca)` rồi đếm ngược xuống `🛡️ Thận trọng (1 ca)`, Operator bị lú lẫn, tưởng rằng hệ thống sinh thêm các cấp bậc con kỳ quặc (Thận trọng 3 ca, 2 ca, 1 ca) đè lên cấp `Hồi phục 1 / Hồi phục 2`.

### B. Ba tầng độc lập chuẩn hóa (Tư vấn kiến trúc từ Advisor Sol):
1. **Layer 1: Cấp bậc / Nấc thang (Stage / Level):**
   - Trả lời: *Nick đang được cấp quota tải bao nhiêu?*
   - Cấp 1: `🟠 Hồi phục 1` (1–2 fl/ca).
   - Cấp 2: `🟡 Hồi phục 2` (5–8 fl/ca).
   - Cấp 3: `🟢 Khỏe / Nòng cốt` (10–15 fl/ca).
2. **Layer 2: Lộ trình thử thách (Recovery Path):**
   - Trả lời: *Nick đi đường thường hay đường ưu tiên?*
   - `Đường thường (Standard)`: Nick tân binh / mới lên giàn / điểm uy tín thấp ($< 60$đ) $\rightarrow$ Đi tuần tự qua từng nấc.
   - `⚡ Ưu tiên (Priority / Fast-track)`: Nick cựu binh uy tín cao ($\ge 60$đ, tuổi đời lớn, nhiều video) $\rightarrow$ Rút ngắn thời gian thử thách (1 ca sạch promote ngay).
   - **THUẬT TOÁN CHẤM ĐIỂM TÍN NHIỆM (RECOVERY TRUST SCORE 0 - 100):**
     $$\text{Recovery Score} = \max\Big(0,\; \text{Base Trust} - \text{Violation Penalty}\Big)$$
     * **Điểm Uy Tín Cơ Sở (Base Trust — Tối đa 100đ):**
       - Lịch sử Follow (`total_followed`): $\ge 100$ fl (40đ), $50-99$ fl (30đ), $20-49$ fl (20đ), $< 20$ fl (10đ).
       - Kỷ lục Max Safe (`max_safe`): $\ge 30$ fl (40đ), $15-29$ fl (30đ), $5-14$ fl (15đ), $< 5$ fl (5đ).
       - Tiến độ sạch (`clean_days`): mỗi ca sạch +10đ (max 20đ).
     * **Điểm Trừ Vi Phạm (USER INVARIANT — PHẢI LÀ PHÉP TRỪ):**
       - Streak 0: trừ 0đ.
       - Streak 1 (Lần đầu bị nhả / nghi do IP/lag): **TRỪ 15đ**.
       - Streak 2 (Tái phạm lần 2): **TRỪ 35đ**.
       - Streak >= 3 (Tái phạm nặng / Sổ đen): **TRỪ 60đ**.
     * **Cơ chế Farm Điểm Lên Fast-Track Tự Động:** Nick ở nhóm Thận trọng ($< 60$đ) hoàn toàn có thể tự leo lên Fast-track qua các pipeline: Upload video đều đặn (+20–30đ), tích lũy micro-follow sạch 3–4 fl/ca (+10đ/ca). Khi điểm chạm $\ge 60$đ, hệ thống tự động thăng lên Fast-track.
3. **Layer 3: Tiến độ nâng cấp (Progress & Requirement):**
   - Trả lời: *Còn bao nhiêu ca sạch nữa để thăng hạng?*
   - Hiển thị rõ dạng tiến độ: `X/1 ca sạch` (mỗi stage đúng 1 ca sạch) và `Cần thêm 1 ca sạch để lên Cấp tiếp theo`.
   - **CẤM TUYỆT ĐỐI:** Nhồi nhét chữ `(X ca)` vào tên huy hiệu (như `Thận trọng (X ca)` hay `Thận trọng (1 ca)`) làm rối loạn phân loại của Operator.

### C. Nghịch Lý Simpson (Simpson's Paradox) & Công Thức Tối Ưu Quota Theo Rủi Ro:
- **Cạm bẫy thống kê Flat:** Thống kê gộp toàn farm khiến nhóm 15+ fl trông an toàn nhất (96.9%) còn nhóm 1-4 fl lại báo nhả cao (33.3%). Đây là **Survivorship Bias** kinh điển: chỉ có nick nòng cốt siêu khỏe mới được cấp 15+ fl, trong khi chỉ có nick mới ra tù / tân binh yếu mới chạy 1-4 fl. Nếu vặn 15+ fl cho nick yếu sẽ chết 100%.
- **Công thức tính Quota tự động (Risk-Adjusted Decision Optimization):**
  $$U(q) = q \times (1 - P_{\text{nhả}}(q)) - P_{\text{nhả}}(q) \times \text{Cost}_{\text{Cooldown}}$$
  với chi phí giam Cooldown phạt nặng theo tầng: S1 ($\approx 30$ fl), S2 ($\approx 60$ fl), Khỏe ($\approx 120$ fl). Công thức này tự động tìm điểm ngọt $q^*$ bền vững cho từng tầng độc lập.

---

## 5. Đối Soát Số Liệu Dashboard: Phân Biệt "Đã Follow (Delta)" vs "🔗 Nội Bộ"

### A. Bản chất kỹ thuật của 2 chỉ số:
- **`ĐÃ FOLLOW: X (+Y)` (`delta_following`):**
  - Số liệu thực tế cào từ profile công khai TikTok qua snapshot mới nhất.
  - Hiệu số `+Y` phản ánh **tổng biến động thực tế** của following trên TikTok giữa 2 lần quét: `delta_following = following_hien_tai - following_snapshot_truoc`.
  - Bao gồm TẤT CẢ các hành vi follow: follow chéo nội bộ, follow tự nhiên khi lướt feed, follow kênh idol / kênh niche theo kịch bản nuôi.
- **`🔗 Nội bộ: +Z` (`internal_followed`):**
  - Số liệu telemetry ghi nhận từ các script kịch bản (`feed_session_watchdog` / `run_follow`) được lưu vào bảng `session_account_actions` và tổng hợp ở `daily_account_actions` trong `tiktok_tracker.db`.
  - Chỉ đếm các lượt **follow chéo giữa các tài khoản nội bộ farm** theo `target_date = max_dt`.

### B. Giải mã hiện tượng Following tăng (+12, +2...) nhưng "🔗 Nội bộ: +0":
1. **Follow tự nhiên ngoài luồng chéo (Natural / Niche Follows):**
   - Khi chạy ca lướt nuôi nick (`feed_session`), kịch bản bấm follow các video/kênh hot hoặc tài khoản gợi ý bên ngoài để tăng trust account và định hình niche.
   - Các lượt này làm tăng số Following trên TikTok (`delta_following` dương), nhưng không thuộc danh sách đối soát follow chéo chùm nick nội bộ farm.
2. **Lệch mốc thời gian / Chưa có phiên chéo trong ngày:**
   - Dashboard lấy `internal_follows` theo ngày của snapshot mới nhất (`target_date = max_dt`).
   - Nếu ngày đó mới chỉ chạy ca lướt đêm/sáng sớm (`internal_follows = 0`), hoặc nick không thuộc danh sách phân bổ chạy follow chéo của ngày (ví dụ ca follow chia theo ngày chẵn/lẻ hoặc chỉ phân bổ cho 1 nhóm máy nhất định), hệ thống trả về giá trị mặc định `+0`.
   - Kết luận: Khi thấy Following tăng mà Nội bộ +0, tài khoản hoàn toàn khỏe mạnh và đang tăng follow tự nhiên ngoài luồng chéo, không phải lỗi hệ thống hay nhả follow.

---

## 7. Giải Mã Hiện Tượng "Chết Ở Lượt Thứ 2" Khi Chạy 2 Phiên/Ca & Quy Tắc Cửa Sổ Trượt (Sliding Window Decay)

### A. Tại sao giả thuyết "cắn luôn 20–30 lượt rồi nghỉ 4 ngày" là bất khả thi?
1. **Thuật toán Cửa sổ trượt (Sliding Window / Leaky Bucket) của TikTok:**
   - TikTok kiểm soát tốc độ follow theo block thời gian (theo phút và theo giờ), **không bao giờ đợi gom đủ 20–30 lượt rồi mới khóa**.
   - Với dàn nick farm nuôi bình thường, ngưỡng chịu đựng an toàn trong 1 giờ chỉ từ **4 đến 8 lượt**.
   - Nếu cố bấm dồn, từ lượt thứ 6–8 trở đi server TikTok đã âm thầm từ chối (silent-drop). Nút bấm trên UI dù đổi trạng thái nhưng server không ghi nhận, đối soát web = 0.
2. **Hậu quả cố nhồi quota khi server đã chặn:**
   - TikTok đánh dấu hành vi *Spam Burst*, kích hoạt án phạt `fail_streak` lũy tiến: Streak 1 (3 ngày), Streak 2 (5 ngày), Streak 3 (7 ngày), Streak >= 4 (giam kịch khung 15–19 ngày).
   - Dữ liệu thực tế farm ghi nhận có tới **327 lượt tài khoản** bị giam cooldown kéo dài tới cuối tháng vì các đợt cố bấm dồn trước đây. CẤM TUYỆT ĐỐI thử nghiệm cấp full quota cho dàn đang dưỡng.

### B. Cơ chế "Chết ở lượt thứ 2" tại Phiên 2 (Dữ liệu đối chứng P1 lúc 06:00 vs P2 lúc 08:00):
- **Phân hóa 2 nhóm rõ rệt:**
  * **Nhóm Khỏe (Trust cao — M37, M36, M39...):** Video $\ge 25$, Follower $> 90$, tuổi $> 200$ ngày. Thuật toán cấp trần ngày 15–20 lượt $\rightarrow$ Ăn trọn cả P1 (7 fl) và P2 (6 fl), tổng 13 lượt sạch 100% không nhả.
  * **Nhóm Hồi phục (Probation Tier 1 & 2 — M4, M14, M21, M28, M41, M52, M57...):** Đang trong diện thử thách, TikTok siết trần sinh tồn chỉ **5–8 lượt/ngày**.
- **Kịch bản "bấm cái thứ 2 là nhả" tại Phiên 2:**
  1. P1 và P2 cách nhau quá ngắn (chỉ 2 tiếng), cửa sổ decay window chưa kịp hồi quota.
  2. Ở P1, nick đã cắn 4–7 lượt (gần cạn quota ngày).
  3. Sang P2, nick chỉ còn đúng **1 slot quota thoi thóp cuối cùng**. Bot bấm lượt 1 thành công.
  4. Đến **lượt thứ 2**: Nút trên danh sách vẫn hiện "Đang follow" do cơ chế **Optimistic UI** của app TikTok lừa đảo. Nhưng khi runner chạy **Path B Verify** (click thẳng vào profile cá nhân kiểm tra) thì nút bị server TikTok trả về màu đỏ (chưa follow).
  5. Runner phát hiện silent-drop, lập tức trả về `FOLLOW_FAILED: TikTok không nhận follow (profile vẫn chưa follow)` và dừng session.
  6. Nếu ở P1 nick đã cắn kịch trần 8 lượt (như M26) thì sang P2 vừa bấm nick đầu tiên là dính nhả 0 lượt ngay.

### C. Phân hóa Inbound Trust Score theo độ dày Profile (Row 1 vs Row 2):
- **Row 1 (Tik1 — Nick già, following dày 100–390):** Bị nhả **60.4% ở nick con** do chạm trần rate-limit ngày.
- **Row 2 (Tik2 — Nick mỏng, following 0–6):** Bị nhả **82.6% ngay tại Anchor** (`_ensure_anchor_followed`). Nick non nớt vừa vào bấm ngay một Anchor to ($\ge 150$ following) khiến AI chống bot của TikTok phát hiện bất thường và nhả nút follow về xám lập tức.

### D. Quy Tắc Điều Phối Bắt Buộc (Invariant Enforcements):
1. **Khóa 1 phiên/ngày cho nhóm Hồi phục:** Toàn bộ tài khoản thuộc `probation_tier1` hoặc `probation_tier2` **BẮT BUỘC chỉ được chạy 1 phiên/ngày (Phiên 1), Phiên 2 tự động Safe-Skip / Nghỉ dưỡng**. Tuyệt đối không để nick vừa follow xong ở P1 lại bị đè ra follow tiếp ở P2.
2. **Chiến lược ăn chắc mặc bền:** Giữ nguyên quy trình Hồi phục 1 (2–4 lượt) $\rightarrow$ Hồi phục 2 (6–8 lượt) $\rightarrow$ Khỏe (10–15 lượt). Không chạy A/B test cấp full quota bừa bãi làm tăng fail streak giam nick 15 ngày.

---

## 8. Cơ Chế Dò Trần Tăng Tiến Có Bộ Nhớ (Adaptive Progressive Ceiling +2 Đến 30 Lượt)

### A. Vấn đề năng suất và bài học thực tế:
- **Trần tĩnh 16 là hạn chế năng suất đối với nick khỏe:** Dàn nick nòng cốt dày dặn (M37, M36, M39...) hoàn toàn có khả năng cày 20–30 lượt/ca nếu được tăng nhịp đều đặn và phân bổ 2 phiên hợp lý.
- **Không áp dụng dò trần cho Hồi phục 1 & 2:** Giai đoạn hồi phục cần sự ổn định tuyệt đối (Zero-Variance) để rửa án phạt của TikTok, chỉ nick đã tốt nghiệp (`graduated == True`) mới được kích hoạt dò trần.

### B. Nguyên lý vận hành Dò Trần Tăng Tiến (+2 mỗi ca sạch):
1. **Dò trần tăng dần:**
   - Nick vừa tốt nghiệp: Chạy mức cơ sở 10–15 lượt.
   - Mỗi khi hoàn thành ca sạch $\ge 15$ lượt: Runner tự động nâng trần:
     $$\text{active\_ceiling} = \min(30, \;\text{proven\_safe\_ceiling} + 2)$$
   - Trần nở dần theo nhịp: $15 \xrightarrow{+2} 17 \xrightarrow{+2} 19 \xrightarrow{+2} 21 \dots \xrightarrow{+2} \mathbf{30\text{ lượt (kịch kim)}}$.
2. **Kỷ luật khi bị TikTok nhả (Bảo toàn quy tắc farm):**
   - Khi dính `FOLLOW_FAILED`: Bắt buộc vào Cooldown (đi tù 3–15 ngày tùy streak), thu hồi graduated.
   - Ghi nhận `last_failed_ceiling = current_ceiling`.
   - Lùi trần an toàn một bước đệm:
     $$\text{proven\_safe\_ceiling} = \max(\mathbf{base\_max}, \;\text{curr\_proven} - 4)$$
   - **Sàn chặn dưới cứng:** `base_max = 15`. Không bao giờ bị tụt không phanh dưới mức tốt nghiệp.
3. **Khôi phục thông minh sau khi ra tù (Không mất trí nhớ):**
   - Hết án phạt, nick hoàn thành đủ 2 ca Hồi phục 1 và Hồi phục 2 để tốt nghiệp lại.
   - Ngay khi tốt nghiệp, hệ thống đọc lại `proven_safe_ceiling` (ví dụ 20 hoặc 22) và cấp thẳng lại mức này cho nick cày tiếp, không bắt nick phải bò lại từ mốc 10–15.

4. **Tương tác giữa Proven Safe Ceiling và Cohort Core Cap (Empirical Priority Invariant):**
   - *Cạm bẫy thiết kế:* Khi áp đặt giới hạn tĩnh của 3 Cohort (Rookie: 16, Mid: 22, Veteran: 30), nếu dùng `active_cap = min(core_cap, ...)` thì một nick non (video < 15 hoặc age < 60) đã từng cày an toàn và có `proven_safe_ceiling = 20` sẽ bị Cohort Rookie đè bẹp xuống 16, phá vỡ nguyên tắc không mất trí nhớ!
   - *Quy tắc bất biến:* Số liệu kiểm chứng thực tế (`proven_safe_ceiling`) của chính tài khoản LUÔN THẮNG giả định phân tầng tĩnh (`cohort core_cap`).
   - *Công thức chuẩn trong code:*
     $$\text{active\_cap} = \max\Big(\text{proven\_safe\_ceiling},\; \min(\text{core\_cap},\; \max(\text{base\_max},\; \text{active\_ceiling}))\Big)$$
   - Đảm bảo trần phiên `session_budget` luôn được bảo toàn ở mức tối thiểu bằng `proven_safe_ceiling` mà nick đã chứng minh an toàn trong quá khứ.

---

## 9. Mô Hình Học Hỏi Phân Tầng 3 Cohort (Stratified Cohort Learning) & Anchor Guard

### A. Bài toán Selection & Survivorship Bias:
- **Hiện tượng Row 1 vs Row 2:** Row 1 (nick già 200d, video 25+, following 100+) cày 5-9 lượt êm 100%. Row 2 (nick mỏng mới reg, video 11-15, following 0-6) bị nhả 82.6% ngay tại Anchor.
- **Cấm lấy số trung bình (Mean) gộp toàn farm:** Nick già kéo số liệu lên cao, đem áp cho nick non sẽ làm đàn nick non gãy hàng loạt.

### B. Ba Cohort phân loại TRƯỚC KHI CHẠY (`determine_cohort`):
1. **Cohort Rookie (Nick mỏng / non):**
   - Tiêu chí: `following < 30` HOẶC `video < 15` HOẶC `age < 60d`.
   - Quota trần: Hồi phục 1 = 4, Hồi phục 2 = 6, Nòng cốt = 16.
   - **Anchor Guard (Bắt buộc):** Nick có `following < 30` CẤM TUYỆT ĐỐI tap Anchor to (`following >= 150`) để triệt tiêu lỗi nhả 82.6% tại Anchor; chỉ được mồi chéo nick nhỏ để nâng following.
2. **Cohort Mid (Nick tầm trung):**
   - Tiêu chí: `following 30–100`, `video 15–25`, `age 60–180d`.
   - Quota trần: Hồi phục 1 = 4, Hồi phục 2 = 8, Nòng cốt = 22.
3. **Cohort Veteran (Nick cựu binh / già):**
   - Tiêu chí: `following > 100`, `video > 25`, `age > 180d`.
   - Quota trần: Hồi phục 1 = 5, Hồi phục 2 = 9, Nòng cốt = 30.

### C. Tiêu chí chọn mẫu & Bảo toàn tính đại diện (Consensus Spec V2):
- **Phân vị thận trọng (Conservative Quantile P20):** Chọn mức quota mà 20% nick yếu nhất trong cohort vẫn an toàn.
- **Ràng buộc an toàn cứng:** Drop rate của cohort phải $\le 8\%$ (T1) và $\le 10\%$ (T2).
- **Hysteresis chống giật cục:** Chỉ tăng/giảm tối đa 1 bước mỗi chu kỳ đánh giá, tránh dao động đột ngột.

### D. Chi Tiết Thi Công Runner & Pitfall Kiểm Thử (Code Invariants):
1. **Hàm `determine_cohort` trong `follow_state.py`:**
   - Input: `video_count: int | None`, `account_age_days: int | None`.
   - Đọc `tot_fl = len(self._data.get("followed", {}))`.
   - Phân tầng trả về `"rookie" | "mid" | "veteran"`.
   - Được gọi ngay đầu `_determine_budget_tier` để nạp bộ trần tương ứng (`t1_cap, t2_cap, core_cap`).
2. **Pitfall Test Fixture (Cohort Clamping Trap):**
   - *Hiện tượng:* Viết unit test cho tính năng Dò trần tăng tiến (Adaptive Ceiling 20–30) nhưng test fail ở `assert max(picks) == 20` vì `max(picks)` chỉ đạt `16` (hoặc `15`).
   - *Nguyên nhân:* Test fixture truyền `video_count=10, account_age_days=35` (thông số mặc định). Hàm `determine_cohort` phân loại nick vào `rookie`, và bộ phận bảo vệ an toàn tự động khóa cứng trần ở mức 16!
   - *Khắc phục:* Với các test kiểm tra dò trần vượt 16, test fixture BẮT BUỘC phải nạp profile Veteran chuẩn (`followed >= 120`, `video_count = 28`, `account_age_days = 200`).
3. **Anchor Guard trong `mode2_follow_followers.py`:**
   - Trong `_ensure_anchor_followed`, kiểm tra:
     ```python
     if getattr(engine.state, "determine_cohort", None) and engine.state.determine_cohort() == "rookie":
         engine._last_anchor_follow_outcome = "skipped_rookie_anchor_protection"
         return profile_xml
     ```
   - Tránh việc nick non bị ép follow các Anchor to ($\ge 150$ following) dẫn tới tỷ lệ nhả 82.6% làm dừng cả ca chạy; nick non vẫn đọc và follow danh sách người dùng con bên trong bình thường.



