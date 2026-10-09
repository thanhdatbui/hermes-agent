# Anti-Double-Penalty Follow Cooldown & Transient Safe-Workbook Lock Recovery

## 1. Vấn đề Anti-Double-Penalty Follow Cooldown (Nick bị nhả phiên trước)
### Hiện tượng
- Nick bị nhả follow ở Phiên 1 (dính `FOLLOW_FAILED` và kích hoạt cooldown 3/5/7 ngày).
- Sang Phiên 2 của cùng ngày, báo cáo watchdog lại tiếp tục ghi:
  `Follow tự nhiên: 0 lượt ... (Đã tự trừ N lượt do nick bị nhả/drop)`
  `Nhả follow: M...`
- Người vận hành thắc mắc: "Đã nhả ở Phiên 1 và trừ ở Phiên 1 rồi, tại sao Phiên 2 lại trừ tiếp?"

### Cơ chế lỗi
1. Trong `multi_machine_feed_session.py`:
   `_is_account_follow_cooldown` và `_run_follow_hook` chỉ so sánh chuỗi `state.get("follow_failed_date") == today`.
   Nếu file `follow_state_<M>_row_<R>.json` có `follow_failed = True` và ghi nhận cữ phạt nhưng `follow_failed_date` không khớp hoặc cữ nhả xảy ra từ trước, hàm trả về `False`.
2. Do trả về `False`, Phiên 2 vẫn cấp `_follow_rate` (5%) cho nick đó khi lướt feed $\rightarrow$ nick tiếp tục bấm follow dạo 1 video trên feed.
3. Đến cuối phiên lướt, script gọi `_run_follow_hook` $\rightarrow$ `follow_engine.py` đọc `self.state.follow_failed` thấy `True` nên dừng ngay với `FOLLOW_FAILED (followed = 0)`.
4. Watchdog khi chốt Phiên 2 thấy kết quả `FOLLOW_FAILED` nên lại kích hoạt cơ chế xóa sạch follow tự nhiên của nick đó trong Phiên 2 $\rightarrow$ tạo cảm giác "trừ 2 lần".
5. **Gốc rễ kẹt cờ vĩnh viễn (Zombie Failure Lock trong `follow_state.py`)**:
   Hàm `_check_and_sync_cooldown_expiry` của `FollowState` từng có điều kiện:
   `if "last_failed_at" not in self._data and "follow_failed_date" in self._data: return self._migrate_legacy_cooldown(...)`
   Nếu file state đã có `last_failed_at` nhưng thiếu `cooldown_until_at`, nó bỏ qua migration và trả về ngay `bool(self._data.get("follow_failed"))` $\rightarrow$ luôn là `True` vĩnh viễn dù đã quá hạn 3 ngày. Mỗi lần chạy, `follow_engine.py` thấy cờ `True` là abort ngay ở dòng 799 mà không gọi `set_follow_failed()`, khiến cờ phạt không bao giờ được xóa.

### Nguyên tắc xử lý (Anti-Double Penalty & Cooldown Sync)
1. **Sửa Migration Cooldown trong `follow_state.py`**:
   Kiểm tra `if "cooldown_until_at" not in self._data and (self._data.get("follow_failed") or "follow_failed_date" in self._data):` để tự động tính hạn theo ngày lỗi cũ và xóa sạch `follow_failed = False` ngay khi hết hạn, đưa nick về trạng thái `is_post_cooldown_warmup`.
2. **Kiểm tra trực tiếp cờ `follow_failed`**:
   `_is_account_follow_cooldown` phải kiểm tra `state.get("follow_failed") is True`.
   Tính toán chính xác thời gian mãn hạn dựa trên `fail_streak` (Streak 1 = 3 ngày, Streak 2 = 5 ngày, Streak $\ge$ 3 = 7 ngày).
3. **Khóa follow tự nhiên trên Feed**:
   Khi đang trong hạn cooldown: Tự động ép `child_config["_follow_rate"] = {"for_you": 0, "following": 0, "friends": 0}` (chỉ nuôi lướt, không bấm follow bất kỳ video nào).
