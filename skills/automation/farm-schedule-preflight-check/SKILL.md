---
name: farm-schedule-preflight-check
description: Kiểm tra máy rảnh an toàn trước khi chạy các batch reg / login / upload — tránh xung đột với lịch Cron nuôi acc (TikTok feed/follow).
---

# Farm Schedule Preflight Check

References:
- `references/farm-asset-001-account-protection-and-logout-guard.md` — Quy tắc FARM-ASSET-001 bảo vệ tài sản nick TikTok, cấm tự ý gán nhãn nick rác/lạ để logout, CHỈ logout nick ký sinh (owner_stt != current_stt) đã OCR xác minh, xử lý nick không có trong Excel là Data Desync, và fix bẫy watchdog double-lock collision (25/09/2026).
- `references/farm-asset-001-parasite-only-logout-and-unrecorded-asset-protection.md` — Deep-dive FARM-ASSET-001: anatomy bài học xương máu @annhubvqttr (nick bị logout nhầm khi Excel trống nhưng Gmail sống), invariant cấm tự gán nhãn, quy trình 4 bước khi gặp Data Desync, technical guard `logout_guard.py`, kỷ luật Memory vs Repo (25/09/2026).
- `references/preflight-reg-bu-slot-desync-and-backfill-gate-20260925.md` — Triage cảnh báo máy đủ 8 acc nhưng Excel thiếu slot: đối soát SQLite/Workbook/Safe Workbook, đóng băng không reg/logout, và chỉ backfill khi đủ ID/PASS/GMAIL/PASS MAIL với atomic write.
- `references/data-desync-backfill-and-worker-timeout.md` — Contract backfill theo exact row/slot, phân biệt safe source với combined output, readback bắt buộc và circuit-breaker khi worker timeout.
- `references/cross-farm-parity-and-dual-cluster-auto-provisioning.md` — Nguyên tắc Parity 100% Kibe ↔ Admin (Kibe có gì Admin phải có nấy), quy chuẩn tự động hóa reg bù dual-cluster, định tuyến ADB socket và cơ chế gate follow <10 video (24/09/2026).
- `references/bidirectional-device-lock-and-force-stop-rules.md` — Quy chuẩn Device Lock 2 Chiều (ép cứng user_authorized=True, cấm bypass opt-in), quy tắc quyền force-stop khi test đồ, cơ chế Cron Reaper tháo lock treo 1h TTL, nghiệm thu mail dongvanfb.net ID 57 Zin 100% reg thành công nick @lethanhlan14 trên Máy 22, bài học xử lý sự cố nick ký sinh (Máy 61 bị login nhầm nick anggiathinh2905 của Máy 28 kẹt trần 8 acc) và quy trình đăng xuất sạch trên Máy 201 (23-24/09/2026).
- `references/excel-preflight-validator-and-cluster-invariants.md` — Chuẩn hóa 5 Invariant Rules cho toàn bộ file Excel của Farm (Tik1..Tik8 + taikhoan_run_safe), giải quyết triệt để lỗi lệch dòng, trùng video gốc, văng nick Switcher và cơ chế Fail-Fast Gate bảo vệ 2 cụm Kibe & Admin (17/09/2026).
- `references/evening-phase2-rolling-safety-gate.md` — Quy tắc vàng: CHỈ mở cuốn chiếu sau Phiên 2 Ca tối (20:15 - 23:45), khóa chặt khe P1-P2 (35-60p) chống tranh chấp thiết bị S7 với cron nuôi acc chính (17/09/2026).
- `references/per-machine-rolling-chaining-and-avatar-gpm-flow.md` — Kiến trúc cuốn chiếu theo từng máy (Per-Machine Rolling Pipeline) sau Phiên 1 (18:45) và Phiên 2 (20:15) Ca tối: Up avatar -> Login GPM & Dual OAuth nối tiếp, loại bỏ hoàn toàn farm-level all-done blocks và khung giờ tĩnh (16/09/2026).
- `references/row-provisioning-and-cron-sync-discipline.md` — Quy tắc bắt buộc về vị trí slot khi reg bù (Row thiếu nào điền đúng Row đó, cấm điền dồn), loại bỏ hoàn toàn reg sau ca nuôi, và quy trình sync cron deployment (12/09/2026).
- `references/active-cohort-takeover.md`
- `references/night-and-evening-watchdog-chaining.md` — Quy tắc Watchdog tự động canh nhả lock sau Ca 3 (Up avatar, GPM login Dual OAuth) và sau Ca 4 đêm (Dọn cache TikTok), loại bỏ mốc giờ tĩnh (14/09/2026).
- `references/multi-host-cron-sync-and-reporting.md` — Cơ chế tự động đồng bộ Cron jobs.json + scripts toàn farm và kỷ luật phân tách báo cáo Kibe vs Admin (14/09/2026).
- `references/gmail-reg-ui-detours-and-error-triage.md`
- `references/tiktok-cadence-and-8acc-capacity.md`
- `references/zombie-summary-prevention-and-adaptive-idle-watcher.md` — Xử lý báo cáo ma (Zombie Summary trong pipeline đêm do crash fallback nhặt log cũ & lỗi thiếu batch_start_time trong ensure_row_accounts.py) và mẫu Watchdog động (Adaptive Lock Watcher) canh máy rảnh tự động thay vì đoán mốc giờ tĩnh (12-24/09/2026).
- `references/parasite-account-logout-and-zombie-summary-fix.md` — Quy chuẩn đăng xuất nick ký sinh an toàn qua Settings (xác nhận user không bị mất session các nick khác), cơ chế xử lý Zombie Summary trong ensure_row_accounts và dọn dẹp zombie adb.exe giải phóng cổng 5037 (24/09/2026).
- `references/live-manifest-safe-idle-extraction.md` — Trích xuất máy rảnh an toàn (đệm >= 60-90p) từ live assignment manifest ngày hiện tại (12/09/2026).
- `references/gmail-canary-password-loss-and-workbook-persistence.md` — Bắt buộc ghi log pass & fallback atomic Excel khi chạy lẻ/canary, chống mất pass do thiếu cờ result-dir (12/09/2026).
- `references/gmail-2fa-fresh-account-delay-and-cron-policy.md` — Quy tắc hoãn bật 2FA sau 24-48h ngâm, ngắt hook bật 2FA ngay sau reg chống loop xác minh của Google, 3 tầng bảo vệ chống xung đột cron nuôi acc, phân tích bản chất On-Device Webview challenge (reCAPTCHA) vs kiến trúc chuẩn Web Playwright + S7 Security Code Bridge trong GPM auto, kỷ luật chặn stub report ảo và silent watchdog (16/09/2026).
- `references/gmail-fresh-account-survival-and-newsletter-warmup.md` — Kỹ thuật giữ sống Gmail ngâm 48h bằng hook đăng ký Newsletter tự động (inbound traffic) và quy hoạch bật 2FA sau ca trưa 15:00 (12/09/2026).
- `references/gmail-chatgpt-ondevice-warmup-hook.md` — Hook đăng ký ChatGPT on-device Samsung S7 qua Google OAuth thay thế newsletter ảo, triệt tiêu false-positive, xử lý dialog Chrome/màn hình pwd và kỷ luật preflight check live (15/09/2026).
- `references/s7-android8-account-cleanup-and-preflight-checklive.md` — Gỡ tài khoản DIE trên Samsung S7 Android 8 qua SYNC_SETTINGS, preflight checkmail.live và lưu log gmail_die_tong.txt (15/09/2026).
- `references/cron-duration-assumption-and-idle-slot-selection.md` — Cạm bẫy tính thời lượng ca nuôi tĩnh (60-90p thực tế vs 40p lý thuyết), chuyển sang chọn máy trống slot (Zero-Account) hoặc Watchdog động (14/09/2026).
- `references/cron-watchdog-silent-and-anti-duplicate-alert.md` — Quy chuẩn watchdog no_agent=True: cấm gọi send_farm_alert song song stdout gây báo đúp, im lặng hoàn toàn khi 0 máy đủ điều kiện, cấm StreamHandler(sys.stdout) chống bẫy chia chunk (1/N) spam Telegram, quiet-on-success cho cron nuôi, và chặn spam lặp lại qua session key (15/09-02/10/2026).

