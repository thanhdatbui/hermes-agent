---

name: taadaa-farm-batch-ops

description: "Re-run / resume farm batch jobs (TikTok upload, Tik3 render, reg, nuoi acc) using the EXACT canonical command that worked before. Resume semantics, no reinventing entrypoints, no restart-from-scratch."

version: 1.0.0

author: Hermes Agent

tags: [tiktok, farm, batch, render, upload, resume, kibe]

---



# Taadaa Farm Batch Ops


## 🛑 STOP GATE (bắt buộc — chi tiết: skill taadaa-farm-ops-rules)
Máy live + script chạy/lỗi → KHÔNG tự sửa code, KHÔNG tự chạy lại, KHÔNG tự probe/tay khi chưa được user yêu cầu.
Lỗi → screencap → gửi ẢNH THẬT (MEDIA:<path> dòng riêng, KHÔNG bọc markdown, KHÔNG gửi đường dẫn text) → DỪng chờ user hướng dẫn.
User hướng dẫn bước nào → encode bước đó vào script + test → mới chạy lại. Nghi ngờ → HỎI.

Re-running or resuming a farm batch job on the kibe/admin farm (Tiktok-video,

Tiktok_Reg, tiktok-luot nuoi acc repos).



## When to use

- User says "chạy tiếp", "resume", "y như bữa", "chạy lại cho tik3/tik2", or asks to

  continue a render/upload/reg batch that was run before.

- After a machine reset / crash interrupted a long batch and you must pick it back up.



## Core rule (from user, non-negotiable)

**Run the EXACT command that worked before. Do NOT substitute a different script or

entrypoint.** If the prior success used `run_tik3_random_render.ps1`, use that — do NOT

call `tik3_multi_batch.py` or any other module even if it looks equivalent. Different

entrypoints read different config/mapping and fail.



UPDATE 2026-08-16: `tik3_multi_batch.py` WAS fixed in-repo (find_headers now falls back

to the `Folder Video` column when no `sttvideo` column exists), so it IS a valid

entrypoint for Tik3 render now — but only when launched with the proven flag set:

`--min-videos 45 --parallel 1 --allow-existing-output --resume-complete --execute`

(start-output/start-source from the workbook row). See `references/tik3-render-avatar-20260816.md`.



This is the same as the standing farm rule: reuse the canonical script; never write a

new runner. If the canonical script lacks support, FIX+TEST that script — don't replace it.



## Steps

1. `session_search` for the exact prior command (query the launcher name + flags, e.g.

   `run_tik3_random_render StartMachine AutoRun`). Copy it verbatim — including

   `-Parallel`, `-Slot`, `-AutoRun`, working dir.

2. To RESUME (continue partial work, not restart): add ONLY flags that already exist in

   the original launcher (e.g. `-ResumeVerifyExisting`, `-OnlyExistingOutput`). Do not add

   new logic or a different script.

3. Launch as background process (`terminal` background=true, notify_on_complete=true).

4. Poll the first ~20s of log to confirm resume behavior (see Pitfalls).



## Pitfalls

- **Never delete rendered output files. EVER.** batch_render.py auto-skips outputs that

  already exist (`skipped: N.mp4 ... output da ton tai`). If a folder has 40/45 files,

  RE-RUN the render — it skips the 40 and renders only the missing 5. Deleting the 40 to

  "start clean" forces re-rendering from scratch (wasted hours + user anger 2026-08-16:

  "Lại tự ý xoá mà đéo hỏi"). The only safe partial-render flags are

  `--allow-existing-output --resume-complete` (allow-existing lets batch_render skip

  existing; resume-complete records workbook for already-complete folders).

- **Don't restart from scratch.** "Running the launcher again" is usually a RESUME:

  canonical launchers auto-skip existing valid outputs. Verify by reading the log — lines

  like `skipped: 3.mp4 -> 3.mp4 (output da ton tai)` or `(output da duoc ffprobe xac

  nhan)` mean safe resume, NOT overwrite.

