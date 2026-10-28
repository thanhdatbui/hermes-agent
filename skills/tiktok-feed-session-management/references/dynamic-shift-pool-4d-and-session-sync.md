# Kiến Trúc Dynamic Shift-Pool Xoay Tua Thuần Theo Pool State (Đã Bỏ Chu Kỳ Ngày & Bỏ Ngày 4 Dưỡng Sinh)

## 1. Thiết Kế Shift-Pool Dynamic State-Driven (Đã Bỏ Hoàn Toàn Lịch Chu Kỳ Ngày)
Hệ thống quản lý tới tầng tài khoản (Account-Level Telemetry), **đã loại bỏ hoàn toàn lịch ngày cứng (D0/D1/D2/D3, `_ANCHOR_ORDINAL`, `cycle_day = total_days % 4`, `cycle_idx`) và BỎ NGÀY THỨ 4 DƯỠNG SINH TOÀN FARM**.
Hệ thống vận hành theo **Vòng xoay thành công thuần túy State-Driven (`cycle_history` per machine per ca)**:

### Phân Bổ Ca Nuôi & Ranh Giới Pool:
- **Ca 1 (Sáng: 06:00 & 08:00):** Pool `{1, 2, 7}`. Đi lần lượt theo thứ hạng sức khỏe. Khi cả 3 nick đều đã chạy $\to$ Tự động reset vòng mới. Follow chạy 100% bình thường, tuyệt đối KHÔNG fallback ra ngoài pool, KHÔNG có ngày dưỡng sinh.
- **Ca 2 (Trưa: 12:00 & 14:00):** Pool `{3, 4, 8}`. Đi lần lượt theo thứ hạng sức khỏe. Khi cả 3 nick đều đã chạy $\to$ Tự động reset vòng mới. Follow chạy 100% bình thường, tuyệt đối KHÔNG fallback ra ngoài pool, KHÔNG có ngày dưỡng sinh.
- **Ca 3 (Tối: 18:00 & 20:00):** Pool `{5, 6}` + 1 Dynamic Slot:
  * Lượt 1: Bốc nick thứ nhất trong `{5, 6}`.
  * Lượt 2: Bốc nick thứ hai trong `{5, 6}`.
  * Lượt 3 (sau khi cả 5 và 6 đều đã chạy xong): Kích hoạt đúng **1 lượt Dynamic Slot** nuôi dưỡng sinh 3 phễu (Đề xuất $\to$ Nhả $\to$ Yếu) và **TẮT FOLLOW** (`reason: dynamic-nurture-row-follow-disabled`).
  * Xong lượt Dynamic Slot $\to$ Tự động reset `history` về rỗng để bắt đầu vòng mới quay lại `{5, 6}`.

- 🛑 **Cạm bẫy Sót Code Lịch Ngày Cũ (`cycle_day == 3`) — Gây Tắt Follow Toàn Farm:**
  * **Hiện tượng:** Sáng ngày 26/10/2026, toàn bộ 160 máy Ca Sáng đều bị Watchdog báo `Bỏ qua (76/78): dynamic-nurture-row-follow-disabled`.
  * **Nguyên nhân:** Dù đã bỏ ngày 4 dưỡng sinh, nhưng trong `shift_pool_selector.py` vẫn sót lại dòng `if cycle_day == 3 or (cycle_day == 2 and ca == 3): raise ValueError(...)`. Vì ngày 26/10 là ngày thứ 15 tính từ mốc cũ ($15 \pmod 4 = 3$), điều kiện này vô tình kích hoạt fallback sang 3 phễu cho toàn bộ Ca 1, gán `rest_day_no_follow = True`.
  * **Khắc phục triệt để:** Xóa bỏ hoàn toàn `_ANCHOR_ORDINAL`, `cycle_day`, `cycle_idx`. Xoay tua `candidates = [r for r in pool if r not in used]` chỉ phụ thuộc vào `state['cycle_history'][ca][machine]`. Chỉ riêng Ca 3 khi hết pool mới kích hoạt 1 lượt Dynamic Slot.
  * **Cập nhật Unit Test Suite:** Khi xóa bỏ lịch ngày, các unit test cũ có `with pytest.raises(ValueError): _pick(state, 3)` (ép văng lỗi ngày 4) phải được refactor sang kiểm tra vòng lặp xoay tua pool thuần túy (`used` set tích lũy đủ các nick trong pool thì tự reset vòng mới).

