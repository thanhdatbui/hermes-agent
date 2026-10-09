# Case UI-82: Path B False Positive Do Bắt Nhầm Nhãn Thống Kê Profile (`text="Đã follow"` trên `id/t_q`)

> 📌 **Bối cảnh (2026-10-01)**: 
> Sau khi điều tra thắc mắc của User về báo cáo ca trưa (Ca 2) bị lệch dữ liệu đối soát nặng nề:
> - Script báo cáo hoàn thành: **220 lượt follow** (Ca 2 P1: 120 lượt, Ca 2 P2: 100 lượt).
> - TikTok Web cào đối soát chỉ tăng: **+9 lượt** (M21 tăng +8, M8 tăng +1, toàn bộ 10 máy còn lại tăng +0).
> - **Lệch thực tế: -211 lượt follow (-96%)**.
> - Đọc trực tiếp hiện trường `ui.xml` trên máy thật (Máy 9 - `@dokieu203` lúc 12:47): `follow_result.json` báo đã follow 18 nick, nhưng trên Profile máy thật số người đang follow hiển thị: `text="1"`, `text="Đã follow"`. Tức là 18 lượt follow hoàn toàn không hề ăn vào server TikTok!

---

## 1. Cơ Chế Lừa Đảo Của TikTok & Mục Đích Ban Đầu Của Path B

1. **Optimistic UI Của TikTok:**
   - Khi bot tap nút Follow trên danh sách follower (Mode 2 RecyclerView), app TikTok client-side tự động chuyển trạng thái nút sang *"Đang theo dõi"* / *"Bạn bè"* ngay lập tức để tạo trải nghiệm mượt mà, **ngay cả khi server TikTok đã âm thầm chặn (Silent Action Block / Drop Follow ngầm)** do nick bị giới hạn hành vi hoặc proxy bị gắn cờ.
2. **Vai Trò Thiết Kế Của Path B:**
   - Để triệt tiêu việc bị Optimistic UI đánh lừa, runner xây dựng hàm `_path_b_verify(engine, row_node, uid)`:
   - Tap vào username để mở Profile cá nhân của người vừa follow $\rightarrow$ Đọc trực tiếp nút hành vi trên Profile đó (nếu TikTok server drop follow thì trên Profile nút vẫn là màu đỏ *"Follow"* / *"Follow lại"*).

---

## 2. Lỗ Hổng Trọng Yếu Trong Code (`_classify_profile_action`)

Trong file `D:/Taadaa/tiktok-follow/follow_runner/flows/mode2_follow_followers.py`:

```python
def _classify_profile_action(xml_text: str) -> str:
    from .verify_follow import classify_button
    res = classify_button(xml_text)
    if res == "unknown":
        try:
            nodes = _parse_mode2_nodes(xml_text)
            followed_kw = {
                "nhắn tin", "send message", "đang theo dõi", "message",
                "following", "đã follow", "gửi tin nhắn", "friends", "bạn bè"
            }
            not_followed_kw = {"follow lại", "follow", "theo dõi"}
            has_follow_btn = False
            has_followed_btn = False
            for n in nodes:
                b = n.get("bounds")
                if not b or b[1] >= 1200:
                    continue
                vals = {
                    (n.get("text") or "").strip().lower(),
                    (n.get("content_desc") or "").strip().lower(),
                }
                vals.discard("")
                if vals & not_followed_kw:
                    has_follow_btn = True
                if vals & followed_kw:
                    has_followed_btn = True

            if has_followed_btn and not has_follow_btn:
                return "followed"
        except Exception:
            pass
    return res
```

### Tại Sao Lỗ Hổng Này Gây Dương Tính Giả (False Positive) 100%?
1. Trên giao diện TikTok tiếng Việt, cột thống kê số lượng tài khoản đang follow của chủ kênh luôn mang nhãn text:
   `<node index="1" text="Đã follow" resource-id="com.ss.android.ugc.trill:id/t_q" bounds="[36,537][204,582]" />` (hoặc `id/sdn`, `id/shq`).
