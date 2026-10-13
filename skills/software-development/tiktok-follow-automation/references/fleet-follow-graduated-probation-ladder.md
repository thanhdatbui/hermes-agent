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

### Nhóm 2: Tân Binh & Nick Có Tiền Án (Bắt buộc đi qua lộ trình 2 nấc accelerated: 2 ca/stage)
- **Quy tắc Tân Binh (USER INVARIANT):** Nick mới đủ Dual Gate (`age >= 21d`, `video >= 6`) nhưng chưa từng đi follow hoặc chưa tích lũy đủ follow an toàn (`< 15` follows, chưa có cờ `graduated`) đi dò với Quota 1–2 lượt. Bị nhả chỉ phạt cá nhân (tăng fail_streak, cooldown 3-14 ngày dưỡng sinh), **CẤM TUYỆT ĐỐI GIẬT CẦU DAO IP** (xem chi tiết `references/tier-aware-circuit-breaker-and-accelerated-probation.md`).
- **Quy tắc Nick Ra Tù:** Nick vừa hết hạn cooldown quay lại thử thách với Quota 1–2 lượt.

Áp dụng lộ trình 2 nấc thang tính theo số ca/ngày chạy sạch (`probation_clean_days` - 2 ca sạch / nấc; mỗi stage chỉ đúng 2 lần chạy hoàn thành là thăng cấp):

* **HỒI PHỤC 1 (Probation Tier 1 - Tân binh khởi động & Nick mới ra tù, `clean_days < 2`):**
  - **Quota:** 1 – 2 follows / ca (đồng nhất cho cả tân binh và nick ra tù).
  - **Tiến độ thực tế:** Cần đúng 2 ca chạy sạch hoàn thành để thăng lên Hồi phục 2 (`sessions_needed = max(1, 2 - clean_days)`).
  - **Hiển thị Badge Thận trọng:** Tối đa 2 ca (`🛡️ Thận trọng (2 ca)` khi mới vào nấc, giảm còn `1 ca` sau 1 ca sạch). CẤM TUYỆT ĐỐI để công thức cũ `3 - clean_days` văng ra 3 ca gây mâu thuẫn với nhãn `0/2 ngày`.

* **HỒI PHỤC 2 (Probation Tier 2 - Tăng tải an toàn, `2 <= clean_days < 4`):**
  - **Quota:** 5 – 8 follows / ca.
  - **Tiến độ thực tế:** Cần thêm đúng 2 ca chạy sạch tiếp theo để tốt nghiệp (`sessions_needed = max(1, 4 - clean_days)`).
  - **Hiển thị Badge Thận trọng:** Tối đa 2 ca (`🛡️ Thận trọng (2 ca)`).

* **NẤC 3 (Tốt nghiệp - Graduation, `clean_days >= 4`):**
  - Sau tổng cộng 4 ngày/ca chạy sạch (~8 – 9 ngày ngoài đời thực).
  - Hệ thống chính thức tốt nghiệp (`graduated = True`, `fail_streak = 0`, xóa `probation_clean_days`), thăng hạng lên Nhóm Nick Khỏe (Full Budget 10 - 20 lượt).
  - **Cầu Dao IP (Tier-Aware Breaker):** CHỈ KHI NICK ĐÃ TỐT NGHIỆP (`was_graduated is True`) BỊ NHẢ mới kích hoạt ngắt Cầu dao IP 48h (`trip_ip_breaker`). Nick chưa tốt nghiệp (Tân binh, Hồi phục 1 & 2) bị nhả chỉ phạt Cooldown account, KHÔNG ngắt IP breaker (`[IP_BREAKER_SKIPPED_TIER]`).

