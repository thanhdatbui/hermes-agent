# Chẩn Đoán Nhả Follow (Follow Drop) & Đối Soát Lịch Sử Theo Chu Kỳ Ca Chẵn/Lẻ

## 1. Bối Cảnh & Phân Tích Lỗi Nhả Follow (Follow Drop / Rollback)

Khi runner follow thực hiện thao tác follow một tài khoản (anchor hoặc follower target) qua Path B / Mode 2:
1. **Kiểm tra trạng thái sau vuốt:** Runner thực hiện tap Follow, sau đó vuốt nhẹ / refresh profile và kiểm tra lại nút quan hệ.
2. **Hiện tượng "Nhả Follow":** Nút chuyển về trạng thái chưa follow (`Follow` thay vì `Đang follow` / `Following` / `Bạn bè`), runner phân loại `FOLLOW_FAILED: anchor @... bị nhả sau vuốt — dừng session` và kích hoạt cooldown cho tài khoản đó trong ngày để bảo vệ nick.

### Phân Loại Mức Độ Nhả Follow
- **Nhả ngay lượt đầu (`followed_count = 0`):** Tài khoản bị shadow drop / rate-limit cấp độ tài khoản ngay từ đầu phiên, hoặc anchor UID bị gắn cờ hạn chế tương tác.
- **Nhả sau một số lượt (`followed_count = 1..16`):** Tài khoản đã hoàn thành thành công $N$ lượt follow trước khi chạm giới hạn tần suất (rate-limit) của TikTok trong phiên hiện tại.

---

## 2. Quy Trình Trích Xuất Dữ Liệu Thực Tế Khi Điều Tra

Khi người dùng hỏi về tình trạng nhả follow của các máy:
1. **Đọc trực tiếp thư mục runtime của phiên hiện tại:**
   - Đường dẫn: `D:\Taadaa\runtime\kibe\live\<YYYY-MM-DD>\<shift-folder>\<run-id>\machines\machine_<N>\<run-id>\follow_result.json`.
   - Trích xuất: `status`, `followed_count`, `details` / `reason`, anchor UID gây dừng phiên.
2. **CẤM quét đệ quy toàn bộ thư mục runtime:** Luôn truy cập trực tiếp theo số máy `machine_<N>` đã biết để tránh nghẽn I/O.
3. **Báo cáo rõ ràng 2 thông số:**
   - Số lượng follow đã hoàn thành trước khi dừng.
   - Nguyên nhân dừng cụ thể (nhả anchor nào, không nhận follow ở profile nào).

---

## 3. Quy Tắc Đối Soát Lịch Sử Chu Kỳ Ca Chẵn / Lẻ (Odd / Even Schedules)

Hệ thống phân bổ tài khoản theo quy tắc:
- **1 Máy = 3 Ca = 6 Row:**
  - Ca 1 (Sáng): Row 1 (Ngày Lẻ) / Row 2 (Ngày Chẵn).
  - Ca 2 (Trưa/Chiều): Row 3 (Ngày Lẻ) / Row 4 (Ngày Chẵn).
  - Ca 3 (Tối): Row 5 (Ngày Lẻ) / Row 6 (Ngày Chẵn).
- **Lịch Ngày Chẵn (2, 4, 6):** Chạy Row 2, Row 4, Row 6.
- **Lịch Ngày Lẻ (1, 3, 5, 7):** Chạy Row 1, Row 3, Row 5.

### Lưu Ý Quan Trọng Khi Truy Vết Lịch Sử Của Một Row
- Khi kiểm tra lịch sử "2 ngày trước" của một tài khoản trên **Row 2**:
  - Không đọc dữ liệu của ngày hôm qua (ngày lẻ, chạy Row 1/3/5).
  - Phải lùi về đúng ngày Chẵn gần nhất trước đó (ví dụ: ngày 02/09 -> kiểm tra ngày 30/08).
- Tránh kết luận nhầm "tài khoản không chạy" khi ngày hôm trước là ngày nghỉ theo chu kỳ của Row đó.

---

## 4. Cơ Chế Báo Cáo Của Feed Session Watchdog & Độ Trễ Thời Gian

- Script `feed_session_watchdog.py` chạy theo chu kỳ cron `*/5 * * * *` (mỗi 5 phút).
- Watchdog tuân thủ nguyên tắc **Silent Watchdog**: Chỉ gửi báo cáo khi phát hiện phiên ĐÃ HOÀN TẤT (`run_manifest.json` có `end_time` và `completed_steps`).
- **Trường hợp phiên kết thúc lệch giây so với tick cron:**
  - Ví dụ: Phiên kết thúc lúc `06:45:46`, lượt cron lúc `06:45:22` kiểm tra thấy phiên chưa xong nên im lặng.
  - Watchdog sẽ gửi thông báo vào lượt cron tiếp theo lúc `06:50:00`.
  - Đây là cơ chế vận hành bình thường, không phải lỗi sót báo cáo.