2. Nhãn này nằm ở toạ độ `b[1] = 537 < 1200`.
3. Khi `classify_button` trả về `"unknown"` (do TikTok 46/47 làm mờ clickable hoặc đổi layout action button), nhánh fallback được kích hoạt.
4. Nhánh fallback duyệt qua node thống kê này và thấy chữ `"đã follow"` nằm trong `followed_kw` $\rightarrow$ gán `has_followed_btn = True`.
5. Đồng thời, nút follow thật của người đó có thể là icon hoặc id khác không khớp danh sách `not_followed_kw` $\rightarrow$ `has_follow_btn = False`.
6. Hệ quả: Điều kiện `if has_followed_btn and not has_follow_btn:` **LUÔN LUÔN ĐÚNG TRÊN 100% PROFILE TIKTOK TIẾNG VIỆT**!
7. `_classify_profile_action` trả về `"followed"` $\rightarrow$ `_path_b_verify` kết luận follow thành công $\rightarrow$ runner báo thành công khống hàng trăm lượt follow ảo!

---

## 3. Quy Tắc Bắt Buộc Để Sửa Dứt Điểm (Remediation Contract)

1. **Tuyệt Đối Không Phân Loại Bằng Text Quét Mù Toàn Màn Hình:**
   - CẤM duyệt tìm `text="Đã follow"` ở bất kỳ node nào có class là `TextView` thuộc khối header thống kê (`id/t_q`, `id/sdn`, `id/shq`, `id/svt`, `id/suu`, `id/t1i`, `id/t1h`).
2. **Chỉ Chấp Nhận ACTION BUTTON Thực Sự:**
   - Nút quan hệ thực tế trên profile bắt buộc phải thuộc các ID hành động đã kiểm chứng (`id/fds`, `id/ff8`, `id/flo`, `id/fij`, `id/fi6` hoặc button có `clickable="true"` và nằm dưới hàng tiểu sử/avatar).
   - Nếu `classify_button` trả về `"unknown"`: Phải đối chiếu với whitelist resource-id của action button, TUYỆT ĐỐI không được fallback bằng cách tìm từ khóa trên các node nhãn thống kê.
3. **Phát Hiện Silent Action Block & Cooldown Sớm:**
   - Khi bot tap follow mà số liệu following thật trên app không nhảy, hoặc sau phiên đối soát web phát hiện lệch liên tiếp:
   - Runner phải lập tức chuyển status thành `FOLLOW_FAILED` / `ACTION_BLOCKED`.
   - Ghi cooldown cho nick đó nghỉ ít nhất 24h-48h, cấm tiếp tục tap follow mù làm hỏng độ trust của tài khoản.

---

## 4. Quy Trình Xác Minh Khi User Thắc Mắc "Script Check Có Báo Sai Không?" & Canary Safety

Khi User nghi ngờ số liệu đối soát bị lệch do script check báo sai:
1. **Kiểm Tra Trạng Thái Vận Hành Farm (CẤM CHẠY CANARY MÙ):**
   - Trước khi nhận lệnh chạy Canary kiểm tra, BẮT BUỘC kiểm tra farm có đang trong ca chạy không (`D:/Taadaa/runtime/kibe/live/<today>/<active_batch>/`).
   - Nếu farm đang chạy ca nuôi (ví dụ Ca 3 Row 5), CẤM TUYỆT ĐỐI chạy canary hay sửa đè code chiếm lock máy làm gián đoạn batch. Bắt buộc báo cáo rõ hiện trường bận và hẹn mốc an toàn sau ca.
2. **Đối Soát Tam Giác 3 Lớp (Triple-Source Telemetry Corroboration):**
   - **Lớp 1 (Runner Self-Report):** `follow_result.json` của máy (ví dụ M11 báo `followed_count: 5`, M9 báo `followed_count: 18`).
   - **Lớp 2 (Server Public Snapshot):** Bảng `snapshots` trong `tiktok_tracker.db` cào qua Web TikTok trước và sau phiên (ví dụ `@dokieu203` và `@juliatbxcy6` đều có `following = 0` hoặc đứng yên không đổi).
   - **Lớp 3 (On-Device Ground Truth):** File XML chụp trên máy thật tại `artifacts/.../verify_profile/ui.xml` đọc số `text` trên node `id/t_r` và `id/t_q`.
