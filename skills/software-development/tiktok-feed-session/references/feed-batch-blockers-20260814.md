# Feed batch blockers — chẩn đoán theo layer (2026-08-13/14)

Khi `multi-machine-feed-session` skip/fail hàng loạt, chẩn đoán ĐÚNG THỨ TỰ này
(với evidence `reason:` trong `summary.txt` / batch `log.jsonl`), đừng đổ lỗi
vội cho 1 lớp:

1. **VPN down — blocker #1** (`blocked-vichanger-vpn`)
   - Log: `required Android VPN is not connected: interface=tun0 tun_up=False vpn_connected=False error=Device "tun0" does not exist.`
   - Thực tế gặp: ~46/80 máy kẹt vì VPN chưa reconnect sau reboot. Không phải
     lỗi script/lock — fail-closed đúng thiết kế (không feed qua IP trần).
   - Fix: chạy `scripts/run-proxy-all.ps1` (hoặc proxy watcher) TRƯỚC batch;
     kiểm tra `tun0` trên device.

2. **Env python** (batch chết ngay lúc import)
   - Terminal Hermes kế thừa `PYTHONPATH` trỏ Hermes venv (Py3.11) → automation
     venv (Py3.12) load nhầm PIL cp311 → `ImportError: cannot import name
     '_imaging' from 'PIL'`. Triage: chạy python với `PYTHONPATH=""` rồi
     `import PIL; print(PIL.__file__)`.
   - Fix launch: wrapper powershell `$env:PYTHONPATH=""; & <run-feed-session.ps1> ...`
     (hoặc set PYTHONPATH = repo\python_runner).
   - `run_tiktok.py` import `automation_core.escalation` — thiếu nếu cài
     automation-core < 0.4.44. Repo yêu cầu P1 wheel:
     `C:\Users\Kibe\p1-venv-wheels-20260812\automation_core-0.4.45-py3-none-any.whl`
     (file name 0.4.45, metadata 0.4.44). Fix:
     `python -m pip install --force-reinstall --no-deps <wheel>`.

3. **Stale device-lock** (`skipped-device-locked` / "device lock active")
   - Lock store: `~/.codex/device-locks/` (`machine_N.lock.json`,
     `serial_<serial>.lock.json`); `DEFAULT_LOCK_ROOT = Path.home()/".codex"/"device-locks"`.
   - Liveness: dùng `automation_core.device_lock.owner_process_alive(owner)`
     (check pid + process_started_at). KHÔNG dùng `os.kill(pid,0)` trên Windows
     (ném OSError/WinError 87). Parse `tasklist /FO CSV /NH` để lấy live pids.
   - Fix: `scripts/reap-dead-owner-locks.py` (move dead-owner lock sang
     `~/.codex/device-locks-reaped/<ts>/`, idempotent). Cron hermes
     `reap-dead-owner-locks` mỗi 30p chỉ dọn lock, KHÔNG dọn handoff.

4. **DEFERRED_LOCKED handoff-evidence gate**
   - `_prior_target_evidence()` rglob `recovery_lock_handoff.json` khắp `.ai-runs`;
     bất kỳ file nào `finish_succeeded != true` (schema
     `tiktok-consumer-lock-handoff-v1`) chặn máy đó fail-closed tới khi dọn.
   - `_verifier_success_proof` (thoát gate) cần: `finish_succeeded=true`,
     `handoff_required=false`, `final_status=success`,
     `expected_terminal_status=released`, lock released, run_manifest success,
     swipes>0.
   - Fix: `scripts/reap-stale-handoff-evidence.py` (giữ file verified-success,
     move phần còn lại sang `~/.codex/lock-evidence-reaped/<ts>/`).

