# Follow Anchor Trap, Streak Decoupling & Cooldown Ladder Invariants

## Bối Cảnh Sự Cố & Chẩn Đoán (2026-10-25)
Trong hệ thống `tiktok-follow` (Mode 2 follow followers), có 97 nick bị kẹt `fail_streak >= 3` với cooldown bị giam 7 đến 15 ngày. Khảo sát đối soát 466 nick và log hiện trường (điển hình Row 4 ngày 2026-10-24: 32/32 máy fail cùng 1 lý do):
1. **Phía TikTok:** TikTok thật sự từ chối lượt follow (silent-drop/rate limit), được kiểm chứng khách quan bằng WinRT OCR và Path B re-entry.
2. **Phía Script:** Có 2 lỗi cơ chế logic nghiêm trọng biến một cú nhả bình thường thành vòng lặp án tù vô tận (Infinite Prison Loop):

---

### 1. Cạm Bẫy "Bắt Buộc Follow Anchor" (`_ensure_anchor_followed`)
- **Vấn đề:** Trong Mode 2 (`follow_runner/flows/mode2_follow_followers.py`), script yêu cầu nick phải bấm Follow Anchor (nick Tik 1/Tik 2 làm gốc) trước rồi mới được mở danh sách Following của Anchor để đi chéo.
- **Thực tế:** Trên ứng dụng TikTok, danh sách Following của tài khoản công khai hoàn toàn có thể mở và đọc mà **không cần phải follow tài khoản đó**.
- **Hậu quả:** 
  - Nick cựu binh (Row 1) đã follow Anchor từ nhiều tháng trước -> `classification == "followed"` -> bỏ qua kiểm tra và chạy an toàn.
  - Nick non (Row 2, 3, 4, 5, 6) hoặc nick vừa ra tù -> Bắt buộc bấm Anchor -> Bị TikTok chặn lượt bấm đầu tiên -> Script phán quyết ngay `state.set_follow_failed()` và hủy toàn bộ phiên chạy! Nick hoàn toàn không có cơ hội đi chéo cho bất kỳ nick con nào khác trong list.

---

### 2. Bóc Tách Hoàn Toàn 2 Hệ Thống: `fail_streak` vs Cấp Độ Quota Tốt Nghiệp

Trước đây hệ thống bị lỗi nghiêm trọng do nhập nhằng giữa **Bộ đếm chuỗi thất bại (`fail_streak`)** và **Tầng Quota Dưỡng Nick (`probation / graduation`)**, khiến nick vừa mãn hạn ra cày được follow sạch nhưng vẫn bị ghim streak cũ, cữ sau lỡ nhả là bị kích hoạt tái phạm oan lên Streak 3, 4 (giam 7–15 ngày).

#### A. Hệ thống 1: `fail_streak` (Chuỗi thất bại liên tiếp)
- **Quy tắc vàng:** Trong `mark(uid, STATUS_FOLLOWED)`, **cứ follow thành công dù chỉ 1 người (`used >= 1`) $\rightarrow$ `self._data["fail_streak"] = 0` ngay lập tức!**
- Chuỗi thất bại bị bẻ gãy ngay tại thời điểm có follow thành công. Không bao giờ để nick đang follow được phải mang án streak 1, 2, 3.
- **Thang phạt Cooldown chuẩn hóa khi dính nhả:**
  - **`Streak 0`:** Nick hoàn toàn sạch, đang chạy khỏe bình thường, không dính án, không cooldown.
  - **`Streak 1` (Nhả lần đầu hoặc chạm trần phiên `used > 0`):** **CHỈ COOLDOWN 24 GIỜ (1 NGÀY)** để xả cache! Tuyệt đối CẤM phạt 3 ngày.
  - **`Streak 2` (Tái phạm lần 2 liên tiếp `used == 0`):** **CHỈ COOLDOWN 3 NGÀY** (Tuyệt đối CẤM phạt 5 ngày).
  - **`Streak 3` (Tái phạm lần 3 liên tiếp `used == 0`):** **CHỈ COOLDOWN 5 NGÀY** (Tuyệt đối CẤM phạt 7 ngày).
  - **`Streak >= 4` (Tái phạm dai dẳng):** Cooldown 15 ngày (giam cách ly kiểm điểm).