- 🛑 **Triage Thắc Mắc 'Còn Ca 2 Đâu' Khi Ở Khung 09:00 - 10:00 Sáng:**
  * Khi User hỏi *"Còn ca 2 đâu"* lúc 09:00 - 10:00 sáng, tuyệt đối không trả lời cụt lủn hay nhầm lẫn:
    1. **Phiên 2/2 của Ca 1 (Sáng lúc 08:00):** Cụm Kibe thường xong lúc ~09:15-09:20, cụm Admin thường chốt summary sau vài phút. Watchdog farm là báo cáo gộp 2 cụm (`dual_cluster_farm_reporting`), chỉ gửi Telegram khi cả 2 cụm hoàn tất để chống spam tin lẻ.
    2. **Ca 2 (Ca Trưa):** Lịch chạy chính thức là 12:00 (Phiên 1) và 14:00 (Phiên 2), quản lý độc lập Pool `{Row 3, Row 4, Row 8}`. Báo cáo rõ cả 2 mốc để User nắm trọn tình hình vận hành farm.

- 🛑 **Triage Thắc Mắc 'Tại Sao Ca Tối (Pool {5, 6}) Lại Chạy Tik 1 / Tik Khác 5, 6':**
  * **Hiện tượng:** User thấy tiêu đề Watchdog báo `[TIKTOK FOLLOW] Ca 3 - Phiên 1/2 (Tối) hoàn tất (Pool {5, 6})` nhưng danh sách máy lại báo `M37 [Tik 1]` (hoặc Tik 2, 3, 4, 7, 8). User thắc mắc tại sao ca tối lại chạy Tik 1.
  * **Nguyên nhân cốt lõi (Lượt Dynamic Slot Ngày 3 của Ca 3):**
    - Khác với Ca 1 `{1, 2, 7}` và Ca 2 `{3, 4, 8}` có 3 nick cứng, **Ca 3 chỉ có 2 nick cứng `{5, 6}`**.
    - Khi máy đã hoàn thành cả 2 nick `{5, 6}` trong chu kỳ (`cycle_history['3'][m]` chứa cả 5 và 6), `candidates` của pool `{5, 6}` bị rỗng $\implies$ máy tự động kích hoạt **Lượt 3: Dynamic Slot (marker `-1`)**.
    - Tại Lượt Dynamic Slot, thuật toán `resolve_dynamic_account_for_machine` quét trên **toàn bộ 8 slot** của máy theo 3 tầng phễu (Lớp 1: Cắn đề xuất $\to$ Lớp 2: Đi tù xả phạt nhả follow $\to$ Lớp 3: Nick non ít video nhất). Nick được bốc có thể là bất kỳ Tik nào từ 1 đến 8 (ví dụ M37 bốc trúng Tik 1).
    - Sau khi hoàn thành lượt Dynamic Slot này, `cycle_history['3'][m]` mới reset về rỗng để bắt đầu vòng tuần tự mới quay lại `{5, 6}`.
  * **Về nhãn hiển thị Watchdog:**
    - Nhãn `(Pool {5, 6})` trên tiêu đề Telegram là nhãn cố định theo khung giờ Ca 3 (do hàm `_row_or_pool_label` map từ Ca 3) để phân biệt ranh giới ca với Ca 1 và Ca 2. Nó KHÔNG mang nghĩa ép cứng máy chỉ được chạy Tik 5/6 khi đang ở Lượt Dynamic Slot.
  * **Quy trình giải thích nhanh cho User:**
    1. Xác nhận máy đang ở Lượt 3 (Dynamic Slot dưỡng sinh) của Ca 3 sau khi đã đi đủ Tik 5 và Tik 6 (`cycle_history['3'][m] == [6, 5, -1]`).
    2. Nêu rõ slot hiện tại được bốc theo 3 phễu dưỡng sinh (cắn đề xuất / xả phạt / nick ít video).
    3. Làm rõ nhãn `(Pool {5, 6})` ở tiêu đề là nhãn định danh khung giờ, không phải khóa cứng nick.

