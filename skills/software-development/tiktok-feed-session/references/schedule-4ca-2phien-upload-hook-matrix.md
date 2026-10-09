# Quy chuẩn Lịch 4 Ca x 2 Phiên & Upload Hook (Nuôi TikTok Farm)

## 1. Bản chất Lịch 4 Ca x 2 Phiên
Hệ thống chạy 4 Ca/ngày, mỗi Ca gồm đúng 2 Phiên (8 windows/ngày):
- **Phiên 1**: Chỉ lướt feed nuôi tài khoản (Feed only). Tuyệt đối không đăng video.
- **Phiên 2**: Lướt feed nuôi tài khoản XONG, nếu có file video theo đúng Row của máy thì tự động kích hoạt upload hook đăng video lên TikTok.

### Bảng khung giờ chuẩn (HCMC - Asia/Ho_Chi_Minh):
- **Ca 4 (Đêm)**: Phiên 1 lúc `00:00` | Phiên 2 lúc `01:30` (Chẵn: Row 8 | Lẻ: Row 7)
- **Ca 1 (Sáng)**: Phiên 1 lúc `06:00` | Phiên 2 lúc `08:00` (Chẵn: Row 2 | Lẻ: Row 1)
- **Ca 2 (Trưa)**: Phiên 1 lúc `12:00` | Phiên 2 lúc `14:00` (Chẵn: Row 4 | Lẻ: Row 3)
- **Ca 3 (Tối)**:  Phiên 1 lúc `18:00` | Phiên 2 lúc `20:00` (Chẵn: Row 6 | Lẻ: Row 5)
- **Dead-zone**: `02:30` đến `05:59` (không dispatch bất kỳ máy nào).

## 2. Ràng buộc kỹ thuật xuyên suốt 4 tầng (Runner -> PS1 -> Python CLI -> Flow)

### Tầng 1: Hermes Cron Runner (`tiktok_runner.py`)
- Hàm `_determine_row(now)` trả về `(row, session_index, window_key)`.
- `session_index = 2` nếu khung giờ thuộc Phiên 2 (`(1, 30)`, `(8, 0)`, `(14, 0)`, `(20, 0)`), ngược lại `session_index = 1`.
- Phải truyền `-SessionIndex <1|2>` vào lệnh gọi PowerShell.

### Tầng 2: PowerShell Orchestrator (`run-feed-session.ps1`)
- Khai báo param `[ValidateRange(1, 2)][int]$SessionIndex = 1`.
- Logic upload flag:
  ```powershell
  if ($AllowUploadHook -or $SessionIndex -eq 2) {
      $arguments += "--allow-upload-hook"
      $arguments += "--session-index", "$SessionIndex"
  } else {
      $arguments += "--session-index", "$SessionIndex"
  }
  ```

### Tầng 3: CLI Entrypoint (`run_tiktok.py`)
- Argument `--session-index` nhận `int` (choices `[1, 2]`), nạp vào `config["_session_index"]`.
- Argument `--allow-upload-hook` (action `store_true`), nạp vào `config["_allow_upload_hook"]`.

### Tầng 4: Flow Gate (`multi_machine_feed_session.py`)
- Hook đăng video chỉ được gọi khi `_effective_session_index(config) == 2`:
  ```python
  if _effective_session_index(child_ctx.config) == 2:
      upload_res = _run_upload_hook(...)
  ```
- Bên trong `_run_upload_hook`: Kiểm tra `session_index != 2` -> skip với reason `not-final-session` (hoặc `missing-session-identity`). Chỉ khi `session_index == 2` mới thực hiện preflight đọc workbook `Tik{Row}.xlsx` và quét video `folder_video/{next_video}.mp4`.

## 3. Pitfall khi viết Unit Test
Khi cập nhật unit test cho `upload_hook` (`tests/test_upload_hook.py`):
- Toàn bộ fixture / context mẫu (`_make_dummy_context`) BẮT BUỘC phải đặt `session_index=2` (không được để `session_index=3` theo chuẩn 3 phiên cũ). Nếu để sai `session_index`, gate kiểm tra sẽ chặn ngay lập tức và trả về `not-final-session`, khiến hàng loạt test gate nhạy cảm (missing workbook, cooldown, video not rendered) bị fail đồng loạt.