#### B. Hệ thống 2: Cấp độ Quota Dưỡng Nick (Hồi phục 1 ➔ Hồi phục 2 ➔ Khỏe)
- Chạy **độc lập 100%** qua `probation_clean_days` và `graduated`, tuyệt đối không phụ thuộc vào `fail_streak`:
  - **Hồi phục 1:** Cấp quota 2–4 lượt.
  - **Hồi phục 2:** Cấp quota 4–6 lượt.
  - **Khỏe (Tốt nghiệp / Graduated):** Cấp quota full 10–15 lượt.
- Cờ `is_post_cooldown_warmup` được kích hoạt khi `(not self.is_graduated) and (not self.follow_failed)` hoặc khi `recovered_date == today`. Nhờ vậy, nick dù có `fail_streak = 0` vẫn giữ đúng quota dưỡng an toàn (2–4 lượt) suốt các phiên cùng ngày và ngày hôm sau, không bị nhảy vọt lên full quota. Nếu cữ sau có lỡ bị nhả thì nick chỉ bị phạt lại ở mức Streak 1 (24h), không bao giờ bị đè lên Streak 2, 3, 4 giam oan.

---

### 3. Quy Tắc Thiết Kế Tránh Bẫy Anchor & Lạm Phát Streak (Invariants)
1. **Không chặn Gateway:** Thất bại khi tương tác với Anchor (nick gốc) không được coi là lỗi vi phạm spam của tài khoản. Chỉ bỏ qua Anchor đó hoặc chuyển sang Anchor khác / Mode 1.
2. **Cấm tăng streak khi `used == 0` do lỗi Anchor:** `fail_streak` chỉ được phép tăng khi nick đã vào danh sách mục tiêu thực tế và bị server TikTok từ chối nhiều lần trong chuỗi hành động hợp lệ.
3. **Decouple Anchor Following:** Luôn ưu tiên mở thẳng tab Following của Anchor mà không ép nick phải thực hiện hành động follow Anchor trước.

---

### 4. Kỷ Luật Dispatch Worker & Timeout
- **Worker Floor 300s:** BẮT BUỘC tuân thủ sàn timeout >= 300s cho mọi lệnh dispatch worker. CẤM TUYỆT ĐỐI Coordinator tự ý gõ cờ `--timeout 30` hay bóp ngắn timeout làm ngắt luồng stream của worker.
- **Claude 100% On-Demand:** Khi user cấu hình Sol Worker, Coordinator BẮT BUỘC tôn trọng Sol Worker. CẤM TUYỆT ĐỐI tự ý đề xuất, hối thúc hay chuyển sang Claude Worker khi user không yêu cầu đích danh. Cấm can thiệp làm hỏng tầng cơ học dispatch worker đã được chuẩn hóa.

---

### 5. Khóa Đồng Bộ Đa Repo (Cross-Repo Sync Contract)
1. **Tại `tiktok-follow` (`follow_runner/core/follow_state.py`):**
   - Trong `mark(uid, STATUS_FOLLOWED)`: Reset `self._data["fail_streak"] = 0` ngay khi có 1 follow thành công.
   - Trong `set_follow_failed()`: Khi `used > 0`, ghi nhận `streak = 1`, không pop `graduated`/`probation_clean_days`, đặt `cooldown_until_local = (now_utc + 24h).astimezone(tz)`. Khi `used == 0`: streak 1 là 24h, streak 2 là 3 ngày, streak 3 là 5 ngày, streak >= 4 là 15 ngày.
