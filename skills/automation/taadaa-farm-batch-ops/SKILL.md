---
name: taadaa-farm-batch-ops
description: "Re-run / resume farm batch jobs (TikTok upload, Tik3 render, reg, nuoi acc) using canonical commands."
version: 1.0.0
author: Hermes Agent
tags: [tiktok, farm, batch, render, upload, resume, kibe]
---

# Taadaa Farm Batch Ops

> 📌 **Tài liệu tham khảo & Tools chuyên sâu**:
> - `references/diagnosing-download-stopped-status.md`: Downloader tự dừng.
> - `references/workbook-sync-lock-and-mass-missing-id-diagnosis.md`: Sync lock.
> - `references/tiktok-farm-tracker-rescan-and-nonlive-diagnosis.md`: Rescan LIVE.
> - `references/cron-reports-and-tracker-triage.md`: Cron triage.
> - `references/avatar-batch-watchdog-reporting-and-rescan.md`: Avatar watchdog.
> - `references/video-sourcing-gaixinh-two-tier-allocation.md`: Gái Xinh.
> - `references/gaixinh-pipeline-cookies-and-admin-remote-ops.md`: Admin batch.
> - `references/video-farm-standard-45-clips-and-supplementary-pipeline.md`: Chuẩn 45.
> - `references/dual-cluster-post-reboot-recovery-and-single-worker-render.md`: Reboot.
> - `references/dual-cluster-downloader-concurrency-and-proxy-hygiene.md`: Downloader & proxy.
> - `references/admin-render-cross-mapping-realignment.md`: Mapping 8 Tik.
> - `references/cross-machine-dedup-and-pet-sourcing.md`: Chống đụng hàng Kibe vs Admin.
> - `scripts/verify_gaixinh_sourcing.py`: Probe kiểm tra claims dedup & ViT/leftover.
> - `references/tiktok-dashboard-prev-day-delta-baseline.md`: Delta dashboard.


## 🎬 BATCH DOWNLOAD TIKTOK VIDEO / NGUỒN SHORT THEO NICHE (2026-09-16)

### Chạy batch download video ngắn theo niche:
- Lệnh chuẩn: `python download_by_niche.py` script sẽ kích hoạt `auto_discover_niche_source`:
  1. Tự động truy vấn YouTube Shorts (`ytsearch15:{niche.label} shorts việt nam` và `ytsearch10:{niche.label} shorts`).
  2. Lọc bỏ các kênh đã claim hoặc đã tồn tại trong sources. Bắt ngoại lệ logging chi tiết: `except Exception as ex: print(f"AUTO_DISCOVER_SEARCH_WARN query={q}: {ex}", flush=True)`.
  3. Probe và kiểm định gate ngôn ngữ/tiêu chuẩn video tối thiểu (`min_videos`).
  4. Nếu qualify, thực hiện claim ledger và lưu persistence:
     - **Thread safety & Thứ tự Persistence transactional**: Toàn bộ khâu kiểm tra ledger, ghi disk, claim và mutate memory PHẢI nằm trong `with _DB_LOCK:`. Thứ tự chuẩn bắt buộc:
       1. Check trùng `sources` in-memory và `claimed_keys` ledger.
       2. Ghi file `sources.json` trước bằng atomic file replacement (`tmp_path` + `os.replace`). Ghi kèm `video_urls=[c.url for c in valid_candidates]` và `uploader=uploader or ""`. Nếu ghi lỗi thì `continue` ngay, không claim và không mutate memory.
       3. Chỉ claim global ledger (`claim_source`) sau khi file `sources.json` đã lưu thành công trên đĩa.
       4. Mutate `sources.append(temp_source)` với `video_urls` và insert candidate vào `state.db`.
     - **Chống race condition Global Ledger**: Truyền `folder_num: int` vào `auto_discover_niche_source(folder_num: int, niche: Niche, ...)`. Gọi `claim_source(args.global_ledger_dir, machine_id, ch_url, folder_num)` trong `with _DB_LOCK:`. Nếu claim thất bại (worker khác đã claim) -> bỏ qua kênh đó.
     - **Atomic File Write chống data corruption**: CẤM dùng `open(..., "r+")` kèm `seek(0)` và `truncate()`. BẮT BUỘC dùng temporary file + `os.replace`:
       ```python
       tmp_path = sources_file.with_suffix(f".tmp.{os.getpid()}.{time.time_ns()}")
       with open(tmp_path, "w", encoding="utf-8") as tf:
           json.dump(raw_sources, tf, ensure_ascii=False, indent=2)
       os.replace(tmp_path, sources_file)
       ```
     - **Bất biến bộ nhớ**: CHỈ append vào `sources` và memory SAU KHI ghi file disk và claim ledger thành công!
  5. Cập nhật vị trí gọi tại `run_folder`:
     `discovered_source, discovered_candidates = auto_discover_niche_source(folder_num, niche, args, sources, exclusions, verified)`

### ⚠️ BẤT BIẾN CHỐNG TRỘN KÊNH & QUY TẮC BÁO CÁO (User: "K lẽ thành 1 folder chứa nguồn 2 kênh cùng niche à"):
- **1 folder = 1 kênh DUY NHẤT 100%**: Tuyệt đối không bao giờ tải video từ 2 kênh khác nhau vào cùng 1 folder, kể cả khi 2 kênh có cùng chủ đề (niche).
- **Phân loại khi xử lý folder thiếu (`insufficient_pool`)**:
  1. **Folder dở dang ($\ge 1$ video trên đĩa / DB)**: KHÔNG ĐƯỢC gán kênh mới! Phục hồi các candidate bị fail do mạng/proxy về `discovered` để kéo nốt từ CHÍNH KÊNH CŨ:
     ```sql
     UPDATE videos SET status='discovered', rejection_reason=NULL WHERE folder IN (...) AND status='failed' AND rejection_reason='download_no_media';
     UPDATE folders SET status='pending' WHERE folder_num IN (...);
     ```
  2. **Folder trống (0 video)**: Chỉ nhóm này mới được nhận kênh mới toanh từ Auto-Discovery.
  3. **Báo cáo User**: Luôn giải thích rõ ràng tách bạch giữa 2 nhóm, khẳng định trước: "Folder dở dang giữ 100% kênh cũ, chỉ folder trống 0 video mới gán kênh mới" để tránh user hiểu lầm là gộp 2 kênh vào 1 folder. database state để tiếp tục download ngay lập tức mà không cần can thiệp thủ công.
1. **DB State Location**:
   - Ưu tiên `C:/CodexRuntime/tiktok-video/state.db` (nếu không có thì `D:/CodexRuntime/tiktok-video/state.db`).
   - Query kiểm tra folder thiếu video / cần nguồn:
     `SELECT folder_num, niche FROM folders WHERE status IN ('pending', 'insufficient_pool') AND (video_count < 30 OR video_count IS NULL)`
2. **Cào bổ sung nguồn qualify (`scripts/fast_targeted_qualify_stream.py`)**:
   - Chạy với python venv: `D:/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe scripts/fast_targeted_qualify_stream.py` từ cwd `D:/Taadaa/Tiktok-video`.
   - Stream kết quả trực tiếp vào `D:/OneDrive/SharedData/tiktok-video/sources.qualified30.json`.
3. **Reset trạng thái folder thiếu trong SQLite**:
   - `UPDATE folders SET status = 'pending', source_channel = NULL WHERE status = 'insufficient_pool';`
4. **Launcher `run_download_kibe.py`**:
   - Sử dụng proxy pool direct: `proxy_pool_67_direct.txt`.
   - Cần có cờ `--all-languages`.
   - Chạy ngầm launcher:
     `D:/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe D:/Taadaa/Tiktok-video/run_download_kibe.py`
   - Kiểm tra log tại `D:/CodexRuntime/tiktok-video/download_run.log`.

## 🛑 STOP GATE (bắt buộc — chi tiết: skill taadaa-farm-ops-rules)
Máy live + script chạy/lỗi → KHÔNG tự sửa code, KHÔNG tự chạy lại, KHÔNG tự probe/tay khi chưa được user yêu cầu.
Lỗi → screencap → gửi ẢNH THẬT (MEDIA:<path> dòng riêng, KHÔNG bọc markdown, KHÔNG gửi đường dẫn text) → DỪng chờ user hướng dẫn.
User hướng dẫn bước nào → encode bước đó vào script + test → mới chạy lại. Nghi ngờ → HỎI.

## ⚡ QUY TRÌNH CHẨN ĐOÁN O(1) KHI USER BÁO "ĐĂNG VIDEO LỖI" / MASS-FAIL (2026-09-16)
Khi user báo "đăng video lỗi lắm" / nghi ngờ batch upload hỏng diện rộng:
1. **Kiểm tra batch gần nhất vs ca hiện tại:** Đọc `D:/CodexRuntime/tiktok-video/batch-runs/` và `runs/run_*` mới nhất theo mốc thời gian (không quét đĩa rộng).
2. **Kiểm tra nguyên nhân ADB offline diện rộng (USB Hub drop):** Nếu log báo `[DEVICE_OFFLINE] CONNECT_DEVICE: Device ... không online. Devices: [...]` chỉ còn <= 10 máy online -> Đây là sự cố phần cứng/Hub USB ngắt kết nối diện rộng, KHÔNG phải lỗi script hay UI TikTok. Chạy `adb devices` xác nhận lại số lượng máy online hiện tại trước khi phán đoán.
3. **Phân biệt Batch Render vs Batch Upload:**
   - Thư mục dạng `slot*-f*` chứa `run_meta.json` và log `0000X_Y.log` là **Batch Render video ffmpeg**, không phải batch upload.
   - Thư mục dạng `batch_tik*` hoặc `run_*` chứa `report.json` mới là **Batch Upload TikTok**.
4. **Phân loại 4 nhóm lỗi kinh điển trên các máy sót lại (khi batch đạt >90% success):**
   - `ACCOUNT_MISSING`: Session TikTok trên máy bị văng / danh sách account switcher không thấy nick mục tiêu -> Cần login / restore session.
   - `ACCOUNT_VERIFY_MISMATCH`: Switch vào nick nhưng profile UI không trùng username trong Excel -> Cần kiểm tra lại profile / logout nick ký sinh.
   - `ADB command timeout`: Máy bị treo kernel/dumpsys power/screencap -> Cần soft reboot máy.
   - `Proxy watcher timeout`: Sau reboot, proxy watcher chưa kịp cấp readiness -> Cần kiểm tra kết nối proxy/gan-proxy.


**QUY TẮC PHÁT FARM ALERT & GIỮ NGUYÊN ẢNH BANNER ĐỎ SỐ MÁY (2026-09-05):**
- **Ảnh hiện trường kèm Banner Đỏ:** BẮT BUỘC giữ nguyên 100% thiết kế ảnh có banner đỏ số máy (`[MAY <N>] - HH:MM:SS DD/MM`).
- **Trần 1,024 ký tự của Telegram API:** Telegram `sendPhoto` chỉ nhận caption tối đa **1,024 ký tự**. Khi nội dung 5 bước recovery + lệnh canary dài vượt trần, **CẤM TUYỆT ĐỐI bỏ ảnh chuyển sang text thuần**. BẮT BUỘC tách thành 2 tin nhắn:
  1. *Tin nhắn 1 (Ảnh)*: Ảnh có banner đỏ kèm tóm tắt ngắn (`summary_caption`) $\le 1024$ ký tự (đóng thẻ HTML an toàn bằng `_safe_truncate_html`).
  2. *Tin nhắn 2 (Text)*: Gửi tiếp văn bản chi tiết đầy đủ 5 bước recovery và lệnh Canary ngay bên dưới.
- **Fail-closed Alert Claim (Chống nuốt lỗi mạng):** Hàm `send_farm_machine_alert` PHẢI trả về `False` khi lỗi mạng HTTP/DNS/timeout và tự động xóa file `.claimed` tạm, cho phép tick kế tiếp retry gửi lại khi có mạng. TUYỆT ĐỐI CẤM return `True` giả mạo làm claim vĩnh viễn và mất alert.
- **Bổ sung `send_farm_script_alert`:** Đối với các lỗi batch/pipeline cấp script tổng (chuỗi đêm Reg Gmail/TikTok, dọn cache, checklive), gọi `send_farm_script_alert` bắn về Farm Alerts (`-5373649734`) kèm file flow, file log và lệnh Canary.
- **BẮT BUỘC BÁO CHÍNH XÁC NGUYÊN NHÂN LỖI TRONG FARM ALERT (CẤM GHI CHUNG CHUNG `upload_subprocess_nonzero`):**
  Khi subprocess upload/follow/batch kết thúc với `returncode != 0`, CẤM TUYỆT ĐỐI gán nhãn tĩnh/chung chung như `upload_subprocess_nonzero` làm mất thông tin hiện trường khiến user không biết máy bị lỗi gì. BẮT BUỘC trích xuất nguyên nhân thực tế từ `report.json` (ưu tiên `[last_state] error/reason`), hoặc dòng lỗi cuối từ `stderr` / exception traceback, hoặc `stdout` `[ERROR]`. Đồng thời BẮT BUỘC `html.escape` mọi biến động trước khi nhét vào template HTML Telegram để chống vỡ thẻ khi gặp `<redacted>`, `<module>` hoặc cú pháp HTML. Chi tiết: `references/upload-hook-exact-error-extraction-and-html-escape-20260905.md`.

Re-running or resuming a farm batch job on the kibe/admin farm (Tiktok-video, Tiktok_Reg, tiktok-luot nuoi acc repos).

## When to use
- User says "chạy tiếp", "resume", "y như bữa", "chạy lại cho tik3/tik2", or asks to continue a render/upload/reg batch that was run before.
- After a machine reset / crash interrupted a long batch and you must pick it back up.

## Core rule (from user, non-negotiable)
**Run the EXACT command that worked before. Do NOT substitute a different script or entrypoint.** If the prior success used `run_tik3_random_render.ps1`, use that — do NOT call `tik3_multi_batch.py` or any other module even if it looks equivalent. Different entrypoints read different config/mapping and fail.

**NGUỒN DỮ LIỆU TAIKHOAN_RUN_SAFE & CẤM TỰ CHẾ MANIFEST (User chốt 2026-09-03):**
- Mọi script vận hành farm (nuôi acc, avatar, follow, upload) BẮT BUỘC dùng `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx` làm nguồn dữ liệu tài khoản chính thống (Slot 1..6 theo ca).
- **CẤM TUYỆT ĐỐI tự chế hoặc bắt buộc dùng các file manifest trung gian** (`assignment-manifest-*.json`).
- Khi chạy batch, đọc trực tiếp ADB online devices để tự động loại bỏ các máy offline (chỉ chạy trên danh sách máy Online có tài khoản hợp lệ). Chi tiết: `references/taikhoan-run-safe-as-single-source-of-truth-20260903.md`.



UPDATE 2026-08-16: `tik3_multi_batch.py` WAS fixed in-repo (find_headers now falls back

to the `Folder Video` column when no `sttvideo` column exists), so it IS a valid

entrypoint for Tik3 render now — but only when launched with the proven flag set:

`--min-videos 45 --parallel 1 --allow-existing-output --resume-complete --execute`

(start-output/start-source from the workbook row). See `references/tik3-render-avatar-20260816.md`.



This is the same as the standing farm rule: reuse the canonical script; never write a new runner. If the canonical script lacks support, FIX+TEST that script — don't replace it.

## Steps
1. `session_search` for the exact prior command (query the launcher name + flags, e.g. `run_tik3_random_render StartMachine AutoRun`). Copy it verbatim — including `-Parallel`, `-Slot`, `-AutoRun`, working dir.
2. To RESUME (continue partial work, not restart): add ONLY flags that already exist in the original launcher (e.g. `-ResumeVerifyExisting`, `-OnlyExistingOutput`). Do not add new logic or a different script.
3. Launch as background process (`terminal` background=true, notify_on_complete=true).
4. Poll the first ~20s of log to confirm resume behavior (see Pitfalls).



