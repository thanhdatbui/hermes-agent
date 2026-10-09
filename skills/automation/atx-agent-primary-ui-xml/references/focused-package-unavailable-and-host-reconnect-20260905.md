# Focused Package Unavailable, ADB Host-Side Reconnect & Photo Mode Feed (2026-09-05)

## Hiện tượng hiện trường (Máy 46, Máy 26, Máy 13)
1. **Máy 46 (serial `ce0916092531413504`, nick `gbowmkadsno`)**:
   - Alert: `focused package unavailable`, hiện trường máy đang mở TikTok Home Feed bình thường.
   - Khi chạy qua ADB, `adb shell` bị timeout hoặc get_focused_activity trả về package `None`.
   - Script feed dừng phiên ngay lập tức với `SAFETY_FAILED` ("focused package unavailable") mà không thử kích hoạt chuỗi phục hồi launcher.

2. **Máy 26 (Case 110)**:
   - Dừng phiên với `screen capture invalid; feed not confirmed`.
   - Màn hình hiển thị post dạng Ảnh (Photo mode) trên feed Đề xuất: có nhãn "Ảnh", nút bình luận có placeholder "Bóc tem", nút "Đăng lại cho follower", bookmark.

3. **Máy 13 (Case 111)**:
   - Dừng phiên với `NameError: name 'ADBError' is not defined` trong `feed_swipe_smoke.py::_perform_feed_swipe` khi lệnh adb swipe gặp timeout.

---

## Root Cause & Phân Tích Kỹ Thuật

### 1. Bẫy logic trong `_is_launcher_focus_loss` (`feed_swipe_smoke.py`)
- Khi transport socket ADB bị nghẽn, `get_focused_activity(ctx)` trả về `{"package": None, "activity": None}`.
- `safety_check` trong `core/safety.py` trả về `SAFETY_FAILED` kèm lý do `"focused package unavailable"`.
- Trong `_is_launcher_focus_loss(ctx, row)`:
  ```python
  if focus_package:
      return True

  return "tiktok focus lost" in reason_lower or "focus lost" in reason_lower
  ```
  Do `focus_package` là rỗng (`None` hoặc `""`), và `reason_lower` chỉ chứa `"focused package unavailable"`, điều kiện trả về `False`.
- **Hệ quả**: Toàn bộ chuỗi phục hồi launcher (`_relaunch_and_poll_tiktok_focus`, baseline recovery, post-swipe recovery) bị bỏ qua hoàn toàn, dẫn đến fail-closed oan.

### 2. Cơ chế Host-side Reconnect bị bypass trên Xiaowei ADB (`automation_core/adb.py`)
- Trên Xiaowei ADB (phiên bản `1.0.32` / `1.0.39` / `1.0.41`), lệnh `adb -s <serial> reconnect device` trả về exit code `0` nhưng **không thực sự reset transport socket phía host Windows**.
- Trong `AdbClient._reconnect_device`:
  ```python
  res = subprocess.run([self.adb_path, "-s", self.serial, "reconnect", "device"], ...)
  if res.returncode != 0:
      subprocess.run([self.adb_path, "-s", self.serial, "reconnect"], ...)
  ```
  Do `res.returncode == 0`, lệnh `adb -s <serial> reconnect` (host reconnect) không bao giờ được gọi. Socket USB tiếp tục bị stall transport.

### 3. Thiếu Photo Mode controls trong `classifier.py`
- Bộ nhận diện `_has_feed_detail_controls` chỉ tìm 5 nhãn truyền thống (`thích`, `bình luận`, `share`, `follow `, `user_avatar`).
- Post dạng Ảnh có placeholder `bóc tem`, nút repost `đăng lại`, nhãn `ảnh`, nút lưu `bookmark` $\rightarrow$ không đủ 3 controls để confirm feed.

### 4. Thiếu import `ADBError` trong `feed_swipe_smoke.py`
- Bắt ngoại lệ `except ADBError as exc:` khi swipe nhưng module thiếu import từ `core.adb`.

---

## Giải Pháp Chuẩn Hóa

1. **Patch `_is_launcher_focus_loss` (`feed_swipe_smoke.py`)**:
   ```python
   if "package unavailable" in reason_lower or "focused package unavailable" in reason_lower:
       return True

   if focus_package:
       return True

   return "tiktok focus lost" in reason_lower or "focus lost" in reason_lower
   ```

2. **Patch Host-Side Reconnect (`automation_core/adb.py`)**:
   Luôn thực hiện `[self.adb_path, "-s", self.serial, "reconnect"]` bất kể return code của `reconnect device` để đảm bảo reset kênh truyền host-side trên toàn bộ farm.

3. **Mở rộng feed detail controls (`classifier.py`)**:
   Thêm `repost_marker` (`đăng lại`, `repost`), `photo_marker` (`ảnh`, `photo`), `bookmark_marker` (`bookmark`, `đã lưu`, `yêu thích`), và bổ sung placeholder `"bóc tem"` vào `comment_marker`.

4. **Import đầy đủ `ADBError` (`feed_swipe_smoke.py`)**:
   Thêm `from core.adb import ADBError` ở header.