2. **Tại `tiktok-luot nuoi acc` (`python_runner/flows/multi_machine_feed_session.py`):**
   - Trong `_is_account_follow_cooldown()`: Tôn trọng tuyệt đối `cooldown_until_at` / `cooldown_until_date` từ state. Khi `streak <= 1`, `streak_days = 1`, cho phép nick đi follow ngay khi hết mốc 24h thay vì tự ý ép phạt 3/5/7 ngày.
3. **Tại Dashboard (`D:/Taadaa/tools/follow_health_helper.py`):**
   - Đối chiếu trực tiếp `cooldown_until_at` với `now` để phân loại trạng thái Cooldown; cấm dùng cờ `follow_failed` đơn thuần làm tiêu chí ném nick vào `🔴 Cooldown`.
4. **Xả án tồn dư & Điểm mù lọc (`reconcile_all_streak_cooldowns.py` & `reconcile_unfair_streaks.py`):**
   - Đồng bộ toàn bộ các file state trên farm để xả án ngay lập tức cho các nick đã hết hạn cooldown 24h (Streak 1), 3 ngày (Streak 2), 5 ngày (Streak 3).
   - **Điểm mù cần tránh:** 
     + `reconcile_all_streak_cooldowns.py` bỏ qua `Streak >= 4` (15 ngày cooldown).
     + `reconcile_unfair_streaks.py` có điều kiện lọc `total_followed >= 10`, khiến các nick mới hoặc nick chưa từng được bot ghi nhận follow thành công (`len(followed) < 10`) bị loại khỏi diện giải cứu và tiếp tục kẹt oan tới tháng 11/2026.

---

### 6. Đối Soát Ground Truth Khi Nghi Ngờ Án Oan Cooldown (S4)
1. **Kiểm tra chỉ số thực tế trên TikTok (Ground Truth):**
   - Đối chiếu số lượng **"Đã follow" (Following)** thật của tài khoản với `fail_streak` và `len(followed)` trong state.
   - Nếu tài khoản có video view organic tốt, tim cao, được tag `🔥 ĐỀ XUẤT`, và đặc biệt **mới follow rất ít người (1–2 lượt follow)** nhưng bị gán `fail_streak >= 4`: **Xác định 100% là án oan do bug lạm phát streak cũ**.
2. **Quy trình xả án O(1) cho file state (`follow_state_<m>_row_<t>.json`):**
   - Xóa bỏ: `cooldown_until_date`, `cooldown_until_at`, `follow_failed_date`, `last_cooldown_decision`.
   - Đặt lại: `fail_streak: 1` (hoặc 0 nếu nick chưa từng có án tích), `follow_failed: false`, `probation_clean_days: 1`.
   - Dashboard lập tức chuyển từ `🔴 Cooldown` sang `🟡 Hồi phục 2`, đưa nick về trạng thái an toàn để tiếp tục chu trình nuôi dưỡng.

---

### 7. Kỷ Luật Điều Tra Dứt Điểm Toàn Farm Khi Phát Hiện Ổ Dịch Cooldown (Anti-Quan Liêu)
1. **Cấm tuyệt đối quy chụp suy diễn:** Khi telemetry dashboard in ra số lượng lớn nick bị giam ở các mức phạt cao (như `🔴 Cooldown (Streak 4): 59 nick`), CẤM TUYỆT ĐỐI tự ý suy diễn rằng "đây là nick lì đòn, tái phạm nhiều lần" để lấp liếm hay xin chốt phiên.
2. **Quy tắc bóc tách 100% state files:**
   - Bắt buộc quét toàn bộ các file state bị dính cooldown.
   - Lập bảng phân bổ: theo ngày lỗi gần nhất (`last_failed_date`), theo tổng số follow (`total_followed`), và theo lý do thất bại (`last_fail_reason`).
   - Nếu đa số nick có `total_followed == 0` hoặc dính từ đợt chạy trước khi fix bug (ví dụ đợt 12–20/10 trước commit `f515805`), xác định 100% đây là án oan do lỗi lạm phát streak cũ hoặc lỗi bẫy Anchor. Bắt buộc lập tool xả án dứt điểm (`reconcile_streak4_unfair.py`) trước khi báo cáo hoàn tất.

