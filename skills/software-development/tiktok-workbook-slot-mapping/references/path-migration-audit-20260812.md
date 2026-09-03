# Path-migration audit: workbook root dời sang TaadaaData\kibe (2026-08-12)

## Bối cảnh
User dời toàn bộ workbook PC kibe sang `D:\OneDrive\TaadaaData\kibe\`. Yêu cầu: quét ALL
repo automation tìm chỗ còn trỏ đường cũ. Kết quả là ma trận dưới đây + kỹ thuật quét.

## Nội dung folder mới `D:\OneDrive\TaadaaData\kibe\` (inventory chuẩn)
```
gmail_clean_v2.xlsx
PROXYgandienthoai.xlsx
taikhoan_dat_v2_updated .xlsx     (DẤU CÁCH trước .xlsx — giữ đúng)
taikhoan_run_safe.xlsx
Tik1.xlsx
Tik2.xlsx                          (thiếu lúc user dời — đã copy từ D:\OneDrive\Tiktok\Tik2.xlsx 2026-08-12)
tik3.xlsx                          (chữ thường, KHÔNG phải Tik3.xlsx)
```
PITFALL: khi user nói "dời hết rồi", ĐỪNG tin mù — verify từng file. Session này Tik2 thiếu,
vẫn nằm ở `D:\OneDrive\Tiktok\Tik2.xlsx` + có bản lạc `D:\Tik2.xlsx` ở root ổ D (không đụng).

## Đường dẫn CŨ cần search (patterns)
- `D:\OneDrive\Tiktok\...` (Tik1.xlsx cũ, folder `D:\OneDrive\Tiktok`)
- `D:\OneDrive\Tiktok_Reg\...`
- `D:\OneDrive\codex_gmail_debug\register gmail\gmail_clean_v2.xlsx`
- `D:\OneDrive\codex_gmail_debug\tiktok-luot nuoi acc\data\taikhoan_run_safe.xlsx`
- `D:\PROXYgandienthoai.xlsx` (root ổ D)
- `TIKTOKTaiKhoan`, `Tiktok Tài Khoản`
- filename: `Tik[123]\.xlsx`, `taikhoan_dat_v2`, `gmail_clean_v2`, `taikhoan_run_safe`, `PROXYgandienthoai`

## Kỹ thuật quét (tránh timeout)
- `search_files` tool có thể fail path D:\ (rg backend). Dùng `terminal` + `rg` trực tiếp.
- **KHÔNG rg một phát cả repo** — timeout vì thư mục history khổng lồ
  (`batch-runs/`, `stale-lock-archive/`, `runs/`, `.runtime/`, `artifacts/`, `venv*/`, `node_modules/`).
- Bước 1: `rg -l` với exclude globs để lấy danh sách file:
```bash
rg -l -i --hidden -g '!.git/**' -g '!__pycache__/**' -g '!*.pyc' -g '!node_modules/**' \
  -g '!*.md' -g '!*.jsonl' -g '!*.log' -g '!reports/**' -g '!.ai-runs/**' -g '!artifacts/**' \
  -g '!tasks/**' -g '!.hermes/**' -g '!*backup*' -g '!*.bak*' \
  -g '!batch-runs/**' -g '!stale-lock-archive/**' -g '!runs/**' -g '!.runtime/**' -g '!venv*/**' \
  '<patterns>' <repo>...