Dùng trước khi khởi chạy bất kỳ batch tác vụ nào (Reg TikTok, Hotmail, Add Mail, Upload video, Reconcile...) để tìm danh sách máy rảnh, không đụng vào lịch nuôi acc tự động.

## 1. Nguyên Tắc An Toàn & Thực Thi
- **Luật Bất Biến Parity 100% Kibe ↔ Admin (Cái nào Kibe có Admin phải có nấy):** CẤM TUYỆT ĐỐI Coordinator tự suy diễn, bịa lý do lo ngại kẹt máy/timeout để phân biệt đối xử hoặc hardcode bỏ qua cluster Admin trong các cơ chế tự động (như `if cluster_name == "kibe":` ở khâu `_preflight_ensure_accounts`). Mọi tính năng tự động reg bù, mua Hotmail, sync an toàn đều phải kích hoạt bình đẳng cho cả 2 cụm.
  * **Marker Isolation:** File marker preflight BẮT BUỘC scoped theo cluster `.preflight_{cluster_name}_{window_key}`, cấm dùng marker global `.preflight_{window_key}` gây nghẽn (starvation) cụm chạy sau.
  * **Remote ADB Routing:** Chạy reg/tool cho Admin từ Kibe PC bắt buộc định tuyến `ADB_SERVER_SOCKET="tcp:192.168.110.119:5037"` và nạp `TAADAA_HOST_CONFIG="D:/Taadaa/machine-config/admin.yaml"`.
  * **Admin Dynamic Workbook Mapping:** Với Admin (STT >= 201), `expected_tik = (m - 201) * 8 + slot`. File Admin là dạng dynamic append: nếu duyệt không thấy hàng khớp slot thì BẮT BUỘC append vào `ws_trk.max_row + 1`, CẤM TUYỆT ĐỐI bỏ qua.
- **Khoảng đệm an toàn:** Máy được chọn ưu tiên **rảnh trong suốt thời gian chạy + cách lịch nuôi acc kế tiếp tối thiểu 1 tiếng (60 phút)** khi chạy batch lớn thảnh thơi.
- **Kỷ luật Reg Bù Hàng Tài Khoản & Tuyệt Đối Điền Đúng Row Thiếu (Anti-Slot-Shift):**
  * Khi kích hoạt reg bù cho ca nào (Row 1..8), tài khoản mới reg thành công **BẮT BUỘC ghi vào đúng Row/Slot thiếu của ca đó** trong cả `taikhoan_dat_v2_updated .xlsx` và `taikhoan_run_safe.xlsx`.
  * **CẤM TUYỆT ĐỐI điền dồn lấp các slot trước:** Tuyệt đối không được tìm slot trống đầu tiên (ví dụ Row 5 đang trống mà ca hiện tại là Row 6 thì tuyệt đối KHÔNG được điền vào Row 5). Việc điền dồn sẽ làm lệch lịch nuôi và phân bổ account theo ca.
  * Đã loại bỏ hoàn toàn khái niệm "Reg sau ca nuôi": Hệ thống chỉ có (1) Preflight On-demand trước ca nuôi (`tiktok_runner.py` gọi `ensure_row_accounts.py <row>`) và (2) Chuỗi ban ngày sau Ca trưa `post-noon-chain-watchdog` (14:30 - 17:30: Reg Gmail -> Add 2FA TikTok). Đã XÓA HOÀN TOÀN cron đêm `night-chain-reg-pipeline` và bỏ hẳn nhánh Reg TikTok ban đêm.
- **Kỷ luật Đồng Bộ Cron Deployment (AppData, Git Deploy & OneDrive Shared):**
  * Script thực thi của Hermes nạp từ `~/AppData/Local/hermes/scripts/`, kho Git deploy lưu tại `deploy/hermes-home/scripts/`, kho share toàn farm lưu tại `D:/OneDrive/Taadaa_Sync_Shared/hermes-cron/scripts/`. Khi sửa đổi/pull bản mới từ git repo, Coordinator BẮT BUỘC đồng bộ sang cả 3 thư mục trên.
  * Tự động đồng bộ cấu hình CSDL Cron `jobs.json`: Mọi thay đổi về lịch/deliverable cron trên Kibe được tự động phản chiếu sang `deploy/hermes-home/cron/jobs.json` và `OneDrive_Shared/hermes-cron/jobs.json` qua `cron_sync_watchdog.py`, đảm bảo script kéo `sync-from-kibe.ps1` trên Admin luôn nhận bản cấu hình 21 jobs mới nhất.
  * Subprocess trong cron script phải dùng `target_python()` (`D:/Taadaa/python-envs/automation/Scripts/python.exe`), cấm dùng `sys.executable`.
- **Cơ chế Lock-Aware tự bảo vệ của Cron nuôi acc:**
  * Runner nuôi acc (`hermes_cron_runner`) luôn kiểm tra `device-locks` trước khi spawn.
  * Nếu máy đang bị lock do tác vụ Reg/Fix đang chạy, Cron nuôi acc sẽ **tự động ghi nhận `SKIPPED_DEVICE_LOCKED` và chỉ bỏ qua DUY NHẤT 1 phiên (slot) nuôi đó**, tuyệt đối KHÔNG can thiệp, KHÔNG chạy đè và KHÔNG làm hủy toàn bộ cả ca nuôi lớn. Các phiên sau khi máy đã mở khóa sẽ tiếp tục chạy bình thường.
- **Quy ước khi User yêu cầu on-demand chạy reg/task ngay:**
  * Khi user yêu cầu "chọn N máy chạy reg" hoặc "chạy batch ngay", agent thực hiện khóa máy (`DEVICE_LOCK_ENABLED=1`) và khởi chạy ngay các máy có target hợp lệ.
  * Nếu chỉ chạy một subset N máy (không chạy hết toàn bộ target phát hiện), dùng `TIKTOK_REG_SKIP_STTS="<list STT bỏ qua>"` khi gọi `_run_all_targets.py`.
- **Phân biệt lệnh "Giả lập/Giả định là [giờ/lịch] rồi kích hoạt chạy" vs "Dry-run":**
  * Khi user yêu cầu *"Giả lập là giờ là 1h đêm rồi kích hoạt chạy xem có lỗi không"* hoặc *"Giả định tới giờ chạy... lock lại chạy"*: User có ý định **KÍCH HOẠT CHẠY THẬT (LIVE RUN)** chạm thiết bị thật trên một tập máy mẫu nhỏ (ví dụ 2 hoặc 5 máy, cờ `--live --limit N`), BẮT BUỘC KHÓA THIẾT BỊ VẬT LÝ (`user_authorized=True`), để kiểm tra thực tế xem thiết bị và flow live có lỗi hay không.
  * **Tuyệt đối CẤM:** Chỉ chạy dry-run/preview không chạm thiết bị khi nhận lệnh này. Chỉ dùng dry-run khi user nói rõ "dry-run", "chỉ preview", hoặc "không chạm thiết bị".
- **Quy tắc Dữ liệu Kho Mail & Tracking:**
  * `gmail_clean_v2.xlsx` là **KHO MAIL LIVE**: Mail sau khi reg TikTok thành công **KHÔNG ĐƯỢC XÓA** khỏi `gmail_clean_v2.xlsx`. Chỉ xóa khi mail die/bị gỡ thực sự.
  * `taikhoan_dat_v2_updated .xlsx` là **BẢNG TRACKING TIKTOK**: ID TikTok đăng ký thành công bắt buộc phải nằm cùng dòng với Email thực tế đã dùng để đăng ký.