- 🛑 **Triage Thắc Mắc 'Tại Sao Máy N Chạy Lệch Row/Tik So Với Số Đông Toàn Farm':**
  * **Hiện tượng:** User thấy đa số farm hôm nay chạy Tik 2 (hoặc Tik 1), nhưng một số máy cá biệt (ví dụ M2) lại chạy ngược lại (chạy Tik 1). User nghi ngờ farm bị chạy lặp nick hoặc thuật toán phân bổ bị sai.
  * **Nguyên nhân cốt lõi (Per-Machine Cycle History):** Thuật toán `resolve_shift_pool_account` quản lý chu kỳ xoay tua **độc lập theo từng máy** (`cycle_history[ca][machine]` trong `shift_pool_cycle_state.json`), KHÔNG ép cứng đồng bộ trạng thái toàn farm.
    - Nếu hôm qua máy X đã chạy Row 2 (`used = [2]`), thì hôm nay ứng viên còn lại trong Ca 1 `{1, 2, 7}` của máy X là `{1, 7}` $\implies$ máy X bắt buộc chạy Row 1 (hoặc 7) để trả chu kỳ `[2, 1]`.
    - Trong khi các máy khác hôm qua chạy Row 1 (`used = [1]`), thì hôm nay còn lại `{2, 7}` $\implies$ chạy Row 2. Do đó máy X sẽ xuất hiện "lệch pha" với số đông.
  * **Quy trình 3 bước đối soát nhanh O(1) khi User thắc mắc:**
    1. Đọc state hiện tại: `D:/Taadaa/runtime/kibe/cron-state/shift_pool_cycle_state.json` $\to$ kiểm tra `today_shift_sessions[ca][str(m)]` và `cycle_history[ca][str(m)]`.
    2. Đọc manifest hôm qua: `D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD_hqua>/row-0-.../run_manifest.json` $\to$ xác nhận máy X hôm qua thực tế đã chạy row nào.
    3. Đối soát overlap: Khẳng định nick hôm nay và hôm qua khác nhau 100% (luân phiên chuẩn, không trùng lặp), giải thích rõ máy đang đi theo đúng cycle history cá nhân.

- 🛑 **Triage Dự Báo Lịch Chạy Ca 3 Ngày 3 — CẤM Nhầm Ca 3 Tự Reset Về {5, 6}:**
  * **Cạm bẫy Agent thường mắc:** Khi User hỏi lịch chạy ngày mai/ca tối của các máy, Coordinator thường nhìn vào pool `{5, 6}` của Ca 3 và đoán nhầm là "Ca 3 sau 2 ngày sẽ reset vòng mới quay lại Row 5/6".
  * **Quy tắc chuẩn hóa 100%:** Ca 1 và Ca 2 chạy chu kỳ 3 ngày (3 nick). Riêng Ca 3 chỉ có 2 nick `{5, 6}`:
    - Ngày 1: Chạy nick 1 của pool.
    - Ngày 2: Chạy nick 2 của pool.
    - **Ngày 3 (Lượt Dynamic Slot):** Khi cả Row 5 và Row 6 đều đã có trong `cycle_history['3'][m]`, `candidates` bị rỗng $\implies$ script bắt buộc ghi nhận marker `-1` và kích hoạt **`3-tier dynamic healing slot`** (`resolve_dynamic_account_for_machine` chọn nick Cắn đề xuất $\to$ Đi tù nhả follow $\to$ Nick non ít video nhất) với cờ **`rest_day_no_follow = True`**.
    - Chỉ sau khi xong Lượt Dynamic Ngày 3 này thì Ca 3 mới reset `history` về rỗng để bắt đầu vòng mới `{5, 6}` ở Ngày 4.
  * **Hành động Coordinator:** Khi dự báo Ca 3 cho máy đã chạy đủ 2 nick `{5, 6}` trong chu kỳ, BẮT BUỘC gọi `resolve_dynamic_account_for_machine` để báo đúng nick cắn đề xuất / xả phạt / nick non sẽ được bốc, cấm đoán mò Row 5 hay Row 6.

