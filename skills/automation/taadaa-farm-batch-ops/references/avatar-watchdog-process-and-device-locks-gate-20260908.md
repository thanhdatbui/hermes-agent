# Watchdog Avatar Kích Hoạt Sau Ca 3 & Dual Idle Gate (Process + Device Locks) (2026-09-08)

## 1. Bối cảnh & Mục tiêu Vận hành
Khi cần tự động hóa việc upload avatar cho một ca/row cụ thể (ví dụ: Row 4 `Tik4.xlsx`) ngay khi Ca 3 nuôi feed vừa kết thúc:
- **Cấm chạy đè (Dual Idle Gate):** Không được kích hoạt batch upload avatar khi feed runner còn chạy HOẶC còn bất kỳ device-lock nào của tiến trình nuôi feed (`tiktok-luot nuoi acc`) chưa được giải phóng.
- **Tránh xung đột chuỗi Reg đêm (Midnight Window Guard):** Batch phải dừng hoặc thoát trước `00:45` để nhường toàn bộ tài nguyên cho chuỗi Reg Gmail / Reg TikTok (`night-chain-reg-pipeline` chạy lúc 01:00).
- **Lọc máy Pending từ Workbook:** Đọc trực tiếp sheet `TaiKhoan` trong `Tik<N>.xlsx`, lọc các máy có ID hợp lệ và cột `Avatar != 'OK'`.

---

## 2. Kiến trúc & Logic Cốt lõi của Watchdog

### A. Dual Idle Gate (Tiến trình + Device Locks)
1. **Kiểm tra Tiến trình (`is_feed_runner_active`):**
   ```python
   def is_feed_runner_active() -> bool:
       target_signatures = (
           "multi-machine-feed-session",
           "multi_machine_feed_session",
           "run-feed-session.ps1",
           "run_tiktok.py",
       )
       for p in psutil.process_iter(["name", "cmdline"]):
           try:
               name = (p.info.get("name") or "").lower()
               if not name.startswith(("python", "powershell", "pwsh")):
                   continue
               cmd = " ".join(p.info.get("cmdline") or []).lower()
               if any(sig in cmd for sig in target_signatures):
                   return True
           except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
               continue
       return False
   ```

2. **Kiểm tra Device Locks còn sống (`count_active_feed_locks`):**
   - Thư mục lock: `C:\Users\Kibe\.codex\device-locks`
   - Chỉ tính các lock file `machine_*.lock.json` có `project` chứa `"nuoi acc"` VÀ PID còn tồn tại trên hệ thống (`psutil.pid_exists(pid)`). Bỏ qua stale locks của tiến trình đã chết.
   ```python
   def count_active_feed_locks(lock_root: Path) -> int:
       count = 0
       for p in lock_root.glob("machine_*.lock.json"):
           try:
               data = json.loads(p.read_text(encoding="utf-8"))
               proj = str(data.get("project") or "").lower()
               pid = data.get("pid")
               if "nuoi acc" in proj:
                   if isinstance(pid, int) and psutil.pid_exists(pid):
                       count += 1
           except Exception:
               continue
       return count
   ```

---

## 3. Lọc Máy Cần Upload Avatar (`get_pending_machines`)
- File: `D:\OneDrive\TaadaaData\kibe\Tik<N>.xlsx`, Sheet: `TaiKhoan`.
- Cấu trúc cột chuẩn:
  - Cột `Máy` (index 0)
  - Cột `ID` (index 2)
  - Cột `Avatar` (index 12)
- Điều kiện Pending:
  - `Máy` là số nguyên hợp lệ (1..80).
  - `ID` hợp lệ (không rỗng, không phải `none`, `null`, `chua_co`).
  - `Avatar` chưa đạt `OK` (giá trị rỗng hoặc khác chuỗi `OK`).

---

## 4. Kích hoạt Batch Upload Avatar Canonical
Khi điều kiện an toàn thỏa mãn (giờ $\ge$ 22:00 hoặc cờ `--immediate`, `is_feed_runner_active() == False`, `count_active_feed_locks() == 0`):
1. **Sinh Assignment Manifest:**
   - File: `D:\CodexRuntime\tiktok-video\assignment-manifest-avatar-tik<N>.json`
   - Schema version 1, owner `hermes-kibe-avatar`, resources: `["machine:1", ...]`.
2. **Gọi Launcher PowerShell Canonical:**
   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1" `
     -Tik <N> `
     -AssignmentManifest "D:\CodexRuntime\tiktok-video\assignment-manifest-avatar-tik<N>.json" `
     -WorkerId "hermes-kibe-avatar" `
     -MaxParallel 20 `
     -HostConfigPath "D:\Taadaa\machine-config\kibe.yaml"
   ```
   - Thiết lập biến môi trường `TIKTOK_VIDEO_AUTOMATION_CORE_VERSION=0.4.45`.
   - Stream song song stdout/stderr ra console và append vào `D:\CodexRuntime\tiktok-video\batch-runs\watchdog_avatar_tik<N>.log`.

---

## 5. Các cờ CLI Bắt buộc
- `--check-status`: In trạng thái hiện tại của feed runner, số feed lock còn active, số máy pending avatar rồi thoát ngay (Exit 0).
- `--dry-run`: Kiểm tra logic vòng lặp canh và in kế hoạch kích hoạt batch mà không chạy PowerShell thật.
- `--immediate`: Bỏ qua gate kiểm tra giờ $\ge$ 22:00 để test hoặc chạy cưỡng bức ban ngày khi feed runner đã nghỉ.