- **Don't kill a process that is resuming.** If you launched without `-ResumeVerifyExisting`

  and the log shows "skipped" lines, it is already resuming correctly — do NOT kill it

  thinking it overwrites. Only kill if you launched a genuinely wrong entrypoint. (Burnt:

  killed a correctly-resuming Tik3 process, then had to relaunch.)

- **Don't invent entrypoints.** User feedback was explicit: "bữa chạy đc thì cứ y v mà

  chạy chứ chế cháo clgt" (just run what worked, stop cooking up alternatives).

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
  - ⚠️ **Worker Concurrency (MaxParallel 40)**: Launcher `run_tiktok_upload_batch.ps1` hỗ trợ `-MaxParallel 40` (cho phép chạy song song tối đa 40 runners theo yêu cầu vận hành farm).
  - ⚠️ **Ánh xạ Row và Tik Workbook**: Row 1 = `Tik1.xlsx` (Ca 1), Row 2 = `Tik2.xlsx` (Ca 2), Row 3 = `Tik3.xlsx` (Ca 3), Row 4 = `Tik4.xlsx` (Ca 4).
  - ⚠️ **Pitfall Profile Grid Scroll & Edit Profile Button (Cập nhật 2026-09-01)**: Sau bước `ACCOUNT_READY` quét đếm video, trang Profile thường bị cuộn lửng xuống dưới khiến nút Sửa hồ sơ / icon bút chì cạnh username (`849, 552`) bị khuất khỏi viewport. Bắt buộc swipe kéo về đỉnh trang Profile (`input swipe 540 400 540 1500`) trước khi click Sửa hồ sơ; lọc bỏ các nút banner như `ct8` ("Tạo") hoặc tab icon để không click nhầm tạo video. Tuyệt đối không để script fallback gọi deep-link `snssdk1233://profile/edit` vì TikTok sẽ chặn popup *"Hoạt động không có sẵn"*.
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
  - ⚠️ **Xử lý Media Fingerprint Ledger bị kẹt `reserved` (`MEDIA_FINGERPRINT_PENDING`):** Khi một lần chạy upload bị ngắt quãng giữa chừng sau khi đã push video, file hash trong `D:\CodexRuntime\tiktok-video\idempotency\media-fingerprints\<hash>.json` có thể bị kẹt ở trạng thái `"status": "reserved"`, khiến các lần chạy sau bị dừng ở checkpoint `MANUAL_REVIEW`. Khắc phục: Tìm file ledger tương ứng của máy trong thư mục trên và xóa (unlink) để hệ thống cho phép chạy lại fresh.
  - ⚠️ **Đối soát máy thiếu ID TikTok (`MISSING_ID`):** Nếu `TikN.xlsx` bị trống cột `ID` (bị skip ở preflight), đối soát ngay với file nguồn `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx` theo đúng số máy và Folder Video của ca tương ứng (Ca 1: folder 1..80, Ca 2: folder 81..160 hoặc dải tương ứng) để điền bổ sung ID và set `Kiểm Tra Dữ Liệu = OK`.
  - ⚠️ **Xử lý kẹt UI, Mất ATX Session & Recent Activity (`.recents.RecentsActivity` / `ATX_SESSION_UNAVAILABLE`):** Khi máy kẹt Recent app hoặc mất session UI, chạy tuần tự:
    1. Kill uiautomator cũ: `adb -s <serial> shell pkill -9 -f uiautomator`
    2. Bật lại daemon: `adb -s <serial> shell /data/local/tmp/atx-agent server -d`
    3. Force-stop app: `adb -s <serial> shell am force-stop com.ss.android.ugc.trill`
    4. Bấm Home thoát Recent: `adb -s <serial> shell input keyevent 3`
  - ⚠️ **Sự khác biệt giữa Runner cũ (PowerShell) và Hook mới (Subprocess):** Bản PowerShell cũ chạy được vì nó pipe token `"YES"` vào stdin con (`$ConfirmationToken | & $Python`). Khi chuyển sang subprocess trong runner Python, nếu script target có `input()` sẽ bị kẹt/crash vì không có bàn phím tương tác. Tuyệt đối không quy kết nhầm sang lỗi cron/reg Gmail.
  - ⚠️ **Thống kê Batch Upload & Tiến độ thực tế:** Tiến độ upload theo batch (mặc định 20 parallel) phải theo dõi qua tiến trình thật và file `TikN.xlsx` (cột `Video Đã Đăng`). Không kết luận toàn bộ farm fail khi các máy mới chỉ đang nằm trong hàng đợi hoặc đang xử lý các state UI/Post/Verify. Cần phân loại rõ ràng: (1) Đã thành công tăng video; (2) Đang chạy; (3) Lỗi trống ID TikTok trong workbook; (4) Lỗi thiết bị offline.
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
  - ⚠️ **Phân định rõ kiến trúc Workbook Sync (DAT ➔ SAFE vs TIKN độc lập):**
    - `taikhoan_run_safe.xlsx` (nuôi feed): Tự động sync 100% từ `taikhoan_dat_v2_updated .xlsx` qua cron `taikhoan-run-safe-sync`.
    - `Tik1..Tik6.xlsx` (đăng video): Đồng bộ 1-chiều từ `taikhoan_dat_v2_updated .xlsx` qua `sync-tik-workbooks.py`.
    - ⚠️ **Quy chuẩn `is_valid_tiktok_id` (Tuyệt đối không blacklist username thật, cập nhật 2026-08-31):** Trong `is_valid_tiktok_id`, chỉ lọc các link HTTP/URL (`http://`, `https://`, chứa `/`), chuỗi rác (`none`, `null`, `ghjfghj`, `chua_co`) và chuỗi thuần số. TUYỆT ĐỐI KHÔNG blacklist các từ khóa/chuỗi username hợp lệ (như `ngomai.ly`, `vo.my`, nick có dấu chấm `.` ở giữa tuân thủ regex `^[a-zA-Z0-9_.]{2,24}$`) để tránh xóa nhầm ID tài khoản hợp lệ thành `MISSING_ID` trong `TikN.xlsx`.
  - ⚠️ **Quy tắc Tổng kết Báo cáo Watchdog Nuôi Acc (Feed Session Watchdog, cập nhật 2026-08-31):**
    - **Merge Multi-run an toàn:** Khi một phiên chạy nhiều đợt quét (chạy chính + chạy vét), dùng các hàm merge nguyên tử (`merge_follow_result`, `merge_machine_result`, `merge_upload_result`). Cờ `FOLLOW_FAILED` và toàn bộ lượt follow/upload thành công ở bất kỳ đợt nào đều được giữ nguyên, không bị đợt sau ghi đè thành `skipped`.
    - **Phân biệt lượt chạy sạch 0 follow với lỗi:** Khi follow hook kết thúc với `exit_code: 0`, `status: "OK"`, `failed: 0` nhưng `followed: []` (do target `following == 0` hoặc đã follow hết qua `zero-following-skip-v2`), đây là lượt chạy thành công an toàn, TUYỆT ĐỐI KHÔNG gom vào mục `Lỗi script/xác minh`.
    - **Thời điểm chốt báo cáo:** Bắt buộc kiểm tra `is_feed_runner_active()` và chỉ phát báo cáo khi toàn bộ runner của phiên đã dừng hẳn, tránh chốt non giữa chừng làm thiếu hụt số lượng máy thực tế.
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
  - Chu kỳ cron `device-locks-watchdog` phải duy trì `every 15m` (không để `every 120m` vì thời gian phát hiện và cảnh báo lock quá trễ). Script chỉ gửi tin khi `len(locks) > 0` và im lặng khi `len(locks) == 0`.