- **Quy ước ngầm định khi User yêu cầu "máy rảnh chạy reg TikTok":**
  * Tự động kết hợp 3 điều kiện: (1) Máy rảnh lịch cron (cách ca nuôi >= 60p), (2) Máy có target mail hợp lệ chưa đăng ký trong inventory/source workbook (`_detect_clean.py`), và (3) Máy đã kết nối VPN proxy an toàn (`verify_live_ip=True` / `GET_IP result=200`). Tuyệt đối không chỉ lọc máy rảnh lịch thuần túy rồi liệt kê máy không có mail hoặc chưa có VPN.
- **Quy tắc Lock & Error screen:**
  * **Hard Invariant khi User giao việc làm tay / Canary / Probe:** *"Kể cả khi User giao việc cho agent làm, agent BẮT BUỘC phải lock lại (sau khi kiểm tra máy rảnh) và sau đó không cron nào được chiếm."* Bắt buộc acquire lock vật lý (`user_authorized=True`, `status="running"`) ra `~/.codex/device-locks/machine_<M>.lock.json` trước khi chạm thiết bị, tạo khiên chắn để mọi cron nền (Reg Gmail, 2FA, feed session) tự động skip né máy đó ra.
  * Khóa thiết bị (`DEVICE_LOCK_ENABLED=1` / `acquire_device_lock`) khi bắt đầu chạy batch / on-demand theo lệnh user ("lock lại khi làm nhé"). CẤM TUYỆT ĐỐI các launcher/module (như `machine_inventory.py`) bypass hay bỏ kiểm tra lock.
  * **Vòng đời Lock:** Duy trì lock xuyên suốt toàn bộ quá trình chạy. **CHỈ mở khóa khi máy hoàn thành SUCCESS (đã lưu tracking & dọn dẹp app về Home) HOẶC khi User trực tiếp ra lệnh mở khóa.**
  * Script chạy batch / on-demand 2FA / reg: Nếu FAIL/Lỗi hoặc chờ OTP/Captcha/Anchor thì giữ nguyên hiện trường màn hình lỗi, chụp ảnh screencap gửi user, giữ nguyên lock, không tự ý đóng app hay unlock. Preflight ca nuôi 06:00 sẽ tự dọn trước khi swipe.
- **Lệnh thực thi trực tiếp (Không dừng lại hỏi / Không dừng ở bước mua mail):** Khi user yêu cầu "chọn N máy chạy <task>" hoặc "mua N hotmail reg các máy...", agent BẮT BUỘC thực hiện luồng khép kín liên tục không ngắt quãng:
  1. Mua tài khoản (BoxTaiKhoan API gói 60 OAuth2) & xác thực OAuth2 token.
  2. Nạp tài khoản vào `gmail_clean_v2.xlsx`.
  3. Khởi chạy NGAY batch reg `_run_all_targets.py` (`DEVICE_LOCK_ENABLED=1`, background + monitor), tuyệt đối không dừng lại ở bước mua/nạp để báo cáo nửa chừng khiến user phải giục.
  4. Đồng bộ CSDL ngay sau khi batch kết thúc (`scripts/apply_deferred_tracking_results.py`).
- **Không áp đặt giới hạn cứng dải máy:** Việc giới hạn số lượng máy ở bất kỳ dải nào (như 75-80) chỉ thực hiện khi user yêu cầu cụ thể trong phiên, không tự động đặt rule cứng.
- **Kỷ luật Canh Máy Rảnh Tự Động (Chống Đoán Giờ Tĩnh - Adaptive Lock Watcher):**
  * **CẤM TUYỆT ĐỐI:** Cài đặt cron với mốc giờ tĩnh cố định (vd `09:15:00`) để chờ máy chạy xong ca. Máy thực tế có thể dump XML chậm, uiautomator reload, hoặc nghẽn mạng khiến lock bị giữ lâu hơn, dẫn đến xung đột hoặc crash khi đến giờ hẹn.
  - **MẪU CHUẨN BẮT BUỘC:** Sử dụng Watchdog động (`gmail_idle_canary_watchdog.py` pattern) thăm dò chu kỳ 3-5 phút:

  ### Bounded monitor/preemption phase protocol (M11/individual machine preemption)
  - Khi operator yêu cầu thực hiện phase monitor/preemption cho một máy đơn lẻ (ví dụ M11) với lệnh không phá hủy:
    1. Kiểm tra song song cả 2 aliases: `machine_<M>.lock.json` và `serial_<SERIAL>.lock.json` (kiểm tra status, owner PID, parent PID, `pinned`, `user_authorized`, `last_heartbeat`).
    2. Xác thực liveness của owner PID từ hệ điều hành qua `psutil.pid_exists(pid)`. Nếu PID còn sống và lock pinned/active -> lock hợp lệ.
    3. Rà soát codebase xem có API cooperative drain request (`drain_requested`, `RESUME_TICKET`, `EXIT_YIELD = 75`) hay không.
    4. **Quy tắc An Toàn Fail-Closed:** Nếu codebase chưa hỗ trợ runtime cooperative drain (chỉ có cờ `force_preempt=True` phá lock thô bạo): TUYỆT ĐỐI CẤM force-preempt, cấm xóa file lock, cấm chạy canary. Trả về cấu trúc `CHECKPOINT: LOCK_HELD` với `drain_reservation.exact_command: null`, `result: NOT_ISSUED`, và ủy quyền quyết định `next_action` cho supervisor bên ngoài.

  ### One-shot restore/login watcher — tránh tự khóa chính mình
  - Khi watcher gọi một runner đã tự `acquire_device_lock()` (ví dụ `tiktok_login_v1.py`), **không được acquire lock bao ngoài rồi gọi runner con**. Nếu làm vậy, runner con sẽ thấy lock của watcher và trả `NEEDS_USER_DECISION`/exit 2. Chọn đúng một chủ sở hữu lock: watcher chỉ quan sát lock rồi launch runner; runner tự acquire/release lock.
  - Trước live action phải kiểm tra cả `machine_<M>.lock.json` và `serial_<SERIAL>.lock.json`, đối soát status (`running`, `active`, `queued`, `queued_v2`) với PID thực tế. Không xóa lock còn owner sống; lock stale chỉ được xử lý bởi reaper chuẩn.
  - Runner timeout hoặc thất bại UI là `FINAL_BLOCKED` cho tick đó, không retry mù trong cùng tick. Ghi stdout/stderr + ảnh/XML checkpoint; giữ máy an toàn và để tick sau xử lý theo backoff.
  - Nếu UI hiện One-tap/“Chào mừng bạn trở lại” với nick đã có sẵn, đây là **resume existing asset**, không phải luồng thêm tài khoản mới: tap đúng nick đã xác minh, rồi chỉ tiếp tục khi có bằng chứng post-action. Nếu chuyển sang “Xác minh email” thì dừng ở trạng thái chờ OTP, không báo success.
  - Watcher chỉ được pause/remove sau khi verifier xác nhận account mục tiêu xuất hiện trong Switcher bằng XML + screenshot; exit=0, PID đã chạy, hoặc workbook đã có dòng không phải bằng chứng thiết bị đã khôi phục.


    1. Quét trực tiếp file lock vật lý tại `~/.codex/device-locks/machine_<M>.lock.json`. BẮT BUỘC máy phải đã giải phóng toàn bộ lock thật sự.
    2. Đọc manifest ngày hiện tại (`runtime/kibe/cron-state/manifests/<DATE>/`): Tính toán khoảng cách đến slot nuôi kế tiếp phải $\ge 60$ phút (khoảng đệm an toàn).
    3. Thỏa mãn cả 2 điều kiện $\rightarrow$ Kích hoạt ngay lệnh on-demand / canary live.
    4. Tự hủy / dừng watchdog (Single-Run / One-shot) ngay sau khi máy hoàn tất để trả lại trạng thái sạch.
- **Quy tắc Tái thử (Retry Discipline) khi Reg Gmail thất bại:**
  * Nhóm Phone Verification (`10, 26, 59...`): **TUYỆT ĐỐI CẤM thử lại ngay**, tự động gắn cờ Cooldown 4 ngày (`cooldown 4d`).
  * Chỉ được phép thử lại (retry on-demand) đối với nhóm máy dính lỗi script / UI detours (`01, 02, 36, 47...`). Xem chi tiết tại Section 6 và `references/gmail-reg-ui-detours-and-error-triage.md`.