- 🛑 **Quy tắc Bất biến Bỏ Qua Follow (`dynamic-nurture-row-follow-disabled` & 48h Interval Gate):**
  * DUY NHẤT VÀ ĐỘC QUYỀN áp dụng khi phiên nuôi rơi vào lượt Dynamic Slot của Ca 3 (hoặc fallback 3 phễu khi cạn pool). `feed_session_workbook.py` gán cờ `rest_day_no_follow: true` vào `MachineAccount`.
  * **Cạm bẫy rơi cờ qua cache:** Khi Session 1 ghi nhận vào `today_shift_sessions`, nếu không lưu cờ `is_dynamic` thì Session 2 hoặc khi đọc lại cache sẽ return số row thông thường mà không raise ValueError, làm rớt cờ `rest_day_no_follow = False`. Bắt buộc ghi nhận `dynamic_sessions[ca][machine] = True` và kiểm tra qua `is_shift_session_dynamic_slot` để duy trì cờ. Khi sang ngày mới hoặc chọn slot tĩnh, bắt buộc xóa cờ dynamic.
  * **Hard gate 48h Interval (`_is_account_follow_cooldown`):** Kiểm tra các lượt trong `state['followed']`. Nếu có lượt follow ở ngày hôm trước mà khoảng cách tính đến hiện tại `0.0 <= age_hours <= 48.0h` -> bắt buộc `is_in_cooldown = True` (skip follow, lý do cooldown). Lượt follow của chính ngày hôm nay không bị chặn để Session 2 cùng ngày chạy bình thường.
  * **Chống trôi lượt khi lỗi (Post-Follow Completion Gate):** CẤM append `row` vào `cycle_history` khi mới select ở Session 1. Chỉ gọi `mark_shift_account_cycle_completed` sau khi phiên follow đã chạy hoàn tất thành công (`proc.returncode == 0 and result.status == 'OK' and not result.failed`). Nếu phiên bị crash/timeout/lỗi trước khi chạy -> KHÔNG mark để ngày hôm sau máy tự retry lại đúng nick đó. Nếu phiên lệch ngày (`state.date != today_iso`), từ chối ghi cycle_history để chống corrupt rotation.
  * Tại `multi_machine_feed_session.py`, `_run_follow_hook` kiểm tra `getattr(account, 'rest_day_no_follow', False)` và tự động bỏ qua bước follow, xuất reason:
    `status: "skipped", reason: "dynamic-nurture-row-follow-disabled"`.
  * Ca 1 và Ca 2 tuyệt đối KHÔNG BAO GIỜ bị dính reason này.

### Quy Luật Bốc Tuần Tự Đi Đủ 8 Nick (Chống Bỏ Đói & Chống Trôi Lượt):
- **Phễu Sức Khỏe 6 Tầng (`_follow_rank`):**
  1. 🟢 **Rank 1 - Khỏe (`healthy`):** `graduated=True` hoặc `healthy`.
  2. 🥈 **Rank 2 - Đề xuất (`boosted`):** `is_account_boosted(machine, row) == True`.
  3. 🥉 **Rank 3 - Hồi phục 2 (`probation_tier2`):** `probation_clean_days >= 1`.
  4. 🎖️ **Rank 4 - Hồi phục 1 (`probation_tier1`):** `probation_clean_days == 0` và `fail_streak > 0`.
  5. ⚠️ **Rank 5 - Nhả (`cooldown`):** Dính phạt nhả follow (`is_in_cooldown=True` hoặc `cooldown_until_date`).
  6. 🌱 **Rank 6 - Mặc định / Yếu:** Nick mới hoặc video count thấp nhất.
- **Nguyên lý xoay vòng & Chống trôi lượt khi lỗi:**
  * Máy lọc các nick trong Pool chưa chạy trong chu kỳ (`candidates = [r for r in pool if r not in used]`).
  * Sắp xếp theo thứ hạng sức khỏe: `min(candidates, key=lambda r: _follow_rank(machine, r, today))`.
  * **Quy tắc sống còn:** Nếu hôm nay chạy nick đó bị lỗi/fail/crash $\implies$ Hôm sau máy VẪN TIẾP TỤC CHẠY LẠI NICK ĐÓ cho đến khi thành công ít nhất 1 lần mới được tính là xong lượt và nhường cho nick tiếp theo.
  * Khi tất cả nick trong pool của ca đó đều đã chạy thành công (`not candidates`) $\implies$ Tự động reset `used` của ca đó để bắt đầu vòng tuần tự mới.
  * **Bảo đảm 100%:** Luân phiên đi đủ cả 8 nick trên từng máy, không bao giờ có nick nào bị bỏ đói!

