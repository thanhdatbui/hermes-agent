# Case Study & Invariant: 4-Way Multi-Tier Cron Sync Parity (Anti-Ghost Revert / Stale Runtime)

## 1. Hiện Tượng Thực Tế
- User và agent đã fix logic cron/runner (ví dụ hàm `_scrape_pre_session_following` để lấy baseline snapshot cào trước phiên trong `tiktok_runner.py`), đã test pass và commit vào Git repo (`bab4d3f`).
- Tuy nhiên đến các phiên sau, báo cáo Watchdog trên Telegram vẫn báo lỗi y hệt (nhãn `UNPROVEN` do stale baseline snapshot > 4h từ ngày hôm trước).
- User bức xúc vì "đã fix lỗi này nhiều lần rồi mà vẫn bị lại".

## 2. Nguyên Nhân Gốc Rễ (Root Cause)
1. **Kiến trúc phân tán 4 tầng lưu trữ file thực thi:**
   - **Tầng 1 (Source/Repo):** `D:/Taadaa/tiktok-luot nuoi acc/scripts/hermes_cron/tiktok_runner.py`
   - **Tầng 2 (Runtime Executable):** `%LOCALAPPDATA%\hermes\scripts\tiktok_runner.py` (nơi Hermes Cron scheduler thực sự gọi khi kích hoạt `no_agent=True`).
   - **Tầng 3 (Deploy Central Repo):** `D:/Taadaa/Hermes/deploy/hermes-home/scripts/tiktok_runner.py`
   - **Tầng 4 (Cloud Backup Sync):** `D:/OneDrive/Taadaa_Sync_Shared/hermes-cron/scripts/tiktok_runner.py`
2. **Lệch pha triển khai (Deployment Drift):**
   - Agent chỉ commit code vào Tầng 1 (Repo).
   - Lệnh deploy wrapper `deploy_hermes_cron_wrappers.ps1` bị lỗi logic check thư mục đích (`$dstResolved -ne $InstallDir` so sánh đường dẫn file với đường dẫn folder) nên ném exception `unexpected destination` và không copy được sang Runtime. (Khắc phục bằng `(Split-Path -Parent $dstResolved) -ne $InstallDir`).
   - Các lời gọi subprocess trong runner chạy ngầm trên Windows bắt buộc kèm `creationflags = 0x08000000` (`CREATE_NO_WINDOW`) để tránh bị chặn hoặc sinh conhost console nháy màn hình.
   - Khi `cron_sync_watchdog.py` chạy tự động, nó đồng bộ giữa Tầng 2, 3, 4 dựa trên mtime. Do Tầng 1 chưa được copy sang Tầng 3 (Deploy), Tầng 2 (Runtime) tiếp tục chạy mã nguồn cũ từ nhiều ngày trước (`f630216e` vs `5709513c`).
   - Dẫn đến tình trạng "Code Git đã sửa nhưng máy chạy thực tế vẫn là code cũ".

---

## 3. Quy Trình Kiểm Tra & Khắc Phục Bắt Buộc (4-Way Parity Enforcement)

Mỗi khi sửa bất kỳ cron script hoặc wrapper runner nào (`tiktok_runner.py`, `feed_session_watchdog.py`, `follow_session_watchdog.py`, `tiktok_picker.py`...):

### Bước 1: Sửa và Kiểm thử Unit Test trên Repo
- Sửa code tại `D:/Taadaa/<repo>/...`
- Chạy focused unit test (pytest) để đảm bảo logic đạt 100% pass.

### Bước 2: Đồng bộ cưỡng bức sang Deploy Repo & Runtime
- Sao chép trực tiếp file vừa sửa sang cả `deploy/hermes-home/scripts/` và `%LOCALAPPDATA%\hermes\scripts\`:
  ```bash
  cp "<repo_path>/<script>.py" "D:/Taadaa/Hermes/deploy/hermes-home/scripts/<script>.py"
  cp "<repo_path>/<script>.py" "$LOCALAPPDATA/hermes/scripts/<script>.py"
  ```

### Bước 3: Kích hoạt Cron Sync Watchdog với cờ `--force`
- Chạy lệnh:
  ```bash
  python "D:/Taadaa/Hermes/deploy/hermes-home/scripts/cron_sync_watchdog.py" --force
  ```
- Đảm bảo lệnh in ra trạng thái đồng bộ thành công sang cả OneDrive và các thư mục liên quan.

### Bước 4: Hậu kiểm SHA-256 trên cả 4 tầng (BẮT BUỘC)
- Chạy đoạn script kiểm tra hash SHA-256 đối soát giữa Repo, Runtime, Deploy và OneDrive:
  ```python
  import os, hashlib
  def h(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()[:8] if os.path.exists(p) else 'MISSING'
  # Đối soát 4 tầng phải trả về True cho h(repo) == h(runtime) == h(deploy) == h(onedrive)
  ```
- Nếu có bất kỳ sự lệch hash nào, TUYỆT ĐỐI KHÔNG BÁO DONE mà phải đồng bộ lại ngay.