- **min-videos DOWNLOAD CHỐT 30 (16/08 đêm).** User phân tích: follow kênh chủ yếu từ
  FOLLOW CHÉO farm (~80-90%), tự nhiên chỉ 10-20% → video không quyết định follow; cần
  ~20-30 video đủ "độ dày" chống flag khi follow chéo dồn (kênh 2-3 video nhận 500 follow
  = pattern → shadow-ban). min 45 khó tìm nguồn (454 kênh → 267 qualified; hạ 30 → nhiều
  hơn hẳn). Đã sửa constraint 42→30 ở CẢ `download_by_niche.py` + `source_pool_builder.py`
  ("yeu cau 30 <= min"). Download/qualify dùng `--min-videos 30 --target-videos 60
  --max-videos 65`; qualify lại ra `sources.qualified30.json`. Source folders
  are pre-verified complete (enough videos already downloaded) — don't gate on min-video
  checks; just render.

- **Report cadence & background job etiquette (User chốt 2026-08-27, cập nhật 2026-08-31):** Khi batch đang tải/render ở background (đã có cron watchdog báo định kỳ mỗi 60 phút hoặc mỗi 10 folder), giữ im lặng tuyệt đối. **CẤM spam thông báo lỗi exit code/retry của tiến trình con hay báo cáo tiến độ lẻ tẻ** khi hệ thống đang tự động phục hồi ("Thì đang down bth đừng có báo nữa"). Khi báo cáo kết quả các đợt chạy farm batch/cron, **TUYỆT ĐỐI CẤM spam từng dòng per-machine `[OK] Machine X...` / `[WARN] Machine Y...`**. BẮT BUỘC chỉ báo định dạng ngắn gọn chuẩn:
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

