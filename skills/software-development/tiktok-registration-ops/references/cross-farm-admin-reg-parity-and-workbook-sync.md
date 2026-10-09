# Cross-Farm Parity (Kibe & Admin) for TikTok Auto-Reg & Workbook Sync (2026-09-24)

## Bối cảnh & Nguyên tắc Parity 100%
Farm Taadaa có 2 cụm máy chính:
- **Kibe**: Máy 1–80, kết nối ADB nội bộ `127.0.0.1:5037`, config `machine-config/kibe.yaml`, workbook `D:/OneDrive/TaadaaData/kibe/`.
- **Admin**: Máy 201–280, kết nối ADB Server từ xa `tcp:192.168.110.119:5037`, config `machine-config/admin.yaml`, workbook `D:/OneDrive/TaadaaData/admin/`.

Nguyên tắc bất biến: **Mọi cơ chế tự động, watchdog, preflight check, auto-reg bù, nuôi feed mà cụm Kibe có thì Admin cũng phải có tương đương 100%**. Tuyệt đối không hardcode loại trừ Admin.

---

## 1. Cron Runner Preflight (`tiktok_runner.py`)

### Pitfall đã fix
Trước đây trong `tiktok_runner.py`, khâu kiểm tra và reg bù bị hardcode:
```python
if cluster_name == "kibe":
    _preflight_ensure_accounts(row, window_key)
```
Hậu quả: Dàn Admin khi thiếu tài khoản (ví dụ Row 5 chỉ có 13/80 nick) không bao giờ được tự động kích hoạt reg bù trước ca chạy.

### Chuẩn hóa Dual-Cluster
- Chữ ký hàm nhận thông tin cluster:
  `def _preflight_ensure_accounts(row: int, window_key: str, cluster: dict[str, Any] | None = None) -> None:`
- Gọi thống nhất trong loop:
  `_preflight_ensure_accounts(row, window_key, cluster=cluster)`
- Marker file tách biệt theo cluster để không chặn chéo:
  `marker = cluster_state_dir / f".preflight_{cluster_name}_{window_key}"`
- Truyền biến môi trường tương ứng vào sub-process:
  ```python
  child_env = dict(os.environ)
  if cluster.get("host_config"):
      child_env["TAADAA_HOST_CONFIG"] = cluster["host_config"]
  if cluster.get("adb_server_socket"):
      child_env["ADB_SERVER_SOCKET"] = cluster["adb_server_socket"]
  ```
- **Lưu ý 3 vị trí đồng bộ**: Khi sửa runner, luôn đồng bộ cả 3 nơi:
  1. Runtime: `C:/Users/Kibe/AppData/Local/hermes/scripts/tiktok_runner.py`
  2. OneDrive: `D:/OneDrive/Taadaa_Sync_Shared/hermes-cron/scripts/tiktok_runner.py`
  3. Git Repo: `D:/Taadaa/Hermes/deploy/hermes-home/scripts/tiktok_runner.py`

---

## 2. Remote ADB Routing Cho Admin (`ensure_row_accounts.py`)

Khi script chạy trên PC Kibe nhưng xử lý cụm Admin (`HOST_ID == "admin"`), các lệnh ADB client phải trỏ sang máy chủ ADB của Admin:
```python
if HOST_ID == "admin" and "ADB_SERVER_SOCKET" not in env:
    try:
        import socket
        if "admin" not in socket.gethostname().lower():
            env["ADB_SERVER_SOCKET"] = "tcp:192.168.110.119:5037"
    except Exception:
        pass
```

---

## 3. Dynamic Workbook Append & Slot Mapping (`ensure_row_accounts.py`)

### Mapping STT Tik theo dải máy
- Kibe (1..80): `expected_tik = (m - 1) * 8 + slot` (Row tĩnh 640 dòng).
- Admin (201..280): `expected_tik = (m - 201) * 8 + slot`.
```python
expected_tik = (m - 201) * 8 + slot if m >= 201 else (m - 1) * 8 + slot
```

### Dynamic Append cho workbook chưa fill đủ dòng (như Admin)
Workbook `taikhoan_dat_v2_updated .xlsx` của Admin không tạo sẵn 640 dòng trống mà thêm dần theo đợt reg.
Nếu tra cứu `c1 == m` và `c2` khớp slot không thấy dòng có sẵn:
- **CẤM** bỏ qua kết quả reg (`Khong tim thay target row cho STT ... Slot ..., bo qua`).
- **BẮT BUỘC** tự động append vào cuối sheet:
  ```python
  if target_row is None:
      target_row = ws_trk.max_row + 1
  ```
- Cột 2 (STT Tik / Folder Video): Giữ nguyên giá trị cũ nếu có, nếu dòng mới thì ghi `expected_tik`, **tuyệt đối không ghi đè số slot (1..8)**.

---

## 4. Tự động mua & nạp Hotmail OAuth2 (`buy_hotmail.py`)

Khi `ensure_row_accounts.py` quét row phát hiện máy thiếu mail:
- Tự động gọi: `python buy_hotmail.py --append-admin N` (hoặc `--append-kibe N`).
- Tool tự verify Microsoft Graph token trước khi ghi vào `gmail_clean_v2.xlsx`.
- Sau khi nạp mail, tiếp tục kích hoạt batch reg song song qua `_run_all_targets.py`.

---

## 5. Hard Gate Follow Chéo vs Video Đã Đăng (`multi_machine_feed_session.py`)

Khi kiểm tra báo cáo Telegram thấy "Follow chéo (0 lượt follow) [Module 2: 0 | Module 1: 0]":
- Kiểm tra số lượng video của tài khoản trong ca: Theo quy tắc Farm (`under-10-videos-follow-disabled`), nick có `< 10` video đã đăng sẽ bị **skip hoàn toàn** khâu follow để chống quét nhả follow từ TikTok.
- Kết hợp với tỷ lệ dưỡng sinh (Organic Rest ~33%), nếu toàn bộ máy trong ca là nick mới hoặc đang dưỡng sinh thì số lượt follow ghi nhận bằng 0 là đúng thiết kế, được ghi nhận trong nhóm "Bỏ qua".