3. **Phán Quyết "Báo Sai" vs "Drop Thật":**
   - Nếu Lớp 2 (Web) VÀ Lớp 3 (App thật) đều KHÔNG TĂNG nhưng Lớp 1 (Runner) báo TĂNG ➔ Script check đối soát báo LỆCH là **CHÍNH XÁC 100%**. Đây là Silent Action Drop / False Positive do runner bị lừa, KHÔNG PHẢI lỗi script check.
   - Chỉ khi Lớp 3 (App thật) đã tăng mà Lớp 2 (Web) không tăng mới là delayed cache web; nếu cả 2 đều không tăng thì chắc chắn follow chưa từng được server ghi nhận.

---

## 5. Giao Thức Giành Lock Chạy Canary An Toàn Giữa Ca (Mid-Shift Preemption Canary Protocol)

Khi User ra lệnh cưỡng chế chạy Canary ngay lập tức giữa ca (`"Đéo đợi. Giành lock chạy canary cho tao"`):

1. **Tuyệt Đối Không Phản Kháng Bằng Cách Đóng Băng / Từ Chối:**
   - Khi User đã phát lệnh giành lock, Coordinator PHẢI kích hoạt quy trình can thiệp có kiểm soát, KHÔNG được tiếp tục bảo thủ "ngồi đợi 15-20 phút".
2. **Kỹ Thuật Chọn Máy Rảnh (Idle Target Selection):**
   - CẤM giành lock trên máy đang có tiến trình con active trong batch (như các máy đang có PID `run_follow` hay đang swipe feed).
   - Dùng lệnh O(1) `python D:/Taadaa/tools/inspect_machine.py <N>` để rà soát máy trong cụm.
   - CHỈ ĐƯỢC CHỌN máy thỏa mãn 3 điều kiện: (a) Màn hình đang `OFF (Sleep/Dozing)` hoặc `LauncherActivity`, (b) Không có tiến trình con `run_follow` / `python_runner` đang chạy trên máy đó trong bảng tiến trình OS (`psutil`), (c) Máy không bị offline ADB.
3. **Cấu Hình Canary Cô Lập Ngân Sách O(1) Cực Nhỏ:**
   - CẤM dùng config production full-budget (`config.example.yaml` hay config chạy 20-40 follow).
   - BẮT BUỘC tạo config canary riêng `config/canary_machine<N>.yaml`:
     ```yaml
     mode: "2"
     budget_per_session: 1
     budget_per_session_min: 1
     budget_per_session_max: 1
     delay_min: 1
     delay_max: 3
     inter_follow_delay_min: 5
     inter_follow_delay_max: 10
     verify_sample_every: 1
     ```
4. **Tham Số Dòng Lệnh Bắt Buộc:**
   - `python -m follow_runner.run_follow --machine <N> --config config/canary_machine<N>.yaml --account-row-index <R> --force-preempt --skip-identity-verify`
   - Cờ `--force-preempt`: Chiếm quyền lock an toàn duy nhất trên máy rảnh đó, phá stale lock nếu có mà không động chạm đến các máy khác của farm.
5. **Kỷ Luật Chạy Lệnh Nền (Terminal Background Requirement):**
   - Vì runner trên máy thật mất 1 - 3 phút để khởi động app, search/open anchor và follow 1 lượt, lệnh này sẽ vượt quá 60s.
   - BẮT BUỘC chạy qua `terminal(background=True, notify_on_complete=True)` để không vi phạm `GUARD_FOREGROUND_TIMEOUT_EXCEEDED`. Báo ngay session ID và PID cho User để theo dõi.

---

## 6. Cạm Bẫy Cấu Hình Canary: `feed_timeout_seconds` vs `reserve_seconds` Gây Ra Silent Zero Follow

Một cạm bẫy cấu hình cực kỳ tinh vi khiến Canary chạy xong báo `status: OK`, `failed: false`, `exit_code: 0` nhưng số lượng follow lại bằng `0` (`followed: []`):

### Cơ Chế Lỗi:
1. Trong file config máy thật (ví dụ `config/machine8.yaml` hoặc khi clone sang `config/canary_machine8.yaml`):
   ```yaml
   feed_timeout_seconds: 90
   ```
2. Trong `FollowEngine.__init__` (`follow_engine.py`):
   ```python
   raw_feed_timeout = getattr(cfg, "feed_timeout_seconds", 1200.0)
   self.feed_timeout_seconds = float(raw_feed_timeout if raw_feed_timeout is not None else 1200.0)
   ```
   Giá trị 90s từ config này được gán làm thời lượng tối đa cho **toàn bộ phiên follow của engine**!
