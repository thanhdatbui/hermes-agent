# Bóc Tách Log & Điều Tra Hiện Trường Nhả Follow Row 1 & Row 2

## 1. Nguyên Tắc Cốt Lõi: Đọc Log Thật Thay Vì Phỏng Đoán

Khi phân tích hiện tượng follow bị nhả (`FOLLOW_FAILED`) hoặc máy đạt ít follow ở Row 1 và Row 2:
- **CẤM TUYỆT ĐỐI SUY ĐOÁN LUNG TUNG** (như "acc lỏ", "TikTok quét diện rộng", "chạm trần đỏ") khi chưa đối soát log chi tiết từng máy.
- BẮT BUỘC kiểm tra trực tiếp 3 nguồn dữ liệu:
  1. `follow_result.json` tại artifact từng máy: kiểm tra `status`, `reason`, `budget`, `mode` (`warmup` vs `full`), danh sách `followed` và `skipped`.
  2. Runtime log (`log.jsonl` / execution trace): xác định chính xác vị trí bị ngắt — bị nhả tại bước bấm Anchor (`_ensure_anchor_followed`) hay bị nhả khi bấm nick con trong danh sách Following.
  3. Cơ sở dữ liệu SQLite `tiktok_tracker.db`: kiểm tra lịch sử biến động (`snapshots`), số lượng video, following, follower và trạng thái `ip_circuit_breaker`.

---

## 2. Phân Tích Thực Tế Ca 1 Ngày 15/10 (Row 1): Đạt 124 Follow Không Phải 100% Full Budget

### A. Thực trạng cơ cấu Budget trong phiên bùng nổ 15/10 (Dữ liệu thực tế 100% từ SQLite & State JSON)
Số liệu đối soát từ `session_action_stats`, `daily_account_actions` và 19 file `follow_state_<m>_row_1.json` ngày 15/10:
- **Phiên 1 (`row-1-060031`):** Đạt 83 lượt follow (18 máy có follow thành công).
- **Phiên 2 (`row-1-080007`):** Đạt 35 lượt follow (10 máy có follow thành công).
- **Phân bổ nấc thang thực tế (100% chạy trong Graduated Probation Ladder, 0% Full Budget):**
  - **Hồi phục 1 (Probation Tier 1 - Quota 2–5 lượt):** **15 / 19 máy (78.9%)**. Tất cả đều có `probation_clean_days = 0` (M2: 5 fl, M4: 4 fl, M14: 4 fl, M16: 6 fl, M20: 6 fl, M21: 2 fl, M28: 4 fl, M29: 5 fl, M32: 2 fl, M36: 7 fl, M39: 7 fl, M52: 4 fl, M57: 4 fl, M70: 4 fl, M71: 4 fl).
  - **Hồi phục 2 (Probation Tier 2 - Quota 6–9 lượt):** **4 / 19 máy (21.1%)**. Gồm M12 (7 fl), M26 (8 fl), M37 (13 fl qua 2 phiên: P1=7, P2=6), M41 (7 fl). Cả 4 máy đều có `probation_clean_days = 1` nên được thăng cấp nâng tải.
  - **Full budget (Graduated - Quota 10–15 lượt):** **0 máy (0.0%)**. Không có máy nào đạt 2 ca sạch liên tiếp trước đó để tốt nghiệp lên Full Quota.
- **Kết luận:** 124 lượt follow là kỳ tích của **bậc thang thử thách phân tầng (Hồi phục 1: 78.9% + Hồi phục 2: 21.1%)**, tuyệt đối không phải do thả trần Full Budget 10–15 lượt.

---

## 3. Khác Biệt Cốt Lõi Giữa Row 1 (Tik1) vs Row 2 (Tik2) Khi Bị Nhả

Đối soát thực tế giữa 48 nick Row 1 bị nhả ngày 15/10 và 23 nick Row 2 bị nhả ngày 16/10:

| Đặc tính | Row 1 (Tik1 — 15/10) | Row 2 (Tik2 — 16/10) |
| :--- | :--- | :--- |
| **Số lượng bị nhả** | 48 tài khoản | 23 tài khoản |
| **Nhả tại Anchor (`_ensure_anchor_followed`)** | 19 nick (**39.6%**) | 19 nick (**82.6%**) |
| **Nhả tại nick con / Verify profile** | 29 nick (**60.4%**) | 4 nick (**17.4%**) |
| **Hồ sơ tài khoản (SQLite)** | Nick già: Following **100 – 390 fl**, video 25–35 | Nick non: Following **0 – 8 fl**, video 11–20 |