- **Phân Bổ Khung Giờ Máy Rảnh & Chiến Lược Vận Hành Farm (80 Máy):**
  - **Kỷ luật Delivery Cron Watchdog về Farm Alert:** Toàn bộ các watchdog/cron farm có phát sinh kết quả vận hành (`post-morning-gmail-2fa-watchdog`, `post-noon-chain-watchdog`, `post-evening-avatar-watchdog`, `post-evening-gpm-login-watchdog`, `end-of-day-clear-tiktok-cache`, `tiktok-feed-session-watchdog`, `farm-render-download-watchdog`) BẮT BUỘC cấu hình delivery đích danh về nhóm Farm Alert (`telegram:-5373649734`). CẤM để `deliver='origin'` hay topic lẻ làm trôi báo cáo.
  - **Kỷ luật Giữ Delivery Group Sau Cập Nhật Cron:** Khi cập nhật schedule hoặc script của các cron watchdog (ví dụ đổi lịch `end-of-day-clear-tiktok-cache`), BẮT BUỘC giữ nguyên `deliver='telegram:-5373649734'`, tuyệt đối không để rơi về `local` hay `origin`.
  - **Kỷ luật Tách Biệt Báo Cáo Kibe vs Admin:** Các tác vụ farm dùng chung gửi về Farm Alert (`telegram:-5373649734`) bắt buộc có prefix `[FARM REPORT][KIBE]` hoặc `[FARM REPORT][ADMIN]`. Các tác vụ giám sát nội bộ (stale watchdog, trim files) gửi về kênh riêng của từng host (`origin` trên Kibe, `telegram:-5188753741` trên Admin).
  - **Kỷ luật Đồng Bộ Cron Toàn Farm Tự Động:** Cron `cron-sync-watchdog` chạy mỗi 15p tự động đồng bộ `jobs.json` từ Kibe sang Git Deploy và `OneDrive_Shared/hermes-cron/`. Trên bot Admin chỉ cần chạy lệnh 1 chạm: `python D:\OneDrive\Taadaa_Sync_Shared\tools\setup_admin_cron.py`.
  - **Kỷ luật Supervisor OmniRoute Watchdog (:20129):** File supervisor `omniroute_watchdog.ps1` tuyệt đối CẤM dùng `$pId` (PowerShell không phân biệt hoa thường sẽ đè biến hệ thống `$PID` read-only gây crash), tăng timeout health probe lên 15s và grace period lên 90s để chống tự kill nhầm khi subagents tạo tải song song.
  - **Lịch nuôi acc chính thức 4 Ca x 2 Phiên / ngày (Cập nhật chuẩn xác 2026-09-13):**
  - **Ca 4 (Đêm):** Phiên 1 lúc `00:00` (Feed only), Phiên 2 lúc `01:30` (Feed + Upload). Chạy Row 8 (ngày chẵn) / Row 7 (ngày lẻ).
  - **Ca 1 (Sáng):** Phiên 1 lúc `06:00` (Feed only), Phiên 2 lúc `08:00` (Feed + Upload). Chạy Row 2 (ngày chẵn) / Row 1 (ngày lẻ).
  - **Ca 2 (Trưa):** Phiên 1 lúc `11:35` (Feed only), Phiên 2 lúc `13:30 - 14:05` (Feed + Upload). Chạy Row 4 (ngày chẵn) / Row 3 (ngày lẻ). Xong toàn bộ ca trưa trước `15:05`.
  - **Ca 3 (Tối):** Phiên 1 lúc `17:45` (Feed only), Phiên 2 lúc `19:35 - 20:10` (Feed + Upload). Chạy Row 6 (ngày chẵn) / Row 5 (ngày lẻ). Xong toàn bộ ca tối trước `21:10`.
  - **Dead Zone:** Từ `03:00` đến `05:59` sáng: Toàn bộ 80 máy nghỉ lướt feed, làm mát thiết bị, dọn cache (`end-of-day-clear-tiktok-cache` chạy 04:00).
  - **Quy tắc Upload Hook:** Phiên 1 CẤM upload. Phiên 2 lướt feed xong tự động đăng video nếu máy có video theo Row trong ca đó.

- **Bản Đồ Phân Bổ Các Watchdog / Cron Sau Từng Ca:**
  1. **Sau Ca 1 (Sáng 08:30 -> 11:30):** `post-morning-gmail-2fa-watchdog` (Schedule: `*/5 8,9,10,11 * * *`) — Bật 2FA Gmail cuốn chiếu cho các acc đủ tuổi ngâm sau ca sáng.
  2. **Sau Ca 2 (Trưa 14:30 -> 17:30):** `post-noon-chain-watchdog` (Schedule: `*/5 14,15,16,17 * * *`) — Chạy chuỗi ban ngày: Reg Gmail ➔ Add 2FA TikTok (đã bỏ hoàn toàn Reg TikTok).
  3. **Sau Ca 3 (Tối 20:15 -> 23:45 - Cuốn Chiếu An Toàn Sau Phiên 2):**
     - **KHÓA TUYỆT ĐỐI KHE P1-P2 (17:35 - 20:15):** Khoảng nghỉ giữa 2 phiên chỉ 35-60p, CẤM TUYỆT ĐỐI mở watchdog trong khe này tránh tranh chấp lock S7 với phiên nuôi 2.
     - `post-evening-avatar-watchdog` (Schedule: `*/5 20,21,22,23 * * *`) — Mở từ 20:15 sau khi các máy đầu tiên xong Phiên 2. Máy nào xong P2 nhả lock là kích hoạt upload avatar cuốn chiếu ngay cho các nick chưa có avatar.
     - `post-evening-gpm-login-watchdog` (Schedule: `*/5 20,21,22,23 * * *`) — Mở từ 20:15. Cuốn chiếu nối tiếp theo từng máy qua `is_machine_avatar_ready(mid)`: máy nào xong P2 và đã có avatar (hoặc vừa up avatar xong) là bốc vào Login GPM & Dual OAuth ngay lập tức (tối đa 10 workers song song), không chờ toàn farm.
  4. **Sau Ca 4 (Đêm 01:00 -> 05:30):**
     - `end-of-day-clear-tiktok-cache` (Schedule: `*/10 1,2,3,4 * * *`) — Chuyển từ mốc cố định 04:00 sang cơ chế Watchdog tự động: canh Ca 4 hoàn tất (`is_ca4_finished`) và lock toàn farm giải phóng sạch thì kích hoạt dọn cache TikTok đa luồng ngay lập tức.
  5. **Đã hủy bỏ hoàn toàn:** Cron đêm `night-chain-reg-pipeline` (01:00) và nhánh Reg TikTok đêm. Tuyệt đối không nhắc lại cron này.
- **Giới hạn dung lượng máy & Trần Reg TikTok (Max 8 accs/máy):** Toàn farm đã nâng cấp thiết kế lên tối đa 8 tài khoản TikTok/máy (hỗ trợ reg và nuôi Row 7 & Row 8). Khi máy đã có $\ge 8$ TikTok ID trong sheet `'Tài Khoản'` của `taikhoan_dat_v2_updated .xlsx` $\rightarrow$ Preflight (`tiktok_target_eligibility.py`) tự động loại bỏ khỏi detector reg, không cấp thêm mail.
- **Chốt chặn 2 tầng chống lỗi trần 8 acc TikTok:**
  * Tầng 1 (Preflight): Bắt buộc đọc tường minh sheet `'Tài Khoản'` (tránh cạm bẫy `openpyxl.active` sheet trả về rỗng). Nếu đếm $\ge 8$ acc $\rightarrow$ skip máy.
  * Tầng 2 (Device Runtime Gate trong `social_reg_v1.py`): Đếm số nick trong Account Switcher. Nếu đủ 8 nick thật trên app, ghi log `MACHINE_FULL_8_ACCOUNTS`, đóng switcher về Home và thoát gracefully; tuyệt đối CẤM crash `RuntimeError` tìm nút "Thêm tài khoản".