3. Trong `has_time_for_next_action(reserve_seconds: float = 180.0)`:
   ```python
   def has_time_for_next_action(self, reserve_seconds: float = 180.0) -> bool:
       remaining = self.feed_timeout_seconds - elapsed
       return remaining > float(reserve_seconds)
   ```
4. Khi bắt đầu vòng lặp follow trong `run_mode2` hoặc `run_mode1`:
   - Ngay ở giây thứ 0, `remaining = 90.0 - 0.0 = 90.0s`.
   - Điều kiện `remaining > 180.0` $\rightarrow$ **LUÔN LUÔN FALSE NGAY TỪ ĐẦU!**
   - Vòng lặp follow bắt gặp `if not engine.has_time_for_next_action(reserve_seconds=180.0): break` $\rightarrow$ Thoát ngay lập tức khỏi cả Mode 2 lẫn Mode 1 mà không thực hiện bất kỳ lượt search hay tap follow nào.
   - Kết quả trả về:
     `FOLLOW_RESULT {"machine": 8, "status": "OK", "followed": [], "details": {"mode2_followed_count": 0}}`

### Quy Tắc Khắc Phục Bắt Buộc:
- Trong mọi config canary YAML hoặc production YAML của follow runner, `feed_timeout_seconds` BẮT BUỘC phải đặt $\ge 600$ (tốt nhất là `600` hoặc `1200`).
- Tuyệt đối không để `feed_timeout_seconds: 90` trong file config của `tiktok-follow` vì nó sẽ bị engine hiểu nhầm là session deadline và kích hoạt soft-deadline escape ngay lập tức.

---

## 7. Chi Tiết Triển Khai Bản Vá Thực Tế (Implemented Code Fix)

Bản vá khắc phục triệt để lỗi báo khống đã được đưa vào codebase với 3 điểm mấu chốt:

1. **`follow_runner/flows/verify_follow.py`**:
   - Thêm `id/t_q` và `id/t_r` vào tuple `_STAT_COUNTER_IDS`:
     ```python
     _STAT_COUNTER_IDS = (
         "id/sdn", "id/shq", "id/svt", "id/svs", "id/suu", "id/sut", "id/svu",
         "id/t1i", "id/t1h", "id/t_q", "id/t_r",
     )
     ```
   - Chặn đứng hoàn toàn việc `classify_button` nhận diện nhầm node `id/t_q` làm nút hành vi.

2. **`follow_runner/flows/mode2_follow_followers.py` (`_classify_profile_action`)**:
   - Loại bỏ chữ `"đã follow"` khỏi `followed_kw` (trên Profile TikTok tiếng Việt chỉ có `"nhắn tin"`, `"đang theo dõi"`, `"bạn bè"`, `"gửi tin nhắn"`).
   - Lọc bỏ mọi node thống kê thuộc `_STAT_COUNTER_IDS`:
     ```python
     nodes = _parse_mode2_nodes(xml_text)
     from .verify_follow import _STAT_COUNTER_IDS
     followed_kw = {
         "nhắn tin", "send message", "đang theo dõi", "message",
         "following", "gửi tin nhắn", "friends", "bạn bè"
     }
     not_followed_kw = {"follow lại", "follow", "theo dõi"}
     has_follow_btn = False
     has_followed_btn = False
     for n in nodes:
         b = n.get("bounds")
         if not b or b[1] >= 1200:
             continue
         rid = (n.get("resource_id") or "").strip().rstrip("/")
         if any(rid.endswith(sc) for sc in _STAT_COUNTER_IDS):
             continue
         vals = {
             (n.get("text") or "").strip().lower(),
             (n.get("content_desc") or "").strip().lower(),
         }
         vals.discard("")
         if vals & not_followed_kw:
             has_follow_btn = True
         if vals & followed_kw:
             has_followed_btn = True

     if has_followed_btn and not has_follow_btn:
         return "followed"
     ```

3. **Khóa Chặn Hồi Quy (Regression Unit Test)**:
   - Thêm unit test `test_classify_profile_action_ignores_stat_label_da_follow` trong `test_mode2_follow_followers.py` xác minh profile chỉ có stat `id/t_q` sẽ trả về `unknown`, không bao giờ trả về `followed`.

