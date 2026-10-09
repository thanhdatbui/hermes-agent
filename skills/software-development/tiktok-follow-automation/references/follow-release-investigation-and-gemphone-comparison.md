# Follow Release Investigation & GemPhoneFarm Comparison (2026-09-12)

## 1. Dữ liệu thực nghiệm 144 máy (Lịch sử Cooldown vs Tỷ lệ phục hồi)

- **Thống kê từ `runs/state/follow_state_*.json`**:
  - Tổng số máy từng dính cờ nhả follow (`fail_streak >= 1`): **127 / 144 máy (~88%)**.
  - Phân bố streak: `fail_streak=1`: 33 máy, `fail_streak=2`: 70 máy, `fail_streak=3`: 24 máy.
  - **Số máy từng tự động phục hồi thành công sau thời gian ngâm Cooldown:** **ĐÚNG BẰNG 0!**
  - **Kết luận thực tế:** Cooldown thời gian thuần túy (48h, 96h, 7 ngày) hoàn toàn **không có tác dụng tự gỡ cờ** nếu nguyên nhân gốc nằm ở Device Fingerprint / Clustering và Proxy.

## 2. Bản chất kỹ thuật: TikTok Risk Control Engine & Sự thật về "Trust Score" (Phản biện 2026-09-14)

- **Lý thuyết "Lướt feed + thêm like để tăng Trust Score gỡ nhả follow" là 70% Bro-Science (Kinh nghiệm truyền miệng):**
  - Không có bằng chứng hay cơ chế nào từ TikTok chấm điểm theo kiểu cộng dồn cơ học: `xem 1 video = +10 điểm, like = +5 điểm`.
  - Hệ thống Anti-Fraud của TikTok vận hành theo mô hình **Anomaly Detection (Phát hiện bất thường)** & **Behavioral Entropy**: Nó không quan tâm nick có like hay không, mà nó đo xem hành vi của cụm máy có dấu hiệu của trang trại (farm) do một người điều khiển hay không.
  - **Cảnh báo phản tác dụng:** Nếu hàng chục máy trong farm cùng chạy automation lướt feed theo một kịch bản rập khuôn (cùng nhịp quẹt, cùng khoảng thời gian xem, tap like phân bố đều), hệ thống AI của TikTok sẽ phát hiện **Behavior Fingerprint Similarity** $\rightarrow$ càng xác nhận rõ đây là bot farm.
- **Bản chất kỹ thuật của hiện tượng "Nhả Follow" (Follow Drop):**
  - Là **Optimistic UI + Async Backend Risk Validation**: Client hiển thị `Following` ngay lập tức để mượt UX, nhưng backend ném vào hàng đợi Risk Engine. Nếu risk score vượt ngưỡng, server **âm thầm rollback (`follow = false`)** mà không báo lỗi về client.
- **Trọng số thực tế của Risk Control (từ cao xuống thấp):**
  1. **Device Fingerprint & Clustering (⭐⭐⭐⭐⭐):** Chí mạng nhất. Cùng phần cứng, nhiều acc/máy, cùng profile thiết bị $\rightarrow$ bị gom vào High Risk Cluster.
  2. **Network / IP / Proxy Subnet (⭐⭐⭐⭐):** IP proxy bị gán nhãn datacenter hoặc nhiều máy chung subnet.
  3. **Behavioral Entropy (⭐⭐⭐⭐):** Độ hỗn loạn hành vi thấp (bot quẹt quá đều, không có tính ngẫu nhiên của con người).
  4. **Lịch sử & Tuổi tài khoản (⭐⭐⭐⭐):** Nick mới lập chưa đủ tuổi, chưa có quan hệ xã hội thật.
  5. **Số lượt Like / Xem video (⭐⭐):** Chỉ là tín hiệu phụ ở Recommendation model, **không phải chìa khóa vượt qua tầng Anti-Fraud**.
- **Nick dính streak 2-3 lần (Burned Assets):**
  - Khi dính streak 2-3 lần, tài khoản bị đưa vào **High Scrutiny Bucket**. Ngưỡng duyệt follow bị siết cực chặt.
  - Ngâm cooldown 7 ngày trên **chính chiếc điện thoại cũ trong farm** không giải quyết được vấn đề vì TikTok vẫn nhận diện ra Device Cluster cũ. Ngay cú click follow đầu tiên sau khi hết cooldown sẽ bị drop tiếp 100%.