- **Worker/spam-IP (user đổi ý 3 lần, CHỐT CUỐI 16/08 đêm, cập nhật scale 2026-08-24):** "tăng worker lên làm" →
  ip à thế thì thôi" → "Download cũng k đc tăng worker sợ dính spam ip à" → cuối cùng
  **"tăng thêm worker dùng proxy khác trong pool proxy đc k" = ĐƯỢC**. CHỐT: **worker ↑
  OK nếu kèm `--proxy-pool` xoay** (mỗi thread 1 proxy khác IP → không spam cùng IP). Đã
  chạy `--parallel 4 --proxy-pool <xlsx> --cookies-file`. KHÔNG tăng worker khi KHÔNG có
  proxy xoay.
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



## Register Gmail & TikTok Chained Night Batch Ops (00:00 Night Cron)

- **Repo liên quan:** `D:\Taadaa\register gmail` + `D:\Taadaa\Tiktok_Reg`
- **Mục tiêu:** Tự động hóa chuỗi chạy ban đêm: 00:00 khởi chạy batch Reg Gmail (`run_all.ps1`) -> Xong Gmail tự động kích hoạt `_run_all_targets.py` để lấy mail mới tạo đăng ký TikTok.
- **Entrypoint Canonical:**
  - Script tổng hợp: `D:\Taadaa\Tiktok_Reg\scripts\run_night_chain_pipeline.py`
  - Launcher Hermes: `C:\Users\Kibe\AppData\Local\hermes\scripts\night_chain_reg_pipeline_launcher.py`
  - Cron Job: `night-chain-reg-pipeline` (ID: `38ea60c09825`, lịch `0 1 * * *`, deliver `telegram:-5139245637` - nhóm Gmai reg).
- **Quy tắc vận hành & Chốt an toàn:**
  - **Kế thừa cấu hình gốc:** `run_all.ps1` tự động lọc cooldown (mặc định 5 ngày), max 15 máy/batch, kiểm tra VPN preflight trên từng máy.
  - **Tự động bốc target:** `_run_all_targets.py` tự gọi `_detect_clean.py` so khớp mail sạch từ `gmail_clean_v2.xlsx` với các máy chưa đủ 6 acc trên `taikhoan_dat_v2_updated .xlsx`.
  - **Quy tắc thoát app/lỗi:** Chỉ khi SUCCESS mới thoát/về Home; máy bị lỗi kẹt lại giữ nguyên màn hình hiện trường theo đúng thiết kế gốc của script. Ca nuôi acc 06:00 sáng tự có preflight dọn dẹp app trước khi vào phiên.
  - **Khóa máy (Lock):** Tuyệt đối KHÔNG tự động lock máy; chỉ lock khi có lệnh trực tiếp từ user.
  - **Báo cáo kết quả:** Gửi đúng 1 tin nhắn tổng kết duy nhất về nhóm Telegram `Gmai reg` (`-5139245637`).