4. **Bổ Sung ID Hành Động Mới `id/fo4` (`verify_follow.py`)**:
   - Thêm `:id/fo4` và `id/fo4` vào `_ACTION_BUTTON_SUFFIXES` để `classify_button` nhận diện đúng nút `Follow lại` trên TikTok 46.x.
   - Thêm unit test `test_classify_machine8_action_button_id_fo4_and_stat_t_q` trong `test_verify_follow.py` đảm bảo cặp nút `Follow lại` + `Nhắn tin` luôn trả về `not_followed`.

---

## 8. Kỷ Luật Phản Ứng: Chống Bẫy "Điều Tra Quẩn Quanh" Khi User Đã Yêu Cầu Sửa Code

> ⚠️ **SỰ CỐ VẬN HÀNH (2026-10-01)**:
> Khi User hỏi: *"Làm xong chưa chạy canary lại xem check ra báo sai k"*, Coordinator hiểu nhầm là User yêu cầu chạy Canary để tái hiện lại lỗi cũ, dẫn đến việc giành lock chạy Canary trên CODE CHƯA SỬA, rồi lại sa đà vào query SQLite và cào Web để chứng minh lại điều User đã biết, khiến User nổi giận:
> *"ủa cái đm t có kêu chạy kiểm tra rà soát qua db đâu? t yêu cầu fix lỗi script báo khống mà????????????"*

### Kỷ Luật Bắt Buộc Cho Coordinator Khi Nhận Chỉ Thị:
1. **Dịch Đúng Ý Định Của User:**
   - Câu hỏi *"Làm xong chưa chạy canary lại xem check ra báo sai k"* nghĩa là: **"Đã fix code chưa? Fix xong thì chạy canary nghiệm thu xem code mới có còn báo sai không!"**
   - TUYỆT ĐỐI KHÔNG CHẠY CANARY TRÊN CODE LỖI để chứng minh lại cái lỗi mình đã kết luận.
2. **Quy Tắc "Stop Investigating, Start Fixing":**
   - Khi nguyên nhân gốc rễ đã xác định rõ (exact diff đã nằm trong tầm tay O(1) <= 15 dòng): **DỪNG NGAY MỌI THAO TÁC RÀ SOÁT / QUERY DB / CÀO WEB LẶP LẠI**.
   - Vào thẳng file nguồn thực hiện vá code ngay lập tức (T1 / L2 Surgery).
3. **Trình Tự Phản Ứng Chuẩn 4 Bước:**
   - **Bước 1:** Patch code logic sửa lỗi (<= 15 dòng).
   - **Bước 2:** Chạy unit test offline (< 30s) đảm bảo GREEN và không gãy test suite.
   - **Bước 3:** Kích hoạt Canary thực tế trên máy rảnh để chứng minh code mới hoạt động chính xác.
   - **Bước 4:** Báo cáo kết quả cuối cùng kèm bằng chứng nghiệm thu (diff + test + ảnh/log Canary).

---

## 9. Lỗ Hổng Tầng 2: Bất Đối Xứng Trong `_is_profile_action_node` Khi Gặp Cặp Nút `Follow lại` + `Nhắn tin` (Missing Action ID `id/fo4`)

Ngay sau khi vá Tầng 1 (`_classify_profile_action` bỏ `"đã follow"`), khi cho chạy Canary lại trên Máy 8 đối với nick `@vy.nguyen8730`, runner **VẪN TIẾP TỤC BÁO KHỐNG** `followed: ["vy.nguyen8730"]` dù server TikTok vẫn giữ nguyên số Following = 7!

### 1. Hiện Trường Dump XML Trên Máy 8:
Dump trực tiếp XML màn hình trang cá nhân của `@vy.nguyen8730` trên Máy 8:
```xml
com.ss.android.ugc.trill:id/fo4 | text='Follow lại' | bounds=[36,594][456,714]
com.ss.android.ugc.trill:id/fo4 | text='Nhắn tin' | bounds=[480,594][900,714]
```
Khi đối phương có follow mình hoặc TikTok cho phép nhắn tin trước, giao diện TikTok xuất hiện **2 nút song song**:
- Nút 1: `Follow lại` (`id/fo4`)
- Nút 2: `Nhắn tin` (`id/fo4`)
Nếu mình ĐÃ follow họ thật sự thì nút 1 phải chuyển thành `Bạn bè` hoặc `Đang theo dõi`, chứ **KHÔNG BAO GIỜ CÒN NÚT `Follow lại`**.