## 2b. Xử lý Thẻ Gợi ý "Follow lại" trên Feed (feed_swipe_smoke.py)
- **Quy tắc điều phối phân nhánh (2026-09-14):**
  - **Nick sạch (`is_account_in_follow_cooldown == False`):** Bấm trực tiếp nút **"Follow lại"** / **"Theo dõi lại"** để nhận tương tác tự nhiên.
  - **Nick đang bị phạt (`is_account_in_follow_cooldown == True`):** Bấm nút **"Không quan tâm"** để tránh bị server drop follow và gia hạn thêm án phạt.

## 2c. Phân tích Kỹ thuật ByteDance Security SDK (`libmetasec_ml.so` / Bdturing)
- **Cơ chế phát hiện Touch Injection từ ADB Shell:**
  1. **Lực nhấn (`Pressure`):** ADB shell luôn phát ra `pressure = 1.000` cố định (phương sai variance = 0), trong khi ngón tay người dao động liên tục từ 0.1 đến 0.8.
  2. **Diện tích tiếp xúc (`Touch Major / Minor / Size`):** ADB shell tạo sự kiện với `size = 0, major = 0`, thiếu hoàn toàn bầu ngón tay sinh học (`major ~ 7.4px, minor ~ 5.2px`).
  3. **Đặc tính gia tốc (Biomechanics / Jerk):** Lệnh vuốt ADB có vận tốc đều tăm tắp (`velocity variance = 0`), đường kẻ thẳng tắp $dx = 0$ tạo thành chữ ký bot (synthetic signature) rất dễ bị phân loại.
  4. **Giải pháp đối phó trong Python Runner:**
     - Vuốt nghiêng tự nhiên (`Natural Thumb Drift`): `start_x` trong [465, 525], ngón tay lệch tự nhiên [-18px, +12px] nằm trong hành lang an toàn [450, 540], phá vỡ hoàn toàn chữ ký $dx = 0$.
     - Tăng Entropy hành vi: Thêm tính năng Bookmark video sau khi thả tim (15-30%) và Comment Peek mở đọc lướt bình luận trên các video Deep Inspect (12%).

## 2b. Lớp Warmup Nhẹ Sau Cooldown (Post-Cooldown Recovery)

- **Nguyên tắc sống còn:** Tuyệt đối không cho nick vừa hết cooldown (1 ngày, 4 ngày, 7 ngày) chạy full budget (15–18 nick) ngay lập tức.
- **Quy trình Warmup:**
  - Phiên đầu tiên sau khi hết cooldown chỉ cấp **budget thăm dò: 3–5 nick**.
  - Kéo giãn khoảng cách delay giữa các lần follow lên **8–15 giây**.
  - Tăng thời lượng xem video feed và anchor lên **15–20 giây**.
  - Nếu phiên thăm dò pass thành công -> reset `fail_streak = 0`, phục hồi budget bình thường cho các phiên tiếp theo. Nếu nhả ở nick #1 -> phanh dừng ngay mà không bị phạt thêm streak.

## 3. Kiến trúc Verify Follow 2 tầng (Anti-Release Protocol)

User correction & invariant đã kiểm chứng thực tế:

### Tầng 1: Anchor (Seed Profile)
- **Hành vi tương tác:**
  - Vào Profile Anchor -> Quét video. Nếu không có video -> Back ra ngay (safe-skip).
  - **LƯU Ý PHÂN LOẠI RESULT (Watchdog Reporting):** Khi Anchor không có video, đây là hành vi **hợp lệ (Safe-Skip)** theo thiết kế, KHÔNG PHẢI lỗi script. Trạng thái trả về phải là `status="SKIPPED"` (hoặc exit code 0) để watchdog báo cáo vào nhóm "Bỏ qua", tránh bị gắn mác "Lỗi script/xác minh" gây báo động giả toàn farm.
  - **Pitfall Anchor Pool:** Anchor chỉ lấy từ pool Tik1/Tik2 (Row 1-2). Cần audit định kỳ `taikhoan_run_safe.xlsx` cột `Video Đã Đăng` (hoặc `video_count >= 5`). Những nick mới chưa đăng đủ video hoặc bị mất video cover sẽ kích hoạt Video Gate skip hàng loạt (ví dụ: 12 máy cùng skip vì bốc phải anchor chưa có video).
  - Bấm mở 1 video của Anchor -> Xem đủ 8–15s (random dwell) -> Thả tim ngẫu nhiên (50%–70%).
  - Bấm nút Follow trực tiếp trên màn hình video player (nút dấu `+` đỏ tại avatar).
  - Chờ 2–4s cho server TikTok nhận rồi bấm `adapter.back()` quay lại trang Profile Anchor.
