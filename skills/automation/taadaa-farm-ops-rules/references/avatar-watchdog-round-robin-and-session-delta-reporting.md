# Avatar Watchdog Round-Robin Scheduling & Action-First Session Delta Reporting (2026-09-19)

## 1. Hiện tượng & Bug Nghẽn cổ chai First-Match (Head-of-Line Blocking)

### Triệu chứng thực tế (18/09/2026):
- Watchdog chạy ca tối `post_evening_avatar_watchdog.py` kích hoạt liên tiếp 18 batch từ 20:56 đến 23:45.
- Cả 18 batch đều là `batch_tik5_list_80_...`, tập trung vào đúng 7 máy của Tik 5 (`M10, M30, M42, M44, M66, M72, M73`).
- Ba máy (42, 66, 73) thành công, nhưng bốn máy còn lại liên tục lỗi.
- Hậu quả: Tik 6, Tik 7, Tik 8, Tik 3, Tik 4 hoàn toàn không được chạy một batch nào suốt cả ca tối. Đến 23:55, watchdog in báo cáo: *"Hết khung giờ ca tối — còn 292 máy chưa up"*.

### Nguyên nhân gốc rễ:
1. **First-Match loop:**
   `for tik in target_tiks: if missing: trigger(tik); return 0`
   Vòng lặp luôn bắt đầu từ phần tử đầu tiên của mảng (`target_tiks = [5, 6, 7, 8, 3, 4]`). Khi Tik 5 còn máy thiếu, nó không bao giờ rẽ sang các Tik sau.
2. **Stale DB Feedback:**
   Hàm kiểm tra `get_tik_avatar_stats` đọc từ SQLite `tiktok_tracker.db` (bảng `snapshots`). Bảng này chỉ cập nhật 1 lần/ngày lúc 07:00 sáng. Sau khi batch Tik 5 chạy xong và máy đã up thành công, DB vẫn chưa cập nhật `has_avatar=1`, khiến watchdog lầm tưởng Tik 5 vẫn còn thiếu máy và kích hoạt lại ngay lập tức.

---

## 2. Giải pháp kỹ thuật chuẩn hóa (Pattern)

### A. Round-Robin Cursor với Persistent State:
- Lưu con trỏ `avatar_rr_cursor` vào state file của watchdog (`D:\Taadaa\runtime\<host>\cron-state\post_evening_avatar_state.json`).
- Mỗi lần kích hoạt batch cho Tik X thành công, cursor tự động tăng:
  `state["avatar_rr_cursor"] = (cursor + offset + 1) % len(target_tiks)`
- Danh sách duyệt được xoay vòng theo cursor:
  `ordered_tiks = target_tiks[cursor:] + target_tiks[:cursor]`

### B. Cooldown chống Spam vòng lặp cùng Tik:
- Ghi nhận `avatar_launch_history` kèm timestamp và máy trong state.
- Bắt buộc kiểm tra cooldown tối thiểu 15 phút (900s) giữa các lần kích hoạt của cùng một Tik:
  ```python
  last_for_tik = next((l for l in reversed(recent_launches) if l.get("tik") == tik), None)
  if last_for_tik and (time.time() - last_for_tik.get("timestamp", 0) < 900):
      continue
  ```

---

## 3. Tiêu chuẩn Báo cáo Action-First Session Delta

Mọi báo cáo watchdog gửi về Farm Alert Telegram phải tuân thủ nghiêm ngặt nguyên tắc **Action-First**:
1. **CẤM TUYỆT ĐỐI** chỉ in số liệu snapshot tĩnh của Workbook/DB ("Đã có 240/532, còn 292").
2. **BẮT BUỘC bóc tách Delta của ca chạy**:
   - Thời gian chạy thực tế và số batch đã kích hoạt trong ca.
   - Thống kê thành công mới: `+X máy vừa hoàn thành (danh sách máy cụ thể)`.
   - Thống kê lỗi thực tế: `Y máy lỗi (mã lỗi cụ thể, lý do)`.
3. **Bóc tách chi tiết nhóm Bỏ qua**:
   - Dưỡng sinh (Organic Rest): danh sách máy.
   - Age-gate / Nick ngâm: danh sách máy.
   - Thiếu nguồn video render: danh sách máy.
   - CẤM gom chung thành `Khác (N)`.

---

## 4. Tự động thu thập Delta và Gom Cụm Lỗi từ batch summary.csv (2026-09-23)

### Quy trình trong `check_batch_status`:
Khi batch PowerShell chạy xong (`is_powershell_batch_alive() == False`):
1. **Trigger Rescan O(1)**: Gọi `rescan_completed_machines(machines)` qua `tiktok_account_tracker.py` để cập nhật `has_avatar=1` vào `tiktok_tracker.db`.
2. **Đọc `summary.csv` của batch mới nhất**:
   - Mở file `summary.csv` với encoding `utf-8-sig` (do PowerShell Export-Csv xuất UTF-8 có BOM).
   - Máy thành công: `Verified == "True"` hoặc `Status == "AVATAR_SMOKE_SUCCESS"`.
   - Máy lỗi: Bóc signature từ `report.json` (`error` / `avatar_error`) bằng regex `\[([A-Z0-9_]+)\]`.
3. **Lưu vết vào State phiên (`sess_key`)**:
   - Duy trì `session_uploaded_machines`: danh sách máy đã up thành công trong ca (tự động loại bỏ khỏi nhóm lỗi nếu máy retry thành công sau đó).
   - Duy trì `session_failed_by_reason`: map `{"ERROR_SIGNATURE": [máy1, máy2, ...]}`.
4. **Hiển thị trên Farm Alert**:
   - Báo cáo Farm Alert (`format_report_html`) bắt buộc nhúng block Delta:
     ```text
     • Kết quả ca tối nay: Thành công +X acc mới | Lỗi Y máy
     📋 CHI TIẾT CỤM LỖI CA TỐI NAY:
       ❌ [AVATAR_UPLOAD_MENU_MISSING] (8 máy): 5, 13, 19, 21, 22, 24, 32, 72
       ❌ [DEVICE_OFFLINE] (1 máy): 30
     ```

---

## 5. Pitfall & Khắc phục: Lỗi AVATAR_UPLOAD_MENU_MISSING (2026-09-23)

### Nguyên nhân:
1. **Timeout Menu do Push ảnh chậm**: Nếu mở màn hình Sửa hồ sơ / chạm vào avatar circle TRƯỚC, rồi mới đẩy file ảnh `avatar.jpg` qua ADB (mất 20-30s), menu bottom sheet của TikTok sẽ bị timeout tự đóng.
2. **TikTok nhảy thẳng vào Photo Picker**: Với một số tài khoản chưa có avatar hoặc sau cập nhật UI, TikTok không mở bottom sheet chọn nguồn mà nhảy thẳng vào Photo Picker hệ thống (`DocumentsUI` / `Gần đây` / `Recent` / resource-id `o_9`).
3. **Thiếu từ khóa Menu**: TikTok có nhiều biến thể localization: `"Chọn từ Thư viện"`, `"Bộ sưu tập"`, `"Chọn từ Album"`, `"Gallery"`, `"Chọn từ"`.

### Giải pháp Invariant:
- Luôn kiểm tra `already_at_picker`: Nếu màn hình đã chứa `com.android.documentsui`, `"Gần đây"`, `"Recent"`, `"Pictures"`, `"Albums"` hoặc resource-id `o_9`, BẮT BUỘC coi là đã mở picker thành công và bỏ qua bước tìm menu bottom sheet.
- Không tap mù tọa độ (540, 580) nếu màn hình đã ở trong Photo Picker.

