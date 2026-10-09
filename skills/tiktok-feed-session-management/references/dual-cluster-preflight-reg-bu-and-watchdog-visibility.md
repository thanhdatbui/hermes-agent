# Dual-Cluster Preflight Reg Bù & Watchdog Multi-Cluster Visibility (2026-10-04)

## Bối cảnh sự cố
Trong ca nuôi Ca 2 (12:00 - Phiên 1, Row 4) ngày 2026-10-04, tin nhắn tổng kết watchdog `feed_session_watchdog.py` chỉ báo cụm `【FARM KIBE - MÁY 1-80】`, hoàn toàn thiếu vắng khối `【FARM ADMIN】`.
Khi người dùng chất vấn: *"ủa là sao, thiếu acc thì phải tự động chạy tiktok reg bù chứ???"*, điều tra phát hiện chuỗi Preflight Reg bù của Farm Admin (`ensure_row_accounts.py 4`) đã bị nuốt nhịp, thoát trong 0.2 giây mà không reg nick nào, dẫn đến Admin có 0 account hợp lệ ở Row 4 và bị runner skip an toàn toàn bộ phiên nuôi.

---

## Giải phẫu nguyên nhân kỹ thuật (Root Cause)
1. **Cơ chế Watchdog đa cụm (`CLUSTERS = [kibe, admin]`):**
   - Trong `feed_session_watchdog.py`, watchdog duyệt qua danh sách các cụm.
   - Nếu thư mục artifact của ngày hôm nay (`D:/Taadaa/runtime/admin/live/2026-10-04`) không tồn tại hoặc không có run folder nào trong khung giờ ca, watchdog chủ động `continue` bỏ qua cụm đó để tránh in khối rỗng. Do Admin bị skip ở bước chạy nuôi, thư mục không được tạo ra $\rightarrow$ Watchdog âm thầm ẩn khối Admin.

2. **Cạm bẫy `sys.path` thiếu `tools` trong `ensure_row_accounts.py`:**
   - Tại mốc 12:00, `tiktok_runner.py` gọi preflight cho cụm `admin` với:
     `child_env["TAADAA_HOST_CONFIG"] = r"D:\Taadaa\machine-config\admin.yaml"`
   - Tuy nhiên, trong `ensure_row_accounts.py`:
     ```python
     TAADAA_ROOT = Path("D:/Taadaa")
     TIKTOK_REG_DIR = TAADAA_ROOT / "Tiktok_Reg"
     if str(TIKTOK_REG_DIR) not in sys.path:
         sys.path.insert(0, str(TIKTOK_REG_DIR))
     try:
         import taadaa_host as _taadaa_host_mod
     except ImportError:
         _taadaa_host_mod = None
     ```
   - Do `taadaa_host.py` nằm ở `D:\Taadaa\tools\taadaa_host.py`, việc thiếu `TOOLS_DIR` trong `sys.path` khiến `import taadaa_host` vấp `ImportError` âm thầm.

3. **Cạm bẫy Fallback mù quáng về Kibe:**
   - Khi `_taadaa_host_mod is None`, hàm `get_host_info()` fallback cứng về:
     `HOST_ID = "kibe"`, `SAFE_WORKBOOK = D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx`.
   - Script preflight đang chạy cho cụm Admin nhưng lại mở workbook của Kibe để đối soát. Do Kibe đã đủ 80/80 nick ở Row 4, script in `[ensure_row] [KIBE] Row 4: Toan bo may da day du tai khoan! Khong can reg.` và exit 0 ngay.
   - `tiktok_runner.py` tưởng preflight xong, sang bước kiểm tra `admin/taikhoan_run_safe.xlsx` thấy `valid_count == 0` nên skip window 12:00 $\rightarrow$ Không sinh artifact $\rightarrow$ Watchdog không hiển thị Admin.

---

## Chuẩn hóa giải pháp (Host Awareness Pattern)
1. **Luôn nạp `TOOLS_DIR` vào `sys.path` trước khi import `taadaa_host`:**
   ```python
   TAADAA_ROOT = Path("D:/Taadaa")
   TOOLS_DIR = TAADAA_ROOT / "tools"
   if str(TOOLS_DIR) not in sys.path:
       sys.path.insert(0, str(TOOLS_DIR))
   ```
2. **Fallback nhận diện trực tiếp qua biến môi trường `TAADAA_HOST_CONFIG`:**
   Nếu `taadaa_host` gặp lỗi ngoại lệ, tuyệt đối không hardcode fallback về `kibe` nếu `TAADAA_HOST_CONFIG` đang chỉ định `admin`:
   ```python
   host_cfg_env = os.environ.get("TAADAA_HOST_CONFIG", "").strip()
   if host_cfg_env and "admin" in host_cfg_env.lower():
       return "admin", Path("D:/OneDrive/TaadaaData/admin"), Path("D:/Taadaa/runtime/admin")
   return "kibe", Path("D:/OneDrive/TaadaaData/kibe"), Path("D:/Taadaa/runtime/kibe")
   ```
3. **Kỷ luật Reg Bù Tự Động (User Invariant):**
   - Khi bất kỳ Row nào của bất kỳ cụm nào thiếu tài khoản, chuỗi Preflight (`ensure_row_accounts.py`) BẮT BUỘC phải phát hiện chính xác danh sách máy thiếu, tự động gọi `buy_hotmail.py` mua mail bổ sung và kích hoạt batch `_run_all_targets.py` để reg bù nick trước giờ chạy feed.
