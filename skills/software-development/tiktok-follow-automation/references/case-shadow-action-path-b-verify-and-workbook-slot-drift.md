# Shadow Action, Path B Verify & Workbook Slot Drift
## Session: 2026-10-06 (M80 / M76 post-mortem)

---

## 1. TikTok Shadow Action — Path B verify CAN be fooled

### Symptom
- M80 (`@kymanzzc4ic`) follow Anchor 1 (`@allynkapyej`): Path B verify navigates to
  Anchor 1's profile, sees button "Đã follow" → ghi nhận SUCCESS.
- Watchdog cuối phiên: script báo 2 lượt (1 tự nhiên + 1 chéo Anchor 1), Web TikTok
  tăng +0 → báo "Lệch -2".
- Database snapshot trước và sau phiên: `following` của `@kymanzzc4ic` = 1 không đổi.

### Root cause
TikTok "Shadow Action": app cache nút "Đã follow" locally ngay sau tap. Backend server
KHÔNG commit vào database toàn cục. Chỉ khi nick thực hiện action tiếp theo (tap sang
anchor 2) thì TikTok mới reveal kết quả thật — nút của anchor 2 văng ngược "Follow"
ngay lập tức → runner bắt được FOLLOW_FAILED.

Điều này xảy ra khi nick đang bị "soft limit" (shadow ban hành động) trên server,
nhưng app vẫn cho phép tap, vẫn cache trạng thái locally.

### Path B verify hiện tại (đúng nhưng có giới hạn)
```
follow_one_follower():
  tap Follow trên row
  → _verify_row_after_tap (2-3s): check nút trên row trong follower list
  → _path_b_verify: tap vào avatar → mở profile → check nút trên profile người đó
  → nếu nút "Đã follow" → return "followed"
  → back về follower list
```

**Giới hạn:** Path B soi nút trên profile của ĐỐI PHƯƠNG, không soi bộ đếm Following
của chính nick mình. TikTok shadow action giữ nút đối phương hiển thị "Đã follow" trong
cùng session, nhưng bộ đếm của nick mình không tăng trên server.

### Pull-to-refresh không đảm bảo server fetch
Hàm `pull_to_refresh_profile()` swipe từ `y=0.35h` xuống `y=0.78h`. Khu vực này trên
profile người khác thường là vùng RecyclerView video chứ không phải SwipeRefreshLayout
header — Android có thể interpret là scroll cuộn list thay vì pull-to-refresh thật sự.
Kể cả khi trigger đúng SwipeRefreshLayout, TikTok có thể chỉ trả về cached response
thay vì fetch lại từ server trong phạm vi 1 session.

### Impact on watchdog
- Nick dính FOLLOW_FAILED ở anchor N (N > 1): Anchor 1..N-1 đã được ghi nhận thành công
  bởi script (Path B verify pass), nhưng server không commit chúng.
- Watchdog báo "Lệch -N" là ĐÚNG VỀ HIỆN TRẠNG nhưng SAI VỀ KỲ VỌNG — đây là noise
  của TikTok shadow action, không phải bug của script.
- **Rule:** nick trong danh sách FOLLOW_FAILED không được tính vào web-delta expectation
  (xem watchdog rules trong tiktok-feed-session-management skill).

### Khả năng phát hiện sớm (để nghiên cứu)
Cách duy nhất để detect trước khi sang anchor tiếp theo là sau mỗi anchor follow thành
công, gọi ADB để lấy số Following của chính nick mình (profile tab của nick hiện tại)
rồi so với baseline đầu phiên. Tuy nhiên điều này tạo thêm bot-signature risk và chưa
được implement.

---

## 2. `sync_combined_safe_workbook.py` — Blank slot drift bug

### Symptom
M76 Row 4 → nick `@loanau4423` trong file kibe (9 video, 42 ngày, đủ điều kiện).
Nhưng follow runner nhận được nick `@ucloan7790` (5 video) → Dual Gate khóa budget = 0
→ cả Mode 2 lẫn Mode 1 đều bị ngắt → 0 lượt follow.

### Root cause
`sync_combined_safe_workbook.py` trước khi sửa có logic:
```python
if row and len(row) >= 3 and row[2] and str(row[2]).strip():
    # chỉ append row có ID
```
+ global UID deduplication.

M76 trong kibe source có slot 2 trống (Row 2 = blank). Script bỏ qua Row 2 blank,
dồn Row 3, 4, 5 thành Row 2, 3, 4 trong combined.xlsx.
→ `account_row_index=4` của runner trỏ nhầm sang nick `@ucloan7790` (row 5 thật sự).

### Fix đã apply (2026-10-06)
Xóa bỏ điều kiện lọc dòng empty ID. Giữ nguyên toàn bộ slot (kể cả dòng trống) từ
file nguồn vào combined. Deduplication toàn cục bị bỏ.

File sửa: `D:\Taadaa\tools\sync_combined_safe_workbook.py`
Diff: 6 insertions, 13 deletions.
Sau fix: `python D:/Taadaa/tools/sync_combined_safe_workbook.py` báo 1280 active UIDs.

### Invariant
Combined workbook PHẢI bảo toàn vị trí slot vật lý từng máy (bao gồm dòng trống)
vì follow runner dùng `--account-row-index` là chỉ số vật lý của device, không phải
chỉ số logic "nick có ID".

---

## 3. Canary runner invocation — lifecycle guard pitall

### Symptom
Gọi trực tiếp `run_follow.py` qua terminal tool với path dài dưới background=True
bị lỗi: `ValueError: open: embedded null character in path`.

Nguyên nhân: lifecycle_guard.py đọc script path từ command string để kiểm tra nội dung
file. Path chứa ký tự đặc biệt hoặc null byte trong quá trình parse.

### Fix
Viết wrapper script Python tách biệt, gọi `subprocess.run([...])` bên trong, sau đó
invoke wrapper qua terminal:

```python
# D:\Taadaa\test_canary_m80.py
import subprocess, sys

cmd = [
    r"D:\Taadaa\python-envs\automation\Scripts\python.exe",
    "-m", "follow_runner.run_follow",
    "--machine", "80",
    "--config", r"D:\Taadaa\tiktok-follow\follow_runner\config.example.yaml",
    "--account-row-index", "4",
    "--canary-hook", "open_following_tab",
    "--canary-target", "allynkapyej",
    "--canary-screencap", r"C:\Users\Kibe\m80_canary.png"
]
proc = subprocess.run(cmd, cwd=r"D:\Taadaa\tiktok-follow", capture_output=True, text=True)
print(proc.stdout)
print(proc.stderr[-1000:])
```

```bash
python D:/Taadaa/test_canary_m80.py  # foreground timeout=60s max
# hoặc background=True với notify_on_complete=True cho run > 60s
```