### Tách Bạch Tuyệt Đối Giữa Nuôi Feed & Cooldown Follow 48h:
1. **Nuôi Feed & Đăng Video:** KHÔNG CÓ BẤT KỲ COOLDOWN 48H NÀO. Được chạy tự do theo ca quy định.
2. **Cooldown 48h:** DUY NHẤT VÀ ĐỘC QUYỀN ÁP DỤNG CHO HÀNH ĐỘNG ĐI FOLLOW.
   * Lần follow gần nhất $< 48\text{h}$ $\implies$ Tắt follow, chỉ cho nuôi feed và up video.
   * Lần follow gần nhất $\ge 48\text{h}$ $\implies$ Cấp quyền follow bình thường.
   * Nick dính án phạt nhả follow BẮT BUỘC tuân thủ streak riêng của nick đó (Streak 1: 1 ngày, Streak 2-3: 3 ngày...). Dù hết 48h toàn farm nhưng nếu án phạt streak chưa hết thì vẫn tự động khóa quyền follow.
   * **Cạm bẫy MagicMock trong Unit Test:** Khi kiểm tra cờ tắt follow `account.rest_day_no_follow`, BẮT BUỘC dùng `getattr(account, "rest_day_no_follow", None) is True` thay vì `getattr(account, "rest_day_no_follow", False)` vì nếu `account` là `MagicMock`, thuộc tính chưa set sẽ trả về mock object con (truthy trong Python), làm sai logic skip follow.

---

## 2. Cơ Chế 3 Phễu Dưỡng Sinh (`resolve_dynamic_account_for_machine`)
Khi rơi vào ca/ngày dưỡng sinh, `resolve_shift_pool_account` raise `ValueError`, tầng `feed_session_workbook.py` tự động kích hoạt 3 lớp phễu chọn nick per-machine:
1. **Lớp 1 (Ưu tiên 1 - Cắn đề xuất):** `is_account_boosted(machine, row, user)` (Follower tăng $\ge 20$, Tim $\ge 50$ trong 7 ngày qua). Giữ nhịp đăng video để ăn view.
2. **Lớp 2 (Ưu tiên 2 - Đi tù / Gỡ hạn chế):** `_is_account_follow_cooldown(machine, row)` (Nick dính nhả follow cần lướt feed xả cooldown).
3. **Lớp 3 (Ưu tiên 3 - Nick non / ít video nhất):** Sắp xếp theo `video_count` tăng dần để kéo nick yếu lên.

---

## 3. Bất Biến "Phiên 2 Bám Phiên 1" (S2 bám S1 100%)
- **Mục tiêu:** Phiên 2 (08h, 14h, 20h - có upload hook) bắt buộc chạy đúng tài khoản đã được nuôi ở Phiên 1 (06h, 12h, 18h) cùng ca trong ngày.
- **Lưu vết:** `record_shift_session_account(machine, row, ca, today_date)` ghi nhận vào `today_shift_sessions[ca][machine] = row`.
- **Đồng bộ Dưỡng Sinh:** Khi Phiên 1 rơi vào nhánh 3 phễu, `feed_session_workbook.py` BẮT BUỘC gọi `record_shift_session_account` ngay khi chọn được nick. Phiên 2 chỉ đọc lại vết này mà không tính lại phễu, chống việc cooldown thay đổi giữa 2 phiên làm lệch nick.
- **Thứ tự kiểm tra Fallback (Crucial Pitfall):** Trong `resolve_shift_pool_account`, điều kiện fallback `cycle_day == 3 or (cycle_day == 2 and ca == 3)` PHẢI ĐẶT TRƯỚC `if machine_key in today_sessions` ở Session 1. Nếu đặt sau, Session 1 của ngày dưỡng sinh có nguy cơ đọc trúng bản ghi cũ từ pool thay vì kích hoạt 3 phễu.
- **Tách bạch Session 2 vs Fallback:**
  * Session 2 LUÔN LUÔN đọc từ `today_sessions[ca_key][machine_key]`. Nếu tìm thấy: log `[SHIFT_POOL_SELECT] ... source=session1_sync` và return ngay. Nếu thiếu: log `[SHIFT_POOL_SYNC_ERROR]` và raise `ValueError`.
  * Khối Fallback chỉ áp dụng cho Session 1: khi thỏa mãn điều kiện fallback, log `[SHIFT_POOL_FALLBACK_TRIGGER]` và raise `ValueError` để chuyển sang 3 phễu.