- **Khử trùng mail nguồn toàn cục (`select_pending_targets`):** Mỗi email chỉ được cấp cho duy nhất 1 máy trong cả batch. Khi nạp kho `gmail_clean_v2.xlsx`, bắt buộc kiểm tra deduplicate chống gán 1 email vào nhiều máy.
- **Xử lý tài khoản bị lệch/đăng nhập nhầm trên 2 máy:** Đối chiếu `taikhoan_dat_v2_updated .xlsx` (sheet `'Tài Khoản'`) và `taikhoan_run_safe.xlsx` để xác định máy chuẩn. Nếu 2 máy cùng chứa 1 nick, BẮT BUỘC báo cáo user chỉ đạo, CẤM tự ý sửa Excel.
- **Quy trình xử lý nick ký sinh / đăng nhập nhầm (Logout an toàn từ Settings):**
  * Khi máy bị đăng nhập nhầm nick của máy khác (nick ký sinh làm đầy trần 8 acc, ví dụ Máy 61 dính `anggiathinh2905` của Máy 28): **ĐƯỢC PHÉP VÀ HOÀN TOÀN AN TOÀN ĐĂNG XUẤT TRỰC TIẾP TỪ SETTINGS** (User xác nhận: *"Log out kí sinh đc mà k lỗi đâu"*, flow chuẩn trong `watchdog_idle_parasite_reconcile.py`).
  * **Quy trình 4 bước chuẩn:**
    1. Mở Switcher (`open_account_dropdown`), tap chuyển sang đúng nick ký sinh mục tiêu.
    2. Vào Hồ sơ -> Menu 3 gạch (`tap(1005, 150)`) -> chọn *Cài đặt và quyền riêng tư*.
    3. Cuộn xuống đáy trang Settings, tap nút *Đăng xuất* -> Xác nhận popup Đăng xuất.
    4. TikTok chỉ đăng xuất riêng nick đó và tự động chuyển về các nick còn lại trong Switcher. Mở lại Switcher để chụp ảnh nghiệm thu (`MEDIA:...`). CẤM lo sợ nhầm lẫn làm trì hoãn giải phóng slot.
- **Kỷ luật nghiệm thu tài khoản:** Ảnh nghiệm thu (`MEDIA:<path>`) BẮT BUỘC chụp tại **Account Switcher** (Bottom sheet Chuyển đổi tài khoản) thể hiện rõ danh sách nick active. CẤM TUYỆT ĐỐI chụp ảnh màn hình Cài đặt & quyền riêng tư, popup xác nhận, Home hay màn hình Hồ sơ trắng rồi báo cáo xong.
- **Khung giờ rảnh cho tác vụ on-demand/tay:**
  - **Khung Đêm - Sáng sớm (`23:30` → `05:30`):** Toàn bộ 80 máy rảnh, mạng & proxy ổn định. Runner nuôi acc silent từ `02:00` đến `05:59`.
  - **Khung Trưa (`10:00` → `11:45`):** Thích hợp chạy on-demand (Login kiểm kê, Reg TikTok bù/fix tay).
  - **Khung Chiều (`16:30` → `18:15`):** Thích hợp chạy on-demand lẻ/canh tay.

## 2. Lệnh / Script Check Nhanh Máy Rảnh (Direct Manifest JSON Parser O(1))
Chạy đoạn Python sau từ terminal để lấy danh sách máy rảnh theo thời gian thực, đọc trực tiếp file manifest `assignment-v1-*.json` của ngày hiện tại (chống lỗi `MANIFEST_IDENTITY_MISMATCH` và trường `account_id` khi source hash thay đổi):

```python
import json, glob, os
from datetime import datetime, timedelta

now_dt = datetime.now()
day_str = now_dt.strftime("%Y-%m-%d")
manifest_pattern = rf"D:\Taadaa\runtime\kibe\cron-state\manifests\{day_str}\assignment-v1-*.json"
files = glob.glob(manifest_pattern)
if not files:
    # Fallback thư mục manifest mới nhất
    dirs = glob.glob(r"D:\Taadaa\runtime\kibe\cron-state\manifests\*")
    if dirs:
        latest_dir = max(dirs, key=os.path.getmtime)
        files = glob.glob(os.path.join(latest_dir, "assignment-v1-*.json"))

if files:
    manifest_file = max(files, key=os.path.getmtime)
    with open(manifest_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    busy_machines = set()
    busy_window_end = now_dt + timedelta(hours=1.0) # đệm an toàn 60 phút

    for e in data.get("entries", []):
        st = datetime.fromisoformat(e["slot_time"]).replace(tzinfo=None)
        et = datetime.fromisoformat(e["slot_end"]).replace(tzinfo=None)
        m = e["machine"]
        if (st <= now_dt < et) or (now_dt <= st < busy_window_end):
            busy_machines.add(m)

    idle_machines = sorted(set(range(1, 81)) - busy_machines)
    print(f"Máy rảnh an toàn (cách ca nuôi >= 60p): {idle_machines}")
else:
    print("Không tìm thấy manifest hôm nay. Kiểm tra thư mục manifests.")
```

## 3. Lock Transient, Mapping Machine↔Serial & Vị Trí Lock Thực Tế (live 2026-09-14)

- **Vị trí thư mục Lock thực tế & CSDL Cooldown Reg Trong Ngày:**
  * Lock thiết bị hiện tại phân tán tập trung tại `~/.codex/device-locks/machine_<M>.lock.json` (thay vì `~\AppData\Local\automation-core\device-locks`), kiểm tra cả 2 nơi nhưng ưu tiên `~/.codex/device-locks` khi rà soát số lượng máy đang chạy (`running`) hoặc hàng đợi (`queued_v2`).
  * **Cạm bẫy API `inspect_device_lock` (Bắt buộc try/except `DeviceLockTransactionError`):** Khi gọi `inspect_device_lock(m)` từ `automation_core.device_lock`, nếu máy không có file lock vật lý (máy hoàn toàn rảnh), hàm **KHÔNG** trả về `None` mà ném ngoại lệ `DeviceLockTransactionError: DEVICE_LOCK_INSPECT_PATH_MISSING: operation=inspect path_index=0`. Bắt buộc script quét máy phải `except DeviceLockTransactionError:` để xác nhận máy là `FREE (no lock)`, tránh crash đột ngột trên máy rảnh đầu tiên.
  * **Cơ chế Cooldown Đăng ký Trong Ngày (`reg_daily_cooldowns.json`):** Quản lý tại `~/.codex/device-locks/reg_daily_cooldowns.json` (chốt chặn `REG_DAILY_COOLDOWN_ACTIVE` — tối đa 1 lượt reg/máy/ngày để bảo vệ thiết bị và IP).
    - Khi máy từng chạy reg trong ngày (dù `status: "in_progress"` từ ca trước hoặc `status: "success"`), bản ghi có `cooldown_until: YYYY-MM-DD` khóa máy đến hết ngày.
    - Preflight `ensure_row_accounts.py` / `_detect_clean.py` đọc qua `is_machine_reg_cooldown_active(machine)` và tự động đưa máy vào `⏸️ Bỏ qua / Cooldown (<N>): <list STT>`.
    - **Triage O(1) khi cần tra cứu lý do Cooldown:**
      1. Đọc trực tiếp `~/.codex/device-locks/reg_daily_cooldowns.json` kiểm tra trường `machines["<M>"]` (xem `date`, `pid`, `status`, `reason`).
      2. Đối soát thư mục artifact chạy trước đó trong ngày tại `D:/Taadaa/runtime/kibe/artifacts/runs/social-batch-all/<YYYYMMDD-*>/batch_*/stt_<M>/` để xác định ca chạy khởi phát.