---

### 8. Bản Chất Kỹ Thuật Của Các Nhóm Streak 1, 2, 3 & Kỷ Luật Giữ Nguyên Án Thật
1. **Nguyên Tắc "Bị Thật Thì Giữ Nguyên, Oan/Hết Hạn Mới Xả":**
   - Khi điều tra hoặc xử lý streak farm, TUYỆT ĐỐI CẤM xả trắng toàn bộ farm vô tội vạ.
   - BẮT BUỘC phân loại thành 3 nhóm rõ rệt:
     * **Nhóm A (Đã hết hạn phạt):** Đã chấp hành đủ 24h (S1), 3 ngày (S2), hoặc 5 ngày (S3) -> Bắt buộc xả án ngay, không để kẹt thêm ngày nào.
     * **Nhóm B (Chạm trần phiên `used > 0`):** Nick đã follow thành công $\ge 1$ lượt trong ca rồi mới dừng phiên -> Oan streak, xả án ngay vì đây là ceiling drop.
     * **Nhóm C (BỊ NHẢ THẬT & ĐANG TRONG THỜI HẠN COOLDOWN HỢP LỆ):** BẮT BUỘC GIỮ NGUYÊN 100% ÁN PHẠT để tài khoản hoàn tất chu kỳ xả cache và dưỡng tự nhiên. Cấm xóa cooldown của nhóm này!
2. **Streak 1 (24h Cooldown):**
   - Đa số (>90%) là lỗi ngoại cảnh/rớt cữ (`empty reason`): mạng chập chờn, proxy timeout, app TikTok crash trước khi kịp bấm follow.
   - Cơ chế xả án: Tính theo giờ rolling 24h (`now_hcm >= cooldown_until_at`). Phải chạy xả án cuốn chiếu trong ngày để nick hết 24h được trả về cữ chạy ngay, không để dồn ứ trên dashboard.
3. **Streak 2 (3 ngày Cooldown) & Streak 3 (5 ngày Cooldown):**
   - Hơn 60% nạn nhân là do **Bẫy Anchor**: Nick non (`0 follow`) vừa ra tù, vào cữ chạy bị ép bấm Anchor phát đầu tiên (`used == 0`) -> Anchor bị TikTok siết nhả -> Script đôn bậc từ Streak 1 lên Streak 2 (giam 3 ngày), rồi lên Streak 3 (giam 5 ngày).
   - **Bẫy so sánh ngày trong script xả án cũ:** Script `reconcile_all_streak_cooldowns.py` dùng điều kiện `today > expiry_day` khiến các nick đúng ngày mãn hạn (ví dụ Streak 3 giam 5 ngày từ 20/10 đến 25/10) bị giam thêm 1 ngày oan đến 26/10 mới được thả. Chuẩn hóa: phải so sánh timestamp chính xác hoặc `today >= expiry_day` khi hết giờ địa phương.
   - Với nhóm dính nhả thật và chưa đủ ngày cách ly: Giữ nguyên hạn phạt cho đến khi đủ ngày. Với nhóm án oan do bẫy Anchor tích tụ lâu ngày hoặc dính kịch khung do bug: chỉ xử lý hạ bậc khi đã chứng minh được điều kiện không phải spammer thật sự.

---

### 9. Pitfall Phân Loại Thuật Ngữ: Nghỉ Xả Cache 24h (Used > 0) Không Phải Là "Án Oan"
1. **Hiện tượng & Cơ chế đúng:**
   - Khi nick cày được $\ge 1$ lượt (ví dụ follow thành công 3 người, `used = 3`) rồi dừng lại ở lượt thứ 4 khi chạm trần, bản vá đã hoạt động chính xác: bảo toàn `probation_clean_days = 1`, giữ `fail_streak = 1`, và cấp cooldown đúng 24h rolling (`now + 24h`).