### 2. Cơ Chế Lỗi Chí Mạng (Asymmetric Classifier Bias):
Trong `verify_follow.py`:
```python
_ACTION_BUTTON_SUFFIXES = (
    ":id/fds", ":id/ff8", ":id/fij", ":id/fi6", ":id/flo", ":id/flp", ":id/fm9", ":id/fmp", ":id/follow_button",
    ...
)

def _is_profile_action_node(node: dict) -> bool:
    ...
    rid = (node.get("resource_id") or "").strip().rstrip("/")
    if any(rid.endswith(sc) for sc in _STAT_COUNTER_IDS):
        return False
    if any(rid == ab or rid.endswith(ab) for ab in _ACTION_BUTTON_SUFFIXES):
        return True
    message_markers = {"nhắn tin", "message", "gửi tin nhắn", "send message"}
    values = _normalized_action_values(node)
    return bool(values & message_markers) or any(m in v for v in values for m in message_markers)
```
1. Resource ID `id/fo4` của TikTok 46.x **chưa có trong `_ACTION_BUTTON_SUFFIXES`**.
2. Khi duyệt qua Nút 1 (`Follow lại`, `id/fo4`):
   - `id/fo4` không nằm trong `_ACTION_BUTTON_SUFFIXES` $\rightarrow$ False.
   - Text "Follow lại" không khớp `message_markers` $\rightarrow$ False.
   - ➔ **`_is_profile_action_node` TỪ CHỐI (IGNORE) NÚT `Follow lại`!**
3. Khi duyệt qua Nút 2 (`Nhắn tin`, `id/fo4`):
   - `id/fo4` không nằm trong `_ACTION_BUTTON_SUFFIXES`, NHƯNG text "Nhắn tin" khớp `message_markers` $\rightarrow$ True.
   - ➔ **`_is_profile_action_node` CHẤP NHẬN NÚT `Nhắn tin`!**
4. Trong `classify_button`:
   - `action_nodes` chỉ thu được DUY NHẤT 1 node: Nút 2 (`Nhắn tin`).
   - Nút 1 (`Follow lại`) đã bị vứt bỏ hoàn toàn.
   - Classifier thấy chỉ có `Nhắn tin` và không có nút follow nào $\rightarrow$ **KẾT LUẬN `followed` (DƯƠNG TÍNH GIẢ 100%)**!

### 3. Giải Pháp Khắc Phục:
- Bổ sung ngay `:id/fo4` và `id/fo4` vào `_ACTION_BUTTON_SUFFIXES` trong `verify_follow.py`.
- Khi `id/fo4` được công nhận là action button, cả 2 nút `Follow lại` và `Nhắn tin` đều được thu thập vào `action_nodes`.
- `recognized_not_followed` có Nút 1 (`Follow lại`) $\rightarrow$ Quy tắc `if recognized_not_followed: return "not_followed"` được kích hoạt $\rightarrow$ Bắt dứt điểm hiện tượng nhả follow, ngắt phiên và cooldown nick ngay lập tức!

---

## 10. Giải Mã Sự Cố: Tại Sao Cơ Chế 2 Lớp (Verify Row + Path B Profile) Bị Tê Liệt Khiến Bot Cứ Tiếp Tục Follow Hết List Anchor?

- **Ý đồ kiến trúc gốc của User:**
  Khi bot duyệt danh sách Following của anchor (Mode 2):
  1. *Lớp 1 (Row-level verify):* Tap nút follow trên hàng $\rightarrow$ kiểm tra nút trên hàng có đổi text không.
  2. *Lớp 2 (Path B verification / verify_sample_every):* Cứ sau N lượt follow (hoặc lượt đầu tiên), bot BẮT BUỘC tap vào username của nick vừa follow để nhảy vào trang cá nhân (Profile) của người đó $\rightarrow$ soi trực tiếp nút quan hệ trên Profile. Nếu TikTok không nhận/nhả follow thì PHẢI DỪNG PHIÊN NGAY LẬP TỨC (`FOLLOW_FAILED`), kích hoạt Cooldown cho nick nghỉ. Nếu follow thật sự thành công thì mới back ra trang Following của anchor để tiếp tục follow các nick tiếp theo.