- **Phân biệt Máy rảnh Cooldown Reg vs Device Lock (Active Feed/Upload Session):**
  * `is_machine_reg_cooldown_active = False` chỉ phản ánh máy không bị vướng cooldown giãn cách giữa 2 lần đăng ký tài khoản (reg cooldown).
  * **Tuyệt đối KHÔNG đồng nhất rảnh cooldown với máy rảnh thực tế:** Trước khi dispatch lệnh reg đơn lẻ hoặc canary (`social_reg_v1.py <STT>`), bắt buộc kiểm tra `~/.codex/device-locks/machine_<STT>.lock.json`.
  * Nếu máy đang có lock `status: "running"` từ tiến trình `run_tiktok.py --mode multi-machine-feed-session` (hoặc upload-hook): Máy đang trong phiên tương tác/upload live. `social_reg_v1.py` sẽ lập tức exit 1 với `[device-lock] SKIP register machine <STT>`.
  * **Hành vi xử lý:** Báo cáo ngay máy đang bận phiên feed/upload, tuyệt đối KHÔNG tự ý kill tiến trình nuôi acc hay force-stop TikTok khi lock còn hiệu lực.
- **File Output Cron trên Windows:** Các file log cron trong `~\AppData\Local\hermes\cron\output\<job_id>` bị tiến trình cron daemon giữ exclusive lock (PermissionError 13 / Error 5 Access Denied khi đọc trực tiếp). CẤM đọc trực tiếp các file này trong lúc cron đang chạy; thay vào đó, kiểm tra trạng thái qua `cronjob action='list'`, manifest JSON ngày hiện tại, hoặc đọc lock file JSON.
- **Lock file CÓ THỂ TRANSIENT**: thấy `machine_XX.lock.json` ở lần check này rồi biến mất vài phút sau (case máy 33: lock 22:52 → mất ~22:55). Quy tắc an toàn khi chọn máy cho task giới hạn: máy TỪNG xuất hiện lock trong cửa sổ chọn → coi là đang có hoạt động quanh nó, TRÁNH; chỉ chọn máy 0 lần thấy lock suốt cả phiên chọn + re-check ngay trước preflight.
- **Mapping nhanh machine→serial**: đọc thẳng `D:\Taadaa\runtime\kibe\cron-source\hermes_cron_source_config.json` — `feed_source.accounts[]` mỗi entry có `{account_id, machine, serial}`. Lưu ý: một số máy KHÔNG có entry feed_source (vd 75–80) → NO-SERIAL, loại khỏi ứng viên cần serial cụ thể. Nguồn thay thế đầy đủ hơn: `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx` (cột A=Máy, B=device ID) — có cả máy không nằm trong feed_source (vd máy 76). Đừng đoán mapping từ tên máy/hostname — luôn đi qua 1 trong 2 nguồn này.

### 3a. Active-cohort takeover gate (bổ sung từ live review 2026-08-31)

Khi user yêu cầu takeover đúng một máy đang nằm trong phiên feed đa máy, **không suy ra quyền takeover từ PID/run ID cũ hoặc artifact FINAL_BLOCKED trước đó**. Trước mọi side effect (ghi target, sửa nguồn mail, acquire lock, launch runner):

1. Đọc đồng thời cả hai alias lock của máy/serial; ghi hash, status, owner PID/host/project/run ID và `owner_active`.
2. Re-verify process identity/command line ngay tại thời điểm hành động. Nếu PID cũ đã chết nhưng lock đã được một owner mới nhận, owner mới là trạng thái có thẩm quyền.
3. Kiểm tra code path chính thức xem có **per-machine exclusion/relinquish** khỏi active cohort hay chỉ có guarded takeover cho lock inactive. Cờ `--full-scope-takeover` không tự chứng minh được takeover từng máy.
4. Nếu không có cơ chế official tách riêng máy khỏi active cohort, dừng fail-closed trước side effect với `FINAL_BLOCKED` và mã `DEVICE_LOCK_CONFLICT_ACTIVE_OWNER`; giữ nguyên lock active và không chạy runner thay thế.
5. Cấm dùng kill/taskkill parent, xóa/ghi đè lock, pause cả cron, hoặc chạy ad-hoc để “làm máy rảnh”. Artifact kết quả phải ghi `runner_started=false`, takeover chưa thực hiện, lock được preserve, và bằng chứng parent/current owner.
6. **Chiến lược Pivot sang máy ngang hàng (Peer Machine Pivot) cho On-Demand / Canary**: Khi máy mục tiêu ban đầu (ví dụ Máy 6) đang bị active cohort (`multi-machine-feed-session`) chiếm dụng, CẤM chờ đợi hay cố gắng can thiệp UI làm hỏng phiên nuôi acc. Quét ngay tập máy rảnh cùng lô (đối soát qua `summary.txt`, file `.success.json` của batch reg vừa rồi) để tìm máy rảnh 100% (không có lock file `running`/`queued_v2`, launcher activity idle, online ADB như Máy 22) và chuyển canary sang máy rảnh đó ngay lập tức để nghiệm thu code mà không làm gián đoạn lịch farm.

Reference: `references/active-cohort-takeover.md`.

## 4. Đọc lịch theo ROW nick (2026-08-25)

