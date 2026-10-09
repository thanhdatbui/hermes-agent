# Anti-Double Penalty Natural Follow & Modulo Slot Gap Hazard (2026-10-05)

## 1. Hiện tượng & Bối cảnh (Sự cố Ca chiều 05/10/2026)
1. **Hiện tượng trừ follow luẩn quẩn:**
   - Phiên 1 (Row 3 - 12:00) có 18 máy bị nhả follow chéo ngay lượt đầu (`FOLLOW_FAILED`), watchdog đã tự trừ sạch toàn bộ 18 lượt follow tự nhiên của các máy này.
   - Đến Phiên 2 (Row 3 - 14:00), watchdog tiếp tục báo: `Follow tự nhiên: 0 lượt ... (Đã tự trừ 2 lượt do nick bị nhả/drop)`, nhả tiếp M8 và M14.
   - Người vận hành chất vấn: *"Chưa hiểu phiên 1 row 3 đã có nick bị nhả trừ follow tự nhiên ra r sao đến phiên 2 lại tiếp tục trừ follow tự nhiên? Đã nhả ở phiên 1 rồi thì trừ ở phiên 1 rồi mà?"*
2. **Hiện tượng nuốt cụm Admin trong báo cáo watchdog:**
   - Toàn bộ tin nhắn báo cáo Phiên 2 chỉ hiện khối `【FARM KIBE - MÁY 1-80】`, hoàn toàn biến mất khối `【FARM ADMIN】`.
   - Người vận hành bức xúc: *"R đéo có report farm admin luôn"*.

---

## 2. Root Cause Kỹ Thuật

### A. Bẫy Không Khóa Follow Sau Khi Đã Dính Cooldown Trong Ngày
- Trong `multi_machine_feed_session.py` và `feed_swipe_smoke.py`:
  - Khi nick M8 bị nhả ở Phiên 1, module follow ghi nhận cờ `cooldown trong ngày` cho tác vụ follow chéo.
  - Tuy nhiên, khi Phiên 2 bắt đầu, runner khởi động session lướt feed mới nhưng **KHÔNG kế thừa trạng thái cooldown này để khóa follow rate về 0%**.
  - Hậu quả: Nick M8 vẫn lướt feed với rate follow 5% và tiếp tục bấm trúng 1 follow tự nhiên vãng lai ở Phiên 2.
  - Sau khi lướt feed xong, runner lại tiếp tục gọi `follow_hook`. M8 ngay lập tức vấp lại kiểm tra cooldown trong ngày $\rightarrow$ trả về `FOLLOW_FAILED (followed = [])`.
  - Watchdog Phiên 2 chạy `calculate_session_natural_follows`, thấy M8 dính `FOLLOW_FAILED` trong Phiên 2 nên tiếp tục khấu trừ 1 follow tự nhiên vừa sinh ra của Phiên 2 về 0.
  - Điều này tạo ra trải nghiệm cực kỳ luẩn quẩn: một nick đã bị nhả từ trưa nhưng cứ mỗi phiên lại đi follow dạo rồi lại bị trừ và báo lỗi nhả lại nhiều lần.

### B. Bẫy Lỗ Hổng Slot Modulo 8 Trong `sync-safe-workbook.py`
- Trong `sync-safe-workbook.py` (hàm `_build_safe_workbook`):
  ```python
  target_slot = (f_num - 1) % 8
  ```