2. **Sai lầm chết người của Coordinator (Anti-Pattern):**
   - Thấy nick hiển thị nhãn `🔴 Cooldown (Streak 1)` trên dashboard liền vội vã kết luận là "nick cày thành công mà vẫn bị bắt đi tù oan", rồi tự tiện chạy script xóa sạch cờ cooldown khi chưa đủ 24h.
   - Hậu quả: Báo cáo gây hoang mang cho User rằng bản vá buổi sáng bị lỗi, đồng thời thả nick ra sân quá sớm trước 24h khiến TikTok server chưa kịp xả cache rate-limit.
3. **Quy tắc kỷ luật:**
   - Nick `used > 0` chạm trần bắt buộc phải nghỉ đủ 24 giờ để xả cache TikTok an toàn. Đây là cơ chế bảo vệ hợp lệ, **tuyệt đối không được gọi là "án oan"**.
   - Chỉ được xả án cho nick `used > 0` khi và chỉ khi **đã quá 24 giờ rolling** (`now_utc >= cooldown_until_at`).

---

### 10. Bẫy Profile Identity Mismatch & Cơ Chế Xác Minh Path B (Chống Rớt Follow Ảo)
1. **Bẫy Bio @Mention & Suggested Accounts Drawer:**
   - Trong `mode2_follow_followers.py` (`_path_b_verify`): Hàm `profile_identity_from_xml` lấy `@` đầu tiên trên toàn màn hình. Khi nick có bio chứa handle khác (ví dụ: `IG: @xyz`) hoặc banner TikTok có `@`, hàm lấy nhầm `@` trong bio làm username, làm lệch `profile_handle != target_uid`.
   - **Quy tắc vàng:** Luôn dùng `_find_header_handle_node` ở dải header (`y < 650`) làm nguồn chân lý duy nhất của profile header handle. Chỉ cần `handle_is_valid` (header node khớp target_uid và package chuẩn), xác nhận dump profile thành công.
   - Trong `verify_follow.py` (Mode 1): Ngay sau khi tap Follow, TikTok thường bật khay "Tài khoản tương tự" (Suggested Accounts). Quét lại màn hình ngay lập tức sẽ thấy xuất hiện các `@` lạ dẫn đến `identity_mismatch`.
   - **Quy tắc xử lý:** CẤM ném `MANUAL_REVIEW` ngay khi gặp `identity_mismatch` sau tap. BẮT BUỘC gọi `_reload()` (pull-to-refresh / re-entry) để xả khay gợi ý và làm mới trang trước khi kết luận.
2. **Bảo Toàn Follow Đã Gửi Lên Server:**
   - Khi nút follow trên row hoặc profile đã được tap thành công và đổi màu sang `followed`, lệnh follow đã gửi lên TikTok server. CẤM để các ngoại lệ render/popup tạm thời làm hủy cả phiên chạy (`break` out of session) hay xóa trắng mảng `followed`.

---

### 11. Chuẩn Hóa Đối Soát Watchdog Theo Account ID (Username) Thay Vì Row Máy
1. **Bản chất Schema TikTok Tracker DB (`tiktok_tracker.db`):**
   - Bảng `snapshots` của crawler TikTok Web chỉ lưu `(username, following, timestamp)`. Hoàn toàn KHÔNG có cột `row` hay `machine`.
2. **Nhược điểm chết người khi đối soát theo Row máy:**
   - Ở các ca hỗn hợp (`active_row = -1`) hoặc ca lẻ/phục hồi, máy có thể chạy Tik 2 hoặc Tik 3. Watchdog tra theo `row` dễ bị nhầm (như Máy 40 chạy Tik 2 `@nguyenkhoi1403` nhưng watchdog lại lấy Tik 1 `@charakrh768` ra đối soát dẫn đến báo lệch -3 lượt oan).
   - Dễ sai lệch nếu file excel bị đổi thứ tự dòng hoặc nhầm lẫn giữa 0-index và 1-index.