- **Tại sao cơ chế trên bị sập / tê liệt khiến bot cứ back ra follow tiếp?**
  Không phải do bot bỏ qua bước nhảy vào Profile của nick, mà là KHI NHẢY VÀO PROFILE CỦA NICK, hàm `_path_b_verify` bị **2 ĐIỂM MÙ ĐÁNH LỪA**:
  1. *Điểm mù 1 (Nhãn cột thống kê):* Quét trúng chữ `"Đã follow"` trên nhãn cột số người đang theo dõi (`id/t_q`).
  2. *Điểm mù 2 (Cặp nút `Follow lại` + `Nhắn tin` thiếu ID `id/fo4`):* Bỏ qua nút `Follow lại` vì thiếu ID trong whitelist, chỉ nhận diện nút `Nhắn tin` $\rightarrow$ kết luận sai là đã follow.
  Vì cả 2 điểm mù này khiến `_path_b_verify` luôn luôn trả về `"followed"` (dương tính giả) dù TikTok server đã drop follow từ lâu, bot lầm tưởng là đã follow thành công 100% $\rightarrow$ yên tâm back ra danh sách Following của anchor, tiếp tục bấm nick 2, nick 3... cho tới khi cạn sạch budget!

- **Hệ quả sau khi sửa dứt điểm 2 điểm mù:**
  Sau khi đưa `id/fo4` vào `_ACTION_BUTTON_SUFFIXES` và gạt bỏ nhãn thống kê `_STAT_COUNTER_IDS`, khi nick bị drop follow, Path B ngay lập tức phát hiện nút thực tế vẫn là `Follow lại` (`not_followed`) $\rightarrow$ kích hoạt `FOLLOW_FAILED`, dừng phiên ngay lập tức và đưa nick vào cooldown bảo vệ trust tài khoản.

---

## 11. Phương Pháp Thực Nghiệm Canary Trực Tiếp Cơ Chế Path B Trên List Following Của Anchor (Live Probe & Evidence)

Khi User yêu cầu: *"Tao cần canary cái cơ chế t vừa nói xem hoạt động trc (bấm follow trên list following anchor -> nhảy vào profile nick vừa follow kiểm tra xem có nhả không -> nếu không nhả mới back ra follow tiếp)"*:

1. **Khó khăn khi chạy qua CLI thông thường (`run_follow.py`):**
   - Vòng lặp `run_mode2` có bước `_ensure_anchor_followed` (bắt buộc follow anchor trước khi đọc list của anchor). Nếu tài khoản đang chạy chưa follow anchor đó hoặc anchor đó cũng bị drop follow, session sẽ dừng ngay từ bước anchor preflight mà chưa kịp chạm tới danh sách following của anchor.
2. **Quy trình cô lập và kiểm chứng Path B độc lập (Direct Flow Probe):**
   - Dựng script kiểm chứng focused (ví dụ `scripts/canary_path_b_live.py`) chạy trực tiếp trên máy rảnh:
     ```python
     # 1. Mở TikTok và điều hướng trực tiếp đến profile của anchor đã follow sẵn
     adapter.shell(['am', 'start', '-a', 'android.intent.action.VIEW', '-d', f'snssdk1180://user/profile?unique_id={anchor_uid}'])
     time.sleep(4)

     # 2. Tap tab Following (Đã follow) của anchor để mở danh sách
     # Tab Following nằm ở hàng thống kê đầu profile (bounds [36, 501][204, 546] hoặc tap tọa độ [120, 500])
     adapter.tap(120, 500)
     time.sleep(3)
     screencap_anchor_list = adapter.screencap()  # Lưu bằng chứng danh sách đã mở

     # 3. Thu thập rows trong list Following của anchor
     nodes = _parse_mode2_nodes(adapter.dump_ui())
     rows = _collect_follower_rows(nodes)

     # 4. Thực thi follow_one_follower với sample=True (bắt buộc kích hoạt Path B)
     outcome, reason = follow_one_follower(engine, target_row['username_node'], target_uid, sample=True)
     ```