4. **Bỏ qua Follow Hook graceful**:
   `_run_follow_hook` tái sử dụng `_is_account_follow_cooldown`. Nếu đang trong hạn, trả về ngay:
   `{"status": "skipped", "reason": "follow-released-daily-cooldown", "followed_count": 0, "failed": 0, "follow_failed": False}`.
   `follow_failed` phải là `False` để watchdog không phân loại nick vào nhóm `released` và không tạo cảnh báo giả.

---

## 2. Transient Safe-Workbook File Lock & Runner State-Lock Recovery
### Hiện tượng
- Runner báo `Row N co 0 account hop le trong taikhoan_run_safe.xlsx, skipping window ...`.
- Cả ca (4 tiếng) của cụm farm đó bị bỏ rơi hoàn toàn, không có máy nào spawn.
- Trong khi đó file workbook thực tế vẫn có đủ nick (ví dụ 75/80 máy).

### Cơ chế lỗi
1. File `taikhoan_run_safe.xlsx` nằm trên OneDrive hoặc đang bị tiến trình reg bù/sync ghi đè tạm thời.
2. `openpyxl.load_workbook` ném ra ngoại lệ `PermissionError` hoặc file lock.
3. Trong `tiktok_runner.py`, khối `except Exception:` ngầm trả về `0`.
4. Khi `valid_count == 0`, runner lập tức gọi `_save_state(row, window_key, now, state_file=...)`.
5. Việc ghi state khiến các nhịp cron 15 phút kế tiếp (`14:15`, `14:30`, `14:45`...) tưởng rằng window đó đã hoàn tất, dẫn đến việc bỏ rơi cả ca 4 tiếng của cụm.

### Nguyên tắc xử lý
1. **Retry đọc Safe Workbook**:
   Thử lại tối đa 3 lần với delay `1.0s` khi gặp `Exception` để chờ OneDrive / sync script nhả file lock.
2. **CẤM ghi `_save_state` khi `valid_count == 0`**:
   Nếu `valid_count == 0` (nghi ngờ lỗi đọc file hoặc chưa kịp sync), runner **chỉ in cảnh báo và bỏ qua nhịp hiện tại**, tuyệt đối không ghi `_save_state`.
   Nhịp cron 15 phút kế tiếp sẽ đọc lại; khi file mở được sẽ phát hiện đủ nick và spawn chạy ngay.

---

## 3. Cluster Visibility Invariant trong Watchdog Report
### Hiện tượng
- Báo cáo watchdog tổng kết phiên chỉ hiển thị một cụm (ví dụ `【FARM KIBE】`), cụm còn lại (`【FARM ADMIN】`) biến mất hoàn toàn không có dấu vết.

### Cơ chế lỗi
- Trong `feed_session_watchdog.py`:
  ```python
  if not session_runs:
      continue
  ```
  Nếu cụm Admin không có run folder trong phiên (do runner bị skip hoặc hoãn), watchdog âm thầm `continue`, dẫn đến report cụt lủn và gây hiểu lầm là watchdog bị lỗi.
- Lỗi biến `cluster_stats` chưa được khởi tạo dẫn đến `UnboundLocalError` khi cụm cuối bị rỗng.

### Nguyên tắc xử lý
1. Khi có ít nhất một cụm đã hoàn tất và xuất báo cáo (`has_any_cluster_runs`), cụm còn lại nếu không có lượt chạy **bắt buộc phải hiển thị khối trạng thái rõ ràng**:
   ```text
   🏢 【FARM ADMIN - MÁY 201-280】
   • Trạng thái: Không có lượt chạy nào trong phiên (Chưa chạy / Bị skip)
   ```
2. Khởi tạo `cluster_stats = []` ở đầu vòng lặp và cập nhật an toàn theo từng cụm để tránh lỗi UnboundLocalError.