- **Hệ Thống Structured Telemetry Logging:**
  * `[SHIFT_POOL_SELECT]` kèm các nguồn: `source=session1_sync`, `source=today_cache`, `source=pool_rotation`.
  * `[SHIFT_POOL_FALLBACK_TRIGGER]`: Ghi nhận máy, ca, ngày chu kỳ khi kích hoạt 3 phễu.
  * `[SHIFT_POOL_EXHAUSTED]`: Cảnh báo khi hết nick khả dụng trong pool.
  * `[DYNAMIC_SESSION_SYNC]` & `[DYNAMIC_SESSION_SYNC_ERR]`: Ghi nhận đồng bộ phiên dưỡng sinh trong `feed_session_workbook.py`.
  * Thu hẹp ngoại lệ: Chỉ bắt `(ValueError, KeyError)` khi gọi `resolve_shift_pool_account` thay vì bắt broad `Exception`.
  * Kiểm thử bắt log: Dùng fixture `caplog` với `caplog.at_level(logging.INFO)` để assert bắt đúng chuỗi telemetry trong unit test.

---

## 4. Chuỗi Nối Dây (End-to-End Wiring) & Các Cạm Bẫy Lập Trình (Pitfalls)
1. **Bug `int(args.account_row_index or 1)`:**
   - Trong Python, khi truyền cờ `--account-row-index 0` để chạy dynamic, biểu thức `0 or 1` đánh giá ra `1` $\implies$ luôn bị ép thành Row 1.
   - Sửa chuẩn: `int(args.account_row_index) if args.account_row_index is not None else 1`.
2. **Forward tham số ShiftCa:**
   - `run_tiktok.py`: thêm cờ `--shift-ca {1, 2, 3}` và gán `config["_shift_ca"]`.
   - `run-feed-session.ps1`: thêm `[ValidateRange(1, 3)][int]$ShiftCa` và forward `--shift-ca $ShiftCa`.
3. **Cron Runner (`tiktok_runner.py`):**
   - Tự động map khung giờ: 6/8h $\to$ Ca 1; 12/14h $\to$ Ca 2; 18/20h $\to$ Ca 3.
   - Kích hoạt dynamic: truyền `-Row 0` và `-ShiftCa <ca>`.
   - Hàm `_get_machines_for_row(0)`: Khi `row == 0`, lọc toàn bộ máy có ít nhất 1 slot hợp lệ trong workbook. Tránh tính `slot_idx = row - 1 = -1` (vướng slot 8).
4. **Validation Bounds:**
   - `record_shift_session_account` kiểm tra chặt `1 <= row <= 8` và `ca in (1, 2, 3)`.
   - `_load_state` bọc `try-catch` kiểm tra chuỗi rỗng để chống crash `JSONDecodeError` khi state file bị 0 bytes.