- Nếu một máy trong `taikhoan_dat_v2_updated .xlsx` có nhiều tài khoản mà số Folder Video của các tài khoản đó vô tình rơi vào cùng một số dư modulo 8 (hoặc máy chỉ có 1-2 tài khoản ở slot 0, 4), thì các slot khác (như slot 2 - tức Row 3) sẽ bị để trống (`None`).
- Thực tế tại Farm Admin ngày 05/10: Các máy `249, 255, 262, 264, 266` có đầy đủ tài khoản trong file DAT nhưng tại `taikhoan_run_safe.xlsx` thì slot 2 (Row 3) bị trống `None`.
- Khi đến giờ chạy Row 3 (14:00), `ensure_row_accounts.py 3` thấy 5 máy này thiếu acc nên kích hoạt batch reg bù khẩn cấp. Batch reg gặp lỗi `FAILED_EXIT_1` $\rightarrow$ preflight fail.
- Kèm theo đó, hàm `_count_valid_accounts_for_row` khi gặp ngoại lệ đọc file lúc bị tranh chấp/lock đã fallback ngầm trả về `0`, khiến `tiktok_runner.py` in:
  `tiktok_runner [admin]: Row 3 co 0 account hop le trong ... taikhoan_run_safe.xlsx, skipping window 2026-10-05T14`
  và ghi nhận `_save_state` coi như đã chạy xong phiên, bỏ rơi toàn bộ cụm Admin trong ca chiều!

### C. Bẫy Watchdog Âm Thầm Bỏ Qua Cụm Trống (`continue` Silent Drop)
- Trong `feed_session_watchdog.py`:
  ```python
  runs = sorted(os.listdir(date_live))
  session_runs = [r for r in runs if in_window]
  if not session_runs:
      continue
  ```
- Do cụm Admin bị runner skip nên thư mục artifact `row-3-140011` không bao giờ được tạo ra.
- Watchdog duyệt qua cụm Admin, thấy không có `session_runs` trong khung 14:00-18:00 thì chủ động `continue` im lặng!
- Kết quả: Báo cáo gửi về Telegram chỉ có khối Kibe, người vận hành hoàn toàn không biết Admin đang chạy hay bị lỗi hay bị skip.

---

## 3. Quy Chuẩn Khắc Phục (Invariants)

1. **Khóa Follow Toàn Diện Khi Đã Dính Cooldown Trong Ngày (Anti-Double Penalty):**
   - Bất kỳ tài khoản/máy nào đã dính cờ `cooldown trong ngày` (do nhả follow ở phiên trước) thì ở tất cả các phiên nuôi kế tiếp trong cùng ngày:
     - BẮT BUỘC ép cứng rate follow tự nhiên về 0: `_follow_rate = {"for_you": 0, "following": 0, "friends": 0}` (tương tự như chế độ Organic Rest Day).
     - BẮT BUỘC bỏ qua luôn bước gọi `follow_hook` (chuyển sang `SKIPPED: daily-cooldown-active`), không để lặp lại tình trạng gọi rồi dính `FOLLOW_FAILED` và in báo cáo trừ follow nhiều lần.

2. **Dồn Slot Thông Minh Trong `sync-safe-workbook.py` (No Slot Hole If Acc Exists):**
   - Khi tạo safe workbook từ DAT: Nếu một máy có tổng số tài khoản >= số slot cần dùng nhưng công thức modulo để lại lỗ trống ở các slot giữa (ví dụ có 6 acc nhưng slot 2 bị None), thuật toán BẮT BUỘC phải dồn các tài khoản còn lại vào lấp đầy các slot trống trước khi chốt file.
   - Tuyệt đối không để xảy ra tình trạng máy có sẵn nick trong DAT nhưng safe workbook lại báo thiếu nick ở Row 1..8.

3. **Cấm Watchdog Nuốt Im Lặng Cụm Farm (Cluster Visibility Invariant):**
   - Trong `feed_session_watchdog.py`: Duyệt mọi cụm trong `CLUSTERS`. Nếu một cụm không có thư mục chạy trong khung giờ phiên (`not session_runs`), watchdog BẮT BUỘC phải xuất khối thông tin:
     ```text
     🏢 【FARM ADMIN - MÁY 201-280】
     • Trạng thái: KHÔNG CHẠY / BỊ SKIP
     • Lý do: Không phát sinh lượt chạy trong khung giờ phiên (Kiểm tra safe workbook / runner logs)
     ```
   - Tuyệt đối cấm `continue` âm thầm làm người dùng tưởng mất report.