---

## 5. Cơ Chế Thống Kê Tổng Lượt Follow & Phân Loại Bỏ Qua (Skip) Của Watchdog

### Nguồn Gốc Số Lượng "Lượt Follow"
- `total_followed_count` trong dòng header `• Follow chéo (N lượt follow):` là **tổng số UID được follow thực tế** trên toàn bộ các máy chạy trong phiên.
- Con số này tính gộp:
  + Các máy hoàn tất thành công (`status: "OK"` / `"SUCCESS"`) với danh sách `followed`.
  + Các máy bị nhả follow (`status: "FOLLOW_FAILED"`) nhưng **đã kịp follow thành công một số lượng UID** (ví dụ 15 UIDs) trước khi chạm ngưỡng rate-limit của TikTok.
- Do đó, ngay cả khi chỉ có 1-2 máy chạy follow (các máy khác skip), tổng lượt follow vẫn có thể đạt 30+ nếu mỗi máy follow được 15 lượt.

### Phân Loại Các Nhóm Bỏ Qua (Skip)
Khi farm hiển thị danh sách Bỏ qua lớn, phân loại theo 2 cơ chế fail-closed gating an toàn:
1. `follow-released-daily-cooldown`: Nick bị nhả follow từ các phiên trước hoặc trong ngày, đang trong thời gian nghỉ Cooldown (Streak 1..3) để hồi phục trust score, tránh dính shadowban.
2. `under-5-videos-follow-disabled`: Nick có số video < 5 (chưa đủ trust score) nên hệ thống tự động khóa follow hook để bảo vệ nick không bị nhả follow 100%.
3. `sensitive-skip-manual_needed`: Máy có cờ nhạy cảm hoặc đang chờ operator xử lý.

---

## 6. Phân Tích Dải Turn (Budget Used), Quy Chuẩn Format Báo Cáo & Bản Chất Nhả Follow Của Farm

### 6.1. Quy Chuẩn Format Báo Cáo Phân Nhóm Nhả Follow Của Watchdog (Chốt 08/09/2026)
Để tránh lú lẫn khi đọc báo cáo (ví dụ dòng `5 - 9 lượt (1): 18 (6 lượt)` dễ gây hiểu nhầm `(1)` là 1 lượt và số máy `18` đứng cạnh `(6 lượt)`), hàm `format_released_follows` trong `feed_session_watchdog.py` và báo cáo tổng kết phiên BẮT BUỘC tuân thủ định dạng 4 tầng phân lập rõ ràng:

```text
  + Nhả follow (N máy):
    - Nhả liền (0 lượt - X máy): M1, M7, M10, ...
    - 1 - 4 lượt (Y máy): M14 (1 lượt), M15 (1 lượt), ...
    - 5 - 9 lượt (Z máy): M4 (7 lượt), M9 (7 lượt), ...
    - 10+ lượt (W máy): M2 (19 lượt), M6 (16 lượt), ...
```

**Các Bất Biến Hiển Thị (Format Invariants):**
1. **Số lượng máy BẮT BUỘC có chữ "máy":** Viết `(1 máy)`, `(27 máy)`, CẤM viết số trơ trọi `(1)` làm người đọc tưởng nhầm là 1 lượt follow.
2. **Định danh máy BẮT BUỘC có tiền tố "M":** Viết `M18 (6 lượt)`, `M4 (7 lượt)`, CẤM viết số trần `18 (6 lượt)` gây hiểu lầm giữa số máy và số lượt.
3. **Kỷ luật dữ liệu minh họa / ví dụ:** Khi giải thích format hoặc đưa số liệu đối soát phiên cũ cho người dùng, BẮT BUỘC gắn nhãn `[VÍ DỤ DỮ LIỆU CŨ TỪ PHIÊN TRƯỚC / MINH HỌA]` ngay đầu tin nhắn. TUYỆT ĐỐI CẤM gửi khối báo cáo giống hệt ca thật khiến operator hoang mang tưởng bot đang chạy nhầm Row hoặc dữ liệu live bị sai lệch.