5. **Cạm Bẫy Deploy Drift Giữa Dev Repo (`tiktok-luot nuoi acc`) và Cron Runtime (`Hermes/deploy`):**
   - **Hiện tượng:** Code dynamic `Row 0` đã commit trong `tiktok-luot nuoi acc`, nhưng hôm sau cron vẫn chạy nhặt fixed row cũ (Row 2, 4, 6...).
   - **Nguyên nhân:** Hermes cronjob (`phase9-runner-tiktok-feed`, `tiktok-feed-session-watchdog`) thực thi scripts từ `%LOCALAPPDATA%\hermes\scripts\`, vốn được đồng bộ định kỳ bởi `cron_sync_watchdog.py` từ repo `D:\Taadaa\Hermes\deploy\hermes-home\scripts\`.
   - **Quy trình Deploy bắt buộc sau khi sửa `scripts/hermes_cron/`:**
     1. Đồng bộ file sang deploy repo:
        `cp "D:/Taadaa/tiktok-luot nuoi acc/scripts/hermes_cron/tiktok_runner.py" "D:/Taadaa/Hermes/deploy/hermes-home/scripts/tiktok_runner.py"`
        `cp "D:/Taadaa/tiktok-luot nuoi acc/scripts/hermes_cron/tiktok_picker.py" "D:/Taadaa/Hermes/deploy/hermes-home/scripts/tiktok_picker.py"`
        `cp "D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py" "D:/Taadaa/Hermes/deploy/hermes-home/scripts/feed_session_watchdog.py"`
        `cp "D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py" "D:/Taadaa/tiktok-luot nuoi acc/scripts/hermes_cron/feed_session_watchdog.py"`
     2. Commit thay đổi vào cả 2 repo (`tiktok-luot nuoi acc` và `Hermes`).
     3. Kích hoạt đồng bộ runtime ngay lập tức:
        `python "D:/Taadaa/Hermes/deploy/hermes-home/scripts/cron_sync_watchdog.py" --force`
     4. Chạy kiểm chứng dry-run/simulation `_determine_row()` và `_get_machines_for_row(0)` để đảm bảo `effective_feed_row == 0` được kích hoạt.
6. **Cạm bẫy `run-feed-session.ps1` cấm kết hợp `-LocalRun` với `-Machines`:**
   - Khi `tiktok_runner.py` gọi pre-session device gate để lọc `healthy_machines`, nó truyền cả `-LocalRun` và `-Machines`.
   - Nếu `run-feed-session.ps1` giữ guard cũ `if ($LocalRun -and $Machines) { throw ... }`, toàn bộ phiên spawn từ runner sẽ văng lỗi.
   - Sửa chuẩn: Cho phép `-LocalRun` kết hợp `-Machines`, lọc mảng máy tìm thấy từ workbook row theo tập `[int]$m` được truyền vào.
7. **Cạm bẫy Line Budget Gate của `feed_session_watchdog.py` (`<= 1450` dòng):**
   - Bộ test kiến trúc `tests/test_watchdog_architecture_gate.py::test_feed_session_watchdog_line_budget` kiểm soát chặt chẽ độ dài `feed_session_watchdog.py <= 1450` dòng.
   - Khi chèn thêm logic/hook (ví dụ `incident_emitter`), BẮT BUỘC phải nén gọn các cấu trúc tĩnh (như list-dict `CLUSTERS` trên 1 dòng) hoặc loại bỏ dòng trống dư thừa để không vi phạm kiến trúc gate.
8. **Kiến Trúc Two-Phase Commit & Auto-Retry Giao Tin Telegram (`feed_session_watchdog.py`):**
   - **Vấn đề:** Hermes scheduler chạy `no_agent: True` không có hàng đợi retry khi gặp lỗi mạng tạm thời (`httpx.ProxyError: Host unreachable`). Nếu script watchdog commit state trước khi Hermes gửi tin thành công, báo cáo phiên nuôi sẽ biến mất vĩnh viễn (do các tick sau script im lặng).
   - **Giải pháp Two-Phase Commit:**
     * *Pha 1 (Pending Claim):* Khi có report mới, lưu vào `pending_delivery: {"session_key": ..., "message": ...}`, chưa commit vào `reported_sessions`, rồi in stdout.
     * *Pha 2 (Hermes Telemetry Verification):* Ở tick kế tiếp, đọc `jobs.json` của Hermes (`_get_hermes_delivery_error(mode)`). Nếu có `last_delivery_error`, tự động re-emit `pending["message"]` để Hermes retry ngay. Chỉ khi `last_delivery_error is None`, mới chuyển `session_key` vào `reported_sessions` và dọn `pending_delivery`.

---

## 5. Quy Ước Định Danh Run Artifacts & Báo Cáo Watchdog (`Run: row-{row}-{hhmmss}`)
- **Cấu trúc nhãn Run:** `row-{row}-{hhmmss}` (ví dụ: `row-0-140735`):
  * **`row` (Row Index):** Bằng `0` khi kích hoạt cơ chế Dynamic Feed (`USE_DYNAMIC_FEED=1` mặc định) — máy bốc nick linh hoạt theo Pool của Ca ({1, 2, 7}, {3, 4, 8}, {5, 6}) và luân chuyển theo 6 tầng phễu sức khỏe (`_follow_rank`). Bằng `1..8` nếu chạy chế độ fixed row tĩnh cũ.
  * **`hhmmss` (Timestamp):** Giờ - phút - giây lúc runner kích hoạt phiên chạy (giờ HCMC, vd `140735` = 14:07:35).
- **Vị trí lưu trữ Artifacts & Logs:**
  * Đường dẫn runtime: `D:\Taadaa\runtime\<cluster>\live\<YYYY-MM-DD>\row-{row}-{hhmmss}\<run_id>\`
  * Chứa đầy đủ: `run_manifest.json`, `summary.txt`, `log.jsonl`, và thư mục con `machines/machine_<id>/`.
- **Hiển thị trên Watchdog Telegram:**
  * Watchdog lọc các thư mục run trong `date_live` khớp với khung giờ ca (`SESSION_WINDOWS`), lấy run mới nhất `sorted_run_names[-1]` gán vào header cụm:
    `🏢 【FARM KIBE - MÁY 1-80】 (Run: row-0-140735)`
  * Mục đích: Phục vụ truy vết nhanh (Traceability), phân biệt rõ giữa Phiên 1 (sớm) và Phiên 2 (muộn) trong cùng 1 ca nuôi.
  * Chi tiết đối soát đa cụm và nhận diện rớt hub USB vật lý: xem [references/multi-cluster-watchdog-triage-and-usb-hub-patterns.md](multi-cluster-watchdog-triage-and-usb-hub-patterns.md).

---

## 6. Phân Định Ranh Giới Nghiệp Vụ: Report Nuôi Feed vs. Report Follow Chéo
Tuyệt đối không nhầm lẫn giữa 2 nhóm chỉ số trong 2 loại báo cáo watchdog định kỳ:

### A. Report TikTok Lướt Nuôi Acc (`feed_session_watchdog` / `tiktok-feed-session-watchdog`):
- **Mục tiêu tối thượng:** Cho User quan sát và kiểm chứng **Flow thiết kế** của ca nuôi (thuật toán Dynamic Feed có bốc đúng và đều các Row trong Pool hay không).
- **Quy ước nhãn Watchdog `_row_or_pool_label` (Tránh hiểu lầm Fixed Row vs Dynamic):**
  * Khi chạy Fixed Row (`row > 0`): Watchdog ghi thẳng `(Row <N>)` (ví dụ: `(Row 5)`).
  * Khi chạy Dynamic Feed (`row == 0` / `effective_feed_row == 0`): Watchdog ghi nhãn Pool theo ca, gồm: Ca 1 `(Pool {1, 2, 7})`, Ca 2 `(Pool {3, 4, 8})`, Ca 3 `(Pool {5, 6})`.
  * **Lưu ý vận hành (FAQ):** Khi thấy báo cáo `(Pool {5, 6})` và artifact `row-0-hhmmss`, hệ thống ĐANG CHẠY 100% DYNAMIC (Row 0), không phải fixed row. Nhãn `{5, 6}` phản ánh tập ứng viên mà thuật toán đang phân bổ xoay vòng trên từng máy trong ca tối.
- **Yêu cầu hiển thị bắt buộc:** Thống kê **Tỉ lệ phân bổ Row trong Pool / Phiên** (ví dụ: `• Phân bổ Row trong Pool {3, 4, 8} (49 máy chạy): Row 8 (47 máy | 95.9%) | Row 4 (1 máy | 2.0%) | Row 7 (1 máy | 2.0%)`).
- **Ý nghĩa vận hành:** Giúp phát hiện ngay việc lệch tải hoặc kẹt thuật toán (ví dụ: 96% máy dồn vào Row 8 thay vì chia đều cho Row 3, 4, 8 trong Pool).
- **CẤM TUYỆT ĐỐI:** Không đưa các khái niệm "nhả follow", "thành công follow", hay "cooldown nhả" vào report nuôi acc, vì phiên lướt feed thuần túy không có hành động nhả follow.

### B. Report TikTok Follow Chéo (`follow_session_watchdog` / `tiktok-follow-session-watchdog`):
- **Mục tiêu tối thượng:** Đo lường **Sức khỏe & Tỷ lệ nhả (Health Tiers & Retention)** của dàn nick khi đi follow trên từng dải IP/Proxy.
- **Yêu cầu hiển thị bắt buộc:** Áp dụng chuẩn cơ chế Sức khỏe:
  * **Thành công:** Phân nhóm theo độ khỏe: Nhóm Khỏe (10+ lượt), Hồi phục 2 (5-9 lượt), Hồi phục 1 (1-4 lượt).
  * **Nhả follow:** Nhả liền (0 lượt), Nhả ở các cấp (Hồi phục 1/2, Khỏe).
  * **Bỏ qua:** Phân loại rõ Cooldown nhả follow (48h), Chưa đủ điều kiện (under video gate / age gate), Sensitive feed...
  * **Cầu dao IP:** `format_ip_circuit_breaker_report` ghi nhận số proxy đã ngắt và danh sách máy anh em được khóa cứu.
