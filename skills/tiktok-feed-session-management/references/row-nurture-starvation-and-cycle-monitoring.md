# Row Nurture Starvation & 4-Day Cycle Monitoring Invariants

## 1. Ngưỡng Cảnh Báo "Bỏ Đói" (Starvation Threshold) vs Độ Dài Chu Kỳ

### Sai lầm chết người (Pitfall):
- Đặt ngưỡng cảnh báo bỏ đói (Starvation threshold) thấp hơn độ dài của 1 chu kỳ xoay tua hoàn chỉnh (ví dụ: chu kỳ 4 ngày = 96 giờ, nhưng lại đặt ngưỡng 48 giờ).
- **Hậu quả:** Gây ra bão cảnh báo giả (false-alarm storm). Các Row đang nằm chờ lượt quay vòng tự nhiên (như Row 5, 6, 7, 8) sẽ liên tục bị gắn cờ đỏ `STARVED` dù script và hệ thống đang hoạt động hoàn toàn bình thường.

### Invariant bất biến:
- Trong mô hình xoay tua $N$-ngày (hiện tại Farm Taadaa là **chu kỳ 4 ngày = 96 giờ**):
  $$\text{Chu Kỳ Nuôi} = 96.0\text{h}, \quad \text{Dung Sai Trễ/Retry} = 12.0\text{h}, \quad \text{Ngưỡng Bỏ Đói (Starvation Threshold)} = 108.0\text{h}$$
- CẤM TUYỆT ĐỐI đặt ngưỡng 48h trong chu kỳ 4 ngày.
- Mọi Row từ Row 1 đến Row 8 được thiết kế để quay vòng lặp lại **chính xác 96 giờ** (4 ngày $\times$ 24 giờ).
- Dung sai 12 giờ cho phép các ca bị trễ do nghẽn ADB, retry runner hoặc lệch lịch ca không kích hoạt báo động giả.
- Chỉ khi một Row vượt quá **108 giờ** mà không có bất kỳ phiên chạy thành công nào, hệ thống mới kích hoạt `🚨 [STARVATION ALERT]`.

---

## 2. Kiến Trúc 3 Trụ Cột Giám Sát Sức Khỏe Farm (Three-Pillar Farm Health Monitoring)

Hệ thống giám sát vận hành Farm bắt buộc bao phủ đầy đủ 3 tầng độc lập:
1. **Trụ cột 1 - Sức Khỏe Cụm Máy (`🏥 Fleet Health`):**
   - Giám sát tầng phần cứng, kết nối USB/Hub, ADB liveness, IP/Proxy tunnel, phát hiện máy đơ/mất mạng.
2. **Trụ cột 2 - Sức Khỏe Follow (`🩺 Follow Health`):**
   - Giám sát tầng tài khoản TikTok: Nick Khỏe, Hồi phục Nấc 1/2, Án phạt Cooldown do bị TikTok nhả follow.
3. **Trụ cột 3 - Sức Khỏe Nuôi Acc 8 Row (`🌾 Row Nurture Health / Starvation Watchdog`):**
   - Giám sát tầng **Điều phối & Kịch bản theo Row**.
   - Phát hiện sớm các lỗi âm thầm: Lỗi logic script, hỏng mapping Excel theo Row, lỗi đường dẫn video cào, kẹt process launcher khiến một Row cụ thể bị bỏ quên nhiều ngày liên tiếp.

---

## 3. Quy Cách Báo Cáo & Phân Loại Trạng Thái Nuôi 8 Row

### Phân loại trạng thái trong cửa sổ 96h + 12h dung sai:
- 🟢 **Đúng chu kỳ (Normal):** Thời gian từ ca chạy cuối $\le 96\text{h}$ (trong vòng 1 chu kỳ 4 ngày).
- 🟡 **Trễ trong dung sai (Pending Grace):** Thời gian từ ca chạy cuối từ $96\text{h} - 108\text{h}$ (đang chờ ca theo đúng lịch hoặc trễ nhẹ/retry).
- 🔴 **BỊ BỎ ĐÓI (STARVED):** Thời gian từ ca chạy cuối $> 108\text{h}$ hoặc chưa từng chạy $\rightarrow$ **Cần can thiệp khẩn cấp**.
- **Hằng số đồng bộ:** `NURTURE_CYCLE_H = 96.0h`, `STARVATION_THRESHOLD_H = 108.0h` (đồng bộ giữa `feed_session_watchdog.py` và `nurture_health_helper.py`).