### 6.2. Cấu Hình Follow Budget An Toàn Mới (Chốt 07/09/2026)
Trần cứng rolling limit của TikTok là ~45-50 follow/24h. Cấu hình cũ (12-15 lượt/phiên, 45 lượt/ngày) qua 3 phiên đẩy tổng lên 38-45 follow khiến Phiên 3 thường xuyên chạm trần và dính lỗi `FOLLOW_FAILED`.
Cấu hình mới đã cập nhật trong `follow_runner/core/config.py`:
- `budget_per_day: 35` (cũ: 45)
- `budget_per_session: 12` (cũ: 15)
- `budget_per_session_min: 9`
- `budget_per_session_max: 12` (mỗi phiên random 9, 10, 11 hoặc 12 lượt)
*Hiệu quả:* Tạo khoảng đệm an toàn 15 lượt dưới trần 50 của TikTok. Máy tự động dừng ở trạng thái sạch `status: OK` khi đủ chỉ tiêu thay vì bị ép đến mức TikTok khóa nút, giúp bảo vệ trust score và giữ tỷ lệ chạy mượt sau 48h trên 75%.

### 6.3. Phân Tích Dải Turn (Budget Used) & Bản Chất Nhả Follow Của Farm

Khi phân tích dữ liệu follow drop trên quy mô lớn (70-80 máy/ca), thống kê số lượt follow hoàn thành trước khi bị nhả (`budget_used`) được chia thành 5 dải turn chuẩn:

1. **Turn 0 (`budget_used = 0`) — Chiếm ~50% - 60% tổng số máy bị nhả:**
   - **Đặc điểm:** Bị nhả ngay lượt follow đầu tiên (hoặc ngay anchor đầu tiên trong Mode 2). Vừa bấm Follow và pull-to-refresh thì nút lập tức bật ngược về "Follow".
   - **Bản chất:** Shadowban / Action Block từ trước (trust score thấp, IP proxy bẩn/trùng lặp, hoặc tài khoản chưa đủ thời gian nuôi dưỡng). Đa số các máy này có `fail_streak >= 2` (kích hoạt progressive cooldown 4 ngày hoặc 7 ngày).
2. **1 - 4 turns (14% - 18%): Ngưỡng nhạy cảm:**
   - Nick vừa bắt đầu tương tác thì thuật toán TikTok phát hiện bất thường và khóa hành động follow.
3. **5 - 9 turns (10% - 20%): Ngưỡng trung bình:**
   - Nick hoàn thành được khoảng 1/3 đến 1/2 chỉ tiêu của một phiên follow thông thường.
4. **10 - 14 turns (4% - 6%): Ngưỡng khá:**
   - Nick hoàn thành gần trọn vẹn chỉ tiêu phiên (15 lượt) trước khi bị chặn.
5. **15+ turns (6% - 20%): Ngưỡng trần tần suất / Rate-limit:**
   - Nick follow thành công 15-50 lượt (chạm gần trần ngân sách ngày 60 lượt như các máy M26, M46, M72 đạt 49-50 lượt).
   - **Bản chất:** Đây là rate-limit tần suất trong ngày thông thường của TikTok, không phải nick hỏng/shadowban. Nick có trust score rất tốt và sẽ tự động mở lại follow ở chu kỳ kế tiếp.

---

## 7. Quy Trình & Script Đối Soát Nhanh State File ↔ Runtime Artifacts

Khi thực hiện audit thống kê toàn farm, đối soát chéo giữa `follow_state` và `runtime`:
- **State File:** `D:/Taadaa/tiktok-follow/runs/state/follow_state_<M>_row_<slot>.json`
  + `budget_date`, `budget_used`: Số lượt follow thành công tích lũy trong ngày.
  + `follow_failed`, `fail_streak`, `last_failed_date`, `last_failed_at`, `cooldown_until_date`.
- **Runtime Artifact:** `D:/Taadaa/runtime/kibe/live/<date>/row-<slot>-*/<run_id>/machines/machine_<M>/<sub_run>/follow_result.json`
  + `status`: `FOLLOW_FAILED`, `OK`, `skipped`, `MANUAL_REVIEW`, `timeout`.
  + `reason`, `followed_count`, `details`.

### Cạm Bẫy Đối Soát Cần Lưu Ý
1. **State Reset do Canary / Manual Test:** Khi máy được chạy canary gỡ cờ thủ công (ví dụ M10 Row 1), file state có thể mang `follow_failed: false, budget_used: 0`, nhưng trong log ca chính thức trước đó máy thực tế đã bị `FOLLOW_FAILED`. Luôn kiểm tra runtime kết hợp state để không sót máy bị nhả trong ca.
2. **Type Coercion của `followed_count`:** Trong `follow_result.json`, `followed_count` có thể là `int` hoặc bị thiếu (khi đó phải đếm `len(followed)` nếu `followed` là list/dict). Tránh dùng trực tiếp `len(d.get("followed_count"))` gây `TypeError: object of type 'int' has no len()`.
3. **Tối ưu hóa I/O Runtime:** Tuyệt đối không chạy `find` đệ quy hoặc quét sâu toàn bộ thư mục `D:/Taadaa/runtime`. Chỉ lặp trực tiếp qua các thư mục ca `row-<slot>-*` của ngày cần kiểm tra.