## Pitfalls
- **Never delete rendered output files. EVER.** batch_render.py auto-skips outputs that already exist (`skipped: N.mp4 ... output da ton tai`). If a folder has 40/45 files, RE-RUN the render — it skips the 40 and renders only the missing 5. Deleting the 40 to "start clean" forces re-rendering from scratch. The only safe partial-render flags are `--allow-existing-output --resume-complete`.
- **Don't restart from scratch.** "Running the launcher again" is usually a RESUME: canonical launchers auto-skip existing valid outputs. Verify by reading the log — lines like `skipped: 3.mp4 -> 3.mp4 (output da ton tai)` or `(output da duoc ffprobe xac nhan)` mean safe resume, NOT overwrite.
- **Don't kill a process that is resuming.** If you launched without `-ResumeVerifyExisting` and the log shows "skipped" lines, it is already resuming correctly — do NOT kill it thinking it overwrites.
- **Don't invent entrypoints.** Run the canonical command that worked before.

- **Never delegate a farm batch to a subagent while the canonical launcher is the owner.**

  Delegating "resume Tik3" to a background subagent spawned a second runner that wrote to

  the SAME output folders in parallel (found via `Get-CimInstance` — two `local_tik3_safe_*`

  python chains + the launcher, three pipelines at once). One canonical launcher owns the

  batch; everything else must be killed or never started. If a subagent was already

  dispatched, kill its process tree (`Stop-Process -Id <pid> -Force`, verify 0 remain)

  before resuming the canonical run.

- **Exit 127 on a launcher is NOT proof of a fixed machine/source bug.** A Tik3 launcher

  died at "RUN machine 27" twice; the same machine then resumed fine on the next launch.

  Check whether the process was externally terminated (user reset / kill / parallel-run

  interference) before assuming a deterministic failure. Re-run the SAME resume command and

  watch the log; if it passes the previously-fatal machine, it was transient, not a bug.

- **Reading launcher logs: they may be UTF-16.** `tail` of `launcher.log` can show `\u0000`

  between every char (e.g. `P\u0000L\u0000A\u0000N\u0000`). Decode as UTF-16, not ASCII/UTF-8.

- **Querying processes from git-bash:** inline `powershell.exe -Command "Get-CimInstance ...

  | Where-Object { $_.CommandLine -match ... }"` breaks — bash eats `$_`. Write the query to

  a temp `.ps1` file and run `powershell.exe -File`, or use `Get-CimInstance -Filter`.

- **Find the command before acting.** Never guess the launcher/flags. `session_search` first.

### Download-recovery communication and duplicate-process guard

- A delayed platform notification about an earlier background session is historical context, not proof that the current downloader just failed. Check the notification's session ID/command and the live process/state before reacting.
- If the user says the downloader is already running normally, do not send a manual progress/error update or restart it. The hourly watchdog is separate; leave it alone unless the user explicitly asks to change its schedule or delivery.
- Before launching recovery, detect the exact production command. If a downloader already exists, keep it and do not start a second copy. If an agent accidentally launches the wrong entrypoint (for example an upload workflow while intending a download recovery), stop only that mistaken process tree immediately, verify it is gone, and then use the canonical `download_by_niche.py` command.
- After a reset, `state.db` may show `reserved`/`downloading` rows even when the process is gone. Use the downloader's normal interrupted-state recovery; do not blindly delete rows, reset the whole database, or rewrite completed folders.
- Verify recovery with three independent signals: an exact real downloader PID (not a shell or a diagnostic command containing the script name), state transitions, and fresh `.mp4`/`.part.mp4` activity or a new report. Do not claim completion from a wrapper exit code alone.
- Keep user-facing updates silent during a healthy long run. Report only a verified final completion or an actionable fatal condition; avoid narrating stale 403s, source skips, or intermediate reservation changes.



## Tik3 / Tik4 render + avatar — user sequencing rules (2026-08-16, cập nhật 2026-08-19)

- **Order:** (1) finish creating NEW avatars for all Tik3/Tik4 folders FIRST, (2) THEN run render, (3) THEN in parallel: continue render + avatar the remaining source folders.
  Don't start render before avatars are done just because a process "could" run alongside.

- **Worker count: render with `--parallel 1` (worker 1).** Explicit user instruction
  ("Render video chạy work 1 thôi"). Slower but the standing choice.

- **min-videos = 45 (NOT 50) cho RENDER Tik3.** User: "Min 45 thôi t chưa bh set min 50". Với Tik4, ngưỡng min-videos của selector là 30 và target 45 (theo chuẩn pool 30).

- **Tik4 Render Launcher (2026-08-19, cập nhật 2026-08-21):** 
  - **BẮT BUỘC dùng launcher:** `powershell.exe -File run_tik4_random_render.ps1 -StartMachine <X> -EndMachine <Y> -AutoRun -Parallel 1` (đọc `D:\OneDrive\TaadaaData\kibe\Tik4.xlsx`, source dải 241..320, output dải `4, 12, 20... 636`). User yêu cầu render chạy **1 worker** (`-Parallel 1`).
  - ⚠️ **CẤM chạy trực tiếp `tik3_multi_batch.py --workbook tik4.xlsx --source-map-workbook tik3.xlsx`**: Script cũ bị mapping nhầm công thức `source 161..240` (gặp folder 164 thiếu video sẽ crash exit code 2). Luôn dùng `run_tik4_random_render.ps1`.
  - ⚠️ **Pitfall `$selectorCode` ném exception khi source thiếu video (< 30 mp4)**: Nếu một source chưa tải đủ 30 video, `select_videos()` sẽ ném lỗi. Do `$ErrorActionPreference = "Stop"`, PowerShell sẽ dừng cả batch. Phải bọc `$ErrorActionPreference = "Continue"` quanh dòng gọi `$selectorCode`, kiểm tra `$selectExit -ne 0` để in warning và `continue` sang máy tiếp theo mà không làm crash cả batch.