### Quy tắc Bắt Buộc: Phân Tách Báo Cáo Sức Khỏe Nuôi Theo Từng Cụm Farm (Dual-Farm Split Invariant)
- **Pitfall chết người:** Gộp chung tiến độ 8 Row của toàn bộ hệ thống hoặc chỉ trỏ `live_root` vào `runtime/kibe/live` khiến Farm Admin (Máy 201-280) bị tàng hình. Nếu Kibe chạy xong Row 3 nhưng Admin bị kẹt USB/rớt máy bỏ lỡ Row 3, hệ thống vẫn báo xanh 🟢 giả tạo vì chỉ nhìn Kibe.
- **Invariant bất biến:** Báo cáo sức khỏe nuôi 8 Row BẮT BUỘC phải phân tách độc lập theo từng cụm (Farm Kibe Máy 1-80 và Farm Admin Máy 201-280).
- Mỗi cụm đọc đúng thư mục `runtime/<cluster>/live` tương ứng, có chuỗi tiến độ R1..R8 riêng và cảnh báo Starvation riêng, đặt trực tiếp dưới khối báo cáo của cụm đó.

### Định dạng hiển thị trong Báo Cáo Watchdog:
```text
🏢 【FARM KIBE - MÁY 1-80】
... (Lướt feed, tim, follow) ...
🌾 Sức khỏe 8 Row: R1:🟢8h | R2:🟢32h | R3:🟢2h | R4:🟢26h | R5:🟢44h | R6:🟢20h | R7:🟢62h | R8:🟢38h

🏢 【FARM ADMIN - MÁY 201-280】
... (Lướt feed, tim, follow) ...
🌾 Sức khỏe 8 Row: R1:🟢8h | R2:🟢32h | R3:🟢2h | R4:🟢28h | R5:🟢46h | R6:🟢22h | R7:🟢64h | R8:🟢40h
```
* Nếu một Farm có Row bị Starved (> 108h):
  * Watchdog tự động thêm dòng cảnh báo ngay dưới Farm đó: `• 🚨 CẢNH BÁO BỎ ĐÓI (>108h): Row [X]`
  * Header tin nhắn Telegram được nâng cấp thành:
    `🚨 [CẢNH BÁO BỎ ĐÓI] PHÁT HIỆN ROW [X] CỤM [KIBE/ADMIN] > 108H CHƯA NUÔI THÀNH CÔNG!`

---