### Pitfalls & Bài học đã fix (2026-08-19)
- **Hermes `no_agent: true` cron output capture & false-positive "provider timeout" alert:**
  - File launcher trong `~/.hermes/scripts/` bắt buộc phải `capture_output=True` từ subprocess và flush thẳng ra `sys.stdout` (`sys.stdout.write`) thì Hermes mới nhận diện có output để đẩy tin nhắn về Telegram (nếu subprocess không pipe stdout thì Hermes báo `Status: silent (empty output)`).
  - Khi script `no_agent: true` kết thúc với exit code 1 (do một số máy trong batch fail) và trong stdout/stderr có chuỗi "timed out" (ví dụ: `proxy readiness timed out`), bộ tóm tắt lỗi của Hermes (`_summarize_cron_failure_for_delivery`) sẽ nhận diện nhầm thành `⚠️ Cron '<job>' failed: provider timeout. Fallback chain was exhausted or unavailable`. Khi gặp thông báo này, kiểm tra ngay file log thực tế tại `~/.hermes/cron/output/<job_id>/<timestamp>.md` để đọc báo cáo thành công/thất bại thực sự của farm thay vì nhầm tưởng là lỗi model AI.
- **PowerShell multi-line string escape với Python inline:** Trong file `.ps1`, tránh dùng khối `@' ... '@` nhiều dòng gọi `python -c` khi có dấu ngoặc kép hoặc `raise RuntimeError("...")` vì PowerShell dễ parse sai dấu đóng ngoặc `)` dẫn đến `SyntaxError: '(' was never closed`. Hãy gói thành chuỗi 1 dòng `"import ...; print(...)"` chuẩn (dùng `sys.exit('...')` để an toàn khi chạy Python `-O`/`-OO`).
- **Lệch cột Excel trong `taikhoan_dat_v2_updated .xlsx`:** Cột `device ID` (cột 10) bị ghi đè ngày giờ `2026-08-18 18:27:39` và dồn serial sang cột 11 (hoặc dòng bị thiếu serial `None`) sẽ làm `_detect_clean.py` của `Tiktok_Reg` chặn toàn bộ batch với lỗi `DETECTION_BLOCKED: TARGET_INVENTORY_CONFLICT` hoặc `TARGET_INVENTORY_MISSING_SERIAL`. Fix: sửa đúng cột trên `taikhoan_dat_v2_updated .xlsx` rồi chạy `taikhoan_sync_cron_launcher.py` để sync sang `taikhoan_run_safe.xlsx`.
- **Assignment Manifest 80 máy:** File `register-gmail.json` trong `automation-core/assignments/` phải khai báo đủ `machine:1` đến `machine:80`, nếu thiếu máy nào launcher `run_all.ps1` sẽ fail ở bước preflight `TARGET_OUTSIDE_ASSIGNMENT:machine:X`.
- **`subprocess.run` Windows pipe decode crash (`UnicodeDecodeError: 'utf-8' codec can't decode byte 0xa0`):** Khi bọc `powershell.exe` hoặc ADB qua `subprocess.run(..., capture_output=True, text=True)`, Windows console có thể in ký tự CP1258/CP1252/byte lạ (`0xa0`). BẮT BUỘC thêm `encoding="utf-8", errors="replace"` trong `subprocess.run()` để tránh crash reader thread.

