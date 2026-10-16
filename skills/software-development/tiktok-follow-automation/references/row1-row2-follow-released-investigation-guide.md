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

### A. Thực trạng cơ cấu Budget trong phiên bùng nổ 15/10
Số liệu đối soát từ `session_action_stats` và `daily_account_actions` ngày 15/10:
- **Phiên 1 (`2026-10-15_ca1_phien1`):** Đạt 83 lượt follow.
- **Phiên 2 (`2026-10-15_ca1_phien2`):** Đạt 35 lượt follow.
- **Cơ cấu phân bổ:**
  - Phần lớn các máy đạt 3–5 lượt thực chất đang chạy theo cơ chế **Hồi phục 1 (Probation Tier 1 - Quota 2–4 lượt)** hoặc **Hồi phục 2 (Quota 6–8 lượt)** sau thời gian cách ly cooldown.
  - Chỉ một số ít nick nòng cốt đạt tiêu chuẩn Khỏe (`graduated == True`, không có tiền án) mới được cấp **Full Budget 10–15 lượt** (như M37 đạt 13 lượt, M36: 8 lượt, M41: 8 lượt, M26: 8 lượt).
- **Kết luận:** Con số 124 lượt là **kết quả cộng dồn của cả 3 tầng (Hồi phục 1 + Hồi phục 2 + Full Khỏe)**, hoàn toàn không phải toàn bộ 30 máy đều được thả rông chạy Full Quota.

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