### Phân Định Ranh Giới Giám Sát: Telegram (Vĩ Mô) vs Web Dashboard Port 1905 (Vi Mô)
- **Quy tắc phân công kiến trúc:**
  1. **Telegram Watchdog = Giám sát VĨ MÔ cấp Fleet & Row:**
     * Chỉ báo cáo tiến độ 8 Row theo từng Farm và tỷ lệ tổng thể.
     * CẤM TUYỆT ĐỐI liệt kê chi tiết từng tài khoản lên Telegram (quy mô 1,280 accounts sẽ gây tràn ngưỡng 4,096 ký tự và tạo bão spam tin nhắn).
     * Chỉ đưa cảnh báo tóm tắt số lượng ngoại lệ nếu có nick bị starved cá biệt (>108h) kèm link trỏ về Dashboard.
  2. **Web Dashboard (`http://127.0.0.1:1905`) = Giám sát VI MÔ cấp từng Account:**
     * Là nơi duy nhất tra cứu chi tiết toàn bộ accounts (Kibe + Admin).
     * Bắt buộc có Tab/Chế độ lọc `🌾 Sức Khỏe Nuôi Acc` (Endpoint: `/api/nurture-health`):
       - Cho phép **Sort 1-click "Đói nhất lên đầu"** theo `last_nurtured` / `hours_since_last_nurture`.
       - Bộ lọc nhanh: Theo Cụm (Kibe / Admin), theo Row (1-8), hoặc chỉ hiện nick bị bỏ đói (`🔴 > 108h`).
       - Bóc tách nguyên nhân kẹt: App crash, mất ADB, lỗi proxy, hoặc trống slot.
     * **Tính toàn vẹn & Bảo mật Dashboard:**
       - **Số lượng động:** CẤM hardcode chữ "1,280 máy". Bắt buộc dùng biến động `${escapeHTML(sm.total || 0)}` (khớp chính xác số account thực tế trong DB, vd 1,255 accs).
       - **Múi giờ đồng bộ:** Bắt buộc chuẩn hóa `Asia/Ho_Chi_Minh` (`HCMC`) trong helper và watchdog.
       - **XSS Prevention:** Mọi chuỗi động (`username`, `cluster`, `err.message`) khi render vào `innerHTML` BẮT BUỘC phải qua hàm `escapeHTML()`.
       - **Minh bạch lỗi DB:** BẮT BUỘC trả mã HTTP 503 và thông báo rõ ràng khi DB lỗi/thiếu bảng, CẤM nuốt ngoại lệ `except Exception: pass` âm thầm.
     * **Quy tắc Mapping Row (Slot `tik` Invariant):**
       - **Pitfall:** Suy diễn Row từ số máy `may` bằng công thức phân bổ `((may - 1) // 8) + 1`.
       - **Thực tế Taadaa Farm:** Mỗi điện thoại chứa 8 accounts ứng với 8 slot Row 1 đến Row 8. Trường `tik` trong bảng SQLite `farm_account_info` CHÍNH LÀ Row slot của nick trên thiết bị (`tik = 1..8`).
       - **Bắt buộc:** Map `row_num = int(tik)` (fallback 1 nếu null/lỗi). CẤM TUYỆT ĐỐI dùng số máy `may` để suy diễn Row.
     * **Kỹ thuật Quét Live Artifact O(1) (CẤM `rglob("*")`):**
       - **Pitfall:** Dùng `Path(live_root).rglob("*")` để tìm folder `row-*`. Trong farm 80 máy chạy 60 ngày, `rglob("*")` duyệt đệ quy qua >200,000 files/dirs, gây nghẽn đĩa và timeout tiến trình >600s.
       - **Bắt buộc:** Chỉ quét 2 cấp phẳng:
         1. Cấp 1: `root_path.glob("????-??-??")`, chỉ lấy tối đa 7 ngày mới nhất.
         2. Cấp 2: Trong mỗi ngày, chỉ duyệt `d_dir.glob("row-*")` để bóc tách timestamp từ tên folder `row-<R>-<HHMMSS>`. Thời gian quét hoàn tất <0.05 giây.

---

## 4. Kỷ Luật Lập Lịch Chu Kỳ 4 Ngày: Fixed Parity 96h vs Bẫy Giãn 120h

### Bài học phát hiện qua Review (Pitfall: Bẫy Giãn 120 Giờ của Random Parity):
- **Phân tích:** Nếu áp dụng cơ chế đảo ngẫu nhiên thứ tự nhóm Chẵn/Lẻ đầu mỗi chu kỳ 4 ngày (Odd-first $\leftrightarrow$ Even-first):
  - Khi Chu kỳ $N$ chạy Odd-first $\rightarrow$ Row 1 chạy vào **Ngày 0**.
  - Sang Chu kỳ $N+1$ gieo xúc xắc trúng Even-first $\rightarrow$ Row 1 bị đẩy sang **Ngày 1**.
  - **Hậu quả:** Khoảng cách giữa 2 lần nuôi của Row 1 bị kéo giãn thành:
    $$4\text{ ngày (chu kỳ hiện tại)} + 1\text{ ngày (bị đẩy lùi)} = 5\text{ ngày} = 120\text{ giờ}!$$
  - Điều này khiến $16/60$ chu kỳ tự động bị vượt ngưỡng $96\text{h}$ và gây bão cảnh báo giả `🚨 [CẢNH BÁO BỎ ĐÓI]` trên Telegram và Dashboard dù hệ thống chạy đúng lịch.