- **BẮT BUỘC PULL-TO-REFRESH TẠI ANCHOR:**
  - Khi back từ video player ra Profile, app TikTok Android vẫn giữ cache local nút "Nhắn tin" trong Activity stack (tưởng là ăn).
  - **Bắt buộc phải vuốt kéo reload (Pull-to-refresh) + sleep 3.5s**: Chỉ khi reload thì app mới đồng bộ server state thật. Nếu bị nhả, nút sẽ nhảy ngược về màu đỏ `Follow` -> bắt được lỗi nhả và dập tắt session ngay tại cửa Anchor!

### Tầng 2: List Following của Anchor (`_path_b_verify`)
- **TUYỆT ĐỐI KHÔNG BỎ `_path_b_verify` & BẮT BUỘC VERIFY 100% NICK (`verify_sample_every: 1`):**
  - Đây là tấm khiên chặn đứng tình trạng "trên list hiện đã follow nhưng server âm thầm drop, máy vẫn cắm đầu bấm tiếp 15 nick rác".
- **Cơ chế hoạt động & Chuẩn hóa xác thực Server trên List Row (2026-09-20):**
  1. **Mở Profile con qua Username Tap:**
     - Tìm exact row của UID trên danh sách Following -> tap vào `username_node` để điều hướng sang Profile Activity.
  2. **Ngẫu nhiên hóa Dwell Time & Xem video (`_maybe_watch_profile_video`):**
     - Tỷ lệ ~30% (1 trong 3-4 nick) kích hoạt xem video trước khi kết thúc verify profile:
       - **Chọn video ngẫu nhiên:** Không tap cố định `video_covers[0]`, lấy ngẫu nhiên trong danh sách cover: `random.choice(video_covers[:min(len(video_covers), 6)])`.
       - **Phân phối xem nhiều video (Behavioral Entropy):** 70% dừng ở 1 video (6–12s), 25% vuốt xem tiếp video thứ 2 (4–8s), 5% vuốt xem tiếp video thứ 3 (3–6s).
       - **Tương tác ngẫu nhiên:** Thả tim 30–50% xác suất khi xem video.
       - **Khôi phục an toàn:** Khối `finally/except` luôn gọi `adapter.back()` quay về lại màn hình Profile đối phương.
  3. **Xác thực Server 2 chiều trên List Row (List Row Server-Validation Protocol):**
     - Sau khi tương tác/xem video trên Profile con, nếu profile chưa follow -> bấm Follow trực tiếp trên Profile.
     - Bấm `adapter.back()` quay lại danh sách Following, poll cho đến khi `_on_follower_list(nodes)` phục hồi.
     - Tìm lại đúng dòng của `uid` trên RecyclerView và kiểm tra trạng thái nút qua `_classify_row_button`:
       - **`followed` (Đã follow / Bạn bè / Following):** Backend TikTok đã ghi nhận follow thành công vào cơ sở dữ liệu sau network roundtrip -> Trả về `followed`.
       - **`not_followed` (Follow / Follow lại):** Backend TikTok đã âm thầm rollback (Async Risk Control Drop) -> Ngay lập tức gọi `state.set_follow_failed()` và fail-closed dừng session ngay để tránh dính thêm án phạt.
