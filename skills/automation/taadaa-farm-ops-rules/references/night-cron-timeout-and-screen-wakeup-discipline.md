# Kỷ luật Đánh thức Màn hình & Cân đối Timeout cho Cronjob Ban đêm trên Phone Farm

## 1. Bối cảnh & Hiện tượng (Case 83 / 91)
- Khi chạy các cronjob ban đêm (khung giờ 01:00 - 05:00 sáng, ví dụ: dọn dẹp cache TikTok `end-of-day-clear-tiktok-cache`), hàng loạt máy (18 - 30 máy) bị báo lỗi `Timeout` (>120s) dù thiết bị vẫn online bình thường.
- Ngược lại, các máy thành công thường chỉ mất 3 - 5s.

## 2. Nguyên nhân cốt lõi (Anti-Patterns)
1. **Thiếu lệnh đánh thức màn hình trước Deep Link Intent:**
   - Ban đêm toàn bộ farm ở trạng thái ngủ sâu (`mWakefulness=Dozing`, `Display Power: state=OFF`).
   - Gửi lệnh `am start -a android.intent.action.VIEW -d 'snssdk1180://clean_cache' ...` khi màn hình đang tắt sẽ khiến activity không được vẽ lên foreground, hoặc UI hierarchy dump ra rỗng / sai activity.
   - Hậu quả: Path 1 (Deep Link nhanh nhất) lập tức thất bại, ép script phải rơi vào Path 2 (In-App Settings fallback).

2. **Nghẽn cổ chai ADB dưới tải 40 workers song song:**
   - Dưới tải 40 workers đồng thời, ADB server Windows và USB hub bị bão hòa. Mỗi thao tác `input tap`, `input swipe`, `dump_ui` tăng độ trễ từ 0.2s lên 3 - 6s.
   - Path 2 (duyệt menu Profile -> 3 gạch -> Cài đặt & quyền riêng tư -> swipe 6 lần tìm Giải phóng dung lượng -> Xóa bộ nhớ đệm -> xác nhận dialog -> verify 0,0MB) cần từ 130s đến 160s để hoàn tất.

3. **Outer Subprocess Timeout bị bóp quá chặt (120s):**
   - Trong script điều phối (`cron_clear_tiktok_cache.py`), lệnh `subprocess.run(cmd, timeout=120)` đặt trần 120s.
   - Mọi máy rơi vào Path 2 đều bị Python kill cưỡng bức ở giây thứ 120 (`subprocess.TimeoutExpired`), tạo ra hiện tượng timeout hàng loạt giả (máy đang chạy bình thường nhưng bị trảm oan).

4. **Độ trễ thử lại ATX dump UI quá lớn khi socket nghẽn:**
   - Nếu socket ATX port 7912 bị nghẽn, vòng lặp thử lại 3 lần (10s) + reset (10s) + thử lại 2 lần (12s) đốt mất 64s cho duy nhất 1 lần đọc XML.

## 3. Quy chuẩn Khắc phục & Vận hành (Invariant Rules)

### Rule 1: Bắt buộc Đánh thức Màn hình ở Mọi Entry Point
Trước khi gọi bất kỳ Intent, Deep Link, hay thao tác UI nào:
```python
shell(serial, "input keyevent KEYCODE_WAKEUP")
shell(serial, "wm dismiss-keyguard")
time.sleep(0.5)
```
Tuyệt đối không giả định thiết bị đang bật sáng màn hình.

### Rule 2: Quy tắc Cân đối Timeout cho Batch Job 40 Workers
- Không được đặt trần `timeout` của outer subprocess thấp hơn thời gian chạy của Worst-Case Path.
- Khi flow có fallback duyệt menu UI nhiều bước:
  * Fast Path (Deep Link / Widget): 5 - 15s.
  * Worst-Case Fallback Path (Menu navigation + Multiple swipes + UI verification): 120 - 180s dưới tải 40 workers.
  * Outer Subprocess Timeout: **Bắt buộc $\ge$ 240s (khuyến nghị 240s - 300s)**.

### Rule 3: Tối ưu Fast Fallback cho UI Dump
- Giảm số lần retry ATX: 2 lần (6s) + reset (5s) + 1 lần (8s).
- Nếu ATX không phản hồi trong vòng ~20s, lập tức fallback sang shell `uiautomator dump /sdcard/...` thay vì đợi 60s+.

### Rule 4: Dọn dẹp Lock Chết (.git lock & shallow lock) sau Timeout
- Khi tiến trình Git hoặc Python bị kill bạo lực do timeout, các file `.git/*.lock` (như `shallow.lock`, `index.lock`, `maintenance.lock`) và process ngầm (`git.exe`) bị kẹt lại.
- Khi gặp hiện tượng Git command bị timeout 180s lặp lại:
  1. Kiểm tra và kill triệt để `git.exe` ngầm qua taskkill.
  2. Xóa các file `.lock` mồ côi trong `.git/`.
  3. Thêm các thư mục lock permissions (như `.tmp-pytest-agent-loop/`) vào `.git/info/exclude`.