### Cơ chế Chuẩn Hóa Bất Biến: Fixed Parity 96h Recurrence
Để triệt tiêu hoàn toàn khoảng trễ 120 giờ và đảm bảo chu kỳ lặp lại toán học chính xác $100\%$:
- Mọi chu kỳ 4 ngày (`cycle_idx = (ordinal - BASE_ORDINAL) // 4`) giữ nguyên Parity cố định (`_is_cycle_odd_first(cycle_idx) == True`):
  * **Ngày 0 (Day 0):** Ca 1 (Sáng) = Row 1 | Ca 2 (Trưa) = Row 3 | Ca 3 (Tối) = Row 5.
  * **Ngày 1 (Day 1):** Ca 1 (Sáng) = Row 2 | Ca 2 (Trưa) = Row 4 | Ca 3 (Tối) = Row 6.
  * **Ngày 2 (Day 2 - Cày đích & Dưỡng sinh tối):**
    - Ca 1 (Sáng: 06h & 08h): **Row 7** (Cày).
    - Ca 2 (Trưa: 12h & 14h): **Row 8** (Cày).
    - Ca 3 (Tối: 18h & 20h): **Dưỡng sinh nick yếu** (Tắt follow, lướt feed + up 1 video).
  * **Ngày 3 (Day 3 - Nghỉ xả tải toàn Farm):**
    - Cả 3 Ca (Sáng, Trưa, Tối): **Dưỡng sinh nick yếu** (bao gồm cả nick ăn nhả follow lẫn nick non chưa đủ 10 video) qua thuật toán chọn Row động `healing_selector.py`.
    - **Tắt 100% follow** (`_follow_rate = 0`), thuần túy lướt feed rửa trust + đăng 1 video/ngày nếu nick chưa đăng.
- **Tính toán học đã chứng minh (Mathematical Invariant):**
  - Mọi Row chính từ Row 1 đến Row 8 quay lại **CHÍNH XÁC 96 GIỜ** ở mọi chu kỳ:
    $$\text{Gaps} = \{\text{timedelta}(\text{hours}=96)\}$$
  - Đã được kiểm chứng qua test suite `test_determine_row_main_rows_recur_exactly_every_96h` xuyên suốt 48 ngày (12 chu kỳ liên tiếp).
- **Bảo toàn nhịp sinh học (User Persona):**
  * Cặp `{Row 1, Row 2}` luôn luôn lướt Sáng (06h & 08h).
  * Cặp `{Row 3, Row 4}` luôn luôn lướt Trưa (12h & 14h).
  * Cặp `{Row 5, Row 6}` luôn luôn lướt Tối (18h & 20h).
  * Thói quen giờ giấc của từng tài khoản được giữ vững, không bao giờ bị xáo trộn giờ lướt.

---

## 5. Tách Biệt Triệt Để Án Phạt Follow Cooldown vs Quyền Upload Video

### Quy tắc bất biến:
- **Án phạt Follow Cooldown chỉ cấm bấm nút follow:** Khi nick dính án nhả follow hoặc đang trong ca dưỡng sinh, bắt buộc `_follow_rate = 0` để chỉ lướt feed rửa trust.
- **TUYỆT ĐỐI KHÔNG CẤM UPLOAD VIDEO:**
  - Ca dưỡng sinh và nick dính Follow Cooldown **VẪN PHẢI UPLOAD ĐÚNG 1 VIDEO/NGÀY** để duy trì nhịp hoạt động tự nhiên của Creator.
  - Cờ `-AllowUploadHook` bắt buộc **LUÔN ĐƯỢC BẬT ở cả Phiên 1 (Feed) và Phiên 2 (Feed + Hook)** trong mọi ca chạy.
  - CẤM viết rào cản `if not is_rest_day` chặn upload hook.
  - Sổ cái giao dịch `shift_upload_history.json` là cơ chế chốt hạ duy nhất đảm bảo tính idempotency: Mỗi nick chỉ upload thành công đúng 1 video trong ngày, phiên sau tự động bỏ qua nếu phiên trước đã upload thành công.

---

## 6. Cơ Chế Chọn Row Dưỡng Sinh Động (`healing_selector.py`) & Bẫy Fallback Tĩnh