* **CHỐT AN TOÀN FAIL-CLOSED & PROGRESSIVE BACKOFF STREAK:**
  - Nếu ở bất kỳ nấc nào (`Hồi phục 1` hay `Hồi phục 2`) mà bị TikTok nhả follow (`set_follow_failed()`) hoặc không follow được:
  - Lập tức xóa `probation_clean_days = 0`, tăng `fail_streak` (Streak 1 -> Streak 2 -> Streak 3+).
  - Đưa vào Cooldown theo Progressive Backoff:
    * `fail_streak = 1`: Giam 3 ngày (quota = 0).
    * `fail_streak = 2`: Giam 7 ngày (quota = 0).
    * `fail_streak >= 3`: Giam 15 ngày (quota = 0).
  - Khi mãn hạn Cooldown: Bắt buộc quay lại từ vạch xuất phát `Hồi phục 1` (1 - 2 lượt/ca). Nếu chạy sạch 2 ngày -> lên `Hồi phục 2` (5 - 8 lượt/ca) -> chạy sạch thêm 2 ngày -> tốt nghiệp lên `Khỏe` (10 - 20 lượt/ca). Nếu tại bất kỳ nấc nào bị nhả tiếp thì tiếp tục tăng `fail_streak` và quay lại Cooldown dài hơn.
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
    * **CẤM tạo thêm hàng nút chọn nhóm lặp lại ở phía dưới (loại bỏ redundancy):** Khi 4 thẻ KPI đã có đủ chức năng và số liệu, việc tạo thêm một hàng nút chọn nhóm phía dưới là dư thừa và làm rối mắt. Xóa bỏ hàng nút dưới, chỉ giữ lại thanh tìm kiếm `🔍 Tìm máy hoặc username...` và tiêu đề danh sách rõ ràng.
    * Bấm vào thẻ KPI nào là lập tức kích hoạt lọc và **tự động cuộn mượt (`scrollIntoView`)** xuống thẳng danh sách máy của nhóm đó, không bắt người dùng phải kéo tay tìm kiếm.
    * Có highlight trực quan (`.active`) trên thẻ KPI đang được chọn.
  - Mặc định khi mở tab phải chọn ngay nhóm **`[💪 Khỏe]`** để hiển thị ngay dàn nick nòng cốt sạch đẹp.
  - Hiển thị danh sách dạng **Lưới thẻ gọn gàng (Compact Cards Grid)**: Mỗi thẻ ghi rõ Máy & Row (`M1 (Row 1)`), `@username`, Trạng thái sức khỏe, và Hạn ra tù / Ngày sạch.
  - **Link trực tiếp đến profile TikTok (USER INVARIANT):** Trên mỗi thẻ nick, `@username` BẮT BUỘC phải là link `<a>` (`href="https://www.tiktok.com/@username" target="_blank"`) kèm icon `↗` và `📈` để người dùng chạm vào là bung ngay ra trang cá nhân của nick đó trên TikTok, giống như ngoài Dashboard chính. Tuyệt đối cấm để username dạng text tĩnh không click được.
  - Tích hợp ô tìm kiếm nhanh (theo số máy `m1`, `18` hoặc `username`).
  - **Deduplication:** Tự động lọc bỏ các file state legacy không có `_row_` (như `follow_state_1.json`) để không bị duplicate dòng hiển thị trên Dashboard.
  - **Quy chuẩn Adaptive Recovery Badge (USER INVARIANT - 2 Ca / Stage):**
    * Thẻ hiển thị huy hiệu `recBadge`:
      - `⚡ Fast-track (1 ca)`: Cho nick điểm tín nhiệm cao ($\ge 60$đ).
      - `🛡️ Thận trọng (2 ca)`: Cho nick điểm tín nhiệm thấp ($< 60$đ) hoặc nick mới.
    * **Công thức `sessions_needed`:**
      - Hồi phục 1: `sessions_needed = max(1, 2 - clean_days)` (tối đa 2 ca).
      - Hồi phục 2: `sessions_needed = max(1, 4 - clean_days)` (tối đa 2 ca).
      - Fallback record (`farm_account_info`): BẮT BUỘC để `sessions_needed = 2`. CẤM TUYỆT ĐỐI để fallback 3 ca cũ gây mâu thuẫn giữa nhãn `(0/2 ngày)` và badge `Thận trọng (3 ca)`.

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
   - Hiển thị rõ dạng tiến độ: `X/2 ca sạch` và `Cần thêm Y ca sạch để lên Cấp tiếp theo`.
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
