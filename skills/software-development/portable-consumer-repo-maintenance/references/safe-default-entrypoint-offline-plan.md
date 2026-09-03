# Safe-by-default entrypoints + offline plan mode (gan-proxy, 2026-08-12)

Session: hoàn tất cấu hình vận hành offline/read-only cho `gan-proxy` — chuyển
batch entrypoint từ live `run --all` sang read-only plan, thêm env-driven
defaults, thêm `--offline` plan mode. Không chạy live proxy assignment, không
đọc secrets/workbook values.

## Pattern: entrypoint safe-by-default, live behavior opt-in

- **Batch default = read-only plan, không live run.** `gan-proxy-all.bat` trước
  đây gọi `python scripts/gan_proxy_fleet.py run --all ...` (live proxy
  assignment lên 80 máy!). Đổi thành: mặc định `plan --offline`; chỉ chạy live
  khi user chủ động set `GAN_PROXY_MODE=run`:
  ```bat
  if /I "%GAN_PROXY_MODE%"=="run" (
    python "%~dp0scripts\gan_proxy_fleet.py" run --all %GAN_PROXY_MAPPING_FLAG% --workers 80 --runtime "D:\CodexRuntime\..."
  ) else (
    python "%~dp0scripts\gan_proxy_fleet.py" plan --offline %GAN_PROXY_MAPPING_FLAG%
  )
  ```
- **Env-driven DEFAULT_* với fallback giữ nguyên giá trị cũ** — Python và bat
  chia một nguồn sự thật, không duplicate path ở 2 chỗ:
  ```python
  DEFAULT_MAPPING = Path(os.environ.get("GAN_PROXY_MAPPING", r"D:\...\PROXYgandienthoai.xlsx"))
  DEFAULT_ADB = os.environ.get("GAN_PROXY_ADB", r"C:\...\adb.exe")
  DEFAULT_RUNTIME = Path(os.environ.get("GAN_PROXY_RUNTIME", r"D:\CodexRuntime\..."))
  ```
  Bat pass-through: `if defined GAN_PROXY_MAPPING (set "FLAG=--mapping "%GAN_PROXY_MAPPING%"") else (set "FLAG=--mapping "<default>"")`.
  Repo policy cho phép env config (README đã có sẵn `GAN_PROXY_VALUE` cho secret
  proxy) — kiểm tra precedent này trước khi thêm env vars.
- **`--offline` flag cho plan mode**: plan mặc định vẫn gọi `is_online()` (ADB
  probe) từng máy — không phải "offline" thật. Thêm flag để plan chỉ parse
  mapping, in `state=mapped` thay vì online/offline. Parser/help/plan chạy được
  hoàn toàn không cần ADB.
- Script phụ (vd `reboot_proxy_provider.py`) import `DEFAULT_*` từ module chính
  → env override tự đồng bộ, không cần sửa. Kiểm tra điều này trước khi thêm
  env vào từng file.

## Pitfall: KHÔNG BAO GIỜ execute nhánh live trong test

Test regression cho bat đã chạy thật nhánh `GAN_PROXY_MODE=run` để assert nó
fail-closed — kết quả: **tạo 4 device lock files** (`~/.codex/device-locks/`
machine_1/machine_2/serial_serial-1/serial_serial-2 — serial giả) **+ 2 runtime
reports** (`D:\CodexRuntime\...\fleet-run-*.json`) vì fleet `run` acquire lock
trước cả khi ADB fail. Dù serial giả, đây là side-effect ngoài scope.

- **Verify nhánh live bằng static check, không execute**: đọc text file và
  assert chuỗi (`'GAN_PROXY_MODE' in text`, `"run --all" in text`,
  `"plan --offline" in text`, path mapping/runtime hiện diện). Assert nhánh
  plan (read-only) bằng subprocess thật thì OK.
- **Nếu lỡ tạo lock/report test**: xác minh ownership TRƯỚC khi xoá — serial
  giả, `project` khớp script đang test, pid đã chết, mapping path trỏ vào
  pytest tmp. Chỉ xoá file thoả tất cả điều kiện; không xoá lock thật của
  người khác.
- Hệ quả phụ: fleet `run` trả exit 0 khi mọi máy `SKIPPED_DEVICE_LOCKED` (chỉ
  FAILED/FINAL_BLOCKED/NO_HANDLER_IMPLEMENTED tính là fail) — đừng assert
  exit != 0 cho nhánh run trong test.

## Pitfall: MSYS `/tmp` path không tồn tại với Windows subprocess

`mktemp -d` trong git-bash cho `/tmp/tmp.XXX` (MSYS virtual). Truyền path này
cho `cmd.exe`/`python.exe` subprocess → `FileNotFoundError` (`\tmp\tmp.XXX`).
Khi spawn Windows subprocess cần file tạm, dùng Python
`tempfile.mkdtemp(prefix=...)` để có path Windows-native
(`C:\Users\...\AppData\Local\Temp\...`). MSYS path chỉ dùng được trong shell
nội bộ.

## Pitfall: ad-hoc verifier harness — tách helper "chạy script" vs "python -m/-c"

Harness có `run(args)` prepend script path (`[PYTHON, str(FLEET), *args]`) →
mọi call đều thành `python fleet.py ...`. Hai call không phải lệnh CLI (kiểm
tra `-m py_compile` và `-c "import ..."` probe) bị lỗi
`invalid choice: 'py_compile'`. Sửa: hai helper riêng — `run(args)` cho CLI
(script + subcommand), `run_py(args)` cho `-m`/`-c`. Chẩn đoán lỗi harness
trước khi nghi ngờ code bị sửa (khớp với quy tắc chung trong SKILL.md).

## Ghi chú môi trường

- `pytest tests/` chạy bằng interpreter `D:\Taadaa\python-envs\automation`,
  terminal python mặc định là hermes venv (`C:\Users\Kibe\AppData\Local\hermes\
  hermes-agent\venv`). Subprocess test kế thừa interpreter của pytest — để yên,
  đừng ép sys.executable.
- `python -m py_compile` (không phải `python -m compileall`) cho từng script là
  check nhanh nhất sau mỗi patch.
- `git diff --check` trước khi báo xong.
- Read-only evidence cuối: `plan --offline` in `mapped_machines=76` +
  `state=mapped`, không lock mới trong `~/.codex/device-locks/`, không
  `fleet-run-*`/`machine-launch-*` mới trong runtime dir.