### Thuật toán chấm điểm ưu tiên Row yếu (`healing_selector.py`):
Trong các ca dưỡng sinh (Ngày 2 Ca 3 và Ngày 3/N4 cả 3 ca), `_SCHEDULE` trả về `None` để chuyển quyền cho `healing_selector.py` tính toán:
$$\text{Score} = 100.0 \times p_{\text{fail}} + 20.0 \times p_{\text{young}}$$
- $p_{\text{fail}}$: Tỷ lệ thiết bị dính án phạt Follow Cooldown hoặc lỗi `follow_failed` (quét trong `runs/state/follow_state_*.json`, có cache 60s).
- $p_{\text{young}}$: Tỷ lệ tài khoản non chưa đủ 10 video (truy vấn từ bảng `farm_account_info` / `snapshots` trong `tiktok_tracker.db`, cache 60s).
- Row có điểm số cao nhất sẽ được chọn để ưu tiên nuôi dưỡng, rửa trust và kéo tương tác.

### 4 Ràng buộc điều phối bắt buộc:
1. **Pairing Rule (S2 bám S1):** Session 2 (08:00, 14:00, 20:00) BẮT BUỘC chạy cùng Row với Session 1 (06:00, 12:00, 18:00) trong cùng một ca.
2. **Chống kẹp ca (Anti-consecutive):** Session 1 loại trừ `last_row` của ca liền trước để không lặp lại cùng một Row qua ranh giới 2 ca.
3. **N4 3 ca 3 row (Rest Day Exclude):** Vào Ngày 3 (Day 3 / cycle_day == 3), loại trừ toàn bộ các Row đã chạy trước đó trong ngày (quét live folder `D:/Taadaa/runtime/<cluster>/live/YYYY-MM-DD/row-*`). Đảm bảo mỗi ca dưỡng một Row yếu khác nhau, không bị trùng.
4. **Audit Trail Schema 1.0:** Mọi quyết định chọn Row động bắt buộc ghi audit log vào `D:/Taadaa/runtime/audit_logs/healing_decision_audit.jsonl` (tự rotate khi file > 5MB).

### 🚨 Pitfall Chí Mạng: Bẫy Nuốt Ngoại Lệ & Fallback Tĩnh Khi Chạy Cron
- **Triệu chứng:** Vào Ngày 4 dưỡng sinh, hệ thống không bốc các Row có tỷ lệ nhả follow cao nhất (như Row 4, Row 2, Row 7) mà luôn luôn chạy cố định: Ca 1 -> Row 3, Ca 2 -> Row 4, Ca 3 -> Row 5.
- **Nguyên nhân gốc rễ (Root Cause):**
  - Khi script `tiktok_runner.py` được Cron (`no_agent: true`) kích hoạt từ thư mục scripts cục bộ trên ổ `C:`.
  - Hàm `_load_determine_healing_row()` chỉ tìm `healing_selector.py` qua:
    `candidates += [p / "tools" for p in Path(__file__).resolve().parents]`
  - Cây thư mục cha trên ổ `C:` không có thư mục `tools/`, đồng thời file `env.json` của cron thiếu biến `HERMES_CRON_TOOLS_DIR`.
  - Hệ quả: Hàm văng `ImportError: healing_selector.py not found (set HERMES_CRON_TOOLS_DIR)`, nhưng ngoại lệ bị khối `except Exception` nuốt chửng và âm thầm kích hoạt khối **fallback tĩnh**:
    ```python
    except Exception as exc:
        elif slot_key in ((6, 0), (8, 0)):
            row = 3
        elif slot_key in ((12, 0), (14, 0)):
            row = 4
        else:
            row = 5 if (cycle_idx % 2 == 0) else 6
    ```
- **Kỷ luật khắc phục & phòng ngừa:**
  1. Trong `tiktok_runner.py`: Danh sách `candidates` bắt buộc bổ sung đường dẫn tuyệt đối chuẩn của repo/tools (`Path("D:/Taadaa/tools")`, `Path("D:/Taadaa/tiktok-luot nuoi acc/tools")`).
  2. Trong `env.json` của cron: BẮT BUỘC khai báo rõ ràng `"HERMES_CRON_TOOLS_DIR": "D:/Taadaa/tools"`.
  3. Cảnh báo lỗi: Tuyệt đối không nuốt im lặng `ImportError` trong khối `except` mà phải phát cảnh báo hoặc fallback có nhật ký rõ ràng.