- **Standalone Avatar Upload Launcher (`run_tiktok_upload_avatar.ps1`):**
  - Khởi chạy tải riêng Avatar theo TikN: `echo 'RUN' | powershell.exe -File run_tiktok_upload_avatar.ps1 -Tik <N> -AssignmentManifest <path> -WorkerId <id> -ForceAvatarMachineList "<machines>" -MaxParallel 40 -HostConfigPath "D:\Taadaa\machine-config\kibe.yaml"`.
  - Có thể chạy trực tiếp qua batch runner: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\Taadaa\Tiktok-video\run_tiktok_upload_batch.ps1" -Tik <N> -AvatarOnly -ForceAvatarMachineList "<machines>" -AssignmentManifest <path> -WorkerId <id> -MaxParallel 40`.
  - ⚠️ **Lỗi ParameterArgumentTransformationError trên `AvatarOnly` khi gọi qua `run_tiktok_upload_avatar.ps1`**:
    `run_tiktok_upload_avatar.ps1` gọi `& powershell.exe -File $batchLauncher @splat` với `$splat['AvatarOnly'] = $true`. Khi PowerShell chuyển `@splat` cho process ngoài qua `-File`, `$true` bị serialize thành chuỗi `"True"`, gây crash: `Cannot convert value "System.String" to type "System.Management.Automation.SwitchParameter"`.
    **Lệnh chuẩn chạy an toàn (dùng `-Command` và switch `-AvatarOnly`):**
    ```powershell
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "& 'D:\Taadaa\Tiktok-video\run_tiktok_upload_batch.ps1' -Tik <N> -AvatarOnly -ForceAvatarMachineList '<machines>' -MaxParallel <P> -HostConfigPath 'D:\Taadaa\machine-config\kibe.yaml'"
    ```
  - ⚠️ **Worker Concurrency (MaxParallel = 30 - User chốt cập nhật 13/09/2026)**:
    - Khi chạy watchdog tự động up avatar ca tối (`post_evening_avatar_watchdog.py`), **BẮT BUỘC đặt `-MaxParallel 30`** (mức cân bằng tối ưu giữa tốc độ và tải ADB/socket).
    - CẤM để 20 workers vì quá chậm, nhưng không đẩy quá 30 trên watchdog nền để tránh quá tải socket uiautomator khi farm vừa hết ca.
  - ⚠️ **Kỷ luật Báo cáo Watchdog Avatar (User chốt 13/09/2026: "Chỉ báo cáo 1 lần khi xong hết toàn bộ ca hoặc hết giờ")**:
    - **CẤM spam báo cáo sau từng đợt cuốn chiếu nhỏ lẻ**: Khi một batch đơn lẻ của 1 Tik chạy xong mà vẫn còn Tik khác chưa xong hoặc đang retry, script watchdog PHẢI IM LẶNG hoàn toàn (`state["running_batch"] = None`), tiếp tục kích hoạt Tik tiếp theo trong nền mà không gửi bất kỳ tin Telegram nào.
    - **CHỈ BÁO CÁO 1 LẦN DUY NHẤT** khi:
      1. Đã hoàn tất 100% toàn bộ các Tik mục tiêu (Tik 5, 6, 7, 8, 3, 4 - 0 máy tồn).
      2. HOẶC khi hết hẳn khung giờ ca tối (sau 23:30 đến trước 04:00 sáng), bắn DUY NHẤT 1 tin tổng kết chốt ca (gồm chi tiết số máy tồn theo từng Tik). CẤM gửi tin nhắn mỗi 40 phút sau mỗi batch lẻ.
  - ⚠️ **Ánh xạ Row và Tik Workbook (Phân bổ Ca Chẵn/Lẻ & Watchdog Avatar cuối ngày)**:
    - **Ngày Lẻ (Lane B)**: Ca 1 = Row 1 (`Tik1.xlsx`), Ca 2 = Row 3 (`Tik3.xlsx`), Ca 3 = Row 5 (`Tik5.xlsx`), Ca 4 = Row 7 (`Tik7.xlsx`).
    - **Ngày Chẵn (Lane A)**: Ca 1 = Row 2 (`Tik2.xlsx`), Ca 2 = Row 4 (`Tik4.xlsx`), Ca 3 = Row 6 (`Tik6.xlsx`), Ca 4 = Row 8 (`Tik8.xlsx`).
    - **Cấu trúc (chốt 09/09)**: 4 ca × 2 phiên/ca. Mốc giờ: Ca 1 06:00, Ca 2 12:00, Ca 3 18:00, Ca 4 00:00. Phiên 2 là phiên cuối ca (kích hoạt hook Đăng Video). Phiên nghỉ giữa 2 phiên: pair_gap 35-60 phút tự nhiên theo từng máy.
    - **8 acc/máy max**: Chẵn Slot 1-4 (Row 2,4,6,8), Lẻ Slot 5-8 (Row 1,3,5,7). Trước đây 6 acc/máy (Row 1-6, 3 ca × 3 phiên).
    - **Watchdog Up Avatar Cuối Ngày (Row 7 & Row 8)**: Kích hoạt sau Phiên 2 Ca 4 (khung 01:15 - 03:00) khi feed runner đã dừng hẳn (`is_feed_runner_active() == False`). Bắt buộc kết thúc trước 03:30 để không tranh chấp với chuỗi Reg ban đêm (`night-chain-reg-pipeline` lúc 01:00). **Lưu ý (cũ: Row 5 & Row 6 sau Ca 3; được cập nhật 09/09 theo kiến trúc 4 ca × 8 row)**.
    - **Idempotency Ledger ("Mỗi row nick 1 lần")**: Lưu lịch sử tại `avatar_upload_history.json`, chỉ bốc máy chưa có trạng thái `success` nạp vào `-ForceAvatarMachineList`. Nếu toàn bộ nick của Row đã hoàn tất avatar thì im lặng không chạy batch thừa.
  - ⚠️ **Pitfall Profile Grid Scroll & Edit Profile Button (Cập nhật 2026-09-01)**:
  - ⚠️ **Pitfall Photo Picker & Crop Surface Controls (Cập nhật 2026-09-02)**:
    - Trong picker ảnh: Nút "Tiếp" ngoài `o_9`, `wrj` còn có thể dùng resource-id `xip` ở góc dưới phải.
    - Trên màn hình Cắt (`Cắt` / Crop): Bắt buộc bỏ tick checkbox "Đăng ảnh này lên Nhật ký" (`[48,1554][120,1626]` hoặc `id/sca`) trước khi lưu để tránh post nhầm story; nút "Lưu" / "Lưu và đăng" nằm tại `bounds=[552,1728][1032,1860]` hoặc `[96,1698][984,1830]`.
  - ⚠️ **Tự động Up Avatar khi đăng Video lần đầu (Video #1, cập nhật 2026-08-30)**: Khi tài khoản chưa đăng video nào (`Video Đã Đăng == 0` -> đăng Video #1 lần đầu tiên), workflow `ENSURE_AVATAR` trong `Tiktok-video` (`state_machine.py`) **tự động kích hoạt tải Avatar** từ `avatar.jpg`/`avatar.png` trong folder video lên Profile TikTok mà không cần cấu hình `-ForceAvatarMachineList`. Từ video #2 trở đi, workflow tự động skip nếu avatar đã `PRESENT`.
  - ⚠️ **Quy tắc dọn dẹp sau Up Avatar (2026-08-21)**: Khi hoàn thành tải và xác nhận avatar thành công trên UI, script BẮT BUỘC tự động `am force-stop com.zhiliaoapp.musically; am force-stop com.ss.android.ugc.trill` và đưa máy về màn hình chính (`input keyevent 3`) để giải phóng tài nguyên.
  - ⚠️ **Pitfall AssignmentManifest schema**: `AssignmentManifest.load()` yêu cầu bắt buộc các trường: `schema_version: 1`, `assignment_id: "..."`, `owner_id: "..."`, `resources: ["machine:X"]`, `reviewed_at: "<ISO timestamp>"`. Thiếu `assignment_id` hay `reviewed_at` sẽ raise `AssignmentError: ASSIGNMENT_MANIFEST_INVALID`.
  - ⚠️ **Pitfall MediaStore & Screen Cleaner**: Luôn xóa sạch file ảnh screenshot rác (`/sdcard/_ss.png`, `_ss_social.png`) trước khi mở picker TikTok; kiểm tra `D:\video goc\<Folder Video>\avatar.jpg` đã tồn tại (copy từ `D:\TIKTOK-videonuoinick\<Folder Video>\avatar.jpg` nếu thiếu) trước khi chạy launcher.

- **TikTok Video Upload CLI Entrypoint, VPN Gate & Canonical Batch Runner (2026-08-23, cập nhật 2026-08-31):**
  - ⚠️ **Canonical Batch Upload Launcher (Không có prompt RUN tương tác, MaxParallel mặc định = 20):** Khi kích hoạt batch upload toàn farm (hoặc theo ca/Tik), BẮT BUỘC dùng canonical PowerShell launcher (chạy thẳng không chặn prompt):
    ```powershell
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\Taadaa\Tiktok-video\run_tiktok_upload_batch.ps1" -Tik <N> -MaxParallel 20
    ```
    Launcher tự động quản lý parallel (mặc định `-MaxParallel 20`), stagger ngẫu nhiên 2000-8000ms, kiểm tra inventory/mapping, load host config `kibe.yaml`, và pipe confirmation token chuẩn cho các tiến trình con. Tuyệt đối không tự chế thêm lệnh prompt `Read-Host` / yêu cầu nhập RUN vào script.
  - ⚠️ **Định tuyến Router Proxy Wi-Fi & Bỏ VPN Gate (`require_android_vpn`):** Farm đã chuyển toàn bộ sang hệ thống Router Proxy Wi-Fi (`wlan0`), không còn sử dụng ViChanger hay interface `tun0` trên từng điện thoại. Các gate kiểm tra VPN `require_android_vpn` ở `RESOLVE_DEVICE`, `run_post.py` và preflight đã được gỡ bỏ hoàn toàn; worker chạy thẳng qua mạng Wi-Fi của router proxy mà không bị chặn fail-closed bởi ViChanger.
  - ⚠️ **Module Entrypoint & Non-interactive TTY Bypass (Commit `889a024` & EOFError Guard):** Khi gọi CLI trực tiếp `python -m scripts.tiktok_workflow --config ... --workflow-workbook ... --machine <N> --no-dry-run`, `run_post.py` được bọc `try/except (EOFError, OSError)` khi đọc `input("> ")` để tự động fallback `confirmation = "YES"` trong môi trường subprocess/pipe. Không để tiến trình kẹt stdin hoặc crash `EOFError`.
  - ⚠️ **Single-Device Canary Test & Báo Cáo Chuẩn B5 (2026-09-06):** Khi chạy Canary test đăng video cho 1 máy cụ thể (sau fix/recovery), BẮT BUỘC dùng `env -u PYTHONPATH python -m scripts.tiktok_workflow --config ... --workflow-workbook ... --single-device <serial> --video-number <N> --no-dry-run`, dọn stale lock trước khi chạy, lưu ý thời lượng thực tế từ 12-15 phút (vượt trần 600s terminal; khi terminal timeout shell ngắt nhưng tiến trình `python.exe` vẫn chạy ngầm trong Windows, bắt buộc dùng PowerShell `WaitForExit` hoặc check PID, cấm chạy đè lệnh mới), đọc `report.json` và báo cáo chuẩn B5: Status, Account, Video Number, Last State, Post Verified, Exit Code. Chi tiết: `references/canary-single-device-tiktok-video-and-b5-standard-20260906.md`.
  - ⚠️ **Xử lý Media Fingerprint Ledger bị kẹt `reserved` (`MEDIA_FINGERPRINT_PENDING`):** Khi một lần chạy upload bị ngắt quãng giữa chừng sau khi đã push video, file hash trong `D:\CodexRuntime\tiktok-video\idempotency\media-fingerprints\<hash>.json` có thể bị kẹt ở trạng thái `"status": "reserved"`, khiến các lần chạy sau bị dừng ở checkpoint `MANUAL_REVIEW`. Khắc phục: Tìm file ledger tương ứng của máy trong thư mục trên và xóa (unlink) để hệ thống cho phép chạy lại fresh.
  - ⚠️ **Đối soát máy thiếu ID TikTok (`MISSING_ID`):** Nếu `TikN.xlsx` bị trống cột `ID` (bị skip ở preflight), đối soát ngay với file nguồn `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx` theo đúng số máy và Folder Video của ca tương ứng (Ca 1: folder 1..80, Ca 2: folder 81..160 hoặc dải tương ứng) để điền bổ sung ID và set `Kiểm Tra Dữ Liệu = OK`.
  - ⚠️ **Xử lý kẹt UI, Mất ATX Session & Recent Activity (`.recents.RecentsActivity` / `ATX_SESSION_UNAVAILABLE`):** Khi máy kẹt Recent app hoặc mất session UI, chạy tuần tự:
    1. Kill uiautomator cũ: `adb -s <serial> shell pkill -9 -f uiautomator`
    2. Bật lại daemon: `adb -s <serial> shell /data/local/tmp/atx-agent server -d`
    3. Force-stop app: `adb -s <serial> shell am force-stop com.ss.android.ugc.trill`
    4. Bấm Home thoát Recent: `adb -s <serial> shell input keyevent 3`
  - ⚠️ **Sự khác biệt giữa Runner cũ (PowerShell) và Hook mới (Subprocess):** Bản PowerShell cũ chạy được vì nó pipe token `"YES"` vào stdin con (`$ConfirmationToken | & $Python`). Khi chuyển sang subprocess trong runner Python, nếu script target có `input()` sẽ bị kẹt/crash vì không có bàn phím tương tác. Tuyệt đối không quy kết nhầm sang lỗi cron/reg Gmail.
  - ⚠️ **Thống kê Batch Upload & Tiến độ thực tế:** Tiến độ upload theo batch (mặc định 20 parallel) phải theo dõi qua tiến trình thật và file `TikN.xlsx` (cột `Video Đã Đăng`). Không kết luận toàn bộ farm fail khi các máy mới chỉ đang nằm trong hàng đợi hoặc đang xử lý các state UI/Post/Verify. Cần phân loại rõ ràng: (1) Đã thành công tăng video; (2) Đang chạy; (3) Lỗi trống ID TikTok trong workbook; (4) Lỗi thiết bị offline.
  - ⚠️ **Batch Error Aggregator & Dual-Threshold Systemic Alert Hook (2026-09-07, cập nhật 2026-09-11):** Khi batch kết thúc và export `summary.csv`, hook `python -m automation_core.batch_aggregator "$summaryPath" --telegram` tự động quét kết quả. Lỗi lẻ tẻ/ngẫu nhiên (< 10% tỷ lệ hoặc < 3 máy) được **Silent Skip** hoàn toàn để tránh spam alert Telegram; chỉ khi lỗi vượt ngưỡng kép ($\ge 10\%$ VÀ $\ge 3$ máy) hệ thống mới phát Telegram alert kèm danh sách máy, signature chuẩn hóa và lệnh Canary Policy đại diện 1 máy.
    - **Header hiển thị rõ ràng (User chốt 11/09/2026 & Case 93 12/09/2026):**
      1. BẮT BUỘC ghi rõ script/quy trình ngay dòng đầu tiên dưới banner đỏ: `• Quy trình / Script: <b><Tên quy trình chuẩn / Script></b>` (tự động phân giải tên tiếng Việt thân thiện qua metadata `_resolve_script_meta`, cờ `--script`, hoặc tự động trích xuất từ `run_manifest.json` / `summary.txt`).
      2. Tổng tỷ lệ thất bại toàn batch: `• Tổng tỷ lệ thất bại toàn batch: <b>X%</b> (failed/total máy)`.
      3. Tách biệt cho từng signature: `Tỷ lệ trên toàn batch: X% (n/total máy)` và `Tỷ lệ trong số máy lỗi: Y% (n/failed máy lỗi)` (tránh nhầm lẫn 75% cục bộ khi 100% máy fail).
    Chi tiết: `references/batch-aggregator-dual-threshold-and-upload-hook-20260907.md`.
  - ⚠️ **Manual Targeted Run & Device Lock Invariant**: Khi chạy batch thủ công (upload video, fix máy, avatar) song song với hệ thống cron 15' đang active, BẮT BUỘC tạo file lock (`~/.codex/device-locks/machine_<N>.lock.json` với `status: "running"`, `user_authorized: true`, `project: "tiktok-video"`, TTL 2h) trên các máy chỉ định trước khi chạy để ngăn cron feed chen ngang gây xung đột UI (màn hình CapCut/Upload vs Profile feed navigation). Đồng thời `cronjob pause` cron feed trong thời gian chạy batch thủ công lớn.

- **Bản chất lỗi ATX Session (Port 7912) trên điện thoại (2026-08-25):**
  - Lỗi `ATX_SESSION_UNAVAILABLE` / `502 RemoteDisconnected` **KHÔNG PHẢI do quá tải máy chủ PC hay do số worker (30/40/50)**. Mỗi worker giao tiếp với đúng 1 điện thoại qua IP/Port riêng.
  - Đây là lỗi cục bộ trên phần cứng điện thoại (Samsung S7 / Android 7 cũ) do TikTok ngốn RAM khiến Low Memory Killer (LMK) của Android tự động kill tiến trình uiautomator ngầm (Exit 137), hoặc do cây UI TikTok refresh quá nhanh làm Accessibility service bị ANR. Khắc phục bằng auto-recovery `reset_atx_agent` (pkill uiautomator stub + khởi động lại atx daemon).

- **TikTok Follow Drop & Trust Cooldown Rules (2026-08-23, cập nhật 2026-08-25):**
  - **Hiện tượng nhả follow (Follow Drop):** Khi nick bị TikTok đánh cờ action limit / shadow penalty, việc nghỉ 3 ngày vẫn có thể bị nhả follow do TikTok cần **5 – 7 ngày** để reset trust score.
  - **Quy tắc Reset Cooldown (Tuyệt đối không spam test):** Mỗi lần gửi tín hiệu tap follow thất bại hoặc bị nhả sẽ **reset bộ đếm thời gian phạt (shadow cooldown) lại từ đầu**. Do đó không được chạy test follow hàng ngày trên các nick đang dính án phạt.
  - **Cơ chế Fail-Closed trong `follow_runner`:** Khi phát hiện 1 follow bị nhả sau bước `verify_after_tap` (kéo `pull_to_refresh`), hệ thống lập tức gọi `set_follow_failed()` để ghim `follow_failed = True` và `follow_failed_date = today`, ngắt toàn bộ lượt follow của nick đó trong cả ngày và đưa app về Home an toàn.
  - **Duy trì trong thời gian nghỉ follow:** Bắt buộc duy trì đăng video đều (đạt tối thiểu **≥ 3 – 5 video/nick**) kết hợp nuôi feed thuần túy (xem video, thả tim nhẹ) để tích lũy tín hiệu user thật trước khi test lại 1-2 follow For You.

- **Quy tắc Khoảng đệm Thời gian & Cấm chạy đè Upload khi Feed Session chưa dứt điểm (2026-08-25, cập nhật 2026-08-26):**
  - Đăng video đồng loạt cuối ca (sau phiên 3) là hành vi chuẩn giúp nick có trust cao; launcher PowerShell tự giới hạn tối đa 16 máy song song và giãn cách 2–8s để không nghẽn mạng/proxy.
  - ⚠️ **Tách biệt Ngân sách Timeout giữa Nuôi Feed và Upload Hook (Commit `9db6c84`):**
    - Subprocess upload hook có budget độc lập (`DEFAULT_UPLOAD_HOOK_TIMEOUT_SECONDS = 1200.0` - 20 phút), không dùng chung hay bị bó hẹp trong timeout lướt feed (~6 phút).
    - Watchdog bao ngoài (`worker_hard_timeout`) ở phiên cuối tự động mở rộng bằng: `feed_timeout + upload_budget + 300s buffer`.
  - ⚠️ **Khóa kép In-Process + Inter-Process cho Upload Ledger (Case 104, 2026-09-05):**
    - Khi 40–74 máy cùng hoàn tất lướt feed ở Phiên 3 và chuyển sang hook upload video, các worker threads trong cùng process Python bắt buộc phải qua `_LOCAL_LEDGER_LOCK = threading.RLock()` trước khi chạm vào OS file lock `msvcrt.locking` (`_InterProcessFileLock`).
    - Thao tác kiểm tra ground truth report trong `D:/CodexRuntime/tiktok-video/runs` bắt buộc dùng `os.scandir` lọc nhanh theo prefix `f"run_{serial}_{date_compact}_"` và thực hiện TRƯỚC khi chiếm exclusive file lock (thay vì `glob` 48.000+ thư mục khi đang giữ lock làm nghẽn 100–300ms/máy).
    - Nâng `lock_timeout` lên `300.0s` (hỗ trợ cấu hình qua `shift_upload_lock_timeout_seconds`) và truyền đúng `deadline_config` để triệt tiêu hoàn toàn lỗi `shift_upload_lock_timeout_fail_closed` ("Timeout/Quá giờ"). Chi tiết: `references/shift-upload-lock-inprocess-coordination-case104-20260905.md`.
  - ⚠️ **Phân định rõ kiến trúc Workbook Sync (DAT ➔ SAFE vs TIKN độc lập):**
    - `taikhoan_run_safe.xlsx` (nuôi feed): Tự động sync 100% từ `taikhoan_dat_v2_updated .xlsx` qua cron `taikhoan-run-safe-sync`.
    - `Tik1..Tik6.xlsx` (đăng video): Đồng bộ 1-chiều từ `taikhoan_dat_v2_updated .xlsx` qua `sync-tik-workbooks.py`.
    - ⚠️ **Quy chuẩn `is_valid_tiktok_id` (Tuyệt đối không blacklist username thật, cập nhật 2026-08-31):** Trong `is_valid_tiktok_id`, chỉ lọc các link HTTP/URL (`http://`, `https://`, chứa `/`), chuỗi rác (`none`, `null`, `ghjfghj`, `chua_co`) và chuỗi thuần số. TUYỆT ĐỐI KHÔNG blacklist các từ khóa/chuỗi username hợp lệ (như `ngomai.ly`, `vo.my`, nick có dấu chấm `.` ở giữa tuân thủ regex `^[a-zA-Z0-9_.]{2,24}$`) để tránh xóa nhầm ID tài khoản hợp lệ thành `MISSING_ID` trong `TikN.xlsx`.
  - ⚠️ **Quy tắc Tổng kết Báo cáo Watchdog Nuôi Acc (Feed Session Watchdog, cập nhật 2026-08-31):**
    - **Merge Multi-run an toàn:** Khi một phiên chạy nhiều đợt quét (chạy chính + chạy vét), dùng các hàm merge nguyên tử (`merge_follow_result`, `merge_machine_result`, `merge_upload_result`). Cờ `FOLLOW_FAILED` và toàn bộ lượt follow/upload thành công ở bất kỳ đợt nào đều được giữ nguyên, không bị đợt sau ghi đè thành `skipped`.
    - **Phân biệt lượt chạy sạch 0 follow với lỗi:** Khi follow hook kết thúc với `exit_code: 0`, `status: "OK"`, `failed: 0` nhưng `followed: []` (do target `following == 0` hoặc đã follow hết qua `zero-following-skip-v2`), đây là lượt chạy thành công an toàn, TUYỆT ĐỐI KHÔNG gom vào mục `Lỗi script/xác minh`.
    - **Thời điểm chốt báo cáo:** Bắt buộc kiểm tra `is_feed_runner_active()` và chỉ phát báo cáo khi toàn bộ runner của phiên đã dừng hẳn, tránh chốt non giữa chừng làm thiếu hụt số lượng máy thực tế.
    - **Bẫy gom Fail trống slot phôi mới & Thiếu báo cáo tỷ lệ thả tim (Case 156, 2026-09-13):**
      + Khi chạy Ca nuôi các Row mới (Row 7 hoặc Row 8), farm chỉ có số lượng nick giới hạn (ví dụ Row 7 có 35 nick, 45 máy còn lại trống). Runner trả về `account row X is empty (no username), skipping` (`config-error`).
      + Watchdog **CẤM gom toàn bộ máy `status != "success"` vào nhóm `Fail`** gây báo động giả toàn farm hỏng (ví dụ báo `Fail (61)` trong khi 45 máy là do chưa có nick). Bắt buộc phân loại 3 tầng: `Success`, `Fail (lỗi thực sự)` và `Bỏ qua do trống slot phôi mới`.
      + Báo cáo Telegram **BẮT BUỘC trích xuất `like_counts`** từ `summary.txt` từng máy và hiển thị tổng số tim / tổng số video lướt cùng tỷ lệ % (`• Thả tim (Like): X tim / Y videos (Z%)`) để người vận hành kiểm soát hành vi tương tác tự nhiên.
    - **Bẫy chốt non khi phiên cuối ngày chạy vắt qua nửa đêm (2026-09-06):** Khi Ca 3 Phiên 3 (21:45 - 23:59) chạy vắt qua nửa đêm (00:00), ngày hệ thống đổi sang ngày mới khiến `is_today` thành `False`. Hàm `can_report_session` BẮT BUỘC phải chặn lại nếu `runner_busy == True` (tuyệt đối không return `True` vô điều kiện khi `is_today == False`). Đồng thời hàm `is_feed_runner_active` phải nhận diện cả cờ CLI `--mode multi-machine-feed-session` (gạch nối `-`), `run_tiktok.py`, `hermes_cron_runner.py`, `tiktok_runner.py`. Khi bị chốt non chỉ 1-2 máy, xóa key `YYYY-MM-DD_caX_phienY` khỏi `feed_session_reported.json` để watchdog tự động báo cáo lại đầy đủ khi runner kết thúc. Chi tiết: `references/feed-watchdog-midnight-rollover-and-process-detection-20260906.md`.
  - ⚠️ **Buffer Time Guard:** Thời gian kết thúc đợt batch upload phải cách giờ bắt đầu của ca cron tiếp theo (ví dụ 06:00 Row 1, 14:00 Row 2, 22:00 Row 3) **tối thiểu 30 – 45 phút**.
  - ⚠️ **CẤM KÍCH HOẠT BATCH UPLOAD KHI FEED SESSION CHƯA KẾT THÚC HOÀN TOÀN**: Tuyệt đối không được bật `run_tiktok_upload_batch.ps1` thủ công khi nhịp chạy vét cuối của Phiên 3 (các đợt 23:15, 23:45, 00:15) vẫn đang còn worker chạy. Việc chạy đè sẽ làm tranh chấp app TikTok, văng focus ra launcher (`TikTok focus lost`), mở nhầm màn hình Camera (`camera_creation_overlay`) và kích hoạt Farm Alerts giả. Bắt buộc kiểm tra `run_manifest.json` và log đợt cuối đã hoàn tất 100% trước khi can thiệp.
  - ⚠️ **Xử lý Fix Lỗi UI Bằng Script Recovery Engine (`-RecoveryMode`):** Khi user yêu cầu "fix các máy lỗi UI / lock lại fix", **BẮT BUỘC dùng script canonical với cờ recovery, CẤM can thiệp sửa tay**:
    ```powershell
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\Taadaa\Tiktok-video\run_tiktok_upload_batch.ps1" -Tik <N> -MaxParallel 20 -RecoveryMode -AllowDeviceRebootRecovery
    ```
    Script tự động xử lý soft-reboot, giải phóng UI kẹt, xóa stale fingerprint reservation của worker chết và hoàn tất đăng video an toàn mà không thao tác tay tùy tiện. Bỏ qua các máy offline / mất ADB. Mọi thay đổi logic recovery/timeout/import phải được encode trực tiếp vào codebase qua Git commit được review APPROVED (như các commit `9db6c84` decouple upload timeout, `cdce610` fallback import benign popup, `0aa6da7` dismiss location dialog).
  - **Không chạy bù upload dồn ép:** Nếu đợt upload trước bị ngắt quãng hoặc sót máy, nhưng chỉ còn < 30 phút là đến giờ cron ca sau, **TUYỆT ĐỐI KHÔNG chạy bù batch upload toàn farm** vì sẽ gây xung đột Device Lock (`SKIPPED_LOCKED`) và xung đột đăng nhập account giữa 2 ca khác nhau (`Tik2.xlsx` vs `Tik1.xlsx`). Việc một vài nick thỉnh thoảng không đăng đều video không ảnh hưởng nghiêm trọng đến farm.

- **TikTok Feed Session Profile Verification Lag & Target Video Range (2026-08-21, 2026-08-22):**
  - Khi đối soát hồ sơ cuối phiên nuôi (`verify_profile`), nếu vừa bấm vào tab Hồ sơ nhưng TikTok chuyển cảnh chậm, node username `@...` có thể chưa kịp render lên cây UI dẫn đến báo động giả `profile verification mismatch: profile account mismatch`.
  - Fix chuẩn (repo `tiktok-luot nuoi acc`, commit `e337d2f`): Tự động `time.sleep(1.5)` và chụp lại XML lần 2 trước khi kết luận mismatch, tránh ngắt phiên và gọi recovery oan.
  - **Ngân sách thời lượng & Target video (2026-08-22):** Mặc định phiên nuôi chuẩn là `10 - 18 video` (`FEED_SESSION_MIN_TOTAL_VIDEOS = 10`, `FEED_SESSION_MAX_TOTAL_VIDEOS = 18`). Trên S7/S7 Edge (latency 40-50s/video gồm swipe, dump XML ATX port 7912 và 17 popup handlers), cấu hình cũ `15 - 30 video` ngốn tới ~27.5 phút gây lỗi `run plan max_duration_seconds exceeded` khi chạm trần 1500s (25 phút). Trần 18 video đảm bảo phiên hoàn thành trong ~17.5 phút, dư >7.5 phút an toàn. Chi tiết: `references/feed-session-duration-and-timeout-budget.md` trong skill `tiktok-feed-session`.

- **Resume collision & Renumber fix trong `download_by_niche.py` (2026-08-21):**
  - Khi resume một folder đã có file số cũ (`1.mp4..46.mp4`) từ đợt chạy trước đó, `renumber_mp4_files` từng ném `FileExistsError: numeric target is not part of the rename set` làm chết cả batch 16 worker.
  - Fix chuẩn (commit `ee654f6`): `stale_orphan_numeric_mp4s()` tự dọn file số cũ (>24h không có trong DB) trước khi kiểm tra conflict. Chạy lại với `--continue-on-insufficient` để skip folder thiếu nguồn.

- **Quy trình Thay thế & Tái cấp nguồn (Cut & Backfill Re-render) khi làm lại video nick (2026-08-24):**
  - **Dọn nick lỗi:** Khi đổi nội dung do reup nhầm kênh / dính bản quyền: xóa sạch `D:\video goc\<máy>` và `D:\TIKTOK-videonuoinick\<Folder Video>`.
  - **Chuyển folder dự phòng:** Lấy folder nguồn và folder render hoàn tất còn dư: **BẮT BUỘC CUT (dọn sạch folder cho đi)**, tuyệt đối không chỉ copy để tránh trùng lặp nội dung video giữa các folder/máy.
  - **Bù lại folder nguồn vừa cho:**
    1. Kiểm tra folder cho đi chưa từng được nick nào chạy upload trong `Tik1..Tik4.xlsx`.
    2. Reset/đồng bộ thông tin folder trong `D:\CodexRuntime\tiktok-video\state.db` (bảng `folders`, `videos`).
    3. Nạp bộ video nguồn sạch mới (≥ 45 video MP4) + `avatar.jpg` vào `D:\video goc\<folder>`.
    4. Chạy render standalone: `python scripts/random_batch_render.py --input-dir "D:/video goc/<folder>" --output-dir "D:/TIKTOK-videonuoinick/<folder>" --preset "presets/preset_owner.json" --randomize --slot <N> --machine-id <M> --seed-offset 0 --parallel 2 --resume-verify-existing`.
    5. Đảm bảo copy `avatar.jpg` từ `video goc` sang `TIKTOK-videonuoinick` nếu render pipeline chưa sync.

- **S7 ROM gốc khi mất điện / sập nguồn (2026-08-21):**
  - Samsung Galaxy S7 chạy ROM gốc **KHÔNG tự khởi động lại** khi mất điện cấp vào box; máy sẽ rơi vào trạng thái sạc pin tắt màn (LPM) hoặc tắt ngúm → sau khi cúp điện / sập nguồn phải bấm nguồn bật tay từng máy (trừ khi đã mod `/system/bin/lpm`).
  - Tránh cắm chung ổ chia PC + 4 Box S7 (tổng tải >1.000W dễ sụt áp / sập nguồn PC). PC nên cắm riêng ổ tường.

- **Cronjob theo dõi tạm thời (Watchdog) phải dùng `no_agent: true`:**
  - Nếu tạo cron LLM-agent không ghim model (`model=None`), khi profile chuyển model toàn cục (ví dụ `worker` → `ag/gemini-3.7-flash-high`) scheduler sẽ chặn chạy với lỗi `Skipped to prevent unintended spend: global inference config drifted`. Luôn dùng `no_agent: true` + `script` cho các cron theo dõi trạng thái / watchdog.
  - **Unified Download & Render Watchdog (`farm-<host>-render-download-watchdog`):**
    - Thay vì dùng các script watchdog lẻ tẻ (`tik3_render_watchdog.py`, `download_progress_watchdog.py`), cả máy Admin và Kibe cần thống nhất dùng Watchdog gộp:
      + **Admin:** `D:\video goc may 2` + `D:\TIKTOK-videonuoinick-admin` (job `farm-admin-render-download-watchdog`).
      + **Kibe:** `D:\video goc` + `D:\TIKTOK-videonuoinick` theo 8 slot `Tik1.xlsx`..`Tik8.xlsx` (job `farm-kibe-render-download-watchdog`).
      + Định dạng HTML chuẩn Telegram: thống kê Video gốc (trạng thái download, tổng folder nguồn, đạt $\ge 30$, đạt $\ge 45$, tổng clip mp4) và Tiến độ Render Tik1..Tik8 (folder $\ge 30$ clip / 80, tỷ lệ %, tổng clip).
      + Cấu hình `deliver: "telegram:-5373649734"` (Group Farm Alerts) và `no_agent: true`.
      + **Lưu ý I/O trên ổ HDD vs SQLite state.db (0.003s vs 180s timeout) & Bẫy Lệch Đường Dẫn SSD/HDD (2026-09-14):**
        - Khi ffmpeg đang chạy render hoặc hệ thống chạy bình thường, quét đĩa đồng loạt 500+ folders trong `D:\video goc` trên ổ HDD sẽ làm tê liệt I/O và **bị timeout sau 180s**.
        - Truy vấn trực tiếp từ `state.db` (bảng `folders`: `SELECT COUNT(*), SUM(CASE WHEN video_count >= 30 THEN 1 ELSE 0 END), SUM(CASE WHEN video_count >= 45 THEN 1 ELSE 0 END), SUM(video_count) FROM folders`) cho kết quả chính xác trong **0.003 giây (3ms)**.
        - ⚠️ **Phân biệt `complete` vs `complete_partial` trong `state.db` (2026-09-17)**: `complete` là folder $\ge target\_videos$ (mặc định 45). `complete_partial` là folder $\ge min\_videos$ (30) nhưng $< 45$. **Cả hai nhóm này (585 complete + 27 complete_partial = 612/640 folders ~ 95.6%) ĐỀU ĐÃ ĐỦ CHUẨN NUÔI NICK**, không phải lỗi. Chỉ có nhóm `insufficient_pool` (video_count = 0 hoặc cạn nguồn shorts đạt chuẩn) mới là các folder cần cào thêm nguồn bù.
        - **BẮT BUỘC ƯU TIÊN ĐỌC SSD TRƯỚC (`C:/CodexRuntime/tiktok-video/state.db`)**: Khi downloader chạy trên SSD C: để tránh nghẽn đĩa cơ, watchdog PHẢI ưu tiên đọc từ SSD C:. Nếu trỏ nhầm sang HDD D: (file cũ dừng cập nhật), cron sẽ báo số liệu ảo bị đứng im ("Có tăng đc video gốc đéo nào đâu????") dù thực tế trên SSD đã tăng hàng chục folder và hàng nghìn video.
        - **Bẫy escape ký tự `\t` trên Windows**: Luôn dùng forward slash `C:/CodexRuntime/tiktok-video/state.db` trong code Python, cấm dùng `r"C:\CodexRuntime\tiktok-video\..."` trần vì dễ dính tab escape `\t`.
      + **Cơ chế Host-Aware tự động nhận diện Kibe vs Admin:**
        - Nếu `D:\video goc may 2` tồn tại $\rightarrow$ Host Admin (`D:\video goc may 2`, `D:\TIKTOK-videonuoinick-admin`, DB `D:\CodexRuntime\tiktok-video-machine2\state.db`).
        - Ngược lại $\rightarrow$ Host Kibe (`D:\video goc`, `D:\TIKTOK-videonuoinick`, DB `D:\CodexRuntime\tiktok-video\state.db`).
      + **Đồng bộ Cron tự động giữa Kibe và Admin:**
        - Cập nhật `setup_admin_cron.py`: thay thế các watchdog đơn lẻ cũ (`tik2-render-watchdog`) bằng `farm-render-download-watchdog` (`expr: "0 * * * *"`, `deliver: "telegram:-5373649734"`).
        - `sync-from-kibe.ps1` tự động thực thi `setup_admin_cron.py` ở bước đồng bộ để nạp và cập nhật danh mục cron Admin không cần can thiệp thủ công.
  - Chu kỳ cron `device-locks-watchdog` phải duy trì `every 15m` (không để `every 120m` vì thời gian phát hiện và cảnh báo lock quá trễ). Script chỉ gửi tin khi `len(locks) > 0` và im lặng khi `len(locks) == 0`.
  - **Cron dọn dẹp cache TikTok cuối ngày (`end-of-day-clear-tiktok-cache`, cập nhật 2026-09-09):** Báo cáo kết quả phải cấu hình `deliver: "telegram:-5373649734"` (Group Farm Alerts). Concurrency tối đa `MAX_WORKERS = 20` (cấm để 40 làm nghẽn hàng đợi ADB server và socket ATX), outer subprocess timeout tối thiểu `300s` để bao trọn worst-case của Path 2 In-App Settings (85s–140s). Chi tiết: `references/cron-clear-cache-timeout-and-worker-budget-20260909.md`.

- **min-videos DOWNLOAD CHỐT 30 (16/08 đêm).** User phân tích: follow kênh chủ yếu từ
  FOLLOW CHÉO farm (~80-90%), tự nhiên chỉ 10-20% → video không quyết định follow; cần
  ~20-30 video đủ "độ dày" chống flag khi follow chéo dồn (kênh 2-3 video nhận 500 follow
  = pattern → shadow-ban). min 45 khó tìm nguồn (454 kênh → 267 qualified; hạ 30 → nhiều
  hơn hẳn). Đã sửa constraint 42→30 ở CẢ `download_by_niche.py` + `source_pool_builder.py`
  ("yeu cau 30 <= min"). Download/qualify dùng `--min-videos 30 --target-videos 60
  --max-videos 65`; qualify lại ra `sources.qualified30.json`. Source folders
  are pre-verified complete (enough videos already downloaded) — don't gate on min-video
  checks; just render.

- **Report cadence & background job etiquette (User chốt 2026-08-27, cập nhật 2026-08-31 & 2026-09-13):** Khi batch đang tải/render ở background (đã có cron watchdog báo định kỳ mỗi 60 phút hoặc mỗi 10 folder), giữ im lặng tuyệt đối. **CẤM spam thông báo lỗi exit code/retry của tiến trình con hay báo cáo tiến độ lẻ tẻ** khi hệ thống đang tự động phục hồi ("Thì đang down bth đừng có báo nữa").
  - **Quy chuẩn Báo cáo Hoàn tất Batch (User chốt 13/09/2026: "K nhé chạy xong mới báo"):** Tuyệt đối KHÔNG gửi tin nhắn Telegram khi batch vừa bắt đầu khởi chạy (không gửi thông báo khởi động). CHỈ phát báo cáo kết quả DUY NHẤT một lần khi batch đã kết thúc hoàn toàn (success/fail tổng hợp).
  - Khi báo cáo kết quả các đợt chạy farm batch/cron, **TUYỆT ĐỐI CẤM spam từng dòng per-machine `[OK] Machine X...` / `[WARN] Machine Y...`**. BẮT BUỘC chỉ báo định dạng ngắn gọn chuẩn:
  • **Tổng máy:** <Số lượng>
  • **Success (<Số lượng>):** <Danh sách STT máy thành công>
  • **Fail (<Số lượng>):** <Danh sách STT máy thất bại kèm lỗi nếu có>
  Chỉ gửi đúng 1 báo cáo tổng kết duy nhất khi hoàn tất trọn vẹn toàn bộ batch hoặc khi gặp blocker cứng thực sự cần user quyết định.

- **Avatar NEW rule (overwrite from Tik3 onward only):** old avatars are wrong content.

  Regenerate via `_make_avatar.py` (calls make_representative_avatar: person → animal →

  bright-frame fallback). Overwrite only folders ≥ Tik3 (Tik3 source = folder 161+);

  SKIP folders 1-160 already used by Tik1/Tik2. `D:\video goc` folders ≥305 may have NO

  video (only avatar.jpg) — those are Tik3 OUTPUT folders whose videos live in

  `D:\TIKTOK-videonuoinick`; generate their avatar direct from the TV folder

  (make_representative_avatar on the TV videos), not from video goc.

- **Avatar rule ƯU TIÊN CAO NHẤT (user đổi 16/08 chiều tối):** người → động vật → frame

  sáng lên ƯU TIÊN CAO NHẤT, **BỎ hẳn avatar kênh thật** khỏi bước 1 (sửa cả

  download_by_niche.py `make_avatar_for_folder` + `_make_avatar.py` subject_type

  `person`→`auto` + yolov8n.pt — commits `662ff58`/`0b2fc7d`). **"Những cái đã sửa r thì

  đừng đụng tới nữa"**: avatar đã tạo (161+ theo rule cũ) GIỮ NGUYÊN — rule mới chỉ áp

  lần chạy sau. KHÔNG chạy lại để "đồng bộ rule" và KHÔNG canary trên folder đã có avatar.

- **Folder structure (don't get confused):** `Folder Video` column = OUTPUT folder in

  `D:\TIKTOK-videonuoinick`; `video gốc` column = SOURCE folder in `D:\video goc`. Each Tik

  (Tik1/Tik2/Tik3) has its OWN output range in TV; numbers overlapping between Tiks is NOT a

  conflict (e.g. Tik3 machines 1-20 → Folder Video 3..155 are correct, not clashing with

  Tik1/Tik2). Tik3 machine N: Folder Video = 8N−5, video gốc = 160+N.



See `references/tik3-render-avatar-20260816.md` for the exact command + avatar scripts.



## Download video gốc (fill to 480 folders) — sequencing + platform state (16/08)

- **Thứ tự CHỐT CUỐI (user đảo quyết định 2 lần trong session):** discovery + download

  **CHẠY SONG SONG** — "Ủa phải discovery xong ms down à, tưởng làm tới đâu down tới đó" +

  "Sao k làm song song". KHÔNG chờ discovery xong mới tải. Cơ chế: `source_pool_builder`

  ghi checkpoint `sources.partial.json` SAU MỖI NICHE → loop script copy partial →

  `sources.json` → chạy download → sleep 120s → lặp (đã có `qualify-loop-20260816.py` /

  `download-loop-20260816.py` tại `D:\CodexRuntime\tiktok-video\`). state.db skip folder

  đã complete nên chạy lại nhiều vòng an toàn.

- **Discovery thiếu nguồn → chạy TIẾP (16/08 đêm):** sau discovery 80/80 chỉ 70 kênh
  qualified (đủ 45) → user "vậy thì discovery tiếp đi?". Đã sửa `target_counts()` trong
  source_pool_builder.py thành YouTube 100% (`{"tiktok":0,"instagram":0,"youtube":total}`)
  + `--min-sources-per-platform 0` (mặc định 1 → fail vì tiktok/IG = 0) → chạy lại
  `--auto-discover --resume-discovery --target-total-sources 480 --min-sources-per-platform 0`
  → 454 YouTube sources (gấp ~4x) → qualify lại → 267 qualified (loại vtv24 còn 267-1).
  Cứ discovery thêm → qualify lại → download hốt nguồn mới (state.db skip đã xong).

  `source_pool_builder --auto-discover` (thiếu `--qualify-videos`) ghi source KHÔNG có

  `qualified_video_count` → kênh 4-video lọt pool → download fail `INSUFFICIENT_POOL`

  đủ loại niche. User: "Tưởng discovery nó đã kiểm tra kênh đủ điều kiện r chứ".

  Đúng quy trình: discovery xong (hoặc song song qua qualify-loop) → chạy

  `source_pool_builder --source-manifest <jsonl> --qualify-videos --qualification-parallel 4

  --min-videos 30 --max-videos 65 --max-candidates-per-source 200 --min-sources-per-platform 0
  --cookies-file <rt>/youtube-cookies-netscape.txt --output sources.qualified30.json`

  → CHỈ tải nguồn đã qualified. qualify probe từng video qua YouTube → chậm + rate-limit

  ("not available" hàng loạt = chặn tạm, không phải video chết) — chạy nền, kiên nhẫn. **`--cookies-file` BẮT BUỘC trong qualify** (flag thêm vào source_pool_builder 16/08 đêm, trước đó `unrecognized arguments: --cookies-file`): qualify không cookies → YouTube probe "not available" ồ ạt + đếm thiếu + chạy cả giờ không xong; có cookies probe đúng + nhanh (454 kênh ~15-20 phút).

- **Worker/spam-IP (user đổi ý 3 lần, CHỐT CUỐI 16/08 đêm, cập nhật scale 2026-08-24 & 2026-09-11):**
  - **Tách biệt Worker Network I/O vs Render CPU (User chốt 11/09/2026):** Worker Download (yt-dlp) chủ yếu là Network I/O, hoàn toàn KHÔNG gây lag máy/CPU $\rightarrow$ Cứ tăng tối đa lên `--parallel 20` workers để kéo nhanh. Chỉ có Worker Render (FFmpeg) là nặng CPU nên bắt buộc giữ `--parallel 1` (hoặc 2).
  - **Scale Download khi có Pool Proxy rộng:** Khi đã có Pool 67 cổng sạch (32 Mobi + 35 MikroTik), chạy 20 workers song song là hoàn toàn an toàn, không sợ spam IP hay bot-check.
  - **Fail-Over Xoay Proxy Tức Thì Khi Lỗi:** Nếu yt-dlp gặp lỗi timeout/407/bot-check trên 1 proxy, BẮT BUỘC retry bốc ngay proxy mới khác trong pool (`max_dl_attempts = 3`), cấm retry lại trên cùng cổng proxy cũ gây nghẽn timeout dồn cục.
  - CHỐT: worker ↑ OK nếu kèm `--proxy-pool` xoay (mỗi thread 1 proxy khác IP → không spam cùng IP). Đã chạy `--parallel 20 --proxy-pool <txt>`. KHÔNG tăng worker khi KHÔNG có proxy xoay.
- **Khả năng scale Worker & Tối ưu bộ lọc Download (2026-08-24):**
  - **Scale Worker:** Máy Kibe (Dual Intel Xeon E5-2680 v4, 56 threads, 64GB RAM) đáp ứng chạy `--parallel 32` workers song song (`ThreadPoolExecutor` I/O-bound + audio check). Resume an toàn qua `state.db` + ledger.
  - **Nới lỏng bộ lọc tiếng Việt:** Nguồn trong `sources.combined_yt_tt.json` đã được qualify từ trước → `candidate_passes_language_source_gate` luôn trả `True` để nhận cả video không dấu / nhạc trend, tránh làm hụt pool video < 30.
  - **Nới lỏng Whisper & Ngưỡng điểm:** Mặc định cho điểm đỗ (0.75) cho video từ nguồn Việt, chỉ loại bỏ khi Whisper xác nhận 100% tiếng nước ngoài (`audio_lang_not_vi`). Giúp tránh gần 70% video bị kẹt ở hàng đợi `review` (`language_score_below_threshold`).
- **1 folder = 1 kênh duy nhất (user: "1 folder vẫn đủ của 1 kênh chứ k phải lấy tùm lum
  kênh cắm vào 1 folder").** Cơ chế code: run_folder thử từng kênh → kênh đầu đủ ≥min
  video → `source = option; candidates = option_candidates; break` → folder CHỈ nhận
  video kênh đó, KHÔNG trộn. `--parallel N` chỉ song song TRONG folder (N thread cùng
  kênh), giữa folder vẫn tuần tự. **Folder đã complete KHÔNG bao giờ đụng lại** (user:
  "Mấy cái đã down đủ r thì k đụng nhé") — reserve_folder chặn status complete, chạy lại
  chỉ skip.

- Nguồn tải chuẩn: `download_by_niche.py --total-folders 480 --start-folder <thiếu đầu>

  --sources <rt>/sources.qualified30.json --state-db <rt>/state.db --runtime <rt>

  --output-root 'D:\video goc' --niche-mode strict --min-videos 30 --target-videos 60
    --max-videos 65 --parallel 4 --continue-on-insufficient
    --proxy-pool "D:/OneDrive/TaadaaData/kibe/PROXYgandienthoai.xlsx"
    --cookies-file <rt>/youtube-cookies-netscape.txt`
  --max-videos 65 --parallel 1 --continue-on-insufficient`. Folder nguồn đã được chuẩn bị

  đủ video bởi khâu tải — không gate thêm min-video. **`--sources` phải là qualified file**;

  **`--continue-on-insufficient` bắt buộc** (mặc định INSUFFICIENT_POOL dừng cả batch — flag

  này skip folder thiếu nguồn, chạy tiếp, đúng ý user \"kênh nào đủ điều kiện thì down\").\n- **Dẹp nguồn = sửa CẢ `PLATFORMS`/`PLATFORM_TARGET` trong script** (không chỉ sources.json):\n  `choose_platform` chọn theo ratio (count/target) → IG chưa đủ target vẫn bị chọn dù không\n  có source. Đã dẹp IG (403 chặn API, yt-dlp 2026.07.04 mới nhất không fix; TikTok extractor\n  trong yt-dlp bị \"marked as broken\" — không search/tải TikTok qua yt-dlp được).\n  **PLATFORMS = (\"youtube\",), PLATFORM_TARGET = {\"youtube\": 1.0} (chốt cuối, commit\n  `241424f`)** — TikTok dẹp luôn vì kể cả target 0.15 vẫn bị `choose_platform` chọn trước\n  (ratio 0) rồi fail do chỉ 3-5 sources. Loại kênh nhà nước (vd @vtv24) theo user.\n- **Qualify gate (commit `241424f`):** discovery KHÔNG tự check kênh đủ điều kiện trừ khi\n  chạy `--qualify-videos` (thiếu flag → 0/176 sources có `qualified_video_count`). Lệnh\n  qualify: `source_pool_builder --source-manifest <jsonl> --qualify-videos\n  --qualification-parallel 4 --min-videos 45 --max-videos 65 --max-candidates-per-source 200\n  --min-sources-per-platform 0 --output sources.qualified.json` — **`--min-sources-per-platform\n  0` bắt buộc** (không có → exit 2 \"thieu platform ['instagram']\" dù đã dẹp IG). Đã verify:\n  70/70 sources qualified ≥45 video (YT 67 + TT 3). Sau khi sửa code: KILL + restart loop\n  (process giữ module cũ).

- **Cookies (CHỐT 16/08 tối): Camoufox cookies là cách qua bot-check YouTube ĐÃ HOẠT ĐỘNG.**

  Chrome/Edge vẫn KHÔNG đọc được (App-Bound/DPAPI — yt-dlp issue #7271) và Firefox profile

  chưa login thì vô dụng — nhưng dùng `camoufox` (pip install camoufox[geoip] + camoufox

  fetch) mở youtube.com headless → export cookies Netscape → `yt-dlp --cookies-file` qua được

  "Sign in to confirm you're not a bot" (test thật: video Numb ok, channel flat ok). Cookies

  hết hạn sau vài giờ → khi download quay lại "Sign in" là phải refresh cookies bằng Camoufox,

  KHÔNG phải lỗi khác. Đã commit `810cf96` (flag `--cookies-file` + `scripts/browser_download.py`).

- **Proxy pool (`--proxy-pool`)**: file xlsx PROXYgandienthoai (cột `proXy`) format
  `host:port:user:pass` (vd `test.taadaa.click:5101:mobi1:TaadaaMobi#2026!`).
  **BẮT BUỘC URL-encode `user` và `pwd` bằng `urllib.parse.quote(..., safe="")`** trong `format_proxy()`.
  Ký tự đặc biệt `#`, `!` nếu không encode sẽ làm yt-dlp parse URL hỏng dẫn tới `407 Proxy Authentication Required` hoặc `Failed to parse URL`.
  **CẤM nạp nguyên file master PROXYgandienthoai.xlsx chứa cả cổng MikroTik bị timeout**: Phải lọc riêng danh sách cổng LIVE của MobiProxy (`test.taadaa.click:5101..5132`) xuất ra file pool text (`live_mobi_proxies.txt`) trước khi chạy download. Downloader sẽ xoay tròn (round-robin) đều qua toàn bộ 32 cổng live thay vì đâm đầu dồn cục vào 1 cổng chết. Chi tiết: `references/proxy-pool-distribution-and-download-health-check-20260911.md`.
  - **Sử dụng MikroTik Proxy Nội Bộ Qua Hosts File & Hợp Nhất 67 Ports (2026-09-11)**:
    - Domain `mirotik1.taadaa.click` trỏ ra IP WAN `171.231.181.33` bị firewall MikroTik DROP (chặn WAN).
    - Router MikroTik nằm tại IP LAN `192.168.110.2`. BẮT BUỘC map `192.168.110.2 mirotik1.taadaa.click` vào `C:\Windows\System32\drivers\etc\hosts` để truy cập nội bộ siêu tốc (~0.4 - 0.5s).
    - Toàn bộ **35 lines PPPoE MikroTik** (`10001..10035`) đều OPEN và live 100%.
    - CẤM suy diễn sai lệch "cổng này dành riêng cho máy, cổng kia tải" rồi chỉ bốc 7 cổng; cả 2 hệ thống proxy đều phục vụ farm.
    - Khi download video, BẮT BUỘC hợp nhất trọn vẹn cả 2 pool: **32 cổng MobiProxy** (`test.taadaa.click:5101..5132`) + **35 cổng MikroTik** (`mirotik1.taadaa.click:10001..10035`) thành **Pool 67 ports xoay vòng** (`combined_proxies_pool.txt`), cho phép nâng concurrency lên 8-12 workers kéo tải cực nhanh mà không dính rate limit hay nghẽn đơn lẻ. Chi tiết: `references/mikrotik-lan-proxy-resolution-and-combined-pool-20260911.md`.
  Sau khi fix URL-encode và đã có Global Whisper Model Lock, download `--parallel 16` xoay vòng qua 38 cổng di động an toàn và đạt tốc độ tối đa.

- Chi tiết + transcript + lệnh test nhanh: `references/youtube-botcheck-camoufox-20260816.md`.

- **CRITICAL PITFALL: `faster-whisper` Memory Leak & OOM 0xc0000142 (2026-08-18):**
  - Khi chạy `download_by_niche.py` song song nhiều worker (16-20 parallel), việc gọi `WhisperModel` (`faster-whisper`) trong thread worker để check ngôn ngữ audio bị leak C++/ONNX heap, phình Virtual Memory lên đến **150 GB**.
  - **Hậu quả hệ thống:** Windows cạn kiệt Commit Charge (Out of Virtual Memory) → Hàng loạt tiến trình mới (`adb.exe`, `conhost.exe`) crash khởi động với mã lỗi **`0xc0000142`** (STATUS_DLL_INIT_FAILED); OneDrive sync engine bị kẹt thread ở Kernel filter driver (`cldflt.sys`) tạo thành zombie process không thể taskkill và bắt đăng nhập lại.
  - **Khắc phục khi bị:** Kiểm tra `Get-Process | Sort-Object PrivateMemorySize64 -Descending` → Kill tiến trình python leak RAM ngay lập tức để giải phóng virtual memory. Với OneDrive kẹt kernel mode, các script local đọc/ghi file `D:\OneDrive` vẫn chạy bình thường, khởi động lại PC sau khi xong ca để phục hồi OneDrive sync. Không chạy whisper song song nhiều worker khi chưa gom model/giải phóng bộ nhớ.

- **youtube_profile regex hóc:** handle Unicode tiếng Việt (`@KhámPháBếpViệt`) fail regex cũ

  `@[A-Za-z0-9._-]+` → đã sửa thành `@[\w.-]+` (source_pool_builder.py, đã commit).

- **state.db folder fail giữ platform cũ:** reset sạch

  `UPDATE folders SET status='pending', platform='pending', source_channel=NULL, video_count=0

  WHERE folder_num=<N>` — chỉ set status không đủ (platform cũ 'instagram' vẫn bị

  folder_row["platform"] đọc lại → lại fail IG). Sau khi đổi PLATFORMS cũng phải reset.

- Chi tiết lỗi + commands: `references/tik3-render-avatar-20260816.md` → mục Download.



## Nuoi acc feed batch (tiktok-luot nuoi acc)



Run the feed/nuôi-acc session for a workbook row across all machines. The canonical launcher

is `run_74machines.bat`, but it does `set /p ROW_INDEX=` (interactive prompt) — so from

Hermes you MUST invoke the underlying PowerShell directly (exact recipe + preflight +

verification in `references/nuoi-acc-feed-batch.md`):



```powershell

# From repo root D:\Taadaa\tiktok-luot nuoi acc

$env:PYTHONPATH=""

powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/run-feed-session.ps1 `

  -Row <N> -Preset full `

  -AccountWorkbook "D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx" `

  -SkipAccountWorkbookSync -LocalRun `

  -MachineStartStaggerMs "2000,8000" -RandomizeMachineOrder `

  -Python "D:\Taadaa\python-envs\automation\Scripts\python.exe" -Run

```



Key points (match the canonical bat — don't reinvent):

- `-Row <N>` — account row 1-6; user must specify which row (preflight).

- `-Preset full -LocalRun` — discover machines from the workbook row, bypass the

  assignment-manifest/worker gate. Do NOT combine `-LocalRun` with `-Machines`.

- `-SkipAccountWorkbookSync` — workbook already synced; avoids re-sync from a (possibly

  moved) tracking workbook. Without it, bare `run-feed-session.ps1` tries to sync from

  `TIKTOK_TRACKING_WORKBOOK` and fails on a stale path.

- `-Python <automation venv>` — EXPLICIT. The ps1 defaults to `python` on PATH, which in the

  Hermes terminal resolves to the hermes venv (Python 3.11, wrong version). Always pass

  `D:\Taadaa\python-envs\automation\Scripts\python.exe`.

- `PYTHONPATH` MUST be cleared (`$env:PYTHONPATH=""`) — the Hermes terminal's PYTHONPATH

  shadows PIL under the 3.12 automation venv (`ImportError: cannot import name '_imaging'`).

  See `consumer-scheduler-orchestration` P9.

- ALWAYS preview first (drop `-Run`): confirm the row resolved to the expected machine list

  (e.g. 1-80 for kibe) before running live.



Launch as `terminal` background=true, notify_on_complete=true; poll the first ~30s to confirm

it printed `[HOST] host=kibe machines=1-80 ...` (host config loaded), NOT an ImportError.

- **Single-Machine Canary Test B4 (Kiểm chứng sau vá lỗi feed session, 2026-09-06):**
  - Chạy lệnh:
    ```powershell
    powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
    ```
  - **Zero-Disk-Scan (CẤM quét đĩa rộng/os.walk):** Tuyệt đối không dùng `os.walk` hay `search_files` đệ quy trong `.ai-runs` để tránh dính timeout >900s. Đọc trực tiếp đường dẫn artifact in ra ở stdout: `D:\Taadaa\tiktok-luot nuoi acc\.ai-runs\<TIMESTAMP>\summary.txt` và file chi tiết `machines\machine_<N>\<TIMESTAMP>\summary.txt` để kiểm tra `final_status == success`, `swipes_completed == 2`, `safety_summary` và `popup_summary`. Chi tiết: `references/canary-feed-session-b4-verification-20260906.md`.




## Register Gmail & 2FA Chained Pipeline (Chuyển sang Chạy Cuốn Chiếu Sau Ca Trưa 2026-09-13)

- **Repo liên quan:** `D:\Taadaa\register gmail` + `D:\Taadaa\tiktok-add-bao-mat-f2a` (+ `automation-core`)
- **Mục tiêu & Quyết định mới (User chốt 13/09/2026):**
  1. **BỎ HẲN Reg TikTok** khỏi chuỗi tự động batch (chuyển sang on-demand/cần mới tạo).
  2. **BỎ cơ chế hẹn giờ cố định ban đêm (01:00 AM)** của cron `night-chain-reg-pipeline` (đã pause ID `38ea60c09825`) để chống xung đột đè máy với Ca 4 (00:00 & 01:30).
  3. **Chuyển sang chuỗi cuốn chiếu (Rolling Pipeline) ngay sau Ca Trưa**:
     - Ca trưa (Phiên 2 lúc 14:00) kết thúc vào ~14:40 – 15:00.
     - Khung giờ 15:00 – 18:00 là khoảng đệm rảnh rỗi 3 tiếng lớn nhất trong ngày trước khi Ca 3 bắt đầu lúc 18:00.
  4. **Chuỗi tuần tự 2 Phase**:
     - **Phase 1:** Reg Gmail (`run_all.ps1`).
     - **Phase 2:** Add 2FA (`run_batch_live_2fa.py` hoặc 2FA Gmail aged).
     - Chi tiết kiến trúc & chốt an toàn: `references/post-noon-chained-pipeline-gmail-2fa.md`.
- **Entrypoint Canonical:**
  - Script tổng hợp: `D:\Taadaa\Tiktok_Reg\scripts\run_night_chain_pipeline.py`
  - Launcher Hermes: `C:\Users\Kibe\AppData\Local\hermes\scripts\night_chain_reg_pipeline_launcher.py`
  - Cron Job: `night-chain-reg-pipeline` (ID: `38ea60c09825`, lịch `0 0 * * *` / `0 1 * * *`, deliver `telegram:-5139245637` - nhóm Gmai reg).
- **Quy tắc vận hành & Chốt an toàn:**
  - **Tuần tự tuyệt đối:** Phase sau KHÔNG BAO GIỜ bắt đầu nếu phase trước chưa return.
  - **Logic chọn Row Ca 4:** Lúc 00:00 lấy ngày theo giờ HCM (`Asia/Ho_Chi_Minh`): ngày chẵn -> Row 8; ngày lẻ -> Row 7 (`8 if day % 2 == 0 else 7`).
  - **Kế thừa cấu hình gốc:** `run_all.ps1` tự động lọc cooldown (mặc định 5 ngày), max 15 máy/batch, kiểm tra VPN preflight trên từng máy.
  - **Quy tắc thoát app/lỗi:** Chỉ khi SUCCESS mới thoát/về Home; máy bị lỗi kẹt lại giữ nguyên màn hình hiện trường theo đúng thiết kế gốc của script. Ca nuôi acc 06:00 sáng tự có preflight dọn dẹp app trước khi vào phiên.
  - **Khóa máy (Lock):** Tuyệt đối KHÔNG tự động lock máy; chỉ lock khi có lệnh trực tiếp từ user.
  - **Báo cáo kết quả:** Gửi đúng 1 tin nhắn tổng kết duy nhất về nhóm Telegram `Gmai reg` (`-5139245637`) theo format: `[BÁO CÁO CHUỖI ĐÊM] Ca 4 Feed Row X -> Reg Gmail -> Add 2FA` kèm thời gian bắt đầu/kết thúc từng phase.
  - ⚠️ **Kỷ luật xử lý Thất bại Phone Verify vs Lỗi Script (User chốt 2026-09-07):**
    - Máy gặp `PHONE_VERIFY` (`Phone verification`) **BẮT BUỘC gán cờ cooldown 4 ngày**, TUYỆT ĐỐI KHÔNG thử lại ngay trong ngày để tránh đốt proxy và bị checkpoint liên hoàn.
    - Khi người vận hành yêu cầu chạy lại/retry sau mẻ đêm, **CHỈ ĐƯỢC CHỌN nhóm máy dính lỗi script** (UI bento switcher, popup bảo mật S7, timeout provider). Bỏ qua 100% nhóm phone verify.
    - Script PowerShell đọc log (`Get-Content`) phải có `-Encoding UTF8`, và pipeline tổng hợp phải phân loại mã lỗi sạch sẽ tránh mojibake (`?` / `Ã¡`) trên Telegram. Chi tiết: `references/gmail-reg-ui-popup-and-switcher-scroll-recovery-20260907.md`.


### Pitfalls & Bài học đã fix (2026-08-19, cập nhật 2026-09-13)
- **Stale `blocked` device-locks của PID đã chết chặn đứng Post-Noon Chain Watchdog (2026-09-13):** `has_active_device_locks()` coi `status: "blocked"` là bận nên watchdog return 0 im lặng dù feed runner đã chết. Preflight O(1): `tasklist` / `psutil.pid_exists` kiểm tra PID trong lock, `Get-CimInstance` quét CommandLine `*run_tiktok*/*multi_machine*/*feed-session*`, đối soát `feed_session_reported.json` (`<today>_ca2_phien2`) + `summary.txt` mới nhất; xóa file `machine_*.lock.json` / `serial_*.lock.json` có PID chết (GIỮ `reg_daily_cooldowns.json`) rồi mới dispatch worker chạy `--force` thật. Chi tiết: `references/post-noon-chain-preflight-stale-lock-cleanup-20260913.md`.
- **Dot-Source Guard trong `run_parallel.ps1` (Chống vô tình chạy batch farm khi test hàm, 2026-09-06):**
  - Khi dot-source `. 'D:\Taadaa\register gmail\run_parallel.ps1'` để test helper functions (`Find-PythonExe`, `Get-RunResultFromLog`, `Try-ReserveQueuedLock`), script thiếu guard ngắt sẽ thực thi toàn bộ logic đọc inventory, chiếm lock và spawn worker thật trên 17 máy.
  - Guard chuẩn: Kiểm tra `$MyInvocation.InvocationName -ne '.'` ở đầu script (tránh `exit 2` khi chưa set canonical launcher) và chèn `if ($MyInvocation.InvocationName -eq '.') { return }` ngay trước phần khởi tạo `$runtimeRoot` và spawn workers.
- **`TAADAA_HOST_CONFIG` bắt buộc cho Phase 3 (Add 2FA TikTok) trong Night Chain Pipeline (2026-09-06):**
  - `python_runner/run_batch_live_2fa.py` gọi `_resolve_proxy_mapping()` ở top-level module (dòng 61), yêu cầu biến môi trường `TAADAA_HOST_CONFIG` trỏ tới `D:\Taadaa\machine-config\kibe.yaml`.
  - Thiếu biến này khiến Phase 3 crash ngay lập tức với `ConsumerPreflightError: proxy mapping workbook unresolved: set TAADAA_HOST_CONFIG or AUTOMATION_PROXY_MAPPING/TIKTOK_PROXY_MAPPING`.
  - BẮT BUỘC `os.environ.setdefault("TAADAA_HOST_CONFIG", r"D:\Taadaa\machine-config\kibe.yaml")` trong pipeline runner (`run_night_chain_pipeline.py`) và Hermes launcher (`night_chain_reg_pipeline_launcher.py`), đồng thời truyền tường minh `env["TAADAA_HOST_CONFIG"]` khi gọi subprocess 2FA batch.
- **PowerShell Safe Log Parsing (`Get-RunResultFromLog`):** Khi đọc file log của worker con trong `run_parallel.ps1`, bắt buộc kiểm tra `IsNullOrWhiteSpace($LogPath)` và bọc `Test-Path -PathType Leaf` + `Get-Content -ErrorAction Stop` trong `try/catch`. File log thiếu/rỗng phải gán reason an toàn (`Missing log, exit code $ExitCode`) thay vì để ném terminating exception `PathNotFound`.
- **Dynamic Gmail Log Path cho Night Chain Alert:** Khi Phase 1 (Reg Gmail) thất bại, `run_night_chain_pipeline.py` không hardcode đường dẫn file `logs/reg.log` mà dùng `find_latest_gmail_log_path()` để trích xuất `RUN_DIR` từ output hoặc quét thư mục `logs_parallel_*` mới nhất dưới `GMAIL_RUNTIME_ROOT` (ưu tiên `summary.txt`), đảm bảo đường dẫn log gửi trong Farm Alert luôn tồn tại trên đĩa.
- **Hermes `no_agent: true` cron output capture & false-positive "provider timeout" alert:**
  - File launcher trong `~/.hermes/scripts/` bắt buộc phải `capture_output=True` từ subprocess và flush thẳng ra `sys.stdout` (`sys.stdout.write`) thì Hermes mới nhận diện có output để đẩy tin nhắn về Telegram (nếu subprocess không pipe stdout thì Hermes báo `Status: silent (empty output)`).
  - Khi script `no_agent: true` kết thúc với exit code 1 (do một số máy trong batch fail) và trong stdout/stderr có chuỗi "timed out" (ví dụ: `proxy readiness timed out`), bộ tóm tắt lỗi của Hermes (`_summarize_cron_failure_for_delivery`) sẽ nhận diện nhầm thành `⚠️ Cron '<job>' failed: provider timeout. Fallback chain was exhausted or unavailable`. Khi gặp thông báo này, kiểm tra ngay file log thực tế tại `~/.hermes/cron/output/<job_id>/<timestamp>.md` để đọc báo cáo thành công/thất bại thực sự của farm thay vì nhầm tưởng là lỗi model AI.
- **PowerShell multi-line string escape với Python inline:** Trong file `.ps1`, tránh dùng khối `@' ... '@` nhiều dòng gọi `python -c` khi có dấu ngoặc kép hoặc `raise RuntimeError("...")` vì PowerShell dễ parse sai dấu đóng ngoặc `)` dẫn đến `SyntaxError: '(' was never closed`. Hãy gói thành chuỗi 1 dòng `"import ...; print(...)"` chuẩn (dùng `sys.exit('...')` để an toàn khi chạy Python `-O`/`-OO`).
- **Lệch cột Excel trong `taikhoan_dat_v2_updated .xlsx` (Nguyên nhân & 2 Hậu quả):**
  - *Nguyên nhân gốc rễ:* Script reg (`social_reg_v1.py` dòng 5070 và `scripts/deferred_tracking_writer.py` dòng 186) khi ghi vào Excel bị chèn thừa 1 ô `None` ở vị trí thứ 8: `[stt, tik, id, pw, 2fa, mail, mail_pw, None, dob, created, device_id]`.
  - *Hậu quả 1 (Khâu Reg):* `device ID` bị đẩy văng ra Cột 11 (Cột 10 bị ghi đè ngày tạo), khiến `_detect_clean.py` chặn toàn bộ batch với lỗi `DETECTION_BLOCKED: TARGET_INVENTORY_CONFLICT` hoặc `MISSING_SERIAL`.
  - *Hậu quả 2 (Khâu Nuôi Acc / Upload Hook):* Ngày tạo ở Row 5/Row 6 bị đẩy dạt sang Cột 10 (index 9) trong khi Cột 8 rỗng `None`. Khiến preflight fail-closed kích hoạt nhầm `account_creation_date_unverifiable`, bỏ qua đăng video hàng loạt 58/66 máy dù nick đã đủ tuổi.
  - *Phòng ngừa chuẩn:*
    1. Consumer (`upload_preflight.py`): Bắt buộc mở rộng `probe_cols = [header_date_col, 8, 9, 7]` nhận diện ngày tạo có `year >= 2025`.
    2. Producer (`Tiktok_Reg`): Cần loại bỏ phần tử `None` thừa ở vị trí thứ 8 trong mảng `values` để ghi đúng 10 cột chuẩn. Chi tiết: `references/triage-upload-skip-unverifiable-creation-date-20260912.md`.
- **Assignment Manifest 80 máy:** File `register-gmail.json` trong `automation-core/assignments/` phải khai báo đủ `machine:1` đến `machine:80`, nếu thiếu máy nào launcher `run_all.ps1` sẽ fail ở bước preflight `TARGET_OUTSIDE_ASSIGNMENT:machine:X`.
- **`subprocess.run` Windows pipe decode crash (`UnicodeDecodeError: 'utf-8' codec can't decode byte 0xa0`):** Khi bọc `powershell.exe` hoặc ADB qua `subprocess.run(..., capture_output=True, text=True)`, Windows console có thể in ký tự CP1258/CP1252/byte lạ (`0xa0`). BẮT BUỘC thêm `encoding="utf-8", errors="replace"` trong `subprocess.run()` để tránh crash reader thread.
- **PowerShell 5.1 `NativeCommandError` False Alarm & Batch Summary Parsing trong Night Chain (2026-09-08/2026-09-09):** Khi launcher PowerShell gọi child script hoặc command sinh stderr/exitcode != 0, PowerShell 5.1 bọc stderr thành `+ FullyQualifiedErrorId : NativeCommandError`. Substring matching naive (ví dụ `"error" in line.casefold()`) sẽ bắt nhầm chuỗi này thành lỗi batch thay vì summary thật. Trong `run_night_chain_pipeline.py`, bắt buộc lọc bỏ các dòng rác PowerShell (`NativeCommandError`, `CategoryInfo`, `FullyQualifiedErrorId`, `RemoteException`), thêm `KET QUA:` vào `summary_markers`, và chỉ gửi `_send_night_chain_alert()` khi không có kết quả batch tổng hợp (`parse_gmail_details().total == 0`). Đồng thời trong `run_all.ps1`, gọi `run_parallel.ps1` trực tiếp trong session (`&`) thay vì spawn child `powershell @parallelArgs`. Đã có bộ test chống tái diễn tại `D:/Taadaa/Tiktok_Reg/tests/test_night_chain_summary.py` (chạy qua pytest).
- **Bẫy Parse Summary Counts Báo Ảo trong Post-Noon Chain Watchdog (14/09/2026, cập nhật 15/09/2026):**
  - **Hiện tượng:** Watchdog bị báo cáo ảo: khi runner bị lỗi khởi động hoặc crash (`exit_code != 0`), watchdog lại báo số liệu cũ của đợt chạy trước (ví dụ đọc nhầm file `summary.json` cũ từ thư mục runtime), hoặc báo nhầm `0 máy`.
  - **Nguyên nhân kép & Khắc phục:**
    1. *Fallback đọc file stale log*: Trong `post_noon_chain_watchdog.py`, việc quét unconstrained `log_dir_hint.glob("logs_parallel_*/summary.json")` sẽ bốc nhầm file log của mẻ chạy thành công trong quá khứ. **Giải pháp chuẩn:** Ghi nhận `start_epoch = start_dt.timestamp()`. Chỉ parse summary khi `returncode == 0` (nếu `code != 0` gán ngay `(0, 0, 0)` và header `LỖI KHỞI ĐỘNG RUNNER`). Với fallback đọc `summary.json`, BẮT BUỘC lọc `p.stat().st_mtime >= min_mtime` để chỉ chấp nhận artifact được sinh ra trong đúng phiên chạy hiện tại.
    2. *Biến môi trường `$env:GMAIL_EXCEL_FILE` trong `run_all.ps1`*: Launcher PowerShell `run_all.ps1` cần tự động gán mặc định `$env:GMAIL_EXCEL_FILE = "D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx"` nếu chưa được set từ môi trường ngoài, đảm bảo `run_parallel.ps1` và các worker luôn trỏ đúng master Excel.
    3. *F-string ngắt dòng trong Python*: Khi ghi log die account (`preflight_s7_rolling_cleanup.py`), ký tự xuống dòng phải viết `\n`, tránh ngắt dòng vật lý trong f-string gây `SyntaxError: unterminated f-string literal`.

- **Nguồn TikTok song song với YouTube & Direct Fallback (2026-08-22):**
  - Cào danh sách video TikTok bằng `yt-dlp` yêu cầu bắt buộc header `User-Agent` Chrome + `Referer: https://www.tiktok.com/` trong `http_headers`.
  - Khi tải stream MP4 đơn lẻ bị TikTok chặn (`Unexpected response from webpage request`), script tự động kích hoạt `download_tiktok_direct()` qua API TikWM để tải trực tiếp video không watermark, tránh lỗi `download_no_media`.


## references/
- `references/downloader-auto-discovery-and-single-channel-safety.md` — **[MỚI 17/09/2026]** Cơ chế Auto-Discovery khi thiếu nguồn (insufficient pool) trong `download_by_niche.py`, quy tắc đối soát an toàn phân loại 2 nhóm folder trong `state.db` (reset discovered 402 videos fail cho folder dở vs reset source_channel=NULL cho folder rỗng) để triệt tiêu tuyệt đối nguy cơ trộn nhiều kênh vào 1 folder.
- `references/triage-upload-hook-auto-advance-veto-20260916.md` — **[MỚI 16/09/2026]** Triage sự cố Watchdog báo lỗi upload hàng loạt (73/80 máy fail) do bẫy VETO so khớp cứng video_number trong hook nuôi acc khi script upload kích hoạt Auto-Advance nhảy số video, chuẩn hóa regex validation 2 chiều và quy trình backfill ledger.
- `references/post-reset-relaunch-render-download-and-cron-path-fix-20260915.md`
- `references/upload-hook-auto-advance-video-number-veto-fix-20260916.md` — **[MỚI 16/09/2026]** Triage & fix lỗi báo động giả toàn farm dính `post_verification_failed` trong upload hook do cơ chế VETO so khớp cứng `video_number == next_video` khi script upload kích hoạt Auto-Advance nhảy cóc video, và giải pháp đồng bộ `effective_video_number` vào ledger.
- `references/triage-upload-hook-auto-advance-veto-mismatch-20260916.md` — **[MỚI 16/09/2026]** Triage sự cố lỗi đăng video cao bất thường (69 máy post_verification_failed) do bẫy VETO so khớp cứng int(rep_video_num) == int(next_video) trong upload hook khi script upload tự động auto-advance nhảy cóc video.
- `references/post-reset-relaunch-render-download-and-cron-path-fix-20260915.md` — **[MỚI 15/09/2026]** Triage & chuẩn hóa relaunch render và download sau reset máy, fix lỗi Script not found trên cron Hermes do nhầm lẫn path ~/.hermes/scripts vs ~/AppData/Local/hermes/scripts, bẫy escape ký tự `\r`/`\t` trong Python Windows, và xử lý dứt điểm thiếu nguồn insufficient_pool.
- `references/downloader-proxy-dns-and-reconcile-watchdog-path-fix-20260915.md` — **[MỚI 15/09/2026]** Triage & fix proxy DNS getaddrinfo 11001 bằng direct IP, launcher ps1 thay thế bat syntax error, và thư mục runtime chuẩn cho Hermes cron scripts.
- `references/triage-mass-fail-blocked-proxy-vs-usb-hub-power-drop-20260915.md` — **[MỚI 15/09/2026]** Triage sự cố Mass-Fail (72/80 máy fail) bị gán nhãn ảo `blocked-proxy-vpn` do thiết bị mất kết nối ADB/USB (`device not found`), quy trình chẩn đoán O(1) qua PnP Device Windows nhận diện rớt toàn bộ Generic USB Hubs (`VID_1A86`) do sập nguồn/lỏng cáp Box S7 vật lý.
- `references/hermes-cron-script-path-and-windows-escape-pitfalls-20260915.md` — **[MỚI 15/09/2026]** Triage sự cố Hermes Cron báo `Script not found: ...\watchdog_post_evening_reconcile.py`, nhầm lẫn `~/.hermes/scripts` vs `~/AppData/Local/hermes/scripts`, bẫy escape `\r`, `\t`, `\a` trong đường dẫn Python Windows (bắt buộc dùng forward-slash `/`), và quy trình 3 bước nghiệm thu cron qua `cronjob(action='run')`.
- `references/downloader-insufficient-pool-and-targeted-discovery-20260915.md` — **[MỚI 15/09/2026]** Triage hiện tượng downloader tự dừng khi thiếu nguồn (insufficient pool), bẫy ratio platform TikTok vs YouTube, kẹt platform cũ trong state.db khi chạy Canary test 1 folder (cần `--fixed-platform youtube`), cơ chế khóa độc quyền global-ledger, và quy chuẩn targeted discovery phủ kín 640 folders.
- `references/triage-downloader-completed-insufficient-and-render-ground-truth-20260915.md` — **[MỚI 15/09/2026]** Triage hiện tượng downloader hoàn tất lượt quét bị dừng do cạn pool nguồn (insufficient_pool), giải phóng stale reserved folder trong state.db và quy trình đối soát ground truth Render ticking CPU / timestamp clip.
- `references/downloader-whisper-bypass-and-render-watchdog-status-20260915.md` — **[MỚI 15/09/2026]** Triage sự cố downloader bị treo khởi động do deadlock import torch/faster_whisper (giải pháp `--all-languages`), bổ sung trạng thái render `is_render_running` trực quan cho `farm_render_download_watchdog.py`, và triệt tiêu tin nhắn báo đúp do vừa gọi Telegram API vừa print stdout khi cron `no_agent=True`.
- `references/bytedance-security-sdk-anti-bot-and-touch-simulation.md` — **[MỚI 14/09/2026]** Phân tích chuyên sâu ByteDance Security SDK (`libmetasec_ml.so`), 3 tử huyệt ADB (Pressure 1.0, Size 0, dx=0), giải pháp vuốt ngón tay nghiêng tự nhiên (Natural Thumb Drift) trong luồng feed & grid scroll, hành vi xem lướt bình luận (Comment Peek) và Dwell time ngâm tự nhiên chuẩn GemPhone trước khi bấm Đăng/Follow.
- `references/windows-subprocess-create-no-window-patch-contract.md` — **[MỚI 14/09/2026]** Chuẩn Patch Contract chêm cờ CREATE_NO_WINDOW cho subprocess ffmpeg/ffprobe trên Windows trong Tiktok-video, bẫy thiếu import sys trong media_probe.py và quy trình kiểm thử pytest.
- `references/download-watchdog-ssd-statedb-path-and-single-report-cadence-20260914.md` — **[MỚI 14/09/2026]** Triage sự cố watchdog báo số liệu video gốc đứng im do đọc nhầm HDD state.db thay vì SSD C:, bẫy tab escape `\t`, và chuẩn hóa kỷ luật báo cáo Avatar Single-Shift (30 workers, cấm spam đợt lẻ, chỉ báo 1 lần khi xong hết hoặc hết ca).
- `references/deferred-tracking-per-account-isolation-and-safe-sync-20260914.md` — **[MỚI 14/09/2026]** Kỷ luật cách ly từng account khi merge kết quả (Per-Account Isolation): duyệt try/except per-file, cấm fail-closed gom batch khiến 1 acc lỗi chặn đứng cả mẻ, và tự động kích hoạt sync-safe ngay sau khi lưu master workbook.
- `references/ondemand-reg-tracking-apply-and-kibe-sync-pitfalls-20260914.md` — **[MỚI 14/09/2026]** Triage 3 điểm nghẽn on-demand reg bù: dữ liệu rác mailto: làm trống tracking_row, thiếu lệnh sync-safe-workbook.py trên host Kibe, và bẫy dirs[0] bỏ rơi kết quả đợt chạy trước khi retry thất bại.
- `references/tap-profile-bottom-nav-geometry-and-oly-selector-case98.md` — **[MỚI 13/09/2026]** Case 98: Khắc phục lỗi hàng loạt 28/78 máy dính PROFILE_ROOT_NOT_CONFIRMED do tap nhầm Inbox/avatar creator: cập nhật resource-id `oly` cho profile_tab và áp dụng bộ lọc hình học bottom-nav (cx >= 0.75*W, cy >= 0.80*H).
- `references/farm-watchdog-report-frequency-and-retry-batch-cadence.md` — Quy chuẩn tần suất báo cáo (1h/lần cho monitor) & nhịp cuốn chiếu retry (im lặng lúc chạy, chỉ báo 1 lần khi mỗi batch xong).
- `references/triage-avatar-edit-unavailable-clone-profile-20260913.md` — **[MỚI 13/09/2026]** Triage lỗi [AVATAR_EDIT_UNAVAILABLE] "TikTok báo hoạt động sửa avatar không có sẵn đối với tài khoản ban đầu" trên clone/secondary profile: nguyên nhân, safe-skip thay vì fail-closed quăng WorkflowError, và quy chuẩn nghiệm thu.
- `references/triage-profile-root-not-confirmed-bottom-nav-misclick-20260913.md` — **[MỚI 13/09/2026]** Triage lỗi PROFILE_ROOT_NOT_CONFIRMED hàng loạt (28/78 máy Ca 3 Row 5): fix tap_profile bottom-nav filter (cy>=0.8*H, cx>=0.75*W), cập nhật resource-id oly và cấm match partial content-desc trong Inbox.
- `references/download-relaunch-checklist-20260913.md` — **[MỚI 13/09/2026]** Checklist chạy lại download Kibe 640 folders: mapping Tik1..Tik8 ↔ video gốc, preflight reset folder kẹt (chú ý platform=youtube), pattern launch subprocess.Popen tránh double process do .bat, và benchmark perf watchdog (psutil ~22s, HDD scan slot 5-8 ~48s/slot).
- `references/post-noon-chain-preflight-stale-lock-cleanup-20260913.md` — **[MỚI 13/09/2026]** Preflight O(1) kiểm tra tiến trình feed kết thúc, dọn stale `blocked` device-locks của PID đã chết trước khi chạy thật `--force` chuỗi Post-Noon Chain Watchdog (Reg Gmail -> Add 2FA TikTok) chống kẹt im lặng.
- `references/triage-adb-offline-masked-serial-and-usb-micro-drop.md` — **[MỚI 13/09/2026]** Triage Farm Alert lỗi ADB offline hàng loạt: giải mã masked serial `device:<hash>`, dấu vết micro-drop USB Hub theo timestamp log và kỹ thuật retry backoff `time.sleep(1.0)`.
- `references/post-noon-chain-watchdog-exit-codes-triage-20260913.md` — Root cause & triage sự cố Post-Noon Chain Watchdog văng trong 1 phút (Code 1 do sync-safe-workbook bốc nhầm pass mail làm device serial gây conflict, Code 2 do gọi sai CLI cờ --all-online/--workers của batch 2FA) (2026-09-13).
- `references/cron-setup-real-canary-vs-mock-dry-run-pitfalls.md` — **[MỚI 13/09/2026]** Quy chuẩn nghiệm thu setup/sửa cron: cấm bẫy dry-run/mock, định nghĩa đúng "chạy giả lập" là gọi lệnh thật trên máy rảnh, cô lập cwd repo và xác thực lưu trữ dữ liệu (Excel/DB).
- `references/batch-alert-empty-cluster-and-serial-o1-lookup-20260913.md` — Bản chất cảnh báo dual-threshold rỗng 0 cụm lỗi, tra cứu serial O(1) qua hermes_cron_source_config.json và teardown an toàn về HOME (2026-09-13).
- `references/post-evening-avatar-watchdog-rules.md` — Quy chuẩn Cron Watchdog tự động kích hoạt batch upload Avatar ngay sau Ca Tối (21:00-23:30) cho các acc chưa bao giờ được up avatar qua lọc workbook TikN, kèm cơ chế báo cáo tiến độ trực tiếp vào nhóm Farm Alert (-5373649734) khi hoàn tất (2026-09-13).
- `references/post-evening-avatar-watchdog-canonical-standard-20260913.md` — Chuẩn hóa post_evening_avatar_watchdog.py canonical trong Tiktok-video, host context (Kibe/Admin) và đồng bộ HTML Farm Report cho cả 2 máy (2026-09-13).
- `references/avatar-watchdog-false-completion-and-alert-reporting.md` — Quy chuẩn chống bẫy False-Completion trong Watchdog up avatar, cấm tăng state mù quáng khi chưa verify đĩa/workbook thực tế, và quy chuẩn CHỈ báo cáo Farm Alert khi chạy xong (2026-09-13).
- `references/rolling-watchdogs-morning-2fa-and-noon-chain-20260913.md` — Quy chuẩn 2 Watchdog cuốn chiếu: 2FA Gmail sau Ca Sáng (08:30-11:30) & Reg Gmail + Add 2FA TikTok sau Ca Trưa (14:30-17:30), bỏ hẳn Reg TikTok và hủy cron cố định đêm (2026-09-13).
- `references/feed-watchdog-empty-slot-and-like-rate-reporting-20260913.md` — Quy chuẩn phân loại 3 tầng trạng thái Lướt Feed trong Watchdog (Success, Fail thực sự, Bỏ qua trống slot phôi mới Case 156) và yêu cầu trích xuất tỷ lệ thả tim (like_counts) lên Telegram (2026-09-13).
- `references/post-noon-chained-pipeline-gmail-2fa.md` — Quy chuẩn chuyển đổi pipeline Reg Gmail & Add 2FA sang chạy cuốn chiếu sau Ca Trưa (15:00 - 17:15) và loại bỏ hoàn toàn Reg TikTok khỏi batch đêm (2026-09-13).
- `references/ondemand-reg-slot-padding-pitfall.md` — Pitfall cơ chế on-demand reg bù Row 7/8 không merge được vào master sheet do một số máy chỉ có 6 hàng vật lý thay vì 8 (2026-09-13).
- `references/ondemand-reg-slot-assignment-and-deferred-apply-pitfall.md` — **[MỚI 14/09/2026]** Cơ chế 2 tầng workbook (Master taikhoan_dat_v2 ↔ Safe taikhoan_run_safe) và cron tự động sync (taikhoan-run-safe-sync), xử lý bẫy First-Empty gán lệch Row khi reg bù, bẫy chuỗi rác mailto: làm kẹt BLOCKED_DATA_CONFLICT toàn batch apply, và bẫy thư mục retry rỗng che mất kết quả đợt trước.
- `references/sqlite-io-bottleneck-and-proxy-failover-downloader.md` — Tối ưu SQLite state.db chống nghẽn I/O ổ đĩa cơ HDD (đánh index và chuyển sang SSD C:) và cơ chế fail-over đổi proxy tức thì khi tải video (2026-09-12).
- `references/triage-upload-skip-unverifiable-creation-date-20260912.md` — Triage hàng loạt máy bị bỏ qua đăng video do chốt an toàn account_creation_date_unverifiable khi ngày tạo trong Excel bị lệch sang Cột 9 (Row 5/Row 6), và giải pháp mở rộng probe_cols fallback (2026-09-12).
- `references/triage-upload-hook-shift-p1-p2-and-cycle-check-20260912.md` — Quy trình điều tra O(1) lịch đăng video Phiên 1 & Phiên 2 theo cơ chế mới (Case 152), chu kỳ ngày chẵn/lẻ (Row 1-4) và đối soát ground truth không quét đĩa diện rộng (2026-09-12).
- `references/triage-excel-shifted-creation-dates-and-gateway-busy-ack-20260913.md` — Triage lệch cột ngày tạo Excel (Col 8/9/7) gây safe-skip upload hàng loạt (Case 155) & quy tắc tắt Gateway busy ack "Interrupting current task" (2026-09-13).
- `references/mikrotik-35lines-lan-and-67proxy-download-pool-20260911.md` — Quy chuẩn map 192.168.110.2 cho domain mirotik1.taadaa.click vào hosts file, giải phóng toàn bộ 35 lines PPPoE MikroTik LAN (10001..10035) + 32 ports Mobi (5101..5132) thành Pool 67 ports master tại proxy_pool_67.txt, và quy tắc scale worker (Download chạy 20 workers không lo lag máy, Render giữ 1 worker) (2026-09-11).
- `references/mikrotik-lan-proxy-resolution-and-combined-pool-20260911.md` — Quy chuẩn map 192.168.110.2 cho domain mirotik1.taadaa.click vào hosts file để dùng 7 cổng MikroTik nội bộ và gộp 32 Mobi + 7 MikroTik thành pool 39 ports xoay vòng tải video (2026-09-11).
- `references/watchdog-batch-state-and-anti-false-completion-20260911.md` — Quy chuẩn kiểm tra returncode/ground truth trong script watchdog batch, cấm tăng index mù quáng khi subprocess fail và chống báo càn "ALL DONE" (2026-09-11).
- `references/avatar-multi-row-idle-watchdog-20260911.md` — Quy chuẩn watchdog tự động canh rảnh (3 Gate: Process, Device-Lock, Shift Boundary) để chạy tuần tự batch upload avatar cho Row 5 -> Row 6 -> Row 3 -> Row 4 và đối soát trạng thái nick theo từng Row/Slot (2026-09-11).
- `references/scheduler-4ca-2phien-migration-20260909.md` — Chi tiết migration 3 ca × 3 phiên → 4 ca × 2 phiên (Row 1-8, 09/09): cấu hình chốt, danh sách file thay đổi, golden vector hash recompute, delegation micro-task anti-timeout pattern, follow budget formula.
- `references/triage-nick-chua-up-video-slot-mapping-20260911.md` — Quy trình điều tra O(1) khi user thắc mắc "nick chưa up video": phân định phạm vi đợt chạy theo Row/Slot (Row 1-4 vs Row 5-8), tránh nhầm lẫn số máy trên UI Remote Tool và đối soát nhanh qua taikhoan_run_safe.xlsx + TikN.xlsx (2026-09-11).
- `references/cron-clear-cache-timeout-and-worker-budget-20260909.md`
- `references/cron-clear-cache-timeout-and-worker-budget-20260909.md` — Cân bằng Outer Timeout (300s), Concurrency (20 workers) và Inner Timing Budget trong kịch bản dọn cache TikTok, triệt tiêu lỗi Timeout hàng loạt 30/78 máy (2026-09-09).
- `references/batch-aggregator-dual-threshold-and-upload-hook-20260907.md` — Cơ chế Batch Error Aggregator lọc lỗi hệ thống qua ngưỡng kép (rate >= 10% và count >= 3), chuẩn hóa signature, silent skip lỗi lẻ tẻ và hook summary.csv cho batch upload (2026-09-07).
- `references/avatar-watchdog-process-and-device-locks-gate-20260908.md` — Quy chuẩn watchdog tự động kích hoạt batch upload avatar cho Row cụ thể (Tik4/TikN) sau Ca 3: dual idle gate (tiến trình feed runner + device locks active còn sống), cửa sổ an toàn 00:45 chống đè chuỗi reg đêm, lọc pending từ workbook sheet TaiKhoan và PowerShell launcher canonical (2026-09-08).
- `references/avatar-post-feed-watchdog-and-cron-automation-20260907.md` — Quy chuẩn module watchdog tự động kích hoạt batch upload avatar sau Ca 3 nuôi feed (Row 5 ngày lẻ, Row 6 ngày chẵn), cơ chế idempotency avatar_upload_history.json ("mỗi row nick 1 lần"), time-window 22:30-00:45 và cronjob avatar-post-feed-watchdog (2026-09-07).
- `references/gmail-reg-ui-popup-and-switcher-scroll-recovery-20260907.md` — Chuẩn hóa so khớp tiếng Việt Bento Card Thêm tài khoản khác, tự động cuộn switcher, dismiss popup Security Update/Meet, bẫy ICMP Ping vs GMS HTTPS (GMS_NO_NETWORK) và điều kiện merge kết quả workbook (2026-09-07).
- `references/canary-feed-session-b4-verification-20260906.md` — Quy chuẩn Canary Test B4 (tiktok-luot nuoi acc), quy tắc đọc trực tiếp summary.txt từ stdout artifacts và cấm quét đĩa rộng os.walk gây timeout 900s (2026-09-06).
- `references/canary-single-device-tiktok-video-and-b5-standard-20260906.md` — Quy chuẩn Canary Test đăng video đơn máy (single-device), dọn stale lock, bọc env -u PYTHONPATH, và định dạng báo cáo chuẩn B5 (2026-09-06).
- `references/feed-watchdog-midnight-rollover-and-process-detection-20260906.md` — Quy chuẩn Watchdog báo cáo phiên nuôi acc: chống chốt non báo cáo khi phiên Ca 3 vắt qua nửa đêm, nhận diện tiến trình CLI multi-machine-feed-session và cơ chế rollback state (2026-09-06).

- `references/workbook-update-lazy-import-and-canary-b4-resync-20260905.md` — Quy chuẩn xử lý lỗi [WORKBOOK_UPDATE_FAILED] do lazy-import automation_core.workbook khi đã post thành công, cơ chế fallback openpyxl và lệnh Canary B4 đồng bộ cursor workbook (2026-09-05).
- `references/upload-hook-exact-error-extraction-and-html-escape-20260905.md` — Quy chuẩn trích xuất lỗi upload đa tầng (report.json -> stderr -> stdout -> exit code), cấm gán nhãn chung chung upload_subprocess_nonzero và escape HTML an toàn cho Farm Alert Telegram (2026-09-05).
- `references/shift-upload-lock-inprocess-coordination-case104-20260905.md` — Quy chuẩn khóa kép In-Process threading.RLock() + Inter-Process file lock, fast scandir và chuẩn hóa deadline_config chống lỗi timeout/quá giờ đăng video Phiên 3 (Case 104, 2026-09-05).
- `references/farm-alert-telegram-photo-limits-and-script-alerts-20260905.md` — Quy chuẩn Farm Alert: giới hạn caption ảnh 1024 ký tự Telegram, tách 2 tin giữ ảnh banner đỏ, fail-closed claim chống nuốt lỗi mạng, và alert cấp pipeline/script tổng (2026-09-05).
- `references/tiktok-upload-subprocess-error-extraction-and-camera-profile-guard-20260905.md` — Quy chuẩn bóc tách lỗi chi tiết upload thay vì báo generic upload_subprocess_nonzero, bảo vệ HTML escape trong alert, và chống nhận nhầm Camera vs Profile root/video playback (Case 82 & Case 83) (2026-09-05).

- `references/gmail-reg-workbook-persistence-and-storage-rules-20260904.md` — Phân định cơ chế lưu trữ dữ liệu Register Gmail: WORKBOOK_GUARD chặn ghi đè trực tiếp khi test canary, luồng single-writer merge_success_results cho batch night chain, và vai trò 3 file Excel đích (gmail_clean_v2, master_gmail_manager, taikhoan_dat_v2) (2026-09-04).
- `references/avatar-edit-recovery-share-card-and-launcher-filter-20260904.md` — Quy trình recovery mở màn hình Sửa hồ sơ avatar: vuốt kéo header Profile về đỉnh, đóng bẫy thẻ Chia sẻ hồ sơ / Tìm bạn bè, tap avatar circle, mở rộng nhận diện bottom sheet Thư viện, và fix lọc danh sách máy chọn lọc trong launcher batch (2026-09-04).
- `references/farm-alert-module-metadata-and-avatar-triage-20260903.md` — Quy chuẩn tầng alert automation_core: tự động ánh xạ metadata quy trình (avatar/feed/video/reg/2fa), cấm hardcode fallback về feed session, và checklist triage màn hình Thay đổi ảnh (2026-09-03).
- `references/avatar-batch-post-feed-orchestration-20260903.md` — Quy trình tự động hóa chuỗi upload avatar ngay sau khi ca nuôi kết thúc: kiểm tra avatar 2 bên, sync assignment manifest và cơ chế idle detection kích hoạt launcher canonical MaxParallel 40 (2026-09-03).
- `references/avatar-cdn-upload-wait-and-no-early-back-20260903.md` — Quy chuẩn upload avatar: cấm gọi adapter.back() hay force-stop sớm trước khi CDN nhận ảnh (chờ 8-12s), visual fallback cho nút Tiếp (Next 1) khi XML rỗng, và xác minh live avatar bằng RGB variance (2026-09-03).
- `references/avatar-picker-empty-xml-next-button-fallback-20260903.md` — Xử lý nút Tiếp (Next 1) màu đỏ trong photo picker khi uiautomator rỗng XML (tọa độ `935, 1810` / `824..1032, 1728..1860`) tránh kẹt timeout AVATAR_CROP_OPEN_FAILED (2026-09-03).
- `references/avatar-upload-flow-optimization-and-reboot-proxy-bypass-20260903.md` — Tối ưu hóa luồng up avatar: nạp media trước khi mở menu, gộp polling nút Tiếp (o_9/xip/wrj/rts/sca) 25s thay vì 360s, và gỡ bỏ proxy-watcher gate khi soft reboot trong mạng Wi-Fi Router Proxy (2026-09-03).
- `references/avatar-only-batch-and-picker-triage-20260903.md` — Quy trình chạy standalone batch upload avatar qua `run_tiktok_upload_avatar.ps1`, triage phân biệt lỗi ACCOUNT_MISSING vs file sai, và cơ chế fallback tap nút Tiếp `(924, 1842)` khi resource-id thay đổi (2026-09-03).
- `references/avatar-upload-profile-scroll-and-story-crop-20260902.md` — Quy chuẩn cuộn Profile về đỉnh trước khi click nút bút chì Sửa hồ sơ, chống bẫy anti-fraud deep-link, xử lý màn hình Cắt/Story và cấu hình MaxParallel 40 cho batch up avatar (2026-09-02).
- `references/avatar-account-missing-vs-avatar-wrong-triage-20260903.md` — Triage "up ava sai": phân biệt ACCOUNT_MISSING (nick chưa login, workflow chưa tới ENSURE_AVATAR) với avatar file sai; checklist file đĩa 2 nơi + log batch UTF-16 + lock/no-lock + khung giờ ca nuôi (2026-09-03).
- `references/random-render-antidetect-and-aspect-fit-20260827.md` — Quy chuẩn ánh xạ Tik5 (Slot 5, dải 5..637 <- 321..400), nâng cấp Anti-Detection A/V sync, in-line noise floor và tự động nhận diện video ngang 16:9 để fit_pad viền đen bảo toàn 100% nội dung (2026-08-27).
- `references/cohort-target-tik-field-validation-and-stale-lock-purging.md` — Quy chuẩn validate target identity không bắt buộc key `tik`, quy trình dọn stale device-locks sau sự cố preflight và cơ chế chờ của watchdog khi batch đang chạy cuối phiên (2026-08-28).
- `references/tiktok-upload-recovery-and-fingerprint-handling.md` — Quy trình recovery upload, gỡ kẹt receipt stale `POST_SUBMISSION_UNKNOWN`, kỷ luật chạy song song (parallel stagger 3s, timeout 600s) và đối soát post (2026-10-02).
- `references/infra-metrics-30vs40-workers.md` — Đánh giá hiệu năng và đo đạc lỗi thuần hạ tầng (ADB transport, socket, device lock, USB bus) giữa 30 workers và 40 workers (2026-08-25).
- `references/tiktok-batch-upload-triage-and-vpn-rules.md` — Quy tắc xử lý non-interactive TTY bypass, kiểm tra VPN live tại RESOLVE_DEVICE và phân loại tiến độ batch upload 16 workers.
- `references/tiktok-upload-live-proxy-ip-and-isolation-20260824.md` — Quy tắc bắt buộc kiểm tra live proxy IP (verify_live_ip=True qua ViChanger GET_IP), cách ly device-lock giữa batch upload và cron feed, và entrypoint chuẩn scripts.tiktok_workflow.
- `references/upload-hook-verification-and-runtime-provenance.md` — Phân biệt hook dispatch với upload thành công, đọc `upload_result.json`/`log.jsonl`, kiểm tra non-interactive prompt và xác minh runtime revision trước khi retry.
- `references/batch-upload-cron-isolation-rules.md` — Quy tắc bắt buộc tạm dừng cron feed khi kích hoạt manual batch upload để tránh tranh chấp thiết bị và lỗi navigation.
- `references/taadaa-cleanup-retention-protocol.md` — Quy tắc bắt buộc backup trước khi dọn dẹp thư mục D:\Taadaa; danh mục log change pass / reg mail / credentials cấm xóa tuyệt đối.
- `references/tik3-resume.md` — exact prior Tik3 command, launcher skip behavior, the

  wrong-entrypoint failure transcript.

- `references/tik3-render-avatar-20260816.md` — Tik3 render exact command (fixed

  tik3_multi_batch.py flags), avatar NEW-rule scripts, folder-structure facts, lock rule.

- `references/nuoi-acc-feed-batch.md` — exact nuoi acc feed-batch recipe: preflight, the

  PYTHONPATH-cleared launch, scheduler re-enable note, and first-30s verification.

- `references/youtube-botcheck-camoufox-20260816.md` — qua bot-check YouTube: Camoufox →
  export cookies Netscape → `yt-dlp --cookies-file`; proxy-pool format/pitfalls (đảo thứ tự
  user@host, 407 khi parallel, test bằng kênh VN); SABR pitfall của browser_download.
- `references/gmail-reg-preflight-and-cooldown-rules-20260827.md` — Quy tắc tính cooldown Gmail chỉ lọc @gmail.com, bỏ date cell khi đọc device serial, dùng AdbClient .run() cho ATX session UI dump và nhận diện chính xác provider Google Samsung S7 (2026-08-27).
- `references/night-chained-reg-gmail-tiktok-pipeline.md` — Quy trình vận hành & cấu hình chuỗi Cron đêm tự động (00:00) Reg Gmail -> Reg TikTok, xử lý capture output Hermes, fix lỗi PowerShell quoting / Workbook mismatch, và lọc false alarm NativeCommandError / parse summary.txt / summary.json (2026-09-08).

  user@host, 407 khi parallel, test bằng kênh VN); SABR pitfall của browser_download.