- **Cảnh báo Pitfall Cadence Spot-Check & Bắt buộc Verify 100% từng nick (`verify_sample_every: 1`):**
  - **Nguyên nhân bug follow mù 4 nick liên tiếp (2026-09-18):**
    - List following trên TikTok dùng **Optimistic UI**: sau khi tap Follow, nút đổi sang "Đang theo dõi" / "Bạn bè" ngay trên RecyclerView. `_classify_row_button` đọc thấy `followed` nên cho qua.
    - TikTok Backend âm thầm drop follow (Async Risk Engine). Trừ khi mở Profile (`_path_b_verify`), app không reload server state trên list row.
    - Nếu để `verify_sample_every: 5` (hoặc cadence spot-check): khi đã follow Anchor trước đó (`used = 1`), các nick 1, 2, 3, 4 trong list đều có `sample = False`, dẫn tới bot tin tưởng UI list và bấm liên tiếp 4 nick bị nhả mà không hề hay biết (báo cáo ảo).
  - **Quy tắc Invariant bắt buộc:** BẮT BUỘC đặt `verify_sample_every: 1` (100% mọi nick đều mở profile qua `_path_b_verify` để kiểm tra thật trước khi sang nick tiếp theo). Nếu nhả ở bất kỳ nick nào -> phanh dừng session ngay lập tức với 0 nick rác.
    - TikTok Backend âm thầm drop follow (Async Risk Engine). Trừ khi mở Profile (`_path_b_verify`), app không reload server state trên list row.
    - Nếu để `verify_sample_every: 5` (hoặc cadence spot-check): khi đã follow Anchor trước đó (`used = 1`), các nick 1, 2, 3, 4 trong list đều có `sample = False`, dẫn tới bot tin tưởng UI list và bấm liên tiếp 4 nick bị nhả mà không hề hay biết (báo cáo ảo).
  - **Quy tắc Invariant bắt buộc:** BẮT BUỘC đặt `verify_sample_every: 1` (100% mọi nick đều mở profile qua `_path_b_verify` để kiểm tra thật trước khi sang nick tiếp theo). Nếu nhả ở bất kỳ nick nào -> phanh dừng session ngay lập tức với 0 nick rác.

## 4. Đối chiếu với Script Gốc GemPhoneFarm (`TIKTOK-FLOW-TÌM-KIẾM` & `TIKTOK-Nuoi-Tai-Khoan-Goc`)
- **Phân tích 3 bộ script gốc (2026-09-14):**
  - `TIKTOK-FLOW-TÌM-KIẾM-Thành-đạt_decrypted.json` (389 nodes): Luồng search & follow target.
  - `TIKTOK-Nuoi-Tai-Khoan-Goc_decrypted.json_decrypted.json` (205 nodes): Luồng lướt nuôi 3 tab.
  - `TIKTIK-ĐĂNG-VIDEO-Đạt_Decrypted.gemphonefarm` (64 nodes): Luồng đăng video hàng ngày.
- **Bí mật timing & nhịp độ follow của GemPhoneFarm giúp tránh bị nhả follow:**
  1. **Dwell Time ngâm Profile trước khi bấm Follow:** Khi search ra đối phương và bấm mở Profile, script GemPhone không bấm follow ngay mà ngâm từ **5.8s đến 12.5s** (Node delay `5812, 12549` ms) để tải hoàn toàn dữ liệu và mô phỏng xem thông tin người dùng.
  2. **Delay chờ server nhận:** Sau khi bấm nút Follow, chờ **1.8s đến 5.6s** (Node delay `1814, 5654` ms).
  3. **Pull-to-refresh xác minh + ngâm Profile sau follow:** Node `n9vr5cu` vuốt kéo reload (từ Y=115 xuống Y=1650) sau khi thấy chữ *"Gửi .."* hoặc *"Bạn bè"*, sau đó lướt xem tiếp 2 lượt video trên Profile đối phương trước khi bấm Home.
  4. **Giãn cách giữa 2 lần follow:** Node `rf10473` quy định khoảng nghỉ giữa 2 lần follow lên tới **5.1s đến 29.5s** (`time: 5142, 29521` ms). Không bao giờ tap follow liên tục.
  5. **Tỷ lệ lướt nuôi 3 tab:** Phân bổ đều giữa Đề xuất (`Random21`, xem 2.6s–8.2s), Đã follow (`Random31`, xem 3s–10s) và Bạn bè (`Random41`, xem 2s–6s). Thả tim ngẫu nhiên 20%–50% (`%_Tim`).
  6. **Bản chất cơ chế cử chỉ (Gestures):** GemPhone chạy bằng Android Accessibility Service (`GestureDescription`), hệ điều hành tự mô phỏng gia tốc và độ nảy ngón tay. Trong khi ADB shell (`input swipe`) đi theo đường thẳng cứng nhắc. Cần tránh các luật ép `dx = 0` thẳng tắp 100% gây lộ dấu hiệu bot.
