# GPM Hotmail Lifecycle Soaking & Change Info Traps

## 1. Bối Cảnh & Kiến Trúc Vòng Đời Hotmail trên GPM
Vòng đời tài khoản Hotmail tự động hóa trên GPMLogin tuân theo chuỗi chuyển trạng thái:
`HOTMAIL_LOGIN` $\rightarrow$ `CHATGPT_REG` $\rightarrow$ `CODEX_OAUTH` $\rightarrow$ `WAIT_7D` $\rightarrow$ `CHANGE_INFO` $\rightarrow$ `REMOVE_RECOVERY` $\rightarrow$ `SIGN_OUT_EVERYWHERE` $\rightarrow$ `RELOGIN_NEW_PASSWORD` $\rightarrow$ `DONE`.

## 2. Các Cạm Bẫy Trọng Yếu Khi Vận Hành (Pitfalls & Invariants)

### Cạm bẫy 1: Giam lỏng vô tận ở `WAIT_7D` do thiếu Fallback mốc thời gian
- **Hiện tượng**: Hàng chục/hàng trăm tài khoản đủ tuổi ($\ge 7$ ngày ngâm) nhưng không bao giờ chuyển sang `CHANGE_INFO`.
- **Nguyên nhân**: Nhiều tài khoản được nạp trực tiếp qua token OAuth mua từ kho (`hotmail_input.txt` / `latest_bought_*.txt`) hoặc đã có session, bỏ qua bước `HOTMAIL_LOGIN`. Khi đó, trường `hotmail_login_at` trong state mang giá trị `None`.
- **Hậu quả**: Lệnh kiểm tra `ready = parse_time(info.get("hotmail_login_at")) and (now - login_time).total_seconds() >= 7 * 86400` luôn đánh giá `False`.
- **Giải pháp bắt buộc**:
  Phải dùng chuỗi fallback cascade để xác định mốc ngâm:
  ```python
  anchor_time = (
      parse_time(info.get("hotmail_login_at"))
      or parse_time(info.get("codex_oauth_at"))
      or parse_time(info.get("chatgpt_registered_at"))
      or parse_time(info.get("created_at"))
  )
  ready = bool(anchor_time and (now_dt - anchor_time).total_seconds() >= 7 * 86400)
  ```

### Cạm bẫy 2: Lỗi Slice List gây "DONE Ảo" (Phantom DONE)
- **Hiện tượng**: Hàng chục tài khoản vừa sang `CHANGE_INFO` lập tức bị đánh dấu `status: DONE` trong khi chưa hề đổi mật khẩu hay cập nhật Excel.
- **Nguyên nhân**: Trong mảng `STAGE_ORDER`:
  - `0`: `HOTMAIL_LOGIN`
  - `1`: `CHATGPT_REG`
  - `2`: `CODEX_OAUTH`
  - `3`: `WAIT_7D`
  - `4`: `CHANGE_INFO`
  - `5`: `REMOVE_RECOVERY`
  - ...
  - `8`: `DONE`
  Nếu viết `if stage in STAGE_ORDER[5:-1]: run_cmd(...)`, phần tử index `4` (`CHANGE_INFO`) bị loại khỏi điều kiện. Hàm rơi xuống cuối `return {"status": "DONE", "stage": stage}`, khiến supervisor đánh dấu `status: DONE` ảo.
- **Khắc phục**: Đảm bảo slice bao gồm index 4: `STAGE_ORDER[4:-1]` hoặc kiểm tra tường minh theo từng stage.

### Cạm bẫy 3: Lệch đường dẫn Script đa Repo (`GPM auto` vs `Hotmail`)
- Script supervisor nằm ở `D:\Taadaa\GPM auto\scripts\batch_gpm_5profiles_supervisor.py`.
- Script đổi mật khẩu lại nằm ở `D:\Taadaa\Hotmail\scripts\gpm_change_hotmail_security.py`.
- Nếu định nghĩa `SCRIPT_DIR = Path(...)` của repo `GPM auto` rồi gọi `SCRIPT_DIR / "gpm_change_hotmail_security.py"`, lệnh gọi `subprocess` sẽ thất bại âm thầm nếu không kiểm tra `exists()`.
- **Quy tắc**: Luôn kiểm tra path tồn tại tuyệt đối hoặc trỏ biến root `TAADAA_ROOT / "Hotmail" / "scripts" / "gpm_change_hotmail_security.py"`.

### Cạm bẫy 4: Kênh nhận Báo cáo Cronjob (Delivery Target Mismatch)
- Khi operator thắc mắc "sao không thấy báo cáo", luôn kiểm tra cấu hình `deliver` trong cronjob (`jobs.json`).
- Job `hotmail-gpm-lifecycle-6h-report` được gán cố định `deliver: telegram:-5373649734` (Nhóm Farm Alerts). Tin nhắn chỉ xuất hiện trong nhóm chung, không tự động đẩy về DM / private chat nếu không cấu hình đa kênh `deliver: origin,telegram:-5373649734`.