5. **Batch song song = tự tranh lock** (lỗi vận hành)
   - Mỗi máy lock ghi pid của process chính; launch batch mới khi batch cũ còn
     chạy → batch cũ giữ "reservation" locks → batch mới skip hàng loạt dù
     owner pid đang chạy THẬT.
   - Rule: CẤM launch batch thứ 2 khi chưa confirm batch trước đã exit (grep
     `tasklist` cho `run_tiktok.py` / `multi-machine-feed`).
   - Batch chỉ xử lý ~34-40 máy/lần rồi "completed with failed machine(s)" —
     để phủ 80 máy: reap giữa các lần + chạy lặp, gộp kết quả theo máy.

6. **Bật lại TikTokScheduler (Windows Task)**
   - Task action bake sẵn env.path — path cũ (vd `D:\OneDrive\Tiktok_Reg\...`)
     gây lỗi sau khi dời workbook; re-register bằng `register-scheduler-task.ps1`
     (chạy `-DryRun` trước). Task "Running" ≠ worker chạy — phải check process
     `python -m scheduler` + log `runs/scheduler-task.log` (0 byte = chết).

7. **ADB server race — 2 watcher `gan_proxy_fleet watch --all` chạy song song**
   - Triệu chứng: `adb devices` liệt kê được nhưng `adb -s <serial> shell` ném
     `could not read ok from ADB Server` / `failed to start daemon` / port 5037
     `Only one usage of each socket address (10048)`; `tasklist` thấy 13 adb.exe
     zombie + 2 process gan_proxy_fleet (một từ automation venv, một từ
     Python312 khác) cùng `watch --all --workers 80`.
   - Root: 2 watcher cùng đọc mapping + cùng khởi động/kill ADB server →
     tranh chấp 5037. gan-proxy host-side KHÔNG quản lý VPN vichanger trên
     device — nó chỉ cấp proxy host; vichanger là app Android per-device phải
     tự connect.
   - Fix probe: `adb kill-server && adb start-server && adb devices` rồi mới
     ADB shell. Về lâu dài: chỉ giữ 1 instance watcher (kill bản Python312
     trùng), không bao giờ chạy `run-proxy-all.ps1`/tray trùng 2 lần.

8. **Chẩn đoán VPN vichanger per-device (phân biệt wifi/adb/app)**
   - Lỗi `blocked-vichanger-vpn` (tun0 missing) KHÔNG tự động = wifi tắt hay
     ADB hỏng. Probe 3 lớp trên cùng serial:
     - `dumpsys wifi | grep 'Wi-Fi is'` → `Wi-Fi is enabled` = wifi OK.
     - `ip addr show tun0` → `Device "tun0" does not exist` = tunnel chưa tạo.
     - `pidof vn.vichanger.app` → `NO_PROC` = app VPN không chạy trên device.
   - Bộ ba `Wi-Fi enabled + tun0 missing + vichanger NO_PROC` ⇒ app vichanger
     chưa connect (bị kill/reboot chưa auto-start/LSPosed chưa active) — KHÔNG
     phải lỗi wifi/adb. Log watcher cũ `[WIFI_NOT_READY] ... radio_on_not_connected`
     là red herring khi wifi thực tế enabled.
   - Fix: reconnect vichanger per-device (proxy watcher reconnect / bật app),
     rồi re-check tun0. Không feed qua IP trần.

9. **Artifact `device:<id>` ≠ ADB serial**
   - Batch log/summary ghi `serial: "device:06bd8c75c7"` (id ngắn) — KHÔNG phải
     ADB serial 16-hex (`988627464e374e3234`). `adb -s device:06bd8c75c7` →
     `device not found`. Phải map máy → Device ID qua workbook
     `taikhoan_run_safe.xlsx` (cột `May`/`Device ID`) trước khi probe ADB.

10. **Báo cáo cho user**
   - Kèm TÊN MÁY với từng ảnh (m8, m51...) — đừng trả ảnh không nhãn.
   - Xác nhận ảnh thực sự hiển thị trên Telegram (MEDIA có thể chỉ render
     path); fallback: báo path local để user mở trên máy kibe.
   - Không kết luận nguyên nhân khi chưa có evidence — kiểm tra layer theo thứ
     tự trên với dòng `reason:`/`final_status:` thực tế.