- **Nguồn TikTok song song với YouTube & Direct Fallback (2026-08-22):**
  - Cào danh sách video TikTok bằng `yt-dlp` yêu cầu bắt buộc header `User-Agent` Chrome + `Referer: https://www.tiktok.com/` trong `http_headers`.
  - Khi tải stream MP4 đơn lẻ bị TikTok chặn (`Unexpected response from webpage request`), script tự động kích hoạt `download_tiktok_direct()` qua API TikWM để tải trực tiếp video không watermark, tránh lỗi `download_no_media`.


## references/

- `references/avatar-cdn-upload-wait-and-no-early-back-20260903.md` — Quy chuẩn upload avatar: cấm gọi adapter.back() hay force-stop sớm trước khi CDN nhận ảnh (chờ 8-12s), visual fallback cho nút Tiếp (Next 1) khi XML rỗng, và xác minh live avatar bằng RGB variance (2026-09-03).
- `references/avatar-picker-empty-xml-next-button-fallback-20260903.md` — Xử lý nút Tiếp (Next 1) màu đỏ trong photo picker khi uiautomator rỗng XML (tọa độ `935, 1810` / `824..1032, 1728..1860`) tránh kẹt timeout AVATAR_CROP_OPEN_FAILED (2026-09-03).
- `references/avatar-upload-flow-optimization-and-reboot-proxy-bypass-20260903.md` — Tối ưu hóa luồng up avatar: nạp media trước khi mở menu, gộp polling nút Tiếp (o_9/xip/wrj/rts/sca) 25s thay vì 360s, và gỡ bỏ proxy-watcher gate khi soft reboot trong mạng Wi-Fi Router Proxy (2026-09-03).
- `references/avatar-only-batch-and-picker-triage-20260903.md` — Quy trình chạy standalone batch upload avatar qua `run_tiktok_upload_avatar.ps1`, triage phân biệt lỗi ACCOUNT_MISSING vs file sai, và cơ chế fallback tap nút Tiếp `(924, 1842)` khi resource-id thay đổi (2026-09-03).
- `references/avatar-upload-profile-scroll-and-story-crop-20260902.md` — Quy chuẩn cuộn Profile về đỉnh trước khi click nút bút chì Sửa hồ sơ, chống bẫy anti-fraud deep-link, xử lý màn hình Cắt/Story và cấu hình MaxParallel 40 cho batch up avatar (2026-09-02).
- `references/avatar-account-missing-vs-avatar-wrong-triage-20260903.md` — Triage "up ava sai": phân biệt ACCOUNT_MISSING (nick chưa login, workflow chưa tới ENSURE_AVATAR) với avatar file sai; checklist file đĩa 2 nơi + log batch UTF-16 + lock/no-lock + khung giờ ca nuôi (2026-09-03).
- `references/random-render-antidetect-and-aspect-fit-20260827.md` — Quy chuẩn ánh xạ Tik5 (Slot 5, dải 5..637 <- 321..400), nâng cấp Anti-Detection A/V sync, in-line noise floor và tự động nhận diện video ngang 16:9 để fit_pad viền đen bảo toàn 100% nội dung (2026-08-27).
- `references/cohort-target-tik-field-validation-and-stale-lock-purging.md` — Quy chuẩn validate target identity không bắt buộc key `tik`, quy trình dọn stale device-locks sau sự cố preflight và cơ chế chờ của watchdog khi batch đang chạy cuối phiên (2026-08-28).
- `references/tiktok-upload-recovery-and-fingerprint-handling.md` — Quy trình xử lý lỗi UI bằng script recovery mode, cấm chạy đè batch upload khi feed session chưa dứt điểm và quản lý fingerprint reservations (2026-08-26).
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
- `references/night-chained-reg-gmail-tiktok-pipeline.md` — Quy trình vận hành & cấu hình chuỗi Cron đêm tự động (00:00) Reg Gmail -> Reg TikTok, xử lý capture output Hermes và fix lỗi PowerShell quoting / Workbook mismatch.

  user@host, 407 khi parallel, test bằng kênh VN); SABR pitfall của browser_download.

