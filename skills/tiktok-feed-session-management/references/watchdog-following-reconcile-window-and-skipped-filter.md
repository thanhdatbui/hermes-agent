# Kỷ luật Đối soát TikTok Web Following & Bộ lọc Reconcile Watchdog

## 1. Bản chất & Nguyên nhân Lệch Đối soát (Time Window Buffer)
Trong cơ chế đối soát Following giữa script và TikTok Web qua `reconcile_cluster_following()`:
- Ca nuôi kết thúc sát giờ mốc (ví dụ Ca 3 Phiên 1 kết thúc lúc 20:00).
- Subprocess cào profile TikTok Web (`tiktok_account_tracker.py`) chạy tuần tự/batch trên dàn nick, thường hoàn thành và ghi snapshot vào SQLite (`tiktok_tracker.db`) lúc **`+15 đến +25 phút`** sau khi ca kết thúc (ví dụ 20:15 - 20:25).
- **Pitfall:** Nếu hàm đệm thời gian `buffer_reconcile_iso(session_end_iso, minutes)` chỉ buffer 10 phút (mốc chặn 20:10:00), câu lệnh SQL:
  ```sql
  SELECT following, timestamp FROM snapshots 
  WHERE LOWER(username) = LOWER(?) AND timestamp <= query_end_iso 
  ORDER BY timestamp DESC LIMIT 1
  ```
  sẽ **bỏ qua snapshot mới cào**, lùi ngược về snapshot của ca sáng (07:03). Khi cả `baseline_row` và `latest_row` đều là snapshot cũ, delta tính ra `0 - 0 = 0`, dẫn đến báo cáo lệch âm sai sự thật (ví dụ: script báo 8 nhưng web báo 0 -> lệch -8).
- **Quy chuẩn:** Buffer `session_end_iso` phải tối thiểu **30 phút** (`buffer_reconcile_iso(session_end_iso, 30)`) để bao phủ trọn vẹn độ trễ của pipeline cào dữ liệu web.

## 2. Kỷ luật Lọc Thiết bị Reconcile (Chống False Alert Thiếu Nick)
- **Pitfall:** Nếu gom toàn bộ máy trong manifest vào danh sách kiểm tra (`target_machines = ... | set(all_follows.keys())`), các cụm máy hoàn toàn không follow (ví dụ 75 máy Farm Admin bị skip do `< 6` video, 0 follow) sẽ khiến vòng lặp `continue` toàn bộ.
- Khi đó `m_to_user` rỗng, kích hoạt fallback:
  ```python
  if not m_to_user and target_machines:
      return [f"  + Đối soát TikTok Web: Không tìm thấy username trong workbook cho {len(target_machines)} máy follow"]
  ```
  tạo cảnh báo giả mạo nghiêm trọng rằng "75 máy follow bị mất username trong Excel".
- **Invariant:** Chỉ đưa các máy thực sự phát sinh follow hoặc có lỗi vào danh sách cần đối soát (`reconcile_targets`):
  ```python
  if cnt <= 0 and natural_cnt <= 0 and not (failed or is_timeout_or_err):
      continue
  reconcile_targets.append(str(m))
  ```
  Nếu `reconcile_targets` rỗng thì trả về `[]` sạch sẽ, không báo lỗi workbook.

## 3. Regression & Architecture Gates khi Sửa Watchdog
Khi sửa `feed_session_watchdog.py`:
1. **Line Budget Gate:** Tổng số dòng script chính bắt buộc `<= 1450 lines`, kiểm tra bằng `pytest tests/test_watchdog_architecture_gate.py`.
2. **Modular Architecture Invariant:** Giữ nguyên 5 module tách rời (`lock`, `merger`, `alerts`, `formatters`, `parser`), cấm định nghĩa lại các class/hàm đã chuyển module.
3. **Pre-commit Gate:** Hook git tự động quét và cấm các lệnh UI regex cấm (`uiautomator dump`, `adb.dump_ui`).
4. **Full Test Suite:** Toàn bộ test suite (`pytest tests`, >= 146 tests) phải pass 100% trước khi commit.