```
  Hoặc giới hạn extension code/config: `-g '*.py' -g '*.js' -g '*.mjs' -g '*.yaml' -g '*.yml' -g '*.json' -g '*.ps1' -g '*.bat' -g '*.sh'`
- Bước 2: đọc thẳng từng file trúng (read_file / rg -n trên file) — đừng scan lại cây.
- Match chỉ tên cột/log (vd `gmail_clean_v2` trong message string của google_health.py) = KHÔNG phải path, bỏ qua.

## Ma trận kết quả (7 repo, 2026-08-12)

### ĐÃ ĐÚNG kibe sẵn (không đụng)
- `Tiktok_Reg/taadaa_host.py` — hiện thân cơ chế host-config (xem dưới)
- `CodexRuntime/tiktok-video/config-machine-*.yaml` — TẤT CẢ đã trỏ kibe
- `tiktok-log-in/login_runner/cli.py`, `gan-proxy/*`, `tiktok-follow/tools/probe_mode2_launch.py`,
  `tiktok-add-bao-mat-f2a/python_runner/run_batch_live_2fa.py`, `Tiktok_Reg/scripts/restore_stt57_source.py`

### ĐÃ SỬA local (tiktok-video, máy này — repo không phải git, an toàn)
`upload-flow-smoke.yaml`, `analysis/count_tik1.mjs`, `artifact-work/goal-audit/audit_tik1.mjs`,
`artifact-work/goal-5-lowest/inspect_tik1.mjs`, `workbook-edit-tik1/inspect_tik1.mjs` + `edit_tik1.mjs`,
`sheet-baseline-20260727/read-baseline.mjs` → `D:/OneDrive/TaadaaData/kibe/Tik1.xlsx`
Baseline rollback: `D:\tmp\path-fix-baseline-20260812/` (copy tên file dùng `tr '/' '_'`).

### CÒN TRỎ ĐƯỜNG CŨ — git-shared, CHƯA sửa (cần user chốt target machine)
Vì repo dùng chung 2 máy (kibe + admin), sửa path cũ → kibe trong git-shared = admin pull về sẽ
dính path kibe → nguy cơ ghi nhầm workbook máy kibe! NGUYÊN TẮC: file shared giữ path cũ
(fail-closed) hoặc resolve qua host-config, không hardcode path máy local.

1. `automation-core/.env.local.ps1` — NGUY HIỂM NHẤT: set env override
   (`TIKTOK_REG_DATA_DIR=D:\OneDrive\Tiktok_Reg`, SOURCE/TRACKING=codex_gmail_debug,
   `PROXY_MAP=D:\PROXYgandienthoai.xlsx`). `taadaa_host.apply_env` chỉ đè
   TRACKING/SOURCE/TARGET_INVENTORY — **DATA_DIR + PROXY_MAP không bị host config đè** → stale env thắng.
2. `tiktok-log-in/scheduler.py` dòng 23-25 `DEFAULT_SAFE_WORKBOOK` = codex_gmail_debug cũ
   (+ `tests/test_cli.py:46` assert đúng path cũ đó — sửa phải kèm test).
3. `Tiktok_Reg/project_paths.py` dòng 27-32, 68 canonical fallback cũ — **GIỮ NGUYÊN**: canonical
   chỉ dùng khi thiếu host config; giữ cũ = fail-closed, không ghi nhầm sang máy khác.
4. `tiktok-follow/follow_runner/config.example.yaml` — trỏ `data/taikhoan_run_safe.xlsx` local (data/
   repo không có file này).
5. `tiktok-log-in/scripts/sync_taikhoan_run_safe.py` + `taikhoan_sync_watcher.py` — default
   `PROJECT_ROOT/data/...` (thư mục data/ repo trống → lỗi nếu chạy không env).

## Cơ chế host-config (nguồn chuẩn path per máy)
- `TAADAA_HOST_CONFIG` → `D:\Taadaa\machine-config\{kibe,admin}.yaml`
- kibe.yaml: `workbook_root: D:/OneDrive/TaadaaData/kibe`, `runtime_root: D:/Taadaa/runtime/kibe`,
  `machine_range: [1,80]`. admin.yaml tương tự cho máy B (200+).
- `taadaa_host.host_guard()` + `apply_env()`: host config THẮNG env stale với warning loud —
  ngoại lệ DATA_DIR/PROXY_MAP kể trên.
- Quét/audit path nào cũng phải phân biệt: file LOCAL máy này (sửa thẳng) vs file GIT-SHARED
  (chỉ sửa khi user chốt target machine; canonical fallback giữ cũ fail-closed).

## BỔ SUNG 2026-08-12 (buổi chiều): repo `tiktok-luot nuoi acc` bị sót trong ma trận 7 repo

Ma trận trên BỎ SÓT repo `tiktok-luot nuoi acc` (D:\Taadaa\tiktok-luot nuoi acc). Cron
`taikhoan-run-safe-sync` (Hermes job 95f8cd3f4e52, script `taikhoan_sync_cron_launcher.py`)
fail `TAIKHOAN_SYNC_SOURCE_STAT_FAILED` vì source/default vẫn trỏ đường cũ. Đã sửa 4 file
(byte-level, giữ EOL — `hermes_taikhoan_sync_cron.py` LF; `sync-safe-workbook.py`,
`run-feed-session.ps1`, `run_74machines.bat` CRLF, bat mixed 7CRLF+5LF):
`D:\OneDrive\Tiktok_Reg\taikhoan_dat_v2_updated .xlsx` và
`D:\OneDrive\codex_gmail_debug\tiktok-luot nuoi acc\data\taikhoan_run_safe.xlsx`
→ `D:\OneDrive\TaadaaData\kibe\` (cả 2 file). HANDOFF.md đã entry (CRLF giữ 51→69).

### Root cause phụ: registry đúng nhưng env process cũ THẮNG script default
`reg query HKCU\Environment` đã trỏ kibe, nhưng env của Hermes gateway (pythonw khởi động
từ trước) vẫn export `TIKTOK_TRACKING_WORKBOOK`/`TIKTOK_SAFE_WORKBOOK_ONEDRIVE` đường cũ →
`os.environ.get("VAR", default)` trả env cũ, default mới không bao giờ chạy. KHÔNG restart
gateway khi batch live → fix ngay cron launcher (file LOCAL `~/AppData/Local/hermes/scripts/`,
ngoài repo git-shared): `env = dict(os.environ); env["VAR"] = <path mới>; subprocess.run(..., env=env)`.
Verify: chạy chính launcher → lần 1 exit 0 + workbook mtime mới + state JSON
(`runtime/taikhoan-sync-state.json`) `source_sig`/`last_sync` refresh; lần 2 exit 0 + stdout
RỖNG (contract no_agent cron silent khi không đổi). Chi tiết: skill
`portable-consumer-repo-maintenance` § "Cron sync path fixes".