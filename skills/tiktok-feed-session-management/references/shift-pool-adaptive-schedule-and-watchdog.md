# Adaptive Biological Shift-Pool Dynamic Selection & Watchdog Reporting Contract

## 1. Bối cảnh & Mục tiêu (Context & Motivation)
Thay vì chạy đồng loạt cả farm chung 1 Row cố định theo giờ cơ học (tạo ra "dấu vân tay đồng bộ" dễ bị TikTok soi), kiến trúc mới nâng cấp lên **Lịch phân tán thích ứng sinh học (Adaptive Biological Schedule)** theo các tổ ca (Shift Pools):
- **Phá vỡ tính tương quan mạng (Anti-Correlation):** Cùng 1 khung giờ, các máy mở các slot khác nhau (ví dụ ca sáng rải đều Row 1, Row 2, Row 7).
- **Giữ nhịp sinh học của nick (Biological Habit):** Nick ca sáng chỉ chạy buổi sáng, nick ca trưa chỉ chạy trưa, nick ca tối chỉ chạy tối.
- **Zero Starvation (100% độ phủ):** Trong 3 ngày chính (Day 0, 1, 2), toàn bộ 8 Row đều được xoay tua chạy đủ 100%.

---

## 2. Quy hoạch Tổ ca (Shift Pools Mapping)

| Khung Ca | Giờ Chạy | Pool các Row xoay tua | Day 0 (N1) | Day 1 (N2) | Day 2 (N3) | Day 3 (Rest Day) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Ca 1 (Sáng)** | 06:00 & 08:00 | `{Row 1, Row 2, Row 7}` | Rank 1 (Khỏe nhất) | Rank 2 (Khỏe nhì) | Rank 3 (Còn lại) | Dưỡng sinh 3 lớp phễu |
| **Ca 2 (Trưa)** | 12:00 & 14:00 | `{Row 3, Row 4, Row 8}` | Rank 1 (Khỏe nhất) | Rank 2 (Khỏe nhì) | Rank 3 (Còn lại) | Dưỡng sinh 3 lớp phễu |
| **Ca 3 (Tối)** | 18:00 & 20:00 | `{Row 5, Row 6}` | Rank 1 (Khỏe nhất) | Rank 2 (Còn lại) | Dưỡng sinh | Dưỡng sinh 3 lớp phễu |

---

## 3. Các Nguyên Tắc Bắt Buộc (Invariants)

1. **Thước đo xếp hạng sức khỏe trong Pool (`rank_shift_pool_accounts`):**
   - **Tier 1 (Ưu tiên tuyệt đối):** Nick cắn đề xuất (`is_account_boosted = True`) $\rightarrow$ Rank 1 để up video đón sóng view.
   - **Tier 2:** Nick sạch án (không dính cooldown nhả follow) $\rightarrow$ Ưu tiên theo độ dày video (`video_count`).
   - **Tier 3:** Nick đang dính cooldown nhả follow hoặc nick non $\rightarrow$ Xếp sau cùng.

2. **Nguyên tắc "S2 bám S1" (100% Tuyệt đối):**
   - Trong cùng 1 ca của ngày hôm đó, Session 2 (08:00, 14:00, 20:00) **bắt buộc chạy đúng slot** mà Session 1 (06:00, 12:00, 18:00) của máy đó đã chọn.
   - Cơ chế: Lưu `today_shift_sessions[ca][machine] = chosen_row`. Session 2 đọc trực tiếp từ state này.

3. **Quản lý chu kỳ qua sổ cái atomic (`shift_pool_cycle_state.json`):**
   - Đường dẫn mặc định: `D:/Taadaa/runtime/kibe/cron-state/shift_pool_cycle_state.json`.
   - `cycle_idx = (now.date().toordinal() - 739900) // 4`.
   - Khi phát hiện `cycle_idx` mới $\rightarrow$ Reset sạch `cycle_history` để bắt đầu chu kỳ 4 ngày mới.

---

## 4. Chuẩn Hóa Báo Cáo Watchdog Khi Chạy Dynamic (`active_row <= 0`)

1. **Header động trên Telegram (`_row_or_pool_label`):**
   - Khi `active_row <= 0`, cấm in `(Row 0)` rác hoặc in một Row cố định gây hiểu nhầm.
   - Tự động phân tích tên ca/khung giờ để hiển thị đúng Pool:
     * Ca 1: `📊 [TIKTOK NUÔI ACC] Ca 1 (Sáng) hoàn tất (Pool {1, 2, 7})`
     * Ca 2: `📊 [TIKTOK NUÔI ACC] Ca 2 (Trưa) hoàn tất (Pool {3, 4, 8})`
     * Ca 3: `📊 [TIKTOK NUÔI ACC] Ca 3 (Tối) hoàn tất (Pool {5, 6})`
     * Khác/Nghỉ: `📊 [TIKTOK NUÔI ACC] ... hoàn tất (Dynamic)`

2. **Hiển thị nhãn slot `[Tik X]` đích danh cho từng máy:**
   - Trong phần Đối soát TikTok Web vs Script, khi chạy dynamic, từng dòng máy được bổ sung nhãn `[Tik X]` (ví dụ: `M1 [Tik 2] (@username)`).
   - Khi duyệt `slots` tìm Tik của tài khoản, **bắt buộc loại trừ slot rỗng, khoảng trắng hoặc `'none'`**:
     ```python
     if not s_val or not str(s_val).strip() or str(s_val).strip().lower() == "none":
         continue
     ```

3. **Cô lập cảnh báo Farm Alert giữa các luồng trong `dispatch_split_reports`:**
   - CẤM dùng `"FARM ALERT" in header` để gán cho `feed_hdr` (vì header tổng có thể bị kích hoạt bởi lỗi Follow/Upload hàng loạt trong khi Feed hoàn toàn bình thường).
   - Tiêu đề báo cáo Feed chỉ chuyển sang Farm Alert khi chính `tot_feed >= DEFAULT_FARM_ALERT_THRESHOLD`.

4. **Kỷ luật chữ ký hàm `should_trigger_farm_alert`:**
   - Bắt buộc giữ thứ tự: `(fl_errors, up_errors, threshold=DEFAULT_FARM_ALERT_THRESHOLD, feed_errors=0)`.
   - Tuyệt đối không chèn `feed_errors` làm tham số vị trí thứ 3 vì sẽ xung đột với các caller truyền `(fl, up, threshold)`.