### Giải mã cơ chế nhả:
1. **Row 1 (Nick già, following dày):**
   - 60.4% bị nhả ở **nick con** trong danh sách following.
   - Lý do: Tài khoản đã tích lũy 150–390 following, khi bấm dồn dập các nick con trong phiên thì dễ chạm trần trust rate trong phiên của TikTok $\rightarrow$ Nút follow bị TikTok revert ngầm (trả về lỗi `TikTok không nhận follow (profile vẫn chưa follow)`).
2. **Row 2 (Nick non, following mỏng):**
   - 82.6% bị nhả ngay tại **nút Anchor** (`anchor @... bị nhả sau vuốt — dừng session`).
   - Lý do: Nick mới chỉ có 0 đến 6 following, vừa khởi động đã bay vào profile của một Anchor dày (following $\ge 150$) và bấm follow trực tiếp Anchor. Thuật toán chống bot của TikTok gắn cờ tài khoản non nớt tương tác bất thường với tài khoản lớn $\rightarrow$ Revert nút follow Anchor ngay lập tức, khiến máy dừng phiên fail-closed mà chưa kịp mở danh sách nick con bên trong.

---

## 3. Bản Chất 2 Điểm Nhả Khác Biệt Trong Luồng Mode 2

Khi đọc log máy bị `FOLLOW_FAILED`, bắt buộc phân biệt rõ 2 kịch bản:

### Kịch bản 1: Bị nhả ngay tại cửa mở Anchor (`_ensure_anchor_followed`)
- **Triệu chứng trong log:**
  - Máy vừa vào profile của Anchor (ví dụ `@phammai1805`, `@tolmavhj12k`), kiểm tra thấy chưa follow $\rightarrow$ Bấm nút Follow $\rightarrow$ Quay ra reload profile kiểm tra lại: Nút bị TikTok revert về đỏ (`FOLLOW_FAILED: anchor @... bị nhả sau vuốt — dừng session`).
  - `followed_count` = 0. Máy **chưa hề bấm được bất kỳ nick con nào trong danh sách**.
- **Nguyên nhân:**
  - Không phải do nick này bị hỏng toàn diện, mà do **tương tác trực tiếp với chính tài khoản Anchor** bị thuật toán TikTok chặn (do Anchor là tài khoản nội bộ bị nhiều máy follow liên tiếp, hoặc layout/video cover của Anchor bị trục trặc).
  - Khắc phục: Bản vá `8231757` & `613d201` đã bổ sung fallback bấm profile follow và ghi nhận telemetry `mode2_anchor_skipped` để đổi sang anchor khác thay vì ngắt phiên mù quáng.

### Kịch bản 2: Bị nhả khi bấm nick con trong danh sách Following
- **Triệu chứng trong log:**
  - Máy đã mở thành công danh sách Following của Anchor, đã lướt và follow được $N$ nick ($N \ge 1$).
  - Đến nick thứ $N+1$, sau khi bấm follow và verify thì phát hiện nút bị nhả $\rightarrow$ Trigger fail-closed dừng session.
- **Nguyên nhân thực tế cần bóc tách từ log:**
  - **Trường hợp A (Chạm trần hành vi tạm thời):** Nick đã follow 4–8 nick liên tiếp trong thời gian ngắn, bị rate limit tạm thời trong phiên.
  - **Trường hợp B (Trùng IP bẩn / Proxy rò rỉ):** Cổng proxy đang phát sinh lỗi kết nối hoặc máy cùng IP vừa bị trảm $\rightarrow$ Kích hoạt Cầu dao IP 48h để khóa cứu các máy còn lại.
  - **Trường hợp C (Chỉ số tài khoản mất cân đối trầm trọng):** Tra cứu DB thấy Following đã chạm 250–350 nhưng Follower $< 20$, video $< 10$. Đây là nick cần chuyển sang diện Thuần Dưỡng (Pure Feed) để cân bằng chỉ số.