3. **Tiêu chuẩn nghiệm thu 3 điểm mốc (Pass Criteria):**
   - **Ảnh Checkpoint 1 (`canary_anchor_list.png`):** Chứng minh bot đã ở đúng trong màn hình danh sách Following của anchor (`FollowRelationTabActivity` / recycler populated).
   - **Thao tác Path B:** Log chứng minh bot tự động tap vào username row $\rightarrow$ mở màn hình Profile cá nhân của nick target $\rightarrow$ soi nút `id/fo4`.
   - **Ảnh Checkpoint 2 (`canary_after_path_b.png`):** 
     + Nếu TikTok server nuốt/nhả follow: Nút vẫn còn `Follow lại` $\rightarrow$ hàm trả về `outcome: failed`, `reason: FOLLOW_FAILED: TikTok không nhận follow (profile vẫn chưa follow)`, `state.follow_failed: True`.
     + **Hành vi dừng phiên:** Script KHÔNG ĐƯỢC PHÉP back ra list anchor để bấm nick tiếp theo, mà dừng ngay phiên làm việc để bảo vệ nick.

---

## 12. Kỷ Luật Bằng Chứng Trực Quan Khi Canary Cơ Chế Xác Thực Đa Bước (Path B Multi-Step Progression Evidence)

> ⚠️ **SỰ CỐ VẬN HÀNH & USER FEEDBACK (2026-10-01)**:
> Khi User yêu cầu: *"Tao cần canary cái cơ chế t vừa nói xem hoạt động trc (bấm follow trên list following anchor -> nhảy vào profile nick vừa follow kiểm tra xem có nhả k nếu k nhả thì back ra trang following của anchor đi follow tiếp mà?)"*.
> Coordinator chạy test xong nhưng chỉ gửi đúng 1 ảnh danh sách Following của anchor, khiến User bức xúc:
> *"Mày gửi hình như cứt ấy ... Tự nhiên t cần theo dõi tiến trình test canary đi gửi mỗi cái list following bố ai hiểu"*.

### 1. Phân Tích Sai Lầm (Root Cause of Bad Reporting):
- Cơ chế đang được kiểm chứng là **Path B (Nhảy vào Profile nick đích để soi nút xem có bị drop không)**.
- Gửi mỗi ảnh màn hình danh sách Following của anchor chỉ chứng minh được bot đã mở danh sách, **HOÀN TOÀN KHÔNG CHỨNG MINH ĐƯỢC BƯỚC XÁC THỰC LÕI**: bot có nhảy vào profile không? Màn hình profile hiển thị những nút gì? Tại sao kết luận là drop/success?
- Báo cáo bằng chứng thiếu màn hình thao tác lõi bị coi là **thất bại nghiêm trọng về mặt bàn giao kết quả trực quan**.

### 2. Tiêu Chuẩn Bắt Buộc 4 Checkpoint Khi Canary Luồng Xác Thực Đa Bước:
Mọi bài test Canary kiểm chứng luồng tương tác đa bước (đặc biệt là Mode 2 Follow + Path B Verify) **BẮT BUỘC PHẢI CHỤP VÀ GỬI ĐỦ 4 ẢNH THEO TRÌNH TỰ TIẾN TRÌNH**:

1. **Checkpoint 1 (Pre-Action Input):** Màn hình danh sách Following của anchor trước khi tap (`step1_following_list_before_tap.png`) — xác nhận danh sách, tên nick target và nút ban đầu (`Follow` / `Follow lại`).
2. **Checkpoint 2 (Post-Action Reaction):** Màn hình danh sách ngay sau khi tap nút Follow trên hàng (`step2_following_list_after_tap.png`) — chứng minh sự kiện click đã được gửi.
3. **Checkpoint 3 (CORE VERIFICATION SCREEN - BẮT BUỘC):** Màn hình Profile cá nhân của nick target khi Path B nhảy vào (`step3_path_b_profile_screen.png`) — **ĐÂY LÀ ẢNH QUAN TRỌNG NHẤT**, thể hiện trực quan nút quan hệ thực tế (`Follow lại` + `Nhắn tin` trên `id/fo4`) và nhãn thống kê để User tận mắt thấy vì sao code phán quyết là `not_followed` hay `followed`.
4. **Checkpoint 4 (Terminal Decision / Guard Enforcement):** Màn hình trạng thái kết thúc (`step4_final_state.png`) — chứng minh script đã ngắt phiên tại chỗ, kích hoạt `FOLLOW_FAILED`, không cắm đầu back ra list để bấm tiếp nick khác.