- Manifest cron mỗi entry có field `account_row` — khi user hỏi/nêu điều kiện kiểu "hôm nay cron chạy row X", PHẢI group theo `account_row` rồi báo số máy từng row, đừng trả lời tổng quát. Lịch xen kẽ theo NGÀY (vd 21/08=row1+3, 22/08=row2+4, 23/08=row1+3) — row hôm nay ≠ row hôm qua.
- Slot của 1 máy có thể trải dài nhiều khung trong ngày; check "đang bận" phải xét TẤT CẢ slot hôm nay + mai (load_active cho 2 ngày), không chỉ block kế tiếp: máy có thể vừa nhả ca này nhưng còn ca khác sau <60'.
- Gate script mẫu (ready/busy/near<60'/offline/locked, JSON out): `C:\Users\Kibe\AppData\Local\hermes\scripts\f2a_row1_gate_check.py`.

## 5. Preflight Google Account Capacity & S7 Rolling Cleanup (Cập nhật 15/09/2026)

- **Trần tài khoản Google:** Cố định **5 tài khoản Google / máy S7** để đảm bảo RAM/heap không bị tràn và tránh Google Play Services kích hoạt flag lạm dụng thiết bị.
- **Preflight Check Live Tự Động Trước Khi Reg (Bắt buộc):**
  * Đọc toàn bộ danh sách Google accounts hiện có trên máy qua `dumpsys account`.
  * Quét real-time qua API/Playwright `checkmail.live` (`run_checkmail_kibe_farm.py`).
  * **Nếu phát hiện tài khoản DIE:** Gắn nhãn `DIE_ACCOUNT_FOUND` và **ƯU TIÊN KÍCH HOẠT GỠ NGAY LẬP TỨC**, không cần chờ máy đủ 5 tài khoản. Điều này giải phóng slot và triệt tiêu nguy cơ Google reCAPTCHA chặn các luồng OAuth/ChatGPT.
  * **Lưu vết kho DIE:** Mọi tài khoản DIE sau khi gỡ thành công bắt buộc tự động ghi log append vào `D:/OneDrive/TaadaaData/kibe/gmail_die_tong.txt` định dạng `<email>|M<machine>|<serial>|<datetime>` để phục vụ đối soát và purge khỏi `gmail_clean_v2.xlsx`.
- **Preflight Capacity & 3-Gate Rolling Cleanup:**
  - Nếu `< 5` accounts sống: `status: "OK"`, `can_reg: True`, `action: "NONE"`.
  - Nếu `>= 5` accounts: Đạt trần $\rightarrow$ phải đối soát 3-Gate Safety để tìm 1 acc cũ nhất gỡ cuốn chiếu (`NEED_CLEANUP`, `can_reg: True`).
  - Nếu `>= 5` accounts nhưng không có acc nào qua cả 3 chốt (chưa đủ 30 ngày ngâm hoặc chưa có OAuth/2FA): `FULL_NO_ELIGIBLE_CLEANUP`, `can_reg: False`, `action: "SKIP"`.
- **3 Safety Gates bắt buộc để gỡ acc cũ:**
  - Gate 1: Có Secret 2FA (`gmail_clean_v2.xlsx` cột 4 len $\ge 16$).
  - Gate 2: Đã nạp OAuth OmniRoute (`omniroute_success` trong `oauth_pipeline_status.json`).
  - Gate 3: Tuổi ngâm GPM / ngày tạo $\ge 30$ ngày.
- **Kỷ luật gỡ acc trên Samsung S7 (Android 8.0 / API 26):**
  * Bắt buộc khóa `acquire_device_lock(..., project="gpm-cleanup", force_preempt=True)` và gỡ trực tiếp trên OS Android (`android.settings.SYNC_SETTINGS`). **CẤM TUYỆT ĐỐI** vào web `myaccount.google.com` để gỡ từ xa (gây dính cooldown 7 ngày `signin/rejected?rrk=77`).
  * **Cạm bẫy dump UI tty:** Lệnh `exec-out uiautomator dump /dev/tty` trên Android 8.0 S7 trả về chuỗi rỗng hoặc bị Killed 137. BẮT BUỘC dùng hàm dump an toàn qua file trung gian `/sdcard/settings_dump.xml` hoặc `get_ui_xml()` từ `gmail_reg_v10.py`.
  * **Quy trình UI gỡ chuẩn:**
    1. Mở `am start -a android.settings.SYNC_SETTINGS`.
    2. Nếu màn hình đang kẹt ở chi tiết 1 account cũ (thấy *"Đồng bộ tài khoản"* hoặc *"XÓA TÀI KHOẢN"*): Tap nút Back trên header tại `(72, 144)` để ra danh sách tất cả tài khoản.
    3. Tap vào mục `Google` (nếu đang ở nhóm danh mục tài khoản).
    4. Tìm email mục tiêu (vuốt nhẹ nếu ở dưới đáy).
    5. Tap vào email $\rightarrow$ Tap nút `XÓA TÀI KHOẢN` trực tiếp hoặc tap menu 3 chấm `(1000, 150)` $\rightarrow$ chọn `Xóa tài khoản`.
    6. Xác nhận popup: tap nút `XÓA TÀI KHOẢN` tại tọa độ `(782, 1145)`.
    7. Bấm phím Home `input keyevent 3` đưa máy về trạng thái sạch.

## 6. Quy Tắc Retry & Phân Loại Lỗi Batch Reg Gmail (2026-09-07)

- **Chi tiết tham chiếu:** `references/gmail-reg-ui-detours-and-error-triage.md`.
- **Kỷ luật Retry (Phone Verify vs Script Error):**
  * **Nhóm Phone Verification (10, 26, 59...):** BẮT BUỘC bỏ qua, **TUYỆT ĐỐI KHÔNG THỬ LẠI NGAY**, tự động gắn cờ Cooldown 4 ngày (`cooldown 4d`). Thử lại liên tục khi Google đòi SĐT sẽ tăng trust penalty và làm liệt IP/thiết bị.
  * **Nhóm Lỗi Script / UI Detours (01, 02, 36, 47...):** **CHỈ ĐƯỢC PHÉP THỬ LẠI CHO NHÓM NÀY** sau khi đã điều tra và vá script/UI.
- **Xử lý UI Detours Samsung S7 (Android 7):**
  * Tự động dismiss popup cảnh báo OS cũ (*"Hãy cập nhật thiết bị để đảm bảo an toàn"*) tại bước chọn provider Google.
  * Khi Bento Account Switcher bị tràn danh sách: Cấm click nhầm SystemUI (`y < 300`), bắt buộc lọc `package="com.google.android.gm"`, `y >= 300` và thực hiện swipe cuộn màn hình để bộc lộ nút *"Thêm tài khoản khác"*.
- **Chuẩn hóa Encoding & Báo cáo Telegram:**
  * Giữ UTF-8 chuẩn trong mã nguồn, chống mojibake; phân nhóm gọn gàng các mã lỗi (`google provider error`, `proxy timeout`, `phone verification`, `proxy unavailable`) thay vì in chuỗi exception thô.
- **Đồng bộ Chốt Chặn Proxy Preflight (Proxy Gate Parity với TikTok Repos):**
  * Script `gmail_reg_v10.py` bắt buộc gọi `require_android_vpn(..., verify_live_ip=True)` và kiểm tra `proxy_ip` public thực tế khác rỗng.
  * Khi proxy bị lỗi (port chết, HTTP 502 Bad Gateway từ Singbox/MobiProxy): BẮT BUỘC fail-closed ngay lập tức (`[PREFLIGHT_PROXY]`), dừng quy trình và nhả lock, tuyệt đối không mở app Gmail để tránh vấp phải màn hình GMS No Network.

## 7. Giới Hạn Tần Suất Follow & Quy Hoạch 4 Ca Nuôi Acc (Max 8 Acc/Máy) (2026-09-09)

- **Chi tiết tham chiếu:** `references/tiktok-cadence-and-8acc-capacity.md`.
- **Cơ chế Hạn Mức Follow TikTok (Rolling 24h, Không Cộng Dồn):**
  * Hạn mức tính theo ngày/session; nghỉ 2 ngày **KHÔNG** làm tăng quota ngày thứ 3.
  * Ép 35 follow/ngày sau thời gian nghỉ dễ dính **Shadow-follow (Ghost follow)** và hạ trust tài khoản. Phân bổ đều 20-25 follow/ngày hoặc hạ trần 25-28 follow/ngày (chia 3 ca: 8-10/ca) giữ tỷ lệ follow thực cao hơn nhiều.
- **Điểm Nghẽn Lịch Trình Khi Nuôi 4 Ca/Ngày (Max 8 Acc/Máy: Row 1–8):**
  * Cấu trúc 1 Ca = 3 Phiên (Session 1, 2, 3) ngốn **~4.5 đến 5.5 tiếng/ca** (do giãn cách pair gap 35-60p).
  * 3 ca hiện tại (06:00, 12:30, 19:00) đã chiếm 13-14 tiếng/ngày. Nếu nhét thêm Ca 4 vào ban đêm (00:00 - 05:30) sẽ gây:
    1. **Xung đột trực tiếp với Cronjob đêm:** `avatar-post-feed-watchdog` (22:00–01:00), `end-of-day-clear-tiktok-cache` (04:00).
    2. **Quá nhiệt & Phồng Pin thiết bị:** Samsung S7 cày 18-19 tiếng/ngày màn hình sáng làm liệt ADB và crash uiautomator (`EXIT=137`).
    3. **Trust penalty:** Lướt feed đêm 2h-4h sáng dễ bị hệ thống chống gian lận gắn cờ bot.
- **Giải Pháp Quy Hoạch 4 Ca (Max 8 Acc/Máy):**
  * **Rút gọn số phiên:** Chuyển từ 3 phiên/ca xuống **2 phiên/ca** (mỗi phiên ~30-35p), rút ngắn mỗi ca còn **~2h - 2.5h**.
  * Phân bổ 4 ca gọn gàng ban ngày & tối: Ca 1 (06:00–08:30), Ca 2 (10:00–12:30), Ca 3 (14:30–17:00), Ca 4 (18:30–21:00).
  * Toàn bộ đêm từ **21:30 đến 05:30 sáng được giải phóng** cho Reg đêm, Up avatar, Dọn cache và làm mát máy.

## 8. Kỷ Luật Dispatch Tham Số & Đồng Bộ Cron Đa Máy (2026-09-11)
- **Chuỗi tham số dispatch nuôi acc bắt buộc:**
  * `tiktok_runner.py` (Hermes Cron) gọi PowerShell `run-feed-session.ps1` BẮT BUỘC truyền `-SessionIndex <1|2>`.
  * `run-feed-session.ps1` chỉ gắn cờ `--allow-upload-hook` khi `$SessionIndex -eq 2`.
  * `run_tiktok.py` nhận `--session-index` và nạp vào `config["_session_index"]`.
  * Tuyệt đối không bật cờ upload vô điều kiện cho mọi phiên, tránh vi phạm quy tắc chỉ đăng video ở Phiên 2.
- **Đồng bộ Cron sang máy Admin (Không bắt User làm tay):**
  * Khi user yêu cầu đồng bộ cấu hình cron sang Admin, cấm hướng dẫn user tự mở file hay paste JSON.
  * Soạn sẵn script thiết lập tự động (`D:/Taadaa/deploy/admin_cron_setup.py`) để bot Hermes trên máy Admin tự động tạo job, cấu hình path, và restart dịch vụ.

## 9. Kỷ Luật Stale Lock File & Preflight Watchdog Chuỗi Sau Ca (2026-09-13)
- **Cạm bẫy cờ `--force` trong Watchdog (`post_noon_chain_watchdog.py`):**
  * Trong thiết kế của `post_noon_chain_watchdog.py` và các watchdog tương tự, cờ `--force` chỉ bỏ qua các điều kiện:
    1. Cửa sổ thời gian (`in_window`: 14:30 - 17:30).
    2. Lịch sử đã chạy hôm nay (`already_ran_today`).
    3. Trạng thái ca nuôi trước đó (`is_ca2_finished`).
  * Nhưng `--force` **VẪN GIỮ NGUYÊN KIỂM TRA KHÓA THIẾT BỊ VẬT LÝ (`has_active_device_locks()`)**:
    ```python
    if has_active_device_locks() and not args.dry_run:
        return 0
    ```
  * Khi có lock file, script sẽ thoát âm thầm (exit code 0, không in log hay stderr).
- **Quy trình Triage Stale Locks & Trạng thái Lock Protocol V2 (`queued_v2`):**
  * BẮT BUỘC kiểm tra trạng thái lock trước: kiểm tra cả 2 thư mục `C:\Users\Kibe\AppData\Local\automation-core\device-locks` và `C:\Users\Kibe\.codex\device-locks`.
  * **Cạm bẫy `queued_v2`:** Lock protocol v2 sử dụng status `"queued_v2"`. Mọi hàm kiểm tra lock (`has_active_device_locks()`) phải xét cả `"queued_v2"` thay vì chỉ `("active", "running", "queued")` để tránh kích hoạt chuỗi đè lên hàng đợi đang chờ chạy.
  * Đối với các file lock có trạng thái `status: "blocked"` hoặc `status: "active"`:
    1. Đọc trường `pid` trong file lock.
    2. Dùng `psutil.pid_exists(pid)` để đối soát process có thực sự còn sống hay không.
    3. Nếu PID đã chết (`pid_exists == False`) hoặc `owner_active == False` từ lâu: Đây là **stale lock file** sót lại từ runner bị crash/kill trước đó.
    4. Tiến hành xóa các file stale `.lock.json` để nhả khóa sạch cho toàn farm trước khi gọi watchdog chạy `--force`.
  * **Xử lý kẹt socket ADB / Worker Hang trên máy đơn lẻ & Zombie ADB Server:**
    - Khi một máy đơn lẻ bị kẹt giao tiếp ADB (ví dụ S7 dính loop `reconnect device` hoặc `adb shell` timeout vô hạn), tiến trình worker của máy đó sẽ treo cứng và giữ lock, chặn script batch mẹ (`run_all.ps1`) kết thúc.
    - Quy trình xử lý O(1): Định vị đúng PID worker của máy đó qua command line (`gmail_reg_v10.py <M>`), kiểm tra phản hồi ADB (`adb -s <serial> shell ...` timeout <= 5s). Nếu treo cứng socket, terminate dứt điểm PID worker của riêng máy đó để script batch mẹ hoàn tất cuốn chiếu và nhả toàn bộ lock an toàn cho chuỗi tiếp theo.
    - **Nghẽn cổng ADB :5037 do Zombie adb.exe:** Khi server ADB bị treo, nhiều process con kẹt socket khiến thiết bị bị chuyển sang `offline` hoặc báo `could not read ok from ADB Server / cannot connect to daemon`: Chạy ngay `cmd.exe /c "taskkill /f /im adb.exe"` để quét sạch toàn bộ zombie process. Daemon sẽ tự khởi động lại sạch sẽ ở lệnh kế tiếp và đưa toàn bộ máy online trở lại.
  * **Cạm bẫy Zombie Summary trong `ensure_row_accounts.py`:**
    - Hàm `send_telegram_summary` nếu chỉ bốc thư mục chạy mới nhất (`dirs[0]`) mà không đối soát thời điểm chạy thực tế (`batch_start_time`) sẽ nhặt lại log lỗi cũ của đợt chạy trước (ví dụ Row 8 chạy trước đó bị gộp nhầm vào báo cáo Row 5). Bắt buộc phải gắn mốc thời gian lọc hoặc chỉ báo cáo khi batch hiện tại thực sự có phát sinh lượt chạy mới.
* **Ngân sách vòng lặp & Phản hồi nhanh (Anti-Overengineering):**
* Khi chạy batch/watchdog nền trong phiên agent, không spawn background process rồi chờ mù. Phải xác minh ngay bằng test nhanh preflight trong 1 lệnh script ngắn để phát hiện sớm lock tồn đọng thay vì tiêu hao vòng lặp vô ích.

## 10. Kỷ Luật Giữ Mốc Giờ Cron Cứng & Cấm Jitter Scheduler Bên Ngoài (2026-09-14)
- **TỬ HUYỆT VỠ LỊCH KHI SỬA GIỜ CRON TRÊN SCHEDULER:**
* **CẤM TUYỆT ĐỐI sửa đổi mốc giờ Cron của hệ thống (`jobs.json` hoặc cron schedule) để tạo độ trôi ngẫu nhiên (Jitter) bên ngoài scheduler.**
* *Lý do 1 (`tiktok_picker.py`):* Bộ lọc ngày logic quy định cứng `02:00 - 05:59` là Silent Window (vùng chết). Nếu cron bị trôi âm (chạy sớm lúc 05:50 - 05:59), picker coi là giờ cấm và tự động `exit 0` nuốt trọn cả ca sáng, toàn bộ 80-160 máy bị bỏ qua không chạy.
* *Lý do 2 (`feed_session_watchdog.py`):* Watchdog định nghĩa ranh giới Ca 1 Phiên 1 cứng là `["06:00", "08:00")`. Nếu runner chạy trước 06:00 (vd 05:55), kết quả run bị gom nhầm vào Ca 4 Đêm. Đến 08:00, Watchdog Ca 1 quét không thấy thư mục hợp lệ sẽ lập tức bắn **Farm Alert ĐỎ (-5373649734) báo "Ca 1 mất tích / Fail toàn tập"** gây hoảng loạn.
* *Lý do 3 (Dây chuyền Watchdog cuốn chiếu):* Các watchdog kế tiếp (`post-morning-gmail-2fa-watchdog` lúc 08:00, `post-noon-chain-watchdog` lúc 14:00) đều bám theo ranh giới ca chẵn để kích hoạt tự động.
- **GIẢI PHÁP AN TOÀN CHUẨN (IN-FLIGHT STAGGER & MICRO-JITTER):**
* Giữ nguyên 100% mốc giờ Cron hệ thống (`00:00, 01:30, 06:00, 08:00, 12:00, 14:00, 18:00, 20:00`).
* **Tầng 1 (Machine Start Stagger):** Sử dụng cờ `-MachineStartStaggerMs "2000,8000"` trong `run-feed-session.ps1` để trễ ngẫu nhiên 2s - 8s giữa các máy, xóa bỏ hoàn toàn đỉnh sóng kết nối đồng thời trên server ByteDance.
* **Tầng 2 (Session Dwell Micro-Jitter):** Nếu cần trôi giờ mở app, chỉ thực hiện bên trong runner PowerShell sau khi `runner_busy = True` (ngâm nhẹ 60s - 180s trước khi chạm máy đầu tiên). Lúc này Watchdog nhận diện runner đang hoạt động sẽ kiên nhẫn chờ, đảm bảo ca hoàn tất trước mốc ca tiếp theo ít nhất 30-40 phút an toàn tuyệt đối.