3. **Chuẩn hóa kiến trúc đối soát:**
   - `follow_result.json`: BẮT BUỘC ghi rõ trường `"account": account.expected_username`.
   - `parser.py`: Trích xuất `"account"` song song với `"row"`.
   - `feed_session_watchdog.py`: Ưu tiên tuyệt đối dùng `f_acc` (ID account) để query SQLite `tiktok_tracker.db`, chỉ fallback về `f_row` nếu thiếu dữ liệu account. Vẫn map ra nhãn `[Tik N]` dựa trên slot thực tế của nick trong máy.
4. **Bảo Toàn Follow Khi Timeout (Salvage Follows on Timeout):**
   - Khi tiến trình chạm trần `follow-timeout`, CẤM gán cứng `followed_count = 0`. BẮT BUỘC đọc file state `follow_state_<m>_row_<t>.json` trong ngày để vớt lại toàn bộ danh sách nick đã follow thành công, chống lệch số liệu đối soát với Web.
5. **Nhả Follow Không Nhồi Đúp Vào Nhóm Thành Công (`fl_success`):**
   - Khi máy được phân loại `category == "released"`, chỉ ghi nhận vào `fl_released`. CẤM TUYỆT ĐỐI append máy đó vào `fl_success` (dù `len(flist) > 0`), tránh việc một máy vừa xuất hiện ở mục "Thành công" vừa ở mục "Nhả liền".
6. **Bảo Toàn Account ID Xuyên Suốt Mọi Kênh Upload và Summary:**
   - Trong `_write_upload_result`: Đính kèm trường `"account"` tương tự follow.
   - Trong `parser.py`: Cào regex username thực tế từ `summary.txt` (`"username": "@..."`) và lưu `"account": m_acc`.
   - Trong `merger.py`: Cả `merge_machine_result`, `merge_follow_result`, `merge_upload_result` đều kế thừa và bảo toàn trường `account`.

---

### 12. Cơ Chế 2-Phase Delivery Confirmation Cho Watchdog Telegram (Chống Mất & Trùng Báo Cáo)
1. **Rủi Ro Của Cơ Chế Fire-and-Forget Cũ:**
   - Watchdog ghi `session_key` vào `reported_sessions` ngay khi vừa `print()` message ra stdout.
   - Nếu Hermes Scheduler gặp lỗi mạng Telegram (HTTP 5xx, timeout, Telegram API network dropped), message không đến được chat của User nhưng state file đã đánh dấu "đã báo cáo" $\rightarrow$ Mất vĩnh viễn báo cáo của cả phiên!
2. **Kiến Trúc 2 Pha với `pending_delivery`:**
   - **Pha 1 (Emit & Lưu Pending):** Khi phát hiện session mới cần báo cáo, watchdog ghi bản ghi `pending_delivery: {"session_key": key, "message": msg, "emitted_at": iso_str}` vào state JSON. Chưa commit vào `reported_sessions`.
   - **Pha 2 (Confirm & Commit):** Ở tick chạy tiếp theo của watchdog:
     * Kiểm tra `jobs.json` của Hermes (`LOCALAPPDATA/hermes/cron/jobs.json`).
     * Nếu có `last_delivery_error`: Re-emit ngay nội dung `pending_delivery["message"]` để Hermes gửi lại.
     * Nếu không có lỗi giao tin: Xác nhận tin đã gửi đến Telegram an toàn $\rightarrow$ Chính thức chuyển `session_key` vào `reported_sessions` và xóa trường `pending_delivery`.
   - Đảm bảo tính idempotency và không bao giờ nuốt chửng báo cáo khi có sự cố hạ tầng messaging.