- **Thực tế về việc "Đăng video đều là follow được":**
  - Đối soát thực tế trên farm ta: **170 / 176 nick dính phạt nhả follow (streak >= 1) đều đã đăng trên 5 video (trung bình 10.9 video, có nick đăng 23 video vẫn dính streak 3)**.
  - Do đó, đăng video đều **chưa đủ** để tự động gỡ cờ nếu nhịp độ follow trong script quá dồn dập (dưới 3-5s) và thiếu thời gian ngâm Profile đối phương như script gốc GemPhone.
  - Bài học: Khi chạy follow, bắt buộc áp dụng đúng nhịp độ của GemPhone (ngâm Profile 6-12s trước khi tap, delay 3-5s sau tap, Pull-to-refresh verify và delay 15-30s giữa các target). Bổ sung ngẫu nhiên hóa tỷ lệ thả tim bạn bè/following thay vì để cố định.

## 5. Dữ liệu thực nghiệm 210 tài khoản: Vì sao Hard Gate bắt buộc >= 10 video (CẤM hạ xuống 5 video)

- **Hiện trường thực tế đợt chạy Row 4 (2026-09-14) khi nick vừa đạt trung bình ~5.2 video:**
  - Toàn bộ **32 / 32 nick Row 4** (độ tuổi video từ 2 – 8 video, tập trung quanh 5–7 video) khi cho kích hoạt follow:
    - Tỷ lệ dính phạt nhả follow: **32 / 32 nick (100% dính `fail_streak > 0`)**.
    - Số lượt follow thành công tích lũy: **Đúng bằng 0** (vừa tap follow thì TikTok backend rollback và giam cờ phạt).
    - Toàn bộ 32 nick bị khóa cứng vào hàng đợi Cooldown cách ly.

- **Bảng phân tích đối soát toàn diện 210 tài khoản từ `runs/state/follow_state_*.json`:**
  | Phân nhóm Video Đã Đăng | Tổng số acc | Từng dính cờ phạt nhả follow | Đang kẹt trong Cooldown | Tổng follow thành công tích lũy | Đánh giá rủi ro |
  | :--- | :---: | :---: | :---: | :---: | :--- |
  | **1 – 4 video** | 17 acc | **88.2%** (15/17) | **94.1%** (16/17) | 4 lượt | Tê liệt gần như 100%. |
  | **5 – 9 video** | 77 acc | **50.6%** (39/77) | **41.6%** (32/77) | 547 lượt | Rủi ro cực cao, >50% nick bị nhả và ăn phạt. |
  | **$\ge$ 10 video** | 115 acc | Có phát sinh theo đợt | Đang hồi phục | **9.003 lượt** (avg 90 fl/acc) | Cột trụ an toàn gánh >90% sản lượng follow toàn farm. |

- **Kết luận Invariant (Quy tắc thép):**
  - **Tưởng nhanh hóa chậm:** Ép nick 5 video đi follow sớm sẽ kích hoạt Silent Follow Drop $\rightarrow$ dính phạt `fail_streak` $\rightarrow$ bị giam Cooldown 48h $\to$ 4 ngày $\to$ 7 ngày. Thời gian tài khoản bị kẹt cấm follow và "chữa bệnh" còn dài hơn gấp nhiều lần so với việc kiên nhẫn đăng đủ 10 video mồi.
  - **Hard Gate `>= 10` video là bất khả xâm phạm:** Nick dưới 10 video chỉ thuần lướt nuôi gốc + đăng bài tạo độ dày kênh; chỉ khi $\ge 10$ video mới mở quyền follow chéo.
