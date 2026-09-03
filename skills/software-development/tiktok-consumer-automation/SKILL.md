---

name: tiktok-consumer-automation

description: Patterns, pitfalls, and proven workflows for TikTok consumer automation — ADB interaction, UI compatibility, VPN gating, 2FA, and reconciliation scripts on Samsung Galaxy farms (SM-G930F/W8).

---



# TikTok Consumer Automation


## 🛑 STOP GATE (bắt buộc — chi tiết: skill taadaa-farm-ops-rules)
Máy live + script chạy/lỗi → KHÔNG tự sửa code, KHÔNG tự chạy lại, KHÔNG tự probe/tay khi chưa được user yêu cầu.
Lỗi → screencap → gửi ẢNH THẬT (MEDIA:<path> dòng riêng, KHÔNG bọc markdown, KHÔNG gửi đường dẫn text) → DỪng chờ user hướng dẫn.
User hướng dẫn bước nào → encode bước đó vào script + test → mới chạy lại. Nghi ngờ → HỎI.

Patterns và pitfall khi phát triển consumer automation cho TikTok trên farm Samsung Galaxy (SM-G930F, SM-G930W8).



> **Refs**: `references/avatar-upload-edit-profile-layout-compatibility.md` (Layout avatar mới) · `references/change-tiktok-email-oauth2-hotmail-and-rotation-fix.md` · `references/shift-upload-ledger-lock-and-avatar-transition.md` (Lock upload ledger & video #1 avatar transition) · `references/xml-first-popup-and-safe-executor-guidelines.md` (Quy chuẩn XML-First Element Bounds loại bỏ 100% tọa độ cứng, Safe Executor Policy Firewall chặn tap quảng cáo/root container, và Fail-closed Account Logged Out Quarantine) · `references/ai-recovery-benign-popup-registry-and-profile-verification.md` (Chuẩn hóa Benign Popup Registry tập trung, AI Patcher deduplication/AST security, sửa lỗi git revert recorded SHA, nhận diện TikTok camera/video creation screen trong classifier, và Strict Evidence Gate đối soát Profile) · `references/sound-detail-and-substring-close-pitfall-20260821.md` (False-positive substring matching từ khóa 'close' trên nút đĩa nhạc bài hát 'Closer' và cơ chế thoát sound_detail_overlay) · `references/ai-recovery-git-mutex-queue.md` (Cơ chế xếp hàng chờ spin lock 60s + quy trình commit trước rebase sau an toàn khi nhiều máy auto-recovery cùng lúc) · `references/tiktok-location-permission-popup-pattern.md` (Xử lý popup vị trí TikTok "Xem nội dung phù hợp và địa điểm lân cận" -> bấm Hủy android:id/button3, modal scope isolation) · `references/account-update-popup-atx-restart-workbook-20260815.md` (popup "Tài khoản cần cập nhật" chặn account switcher → rule `account_update_required_vi` trong core + bump version gate; B1 ATX-kill phải restart atx-agent; workbook = nguồn sự thật, mỗi máy 2 nick Tik1+Tik2, worker-id=owner_id) · `references/s7-otp-activity-preservation.md` · `references/ui-dump-stale-coordinate-fallback.md` · `references/ui-fallback-rule-map.md` · `references/batch-upload-launcher-workflow.md` · `references/canonical-stale-lock-reconciliation-20260813.md` · `references/antidetect-architecture-video-view0-schedule.md` (video gen repo D:\\\\Taadaa\\\\Tiktok-video, view-0 ≠ ban, middleware reality-check, Win scheduler vs Hermes cron) · `references/tiktok-reg-pending-run-20260811.md` (audit workbook theo ID thật, detector row rác, chạy reg `_run_all_targets.py`, FINAL_BLOCKED signatures reg) · `references/tiktok-follow-mode2-follower-probe-20260812.md` (mode2 follower UI evidence máy 1 TikTok 46.3.3: node Hồ sơ=o3i, tab Follower=sdn, item=txt_user_name/txt_desc/tcj, màn FollowRelationTabActivity; safe workbook nhiều dòng cùng serial → dedupe; crash sau dump PROBE_OK → rebuild manifest từ artifact, KHÔNG tap lại) · `references/tiktok-follow-mode1-audit-20260815.md` (vòng 1 audit Mode 1: 5 test đỏ mới trong dirty tree = contract spec — thiếu profile-identity gate trước tap, self-target chưa loại khỏi follow_uids, substring "Follow" dính tab "Follower", verify_after_tap toàn màn) · `references/tiktok-follow-mode1-reaudit-approved-20260815.md` (vòng 2 re-audit sau fix: **APPROVED**, 241 passed — MỌI gate ĐÃ implement, file:line chuẩn cho từng invariant, P2 non-blocking, verification bắt buộc trước live) · `references/tiktok-follow-mode1-live-gate-audit-20260815.md` (vòng 3 gate pre-live: **APPROVED**, 244 passed/147s — xác minh `ensure_feed_for_follow` reuse `_back_to_feed` mode2, wheel pin 0.4.44 vs runtime 0.4.43 drift, HANDOFF.md số test cũ 233≠244, fallback `_wait_search_result` khi len(elements)≠len(nodes)) · `references/tiktok-follow-mode1-live-retry-audit-20260815.md` (vòng 4 sau failure live + search-submit repair: **APPROVED** 1 live retry, 245 passed/154.67s — autocomplete submit contract `tv_search_textview`, artifact-replay verification technique, P2: compat record thiếu submit branch, env 0.4.43≠0.4.44, config example mode both/budget 10) · `references/tiktok-follow-mode1-live-canary-20260815.md` (4 run canary máy 1 → run 4 **OK follow thật** `charakrh768`, 253 passed — nút Follow thật là TextView `id/fds` clickable=false không ancestor clickable, stat "Đã follow" `id/sdn` trùng marker → ưu tiên `id/fds`; B1 hardkill + warmup recapture verified XML)



> **Onboarding popups + uiautomator idle-state (2026-08-07)**: popup "Thêm số điện thoại" (add_phone_number_vi), camera/mic sheet (camera_mic_permission_sheet_vi) — X đóng cả composer, phải pm grant; idle_state_error → UIAUTOMATOR_PROCESS_MARKER; dumpsys-account blind spot; MEDIA_FINGERPRINT_PENDING self-block; owner_id=worker_id; "Đổi Tên"→Hủy; kworker→reboot: `references/tiktok-popups-onboarding-20260807.md`.rror: `references/tiktok-onboarding-popups-20260807.md`.



## Quy tắc vàng



0. **Kiểm tra workbook "thiếu acc" = đếm theo ID THẬT, KHÔNG đếm dòng (user sửa 2026-08-11)**: file `taikhoan_dat_v2_updated .xlsx` (sheet "Tài Khoản") có 80 máy × **8 dòng/máy** (640 dòng; thiết kế gốc 8 slot/máy — chèn lại 2 dòng trống/máy 2026-08-11 sau khi cleanup 14/07 xóa còn 6 dòng) — nhiều dòng là `ID=None` (máy 75–80: đủ 8 dòng nhưng **0 acc thật**). Đếm `len(rows)/máy` rồi kết luận "đủ" là SAI. Đếm số dòng có ID không None/rỗng/không bắt đầu `http`; máy thiếu tik2/tik3 = acc thật < 3. Cùng bẫy ở `taikhoan_run_safe.xlsx` (cột ID rỗng = chưa reg). **Cột `Tik` đã ĐỔI TÊN thành `Folder Video` (2026-08-11) — giá trị là mã folder ghép `D:\TIKTOK-videonuoinick\<folder>`, KHÔNG phải STT dòng, KHÔNG phải thứ tự account.**



   **QUY LUẬT folder video + source (anchor = Tik1 đã đăng video, user chốt 2026-08-11):**

   - `Folder Video slot k của máy m = (m-1)*8 + k` → Tik1=+1 (1,9,17...633), Tik2=+2 (2,10,18...634), tik3=+3 (3,11,19...635). Mỗi máy 8 folder liên tiếp, tổng 640.

   - `video gốc` (source trong `D:\video goc`) slot N của máy m = `(N-1)*80 + m` → Tik1 = m (1..80), Tik2 = 80+m (81..160), tik3 = 160+m (161..240).

   - **Sync MỘT CHIỀU: `taikhoan_dat_v2` (REG) là master → Tik1/Tik2/tik3. File Tik KHÔNG đẩy ngược vào REG.**

   - **Anchor "map theo Tik1"**: Tik1 đã đăng video thật nên folder nó là chuẩn; REG folder có thể lệch (backup 07/07→20/07: máy 10 folder 73,74,75 → 73,75,76 — do sửa dòng cũ). Khi REG lệch Tik1 → sửa REG + Tik2/tik3 theo Tik1, KHÔNG sửa Tik1 theo REG.

   - **Pitfall sync theo "dòng 1/2/3 thứ tự xuất hiện"**: hiểu nhầm này làm hỏng folder Tik1/Tik2/tik3 (đổi folder đúng `(m-1)*8+k` thành giá trị lệch của REG). Sync đúng = theo QUY LUẬT `(m-1)*8+k`, giữ ID theo đúng vị trí dòng slot trong REG (dòng thứ k của máy = slot k, kể cả dòng trống).

   - **Pitfall openpyxl đọc backup không đuôi .xlsx**: backup dạng `Tik2.xlsx.bak-sync-id-*` (không đuôi .xlsx) → openpyxl `InvalidFileException`; phải copy sang temp đuôi `.xlsx` trước khi load. Backup chuẩn nên đặt đuôi `.xlsx` ngay từ đầu.

   - Chi tiết + bảng đối chiếu + script sync: `references/tikn-workbook-folder-mapping.md`.



   **Pitfall resolve serial từ safe workbook — nhiều dòng CÙNG serial (2026-08-12, tiktok-follow máy 1)**: `taikhoan_run_safe.xlsx` có thể có **6 dòng/máy (6 acc) nhưng Device ID TRÙNG** — `[r for r in rows if May==1]` trả 6 serial giống hệt → check `len(serials)!=1` báo nhầm "6 serials khác nhau" và chặn nhầm. Phải **dedupe unique serials** trước khi kiểm tra `len()==1`. Đối chiếu hash sha256: máy 1 → `2b8f46746584…` (suffix `5a46`, online trong `adb devices`).



   **Pitfall ghi manifest bằng `Path` nối chuỗi (2026-08-12)**: `OUT_DIR/"manifest_"+TS` → `TypeError: unsupported operand type(s) for +: 'WindowsPath' and 'str'` — crash NGAY SAU khi probe thành công (lock đã release, mọi dump đã PROBE_OK) chỉ vì dòng cuối ghi manifest. Viết đúng: `OUT_DIR / ("manifest_"+TS+".json")` (cả biểu thức trong dấu ngoặc) hoặc `OUT_DIR / f"manifest_{TS}.json"`. Nếu đã crash sau khi dump PROBE_OK: **rebuild manifest từ chính artifact** (đọc lại file `.json`/`.xml` dump thật) — KHÔNG chạy lại probe/tap (tránh tap trùng lần 2 lên máy thật).



1. **Không reboot khi có VPN**: reboot giết `tun0`, đợi watcher gán lại mất 30-300s. Chỉ reboot khi thực sự cần (startup fail, UiAutomator treo).

2. **Ghi mọi thay đổi UI/handler vào `docs/ui-compatibility.md`**: mỗi fix popup, selector, fallback, startup handler phải có contract entry.

   - **BẮT BUỘC: lỗi vận hành PHẢI handle thành code + regression test + COMPAT entry** — user nhắc lại: mọi lỗi gặp phải handle lại để lần sau không gặp nữa (đã ghi yêu cầu trong mọi repo). Signature lặp lại (uiautomator treo, baseline stale, caption field missing...) → implement handler (consumer hoặc core), thêm regression test, ghi COMPAT entry, commit. Chỉ chấp nhận không-fix khi lỗi là 1-off không tái lập được và có lý do rõ ràng.

3. **Dùng `dumpsys activity` thay vì `uiautomator dump` để detect popup**: UiAutomator treo trên Samsung. `dumpsys activity activities` nhanh và không treo.

4. **Luôn có coordinate fallback cho image navigation**: `bottom_navigation_point` hoạt động ngay cả khi `detect_feed_controls`/`detect_profile_screen` trả về None trên W8.

5. **CẤM ghi/đè bất kỳ file nào vào `D:\video goc`** (kho video gốc — CHỈ ĐỌC). Ảnh/asset sinh mới chỉ ghi vào `D:\TIKTOK-videonuoinick\<folder>\` hoặc runtime root; override nguồn avatar qua `--avatar-source-root`. Vi phạm = phá kho nguồn của user (đã xảy ra: ghi đè avatar.jpg 45/64 không thể khôi phục). Nếu script nguồn (vd `make_avatar_yolo.py`) cần guard, dùng helper `_assert_outside_source(output, source_root)` ném ValueError khi output nằm trong source root.

6. **Batch chết giữa chừng → rerun ĐỒNG LOẠT cả list song song, không debug lẻ từng máy**. User yêu cầu chạy đồng loạt; khi launcher PS1 bị kill giữa chừng, đừng sa vào xử lý từng máy một — xác minh checkpoint/report rồi phóng lại N runner song song (`--recovery-mode` để takeover lock stale). Checkpoint trong `runs/<run_id>/checkpoint.json` là nguồn sự thật (state, post_tap_attempted, post_verified) — không dựa vào process exit.

   - **LUÔN chạy launcher qua `terminal(background=true, notify_on_complete=true)`, KHÔNG foreground.** Terminal foreground chặn cứng 600s; batch 14 máy mất 20-30 phút → Hermes kill PowerShell → workflow con chết giữa VERIFY_POST → để lại `verification_pending` + post mơ hồ (đã xảy ra máy 22, 2026-08-05). Background không giới hạn, tự báo khi xong + ghi summary.csv đủ.

   - Hermes shell approval ≠ operator chưa cấp quyền live. Khi user đã ra lệnh upload/post rõ ràng, đó là authorization cho scope đã nêu; không hỏi lại chỉ vì `terminal` báo approval timeout. Approval timeout chỉ có nghĩa **lệnh shell chưa launch**. Tránh command compound kiểu `xargs | bash -lc | pipe YES` vì smart-approval dễ đánh dấu mơ hồ; ưu tiên gọi trực tiếp launcher PowerShell có sẵn với tham số rõ (`-Tik N`, `-MaxParallel`, `-Confirmation RUN`, manifest nếu subset). Nếu launcher chưa hỗ trợ workbook farm hiện tại, dùng entrypoint canonical có host-config/workbook rõ hoặc sửa chính launcher qua baseline+test; không tạo `tik2-live-launcher.ps1`, runner mới, hay flow riêng cho Tik2.

   - **Canonical launcher invariant (user correction 2026-08-12):** Tik1/Tik2/TikN và account row 1/2/N dùng chung script đã chạy chuẩn; chỉ thay workbook/data/row/config qua tham số. Trước live ghi `canonical_script`, `data_path`, target machines/rows, `MaxParallel`; sau live báo batch dir + summary/report paths. Không coi launcher exit code, worker status, workbook increment hoặc `status=SUCCESS` riêng lẻ là proof.

   - **Background execution invariant:** batch/preflight dài phải chạy background với notify-on-complete; foreground timeout có thể giết launcher giữa batch và để report/lock dở dang. Launcher chết thì scan real worker process, checkpoint, receipt, report theo máy trước retry; không restart mù.

   - **Runtime isolation probe:** nếu launcher pin version nhưng PowerShell thấy package version khác, probe cùng executable với `PYTHONNOUSERSITE=1`; Hermes user-site có thể shadow venv. Isolate environment trong canonical launcher, không nới version gate theo lỗi đoán.

   - **Avatar evidence invariant:** `ENSURE_AVATAR` chỉ upload khi classifier xác định `MISSING`; `PRESENT` skip, `UNKNOWN` skip fail-closed. `--force-avatar-upload` chỉ là explicit replacement cho machine allow-list, không phải cơ chế auto-detect. Report `avatar_status=null` nghĩa là chưa tới/ghi nhận ENSURE_AVATAR, không phải avatar đã upload. Muốn báo Tik2 avatar đã xử lý phải có state/report cụ thể như `UPLOADED_VERIFIED`, `SKIPPED_EXISTING_AVATAR`, hoặc `SKIPPED_AVATAR_STATE_UNKNOWN`. Chi tiết: `references/canonical-batch-and-avatar-evidence.md`.

   - **Subset máy = AssignmentManifest** (launcher HEAD không còn `-MachineList`): JSON `{schema_version:1, assignment_id, owner_id, resources:["machine:N",...], reviewed_at}` + env `TIKTOK_VIDEO_ASSIGNMENT_MANIFEST` + `TIKTOK_VIDEO_WORKER_ID` (khớp owner_id). Inventory lọc `SKIPPED_ASSIGNMENT` ngoài list.

   - **Mỗi lần retry = manifest MỚI đúng scope, KHÔNG dùng lại manifest to.** Dùng lại manifest 14 máy để retry 3 máy → máy đã success resolve video KẾ TIẾP, đăng thêm ngoài ý muốn (máy 43 đăng video 4+5). Luôn check dòng "Máy mục tiêu:" launcher in ra trước khi xác nhận RUN.

   - **`-RecoveryMode` KHÔNG qua được inventory lock filter — preflight vẫn SKIPPED_LOCKED hết → "Máy mục tiêu: none" → 0 runner (2026-08-06).** `machine_inventory.py::_filter_locks` chỉ `path.exists()` check lock file, không biết recovery-mode/takeover; launcher LUÔN chạy inventory preflight trước khi launch nên máy giữ lock handoff bị skip ngay từ preflight (`machine_launch_order` rỗng, batch exit 3, 0 verified, toàn bộ máy "Target bị bỏ qua"). Takeover lock stale chỉ xảy ra ở WORKER lúc live — không cứu preflight. **Muốn retry máy đang giữ lock handoff: xoá lock stale TRƯỚC khi chạy launcher** (cả `machine_N.lock.json` + `serial_<serial>.lock.json`; điều kiện xoá an toàn: `status=handoff` + `owner_active=false` + PID chết qua `tasklist /FI "PID eq X"` — 1 slash, MSYS nuốt `//`; backup trước). `-RecoveryMode` vẫn bật cho worker (soft reboot/OPEN_TIKTOK handler) nhưng không giải phóng preflight. Chi tiết + playbook retry batch 3 vòng: `references/retry-batch-recovery-20260806.md`.

   - **`PYTHONPATH= PYTHONHOME= powershell.exe ...`** khi gọi launcher — hermes venv nhiễm sys.path làm automation python báo core 0.4.32 (thay vì 0.4.34) → launcher throw version mismatch.

7. **Không tải ảnh từ web rồi ghi vào kho nguồn**: avatarLarger từ HTML TikTok có thể là **avatar placeholder mặc định** (account chưa set ảnh) — kết quả ảnh trắng + silhouette, vô dụng. Xác minh nội dung trước khi dùng; và tuyệt đối không đè file trong `D:\\video goc` bằng ảnh tải về.

8. **Check wifi/connectivity trước live run và sau reboot, TRƯỚC khi gán proxy/VPN**: máy trong farm có thể văng wifi tự nhiên (`wlan0` state DORMANT/NO-CARRIER, mất IP, `ping: Network is unreachable`) dù VPN `tun0` vẫn báo CONNECTED — tun0 lên trên nền không mạng = gán proxy mù, upload fail/đăng ảo. Quy trình: (a) verify `ip addr show wlan0` có `state UP` + `inet <ip>` (chấp nhận `state up` HOẶC `state unknown` khi có `inet ` — một số ROM báo UNKNOWN dù có carrier); (b) `ping -c 2 -W 3 8.8.8.8` OK. Nếu wifi chết: `svc wifi enable` không cứu được (NO-CARRIER = radio không thấy AP, cần toggle tay trong Settings hoặc kiểm tra vùng phủ/antenna); `adb reboot` không tự đảm bảo wifi lên lại. **Đã implement trong core** `automation_core/device_recovery.py::wait_for_wifi(adb, timeout, poll_interval, stop_event)` — chỉ quan sát (không mutate device) — và gate `wifi_timeout` trong `watch_device_reconnect` trước `on_ready`: wifi chưa lên trong thời hạn → defer `on_ready` + log `WIFI_NOT_READY` (không gán proxy mù), retry khi wifi về; `wifi_timeout=0` tắt gate; `pending_notified` giữ reason (boot_id_changed) ổn định qua gate. Wheel từ 0.4.23. Không tự toggle/reboot wifi trong core code — chỉ chờ + verify.



## Search-Follow safety gates (Mode 1 tiktok-follow, audit 2026-08-15)



Durable invariants cho MỌI flow search→follow (Mode 1 = search UID → profile → Follow; Mode 2 = search → profile → Follower tab). Mode 2 có gate chuẩn (`mode2_follow_followers.py::_open_follower_tab`); Mode 1 từng thiếu và ĐÃ ĐƯỢC FIX (vòng 2 re-audit APPROVED, 241 passed). Những invariant này là bắt buộc — khi audit/đánh giá bất kỳ thay đổi search→follow nào, check từng cái với file:line hiện tại:



1. **Profile-identity gate TRƯỚC mọi tap Follow/Follower**: sau search, dump profile phải chứng minh `profile_identity_from_xml` cho `username` + đúng 1 node resource_id kết thúc `id/sf5` + normalized handle == UID (`strip @ + casefold`, không substring). Sai/missing → `manual`/fail-closed, KHÔNG tap. Reload/navigation lặp lại phải re-verify identity từng lần — identity sau reload KHÔNG kế thừa. Implement: `mode1_search_follow.py:166-185` `_classify_exact_profile_action` (re-verify qua `classify_fn` trong `verify_after_tap` cho MỌI dump mới, `verify_follow.py:57-131`).

2. **Self-target exclusion**: nguồn UID follow (`follow_uids()` từ safe workbook) PHẢI loại UID của account đang chạy (active handle lấy từ mapping row đã verify). Implement: `follow_engine.py:337-349` + `active_account_handle` set ở `run_session:636`. Không loại → nguy cơ follow chính tài khoản đang login.

3. **Exact marker match, KHÔNG substring + action-resource preference**: `"follow" in text` khớp cả tab "Follower" (sdn) và handle (sf5) → classify/tap sai. Match exact (casefold + strip). **KHÔNG yêu cầu clickable** — live TikTok 46.3.3 (canary 2026-08-15, run 3→4) chứng minh nút action Follow là TextView `id/fds` `clickable=false`, KHÔNG có ancestor clickable trong hierarchy (vùng bấm flatten không expose). Khi dump có CẢ label thống kê "Đã follow" (`id/sdn`, cũng non-clickable, cùng profile) VÀ action "Follow" (`id/fds`) → 2 node trùng marker → ambiguous; **ưu tiên node có resource suffix `id/fds`** (action thật), không phải `id/sdn` (stat). Ambiguous thật (2 action cùng state, không có `id/fds` duy nhất) → fail-closed. Tap vẫn cần **bounds + duy nhất**; node không bounds → không phải target. Implement: `_tap_follow_button` `mode1:346-361` + `classify_button` `verify_follow.py` (`_action_targets` + nhánh `id/fds` preference + `_node_or_clickable_ancestor` fallback cho layout có ancestor clickable thật). Node rid `id/sdn`/`id/sf5` không bao giờ là action candidate; `id/fds` LÀ action candidate.

4. **Verify sau tap phải identity-bound + nút-bound**: KHÔNG quét toàn màn — bất kỳ node "Đã follow" nào (popup, profile khác) = success giả. Mỗi dump mới phải chứng minh identity == UID rồi mới đọc trạng thái nút hành động; unknown → manual, không silent-success. API nhận `classify_fn` inject (identity-bound classifier) để test kiểm soát được — `verify_after_tap` đã có param này.

5. **Test green ≠ gate tồn tại**: vòng 1 test set `eng.active_account_handle` rồi assert exclusion nhưng `FollowEngine.__init__` không bao giờ tạo attribute → test pass vì lý do sai. Trước khi tin test, verify production symbol/setter tồn tại (vòng 2: `run_session:636` set, `follow_uids` đọc).

6. **EditText echo + avatar semantic cho search result**: input search focus echo đúng UID ở `@index=0` — KHÔNG bao giờ là result target (`_wait_search_result` loại class EditText/editable, `mode1:209-215`); Top-result card mở qua đúng 1 clickable descendant bọc 1 ImageView cùng bounds (semantic avatar) hoặc clickable ancestor; suggestion `tvl_unified_sug` chỉ re-evaluate đúng 1 lần.

7. **Autocomplete submit contract — TikTok 46.3.3 (live evidence 2026-08-15)**: sau khi nhập exact UID, màn autocomplete có thể chỉ hiện **EditText echo exact UID + toàn bộ suggestion gần đúng** (`tvl_unified_sug` approximate, KHÔNG có suggestion exact). Khi đó KHÔNG được tap suggestion; phải submit qua **đúng 1** nút Search semantic: bounds + clickable + class `android.widget.Button` + resource suffix `id/tv_search_textview` + text normalized ∈ {tìm kiếm, search} (`_unique_search_submit` `mode1:202-217`). 0/2+ match → None → fail-closed, KHÔNG tap. Icon feed "Tìm kiếm" (content-desc) là node KHÁC (không phải Button class, không resource-id) nên không bao giờ bị chọn làm submit; input là EditText → bị loại bởi class filter. Chỉ submit khi chưa có exact suggestion (`_exact_search_result_from_xml` trước), giữ nhánh một-tap cũ. RED→GREEN: `test_nav_search_submits_exact_uid_before_waiting_for_results` (taps `[(975,175),(927,150),(135,483)]` = icon → submit → avatar, mô phỏng CHÍNH XÁC dump failure thật).

8. **Artifact-replay verification technique**: trước khi đọc code fix, chạy chính các predicate sản xuất (đếm node bằng regex/python) trên artifact failure byte-exact (`ui.xml` + `screen.png` cùng giờ) — `tv_search_textview` count, EditText count/focused, suggestion texts, class/bounds — để chứng minh (a) fix selector khớp signature thật, (b) không có cạnh tranh selector nào khác trên màn đó. Sau đó mới đối chiếu code + test RED→GREEN mô phỏng đúng dump. (Vòng 4, failure `%TEMP%\tiktok-follow-m1-failure1-20260815-090848\`.)



Chi tiết 2 vòng audit: `references/tiktok-follow-mode1-audit-20260815.md` (vòng 1 — findings + 5 test đỏ) và `references/tiktok-follow-mode1-reaudit-approved-20260815.md` (vòng 2 — APPROVED, file:line từng invariant + P2 non-blocking + verification trước live).



9. **Mode 2 `_back_to_feed` phải nhận diện fullscreen Search history (live canary 2026-08-15, 6 run máy 1 → run 6 OK)**: sau account-ready/session trước, UI có thể đang ở màn Search history KHÔNG có bottom-nav → nhánh cũ (≤4 Back + tap Home từ own Profile) không bao giờ pass. Detector `_is_search_history_screen` (`mode2_follow_followers.py`): có submit `tv_search_textview` (clickable) + item recent-search + KHÔNG bottom-nav → đúng 1 Back về Feed. **Marker recent KHÔNG phải resource-id ổn định** — dump thật TikTok 46.3.3 dùng content-desc `Thời gian`/`Đóng` cho mỗi item (`tvl_recent_search`/`tvl_history` KHÔNG xuất hiện). Đừng khóa detector theo resource-id giả định; verify bằng dump thật (probe trực tiếp `_is_search_history_screen` trên `ui.xml` capture).

10. **Mode 2 Path B `_classify_profile_action` PHẢI delegate `classify_button` của Mode 1** — bản tự viết cũ yêu cầu `clickable is True` → fail live vì nút action profile là TextView `id/fds` `clickable=false` (CÙNG bug Mode 1 đã sửa ở invariant 3). Không bao giờ viết classifier thứ 2 với semantics clickable khác; dùng chung `verify_follow.classify_button(xml_text)` (preference `id/fds` + loại stat `id/sdn`). Fix: `mode2_follow_followers.py::_classify_profile_action` đổi signature nhận `xml_text` rồi `return classify_button(xml_text)`.

11. **Live canary fail nhiều run cùng reason string ≠ cùng stage fail** — 5 run Mode 2 đều báo `"không quay về được feed trước seed search"` nhưng stage thật dịch chuyển (đầu: không detect Search history; sau khi fix detector: đã qua `_back_to_feed`, fail ở Path B classify). Khi fix không ăn: (a) probe trực tiếp trên state máy hiện tại + instrument tạm (hook `engine._debug` list ghi homes/profiles/searches/sf5/search_history mỗi vòng) để tìm stage fail THẬT; (b) đừng đổ lỗi pycache/env trước khi có bằng chứng — xóa `__pycache__` là red herring nếu module import đã ra bản mới (`inspect.getsource` có marker mới); (c) verify module import đúng bản: `inspect.getsource(m2._is_search_history_screen)` chứa marker mới.



Chi tiết 6 run canary + evidence: `references/tiktok-follow-mode2-live-canary-20260815.md`.



### Checklist pre-live gate (vòng 3, 2026-08-15 — APPROVED, 244 passed)



Khi user yêu cầu audit "pre-live candidate" cho Mode 1 (máy 1), ngoài 6 invariant ở trên còn phải verify:



1. **Feed precondition trước MỖI Search**: `run_mode1` gọi `engine.ensure_feed_for_follow()` trước mỗi UID (kể cả UID đầu) — implementation reuse đúng `mode2_follow_followers._back_to_feed` (bounded ≤4 Back + ≤1 Home semantic, đúng 1 Search/Home/Profile, Home selected, không follower recycler). Đừng chỉ đọc lời HANDOFF "reuse mode2" — đọc code `follow_engine.py:337-348` + test `test_ensure_feed_for_follow_reuses_bounded_semantic_navigation` + `feed_checks == 2`.

2. **Wheel pin ≠ runtime**: audit chỉ đọc lời "dùng core 0.4.44" là CHƯA ĐỦ. `pip show automation-core` (runtime) có thể là 0.4.43 trong khi pin/dự kiến production là wheel 0.4.44 (`D:\Taadaa\automation-core\dist\automation_core-0.4.44-*.whl`). API khớp signature (đối chiếu bằng giải nén wheel + `inspect.signature`), nhưng ghi rõ: trước live máy 1 phải cài đúng 0.4.44 — đây là ghi chú vận hành, không phải lỗi code.

3. **HANDOFF.md số liệu cũ**: số test ghi trong HANDOFF (233) có thể lệch suite hiện tại (244) — chạy lại suite thật và lấy con số mới; lệch = NIT doc, không phải blocker.

4. **Fallback nhỏ trong `_wait_search_result`** (`mode1:264`): khi `len(elements) != len(nodes)` (parse lệch) trả identity raw (bounded) thay vì bounce — vẫn an toàn vì profile identity gate `id/sf5` chặn mọi profile sai trước tap Follow; không follow nhầm. Ghi nhận như NIT, không phải finding.

5. **Không đụng untracked**: `NUL` + `uids.txt` untracked trong worktree — không đọc/chạm/stage (đúng HANDOFF chỉ đạo).

6. **Offline verify trước verdict**: `python -m pytest follow_runner/tests/ -q` (244 passed/147s) + `py_compile` + `git diff --check` — đủ để APPROVED cho pre-live; live run là bước tiếp theo của operator, không nằm trong audit.

7. **Vòng 4 (sau failure live + search-submit repair, 245 passed/154.67s)**: verify thêm — (a) submit contract `tv_search_textview` (invariant 7) khớp artifact failure; (b) `docs/ui-compatibility.md` CHƯA có record cho submit branch → **P2** (vi phạm binding AGENTS.md "selector change phải cập nhật local registry"); (c) env runtime 0.4.43 ≠ pin 0.4.44 → **P2** (profile.py hash khớp nên không ảnh hưởng fix); (d) config example `mode: "both"` + `budget_per_session: 10` → live retry phải dùng config thật `mode: "1"` + `budget_per_session: 1` → **P2**. P1 = không có → APPROVED 1 live retry.



Chi tiết vòng 3: `references/tiktok-follow-mode1-live-gate-audit-20260815.md`. Chi tiết vòng 4 (failure live + submit repair + APPROVED 1 live retry): `references/tiktok-follow-mode1-live-retry-audit-20260815.md`.



## ADB Patterns



### ADB load tuning & UI-capture timeout contract (2026-08-13, user chốt)



- UI capture timeout cố ý = **60s** (user quyết định: để UI load, tránh lỗi UI). KHÔNG tăng lên 120/180s. Chỉ 2 chỗ dài hơn KHÔNG phải UI capture: `adb push` 120s (`media_manager.py:116`) và reboot recovery `boot_timeout=120`/`verification_timeout=180` (`state_machine.py:4264`). Timeout inventory đầy đủ: `references/adb-load-tuning-20260813.md`.

- Giảm tải ADB = giảm **MaxParallel** (mọi worker chia 1 ADB server port 5037), không phải tăng timeout. **Đã thực thi 13/08**: launcher default `$MaxParallel = 16` (ValidateRange vẫn 1-30); preflight chạy `Peak active runners: 16/16` OK. Khi user đồng ý tuning ADB, 2 hướng đã chốt: (a) giảm MaxParallel 30→12-16, (b) screencap `exec-out` trước.

- Env User kibe PC (đã set 13/08): `ADB_SERVER_SOCKET=tcp:localhost:5037`, `ADB_MDNS_OPENSCREEN=0` — ghim socket + tắt mDNS; vô hại với farm USB (restart adb server xong vẫn thấy đủ devices). Nhật ký cấu hình + hướng dẫn revert: `D:\Taadaa\reports\adb_environment_tuning.md`. Verify: PowerShell `[Environment]::GetEnvironmentVariable(name,'User')`; revert: set `$null` + `adb kill-server`/`start-server`.

- Lỗi UI capture chia 3 nhóm KHÁC NHAU, đừng quy hết cho ADB lag: `uiautomator_idle_state_error`/`null_root_node` = ATX/UiAutomator treo (B1 ATX-kill); `DEVICE_NOT_PROVISIONED` = persistent backend chưa provision (retry ADB mù vô ích); `ADB command timeout ... screencap` rồi `exec-out fallback` thành công = transport lag thật.

- **Screencap exec-out-first (đã implement 13/08, `device_transport.py::screenshot`)**: thử `exec-out screencap -p` (1 lệnh ADB duy nhất, stream PNG) TRƯỚC; fallback shell screencap + pull chỉ khi exec-out fail. Đo thật máy 62: exec-out 0.98s/416KB. Trước đây thử shell+pull trước rồi mới fallback exec-out → thêm 1 cặp lệnh ADB chậm khi nghẽn.

- **Multi-port ADB KHÔNG giúp giảm lag**: ADB server chỉ nghe 1 port (5037 mặc định); mỗi device chỉ gắn được 1 server; bottleneck là device CPU/USB hub, không phải host port. Chạy nhiều `adb start-server -P` = phức tạp + dễ vỡ, không giải quyết gì. Đừng đề xuất.

- Test stale pitfall: `tests/test_machine_inventory.py::test_upload_launcher_core_version_gate...` assert `$defaultAutomationCoreVersion` hardcode (cũ 0.4.35, launcher dùng 0.4.40) → fail oan khi sửa launcher. Khi bump version gate trong launcher, update test assert đó cùng lúc.



### AdbKeyboard text input



```python

# Cách 1: Broadcast (có thể timeout nhưng text vẫn vào)

b64 = base64.b64encode(text.encode()).decode()

subprocess.Popen([ADB, "-s", SERIAL, "shell", "am", "broadcast",

    "-a", "ADB_KEYBOARD_INPUT_TEXT", "--es", "text", b64],

    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)



# Cách 2: input text (nhanh, cần field đã focus)

subprocess.run([ADB, "-s", SERIAL, "shell", "input", "text", text], timeout=10)

```



### Detect popup không cần UI dump



```python

activities = adb.shell(["dumpsys", "activity", "activities"]).stdout

if "UniversalPopupActivity" in str(activities):

    adb.shell(["input", "swipe", "540", "1600", "540", "400", "300"])

if "com.android.vending" in str(activities):

    # Google Play ToS hoặc PlayCore

    adb.shell(["input", "tap", "863", "1419"])  # Chấp nhận

```



### Samsung USB connection popup (sau PC sleep)



Popup `com.samsung.android.MtpApplication/.USBConnection` xuất hiện sau khi PC

sleep/bật lại (USB reconnect). Nó phủ lên MỌI app, chặn uiautomator dump, khiến

flow fail với `AVATAR_EDIT_OPEN_FAILED`/`OPEN_TIKTOK_FAILED` (mọi tap trúng

popup). Detection BẮT BUỘC qua `dumpsys` (uiautomator bị chặn):

`mCurrentFocus=...MtpApplication/.USBConnection`; nút dismiss là

`app:id/button_cancel` (bounds 0,0-540,162 → center ~(270,81)), fallback Back.



Handler app-neutral đã có trong core: `automation_core/usb_popup.py`

(`usb_popup_activity_present` + `dismiss_usb_popup`, từ wheel 0.4.21). Consumer

TikTok import + gọi ở 4 chỗ (profile-root recovery, account-switcher,

ENSURE_AVATAR). KHÔNG duplicate handler per-consumer.



**Hướng tối ưu (user đề xuất)**: popup này xuất hiện BẤT KỲ LÚC NÀO (mỗi lần PC

sleep bật lại), nên đừng gọi dismiss rải rác từng flow — đưa auto-dismiss vào

`automation_core/device.py::prepare_device` (cuối hàm, sau swipe-unlock; dùng

`dismiss_usb_popup_shell(adb)` — shell input không cần adapter consumer). Mọi

consumer (upload, feed, login, gmail, gan-proxy) đều đi qua `prepare_device`

qua `wait_until_unlocked`/`watch_device_reconnect` → "kệ mẹ nó, chạy cái gì

cũng bỏ qua popup". Dismiss fail chỉ log warning + field evidence, KHÔNG raise

(giữ contract `DeviceReadiness`). **Đã implement từ core 0.4.22** (commit

`1933c24`).



**Pitfall verify**: `dismiss_usb_popup` cũ dùng `uiautomator dump` để tìm Cancel

+ recapture — nhưng popup Samsung chặn uiautomator → recapture trả `unavailable`

→ hàm trả False dù BACK đã đóng. Fix: `dismiss_usb_popup_shell` verify bằng

**ActivityManager probe** (`_shell_probe` qua `dumpsys activity`) sau mỗi action

(thay vì uiautomator). Rule: bất kỳ handler nào phải xử lý popup chặn

uiautomator đều verify bằng `dumpsys activity`, không bằng UI dump.



**Pitfall timeline**: nếu consumer/core vừa sửa nhưng máy chạy TRƯỚC mốc đó thì

handler chưa có hiệu lực — kiểm tra mtime `state_machine.py`/wheel vs thời điểm

run trước khi kết luận "rule không hoạt động". Cũng check env đã cài đúng wheel

mới chưa (xem mục "Env automation_core dở dang").



**Pitfall verify-avatar false negative (máy 74)**: verify avatar sau save bằng

correlation pixel (ngưỡng 0.8) trên vùng crop — nhưng avatar hiển thị trong

khung tròn + overlay bị crop/scale khác nguồn vuông → correlation thấp

(0.02-0.25) dù nội dung ĐÚNG. **User nhìn xác nhận avatar đúng = bằng chứng

mạnh hơn pixel correlation** — báo user + để user xác nhận trước khi kết luận

fail; phân biệt similarity thấp TRƯỚC Next (chọn sai tile — bug thật) vs SAU

save (có thể false negative do overlay).



**Pitfall post-save verify BLANK — entropy thấp ≠ corr thấp (m36, 2026-08-10)**:

sau fix album ảnh (ccd28f3), picker giờ MATCH được (`[ENSURE_AVATAR] Visual picker

match corr=0.601 ≥ 0.600` tại tile bounds) nhưng verify SAU save vẫn FINAL_BLOCKED

với `Avatar source similarity=-0.034, threshold=0.800` + `Avatar crop entropy=1.83,

threshold=4.00` (7 poll/30s, `[ENSURE_AVATAR] Avatar sau save vẫn dưới ngưỡng sau

30.0s`). **Entropy thấp = vùng crop ĐỒNG NHẤT (rỗng/trống)** — KHÁC false-negative

m74 (corr thấp nhưng crop có nội dung). Dấu hiệu avatar chưa được save/áp dụng

(tap Xong/Lưu miss, save không commit) — đừng sửa ngưỡng correlation, kiểm tra

bước save surface. Báo user kiểm tra ảnh thực tế trên máy trước khi kết luận.



- **Avatar picker stale screenshot pollution**: Nếu thiết bị có file `_ss.png` hoặc ảnh chụp OTP cũ, MediaStore có thể đưa ảnh đó lên đầu album "Gần đây". Khi upload avatar, bắt buộc xóa file chụp màn hình rác trước khi push avatar mới hoặc kiểm tra visual correlation/vision xác nhận ô ảnh chọn là ảnh chân dung người, không tap mù tile đầu tiên (2026-08-20).

## UI Compatibility



### Machine 9 (SM-G930W8, TikTok 44.2.3)



- `detect_feed_controls`, `detect_profile_screen` → None (không detect được)

- `bottom_navigation_point(screenshot, "profile")` → (972, 1857) ✅

- Account switcher: `tap(540, 552)` sau khi vào Profile

- Consent popup: `UniversalPopupActivity` + swipe up

- Google sign-in: `AssistedSignInActivity` → Back key

- Login flow: "Bạn đã có tài khoản? Đăng nhập" → email option



### Các popup đã biết



| Popup | Detection | Dismiss |

|-------|-----------|---------|

| Consent "Đồng ý và tiếp tục" | `UniversalPopupActivity` | swipe(540,1600,540,400,300) |

| Google Play ToS | `com.android.vending` + `TosActivity` | tap(863, 1419) |

| Google Play PlayCore | `com.android.vending` + `PlayCoreAcquisitionActivity` | tap(783, 1824) then relaunch TikTok |

| Security check "Kiểm tra bảo mật" | "Hãy cùng kiểm tra bảo mật" text | tap(996, 923) — nút Đóng |

| Contacts permission | "Cho phép TikTok truy cập vào danh bạ" | tap(557, 1134) — TỪ CHỐI |

| Google sign-in | `AssistedSignInActivity` | `keyevent 4` (Back) |

| Account update required (2026-08-15) | "Tài khoản của bạn cần được cập nhật — liên kết số điện thoại hoặc email trước khi chuyển đổi tài khoản" | tap "Để sau" (`btn_later`) — rule `account_update_required_vi` trong core |



### Popup chặn account switcher → ghi vào automation-core, KHÔNG handler per-consumer (2026-08-15)



Popup "Tài khoản của bạn cần được cập nhật" xuất hiện SAU khi `select_exact_account` (chặn chuyển nick) → account switcher kẹt → `PROFILE_ROOT_NOT_CONFIRMED` + "Restored TikTok subpage detected; Back recovery 12/12" fail dù ATX sống. Cách phát hiện thật: mở switcher tay (tap mũi tên cạnh tên hiển thị trong profile, máy 23 = (672,547)), chọn nick → popup bảo mật hiện với nút "Để sau".



**User bắt buộc: popup mới ghi ở CẤP ĐỘ automation-core** (`TIKTOK_POPUP_RULES` trong `automation_core/tiktok_popup.py`) chứ không chỉ trong tiktok-workflow — mọi consumer dùng chung. Quy trình:

1. Thêm `PopupRule` vào `TIKTOK_POPUP_RULES` (markers tiếng Việt casefold + selector nút dismiss).

2. Thêm regression test trong `tests/test_tiktok_popup.py` (pattern: FakeAdb + XML mẫu; node dismiss PHẢI có `bounds` — thiếu bounds → `action_taken=None` dù detected; assert `["input","tap",...] in adb.calls`, KHÔNG assert text vì tap theo tọa độ).

3. Cài editable vào venv dùng chung (`pip install -e ".[test]"`) — nếu không test chạy từ venv cũ sẽ fail "rule chưa có" (venv cài sẵn ≠ source repo).

4. **Bump version gate** `$defaultAutomationCoreVersion` trong `run_tiktok_upload_batch.ps1` + test assert hardcode (`test_upload_launcher_core_version_gate...`) — bỏ quên → "automation-core version mismatch: expected=0.4.40; actual=0.4.44" chặn mọi batch.

5. Consumer (state_machine) sau `select_exact_account` gọi `dismiss_shared_tiktok_popup(adb, package=config["tiktok_package"]="com.ss.android.ugc.trill", artifact_dir=run_dir)` — KHÔNG tự viết handler duplicate. Lưu ý default package của core là `com.zhiliaoapp.musically` (TikTok quốc tế), farm dùng `com.ss.android.ugc.trill` → luôn truyền package.



### B1 ATX-kill phải kèm RESTART atx-agent (2026-08-15, fix máy 23/26/29)



`_recover_uiautomator` (automation-core) chỉ **kill** atx-agent (`pkill -9`) nhưng KHÔNG restart → sau B1, atx-agent chết hẳn → `capture_persistent_ui` fail `HTTPERROR`/UNHEALTHY → fallback shell uiautomator (chết trên máy yếu) → `PROFILE_ROOT_NOT_CONFIRMED`/`non_xml_ui_dump` kéo dài. **Fix canonical**: sau mỗi `_recover_uiautomator` gọi `_restart_atx_agent(adb)` = `adb.shell(["/data/local/tmp/atx-agent", "server", "-d"])` + verify `capture_persistent_ui` trả XML có `<hierarchy` + log `[ATX_RESTART]`. 4 call site B1: `_execute_with_ui_retry`, `_run_ui_failure_ladder`, CONNECT_DEVICE, WAIT_FEED. (Commit `b9351b7`.)



**Dump UI ưu tiên ATX persistent (cơ chế Tiktok_Reg, commit `850e883`)**: `adapter._dump_ui_real` thử `capture_persistent_ui(adb, timeout=30)` (atx-agent port 7912, XML tươi qua JSON-RPC, sống khi shell uiautomator chết) TRƯỚC, fallback `capture_ui_xml` (shared backend).



**Chẩn đoán nhanh máy nghi ATX chết**: `python -c "from automation_core.persistent_ui import capture_persistent_ui; ..."` — `UNHEALTHY/HTTPERROR` = atx-agent cần restart tay (`/data/local/tmp/atx-agent server -d`; verify `ps -A | grep atx-agent` + log "listening on :7912"); `VERIFIED_HEALTHY` = OK. **Pitfall**: log run KHÔNG có dòng `persistent/ATX_RESTART` = B1 không được gọi (CONNECT_DEVICE pass) — đừng kết luận "ATX không giúp" khi ATX chưa từng chạy. Restart atx-agent đúng cách: chạy `server -d` riêng (kill + start trong cùng lệnh dính race).



### Workbook = nguồn sự thật duy nhất — CẤM tự chế mapping (user correction 2026-08-15)



User: *"lưu cái rule lấy dữ liệu lại, lần sau đừng có ngu lồn tự chế nữa"*. Quy tắc (đã ghi PROJECT_RULES.md):

- `Tik1.xlsx`/`Tik2.xlsx` chứa sẵn Máy/device/ID/Folder Video cho MỌI máy — workflow đọc trực tiếp theo `-Tik N`, **KHÔNG cần config riêng từng máy, KHÔNG tự suy luận mapping** (đã ghi memory: "chạy theo -Tik đúng workbook, CẤM tự chế mapping").

- **Mỗi máy vật lý có 2 nick (Tik1 + Tik2 cùng device)**. Chạy `-Tik 1` chỉ đụng nick Tik1; nick Tik2 của máy 1-37 (nhóm Tik1 default theo config) chưa bao giờ được xử lý nếu chỉ chạy theo config default. Muốn xử lý nick Tik2 của mọi máy → chạy `-Tik 2` riêng cho cả nhóm (không lọc theo config).

- Máy có `ID=None` trong workbook (cột ID trống) → preflight `Missing required fields: ID TikTok` — **lỗi DỮ LIỆU workbook, cần user điền ID, KHÔNG phải retry/VPN/lock**.

- Avatar thiếu ở `D:\video goc\<folder>` nhưng có ở `D:\TIKTOK-videonuoinick\<folder>` → copy sang (folder `video goc` đôi khi chưa tạo; không đè file có sẵn).

- **Worker-id phải khớp `owner_id` manifest**: `-WorkerId X` ≠ `owner_id` → `INVENTORY_ERROR: assignment preflight failed: AssignmentError` (assert_owner). Luôn dùng đúng owner_id từ manifest (đã có pitfall `ASSIGNMENT_WRONG_OWNER` ở trên, lần này lộ thêm dạng `AssignmentError` chung chung không log chi tiết — chạy `machine_inventory` trực tiếp với worker-id khác nhau để phân biệt).



## VPN Preflight Pattern



```python

from automation_core.preflight import require_android_vpn, serial_is_mapped_in_workbook

VICHANGER_SERIAL_HEADERS = ("phoneId", "deviceId", "serial")



# Trong reconcile_target, SAU lock acquisition:

if proxy_mapping and proxy_mapping.is_file():

    require_android_vpn(

        adb,

        required=serial_is_mapped_in_workbook(

            proxy_mapping, target.serial, serial_headers=VICHANGER_SERIAL_HEADERS,

        ),

    )



# Trong verify_post_reboot callback:

reboot_and_restore(

    adb,

    cleanup_before_reboot=lambda: None,

    recover_post_reboot=lambda: wait_until_unlocked(adb),

    verify_post_reboot=lambda: _verify_vpn(adb, target, proxy_mapping),

    boot_timeout=180,

    verification_timeout=300,  # Đủ 10 chu kỳ watcher 30s

)

```



## 2FA TOTP từ Workbook



```python

import pyotp

# Đọc cột 2FA từ workbook, tìm theo (machine, identifier)

totp = pyotp.TOTP(secret_2fa)

code = totp.now()  # 6-digit code

```



## Proxy readiness bypass (automation-core 0.2.40+)



`acquire_device_lock` gọi `wait_for_proxy_ready` để đợi watcher ghi marker `proxy_ready`. Nếu VPN (`tun0`) đã up nhưng watcher chưa ghi marker, dùng `live_vpn_verifier`:



```python

def _check_tun0(adb_path: Path, serial: str) -> bool:

    try:

        adb = AdbClient(str(adb_path), serial, default_timeout=10)

        result = adb.shell(["ip", "addr", "show", "tun0"], timeout=10)

        return result.ok and "inet " in str(result.stdout or "")

    except Exception:

        return False



# Trong reconcile_target:

lease = acquire_device_lock(

    ...,

    live_vpn_verifier=lambda s: _check_tun0(adb_path, s),

)

```



## Coordinate login fallback



Khi provider `login_one_account` fail (image-nav không hoạt động), dùng coordinate tap + `input text`:



```python

def _coordinate_login(target, account, adb_path):

    adb, s = str(adb_path), target.serial

    uid = account["id"]; pw = account.get("pass") or account.get("password")

    subprocess.run([adb,"-s",s,"shell","input","tap","427","1788"], timeout=10)  # Thêm TK

    time.sleep(2)

    subprocess.run([adb,"-s",s,"shell","input","tap","540","1830"], timeout=10)  # Đăng nhập

    time.sleep(1.5)

    subprocess.run([adb,"-s",s,"shell","input","tap","561","851"], timeout=10)   # SDT/email

    time.sleep(1)

    subprocess.run([adb,"-s",s,"shell","input","tap","713","288"], timeout=10)   # Tab Email

    time.sleep(0.5)

    subprocess.run([adb,"-s",s,"shell","input","text", uid], timeout=10)

    time.sleep(1)

    subprocess.run([adb,"-s",s,"shell","input","tap","540","1681"], timeout=10)  # Tiếp tục

    time.sleep(2)

    subprocess.run([adb,"-s",s,"shell","input","text", pw], timeout=10)

    time.sleep(1)

    subprocess.run([adb,"-s",s,"shell","input","tap","540","1681"], timeout=10)  # Tiếp tục

    time.sleep(3)

    subprocess.run([adb,"-s",s,"shell","input","tap","996","923"], timeout=5)    # Dismiss security

    return True

```



Gọi trong reconcile khi `login_module.login_one_account()` trả về False.



## Media fingerprint stale reservation recovery



Khi workflow chết giữa chừng (batch bị kill), ledger `idempotency/media-fingerprints/<key>.json` có thể giữ entry `status: reserved` của run chết. Lần chạy sau sẽ fail `MEDIA_FINGERPRINT_PENDING` ở `RESOLVE_NEXT_VIDEO` trước khi push media.



**Phân loại đúng trước khi xoá:**

- **Chưa từng post** (`post_tap_attempted=false` trong checkpoint, không có receipt `post-attempts/machine_X_video_N.json`) → reservation là stale hoàn toàn → **xoá entry** để retry chạy tiếp.

- **Đã bấm Post** (`post_tap_attempted=true`, checkpoint ở `VERIFY_POST`) → **KHÔNG xoá**; giữ reservation để recovery recheck profile, tránh repost mù.



**Pitfall tìm fingerprint theo machine — so sánh kiểu dữ liệu (máy 74, 2026-08-05):**

lọc `d.get("machine") == 74` (int) có thể BỎ SÓT entry khi ledger lưu machine là

string `"74"` — lệnh in ra rỗng dù fingerprint `reserved` tồn tại. Luôn duyệt

ledger theo **`str(d.get("machine")) == str(machine)`** hoặc tìm theo

`run_id` chứa mã run đang nghi (`if "20260805_0830" in str(d.get("run_id"))`).

Khi log báo `MEDIA_FINGERPRINT_PENDING ... status=reserved` nhưng scan theo

machine rỗng → scan theo run_id / prefix sha256 (lấy từ log) trước khi kết luận

"không có fingerprint".



**Pitfall vòng lặp xóa fingerprint — re-reserve mỗi lần chạy (máy 74, 2026-08-05):**

xóa fingerprint `reserved` stale rồi chạy lại → workflow resolve video đó và

**tự reserve LẠI** ngay đầu run; nếu run đó fail LẠI ở bước sau (màn tối,

clipboard, clear caption...) → lần chạy sau dính `MEDIA_FINGERPRINT_PENDING`

lần nữa → lại phải xóa → vòng lặp xóa-rerun (dính 3 lần liên tiếp cùng máy 74

video 4). Xóa fingerprint chỉ mở khóa CHẠY, không sửa lỗi gốc. **Trước khi

rerun sau khi xóa, phải fix LÝ DO run trước chết** (đọc report/last_state

signature: `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED` = màn tối → force-stop relaunch

+ verify brightness; `Clipboard setup failed`/`Không thể xoá caption cũ` =

handler CAPTION-001/002) — nếu không, xóa bao nhiêu lần cũng vẫn fail. Điểm dừng:

cùng signature fail ≥2 lần → dừng xóa-rerun, sửa handler/trạng thái máy trước.



**Pitfall checkpoint bị dọn**: run cũ bị kill nhiều ngày trước có thể KHÔNG còn

`checkpoint.json` (bị cleanup). Khi đó dùng `idempotency/post-attempts/machine_X_video_N.json`

làm nguồn sự thật:

- `status: completed` → video đã đăng xong + ghi workbook, không đụng.

- `status: verification_pending` + `post_submission_state: ACCEPTED` → TikTok đã

  nhận bài (`post_submission_accepted=true`) nhưng chưa verify/ghi workbook — run

  lại sẽ hậu kiểm profile (receipt barrier chống repost). KHÔNG xoá fingerprint.

- Không có file post-attempt cho video đó → chưa bấm Post → fingerprint `reserved`

  là stale an toàn xoá.



**Pitfall lock/fingerprint TÁI XUẤT HIỆN khi batch đang LIVE (2026-08-06)**: sau khi

dọn lock stale + fingerprint reserved rồi phóng batch, verify giữa chừng thấy

`machine_<N>.lock.json`/`serial_<serial>.lock.json` và fingerprint `reserved` video N+1

XUẤT HIỆN LẠI — đây là dấu hiệu HEALTHY: worker đã re-acquire lock (giữ máy) và

re-reserve fingerprint video kế tiếp khi resolve (pitfall re-reserve đã biết). KHÔNG

xóa lần nữa, KHÔNG panic — nó chứng minh batch thật sự đang chạy trên máy. Kiểm tra

bằng `process poll` xem launcher còn running + máy có đang tiến triển; chỉ xóa lại

khi batch ĐÃ kết thúc và máy fail vì chính fingerprint/lock đó.



**Pitfall `verification_pending` nhưng tile không tăng** (máy 5 video 6, 2026-08-05):

post-attempt ghi `ACCEPTED` nhưng VERIFY_POST quét profile nhiều lần vẫn baseline

(`Profile video tiles: 5 (baseline=5)`) → có thể TikTok nhận nhưng chưa xử lý xong

hoặc bài ẩn. KHÔNG tự kết luận đăng thất bại, KHÔNG xoá fingerprint; giữ

`verification_pending` + ghi HANDOFF để hậu kiểm sau (so tile thực tế trên máy).



**Pitfall `POST_RECHECK_UNAVAILABLE` — post mơ hồ kéo dài, baseline stale (máy 22, 2026-08-05):**

bấm Post xong bị kill giữa VERIFY_POST; chạy lại nhiều lần (2 lần cùng ngày) vẫn

`MANUAL_REVIEW` + `reason: [POST_RECHECK_UNAVAILABLE] Không mở/đọc được profile

để kết luận bài đã đăng hay chưa`. Log lộ baseline bất thường

(`Profile video tiles: 4 (baseline=7)` — máy mới posted 3-4 mà baseline 7).



**Root cause đã được user giải thích (KHÔNG phải lỗi profile/account-switch):**

máy từng **post trùng nhiều lần** (4-5 lần) → profile có ~7 tile tại thời điểm

post video 4 → baseline=7 là ĐÚNG lúc đó. Sau đó **user xóa mớ video trùng** →

profile còn 4 tile → verify thấy `4 ≠ baseline 7` → tưởng "tile giảm bất

thường" → MANUAL_REVIEW. Baseline đúng nhưng **stale sau khi user dọn trùng**.



**Fix chuẩn — sửa baseline trong post-attempt receipt** (không xóa fingerprint,

không retry mù):

```python

# idempotency/post-attempts/machine_22_video_4.json

d = json.load(open(pa)); d["pre_post_video_count"] = <baseline đúng>

# backup trước + ghi baseline_correction{reason, corrected_to, corrected_at}

```

Rồi chạy lại workflow: nó đọc baseline mới → đếm tile thực tế: bằng baseline

(video không còn, bị xóa nhầm) → cho phép đăng lại đúng 1 lần; baseline+1

(video còn) → ghi workbook. Receipt barrier vẫn chống repost.



**QUAN TRỌNG — baseline ĐÚNG ≠ số tile hiện tại** (máy 22, 2026-08-05):

lần sửa đầu đặt baseline = tile hiện tại (4) vẫn MANUAL_REVIEW vì video 4 (bài

đăng mơ hồ) VẪN còn trên profile → 4 tiles = baseline → không > → không FOUND.

User làm rõ: *"máy 22 có 1 video đăng 4h trước gần nhất. t xoá video máy 22 là

xoá máy video cũ ở xa nhất"* — video đăng mơ hồ CÒN, chỉ video cũ xa bị xóa.

→ **baseline đúng = số video CŨ trước bài đăng mơ hồ = posted count trong

workbook** (3), KHÔNG phải tile hiện tại (4 gồm cả bài mơ hồ). Với baseline=3,

profile 4 tiles → 4>3 → FOUND → chỉ ghi workbook, không đăng lại → SUCCESS.



**Hỏi user trước khi đặt baseline:** "bài đăng mơ hồ (post lúc X) còn trên

profile không?" — CÒN → baseline = posted count workbook (chỉ video cũ);

KHÔNG còn (bị xóa nhầm luôn) → baseline = tile hiện tại, workflow sẽ đăng lại

đúng 1 lần. Đặt nhầm baseline = tile hiện tại khi bài mơ hồ còn → kẹt

MANUAL_REVIEW vô hạn (đã dính 2 lần cùng ngày).



**Trước khi sửa baseline:** xác nhận tile thực tế. Dấu hiệu baseline cũ sai =

`pre_post_video_count` trong receipt cao bất thường so với `posted` workbook

(vd máy posted 3 mà receipt ghi 7). User xác nhận "đã xóa video trùng" là đủ

căn cứ để đặt baseline = số tile hiện tại (đếm thủ công qua profile hoặc chạy

workflow một lần để nó đếm).



```python

# Checkpoint là nguồn sự thật:

# runs/<run_id>/checkpoint.json  →  last_state, post_tap_attempted, post_verified, status

```

## Canonical live-launch evidence and reporting



For the exact operator workflow and concise Vietnamese reporting contract, see `references/live-launch-evidence-and-concise-reporting.md`. Durable rule: launcher exit and report existence are not success evidence; `summary.csv` plus accepted/verified post evidence is authoritative, and a live worker at wait-budget expiry must be reported as `INCOMPLETE_PENDING_WORKER` without kill/retry.



## Lọc máy bằng Assignment Manifest (thay cho `-MachineList` đã bỏ):



Launcher HEAD không còn param `-MachineList` (bản cũ 27c5cda có). Lọc máy qua

manifest + worker id, không cần sửa code:



- Manifest JSON format (xem `automation_core.assignments.AssignmentManifest`):

  ```json

  {"schema_version": 1, "assignment_id": "...", "owner_id": "...",

   "resources": ["machine:5", "machine:8", ...], "reviewed_at": "..."}

  ```

  Resource format BẮT BUỘC `machine:<số>` — khớp `assert_assigned(f"machine:{entry.machine}")`.

  Nếu để `5` thay vì `machine:5` → mọi máy bị `SKIPPED_ASSIGNMENT` im lặng.

- Truyền qua env `TIKTOK_VIDEO_ASSIGNMENT_MANIFEST` + `TIKTOK_VIDEO_WORKER_ID`

  (launcher param `-AssignmentManifest`/`-WorkerId`); `owner_id` trong manifest

  phải khớp worker id, không khớp → `ASSIGNMENT_WRONG_OWNER`.

- Luôn chạy `-PreflightOnly` trước live. Máy ngoài manifest = `SKIPPED_ASSIGNMENT`;

  máy có lock = `SKIPPED_LOCKED`. Nếu target label hiện "none" và 80 máy bị skip,

  đọc `summary.csv` cột `SkipReason` để phân biệt 2 lý do.

- `machine_inventory.py` là read-only: không ghi workbook, không acquire lock.

- **Inventory pass chưa chứng minh account đang mở đúng.** Live worker bind `target_account` từ cột `ID`/`ID TikTok`, precheck Profile bằng `verify_selected_account`, nếu lệch mới `select_exact_account`, rồi state `ACCOUNT_READY` recapture Profile và exact-verify lần nữa **trước khi resolve/push media**. Matching chuẩn hóa bỏ `@` và casefold nhưng không substring. `ACCOUNT_VERIFY_MISMATCH`, thiếu target hoặc không thấy exact account → fail closed/MANUAL_REVIEW, không Post. Khi user hỏi có check ID Excel chưa, phải trả lời rõ phân biệt **preflight workbook/device/video/lock** với **live ACCOUNT_SWITCHER→ACCOUNT_READY exact identity gate**, và nêu test/evidence thật nếu vừa verify.



**Chạy "all máy không bị lock" (workflow chuẩn, 2026-08-06):**

1. `-PreflightOnly` chạy trên toàn workbook → đọc `summary.csv` mới nhất (cột `Status`): tách 3 nhóm — `THÀNH CÔNG` (eligible), `SKIPPED_LOCKED` (có lock), `LỖI` (preflight fail).

2. **Preflight `LỖI` (exit=1) ≠ lock** — đọc `machine-<N>.err.log` (lưu ý: err.log encode **UTF-16LE** — cat bằng git-bash ra ký tự `\u0000` xen kẽ; decode qua `iconv -f UTF-16LE` hoặc python `encoding='utf-16'`). Signature gặp: `Missing required fields: ID TikTok` = **workbook Tik1.xlsx thiếu giá trị cột `ID TikTok`** cho máy đó → lỗi dữ liệu workbook, cần bổ sung cột, KHÔNG phải unlock/retry.

3. Tạo manifest MỚI chỉ gồm nhóm `THÀNH CÔNG` (máy không lock) — đừng bao giờ gom cả 80 máy.

4. Chạy lại `-PreflightOnly` VỚI manifest → verify dòng "Máy mục tiêu:" khớp đúng list, không có `SKIPPED_ASSIGNMENT`.

5. Live qua `terminal(background=true, notify_on_complete=true)` + `-Confirmation RUN`; máy nào lock xuất hiện giữa chừng vẫn tự skip `SKIPPED_LOCKED` an toàn.



**Pitfall retry/subset batch (đã gây đăng thừa video — máy 43, 2026-08-05):**

khi chạy LẠI một nhóm máy con (vd retry 3 máy lỗi), PHẢI tạo manifest MỚI chỉ

gồm đúng máy cần chạy lại. Tái sử dụng manifest cũ của batch đầy đủ khiến máy

đã SUCCESS chạy lại → resolve video KẾ TIẾP và đăng thêm video ngoài ý muốn

(máy 43 đăng video 4 + 5 cùng ngày). Máy đã verified thường KHÔNG bị đăng trùng

(fingerprint verified chặn) nhưng máy đang `verification_pending`/lỗi dở sẽ

resolve tiếp. Rule: mỗi lần chạy launcher = 1 manifest mới đúng scope; ghi

`assignment_id` + `owner_id` khác nhau để trace được batch nào đã chạy máy nào.



## Phân loại device lock trước khi dọn (lock consumer khác)



- PID chết (tasklist/wmic không trả về) = **stale**, kể cả khi file ghi

  `status: "running"` + `owner_active: true` (lock ghi running nhưng process đã chết).

- **Pitfall xóa lock: PHẢI xóa cả `machine_<N>.lock.json` VÀ `serial_<serial>.lock.json`**.

  `device_lock_paths(machine, serial)` trả cả 2 tên (xem `_lock_names`); chỉ xóa

  machine lock thì inventory vẫn báo `device lock present` (đã dính 2026-08-05:

  xóa 14 machine lock mà preflight vẫn SKIPPED_LOCKED). Serial lấy từ cột

  `device ID` workbook. Backup trước khi xóa: cp vào `backup_takeover_<date>/`.

- **Pitfall `-RecoveryMode` KHÔNG qua được lock filter ở preflight (2026-08-06)**:

  `machine_inventory._filter_locks` chặn MỌI máy có lock file (kể cả `status=handoff`,

  PID chết) ngay tại preflight — `-RecoveryMode` chỉ ảnh hưởng worker (cho phép

  handler soft-reboot/`--recovery-mode`), KHÔNG đưa máy bị lock vào

  `machine_launch_order`. Manifest chỉ gồm máy bị lock → preflight in "Máy mục tiêu:

  none" + 0 runner; phóng live vẫn 0 runner, exit 3 (đã dính 2 lần cùng ngày: retry

  11 máy lock). Quy trình đúng: (a) verify PID chết qua `tasklist /FI "PID eq X"`

  (1 slash, không `//`), (b) backup + xóa CẢ machine + serial lock, (c) preflight

  LẠI phải hiện đủ máy eligible TRƯỚC khi phóng live. `-RecoveryMode` vẫn nên bật

  khi live nếu có máy OPEN_TIKTOK_FAILED/UI_DUMP cần soft-reboot handler, nhưng

  đừng kỳ vọng nó mở khóa máy bị lock.

- Cảnh giác: scheduler `recovery_runtime` của `tiktok-luot nuoi acc` chạy LIVE với

  shift `machine=all` có thể re-acquire lock giữa chừng (đã xảy ra: máy 70-72

  `DEVICE_LOCK_FAILED` giữa batch). Dừng feed scheduler trước khi dọn lock + chạy batch.

- Pitfall git-bash: `tasklist //FI "PID eq X"` fail (MSYS nuốt `//` thành path)

  → dùng `tasklist /FI "PID eq X"` (1 slash) hoặc `wmic process where "ProcessId=X"`.

- **Pitfall WMIC CommandLine-like TỰ MATCH shell wrapper (2026-08-10)**: chạy

  `wmic process where "CommandLine like '%tiktok_workflow%'"` trả về CHÍNH bash

  wrapper của Hermes terminal (command chứa text lệnh) → false positive giống

  wrapper-only match đã biết. Query ĐÚNG để scan competitor: lọc Name TRƯỚC —

  `wmic process where "Name='python.exe' or Name='pythonw.exe'" get Name,ProcessId,CommandLine /format:list`

  rồi mới soi CommandLine cho `-m tiktok_workflow --machine N`. Đây là dạng

  chuẩn hoá của guard "accept only real python.exe/pythonw.exe".

- **Pitfall search_files không duyệt được drive D: trên host này (2026-08-10)**:

  `search_files` trả `IO error ... The system cannot find the path specified` với

  cả `D:\...` lẫn `/d/...` trong khi `read_file` đọc được — fallback dùng

  `grep -rn` qua terminal sau `cd /d/Taadaa/Tiktok-video` (read-only vẫn hợp lệ).



## Retain lock `blocked` khi FINAL_BLOCKED/MANUAL_REQUIRED + script gỡ lock tay (2026-08-06)



**Vấn đề gốc**: máy fail (vd `CAPTURE_INVALID`) → recovery `FINAL_BLOCKED` → `MANUAL_REQUIRED`,

nhưng flow `multi_machine_feed_session.py` `finally` block gọi `lease.finish(succeeded=False)`

→ chỉ `set_status("handoff")` (KHÔNG xóa file) — nhưng lock vẫn mất vì scheduler reserve mới

`status="queued"` cùng run_id mới → `_queued_promotion_payload` cho claim lại. Hệ quả:

`incident_key` chứa shift/artifact → shift kế tiếp key khác → `_is_terminal_incident`=False →

**nhặt lại máy lỗi, thử lại 7 slot, FINAL_BLOCKED lại — lỗi không bao giờ tự sửa, tốn quota**.



**Fix (consumer-only, KHÔNG đụng core)**: flow `finally` khi fail → `lease.set_status("blocked")`

(giữ file, `owner_active=false`) thay vì `finish(False)`; success → `finish(succeeded=True)` như cũ.

- `acquire_device_lock` gặp lock `blocked`: `_queued_promotion_payload`→None (status≠queued),

  `_takeover_payload`→từ chối trừ khi `takeover_authorized=True` (user chủ động) → **chặn được shift tới**.

- `_write_recovery_handoff_evidence` thêm field `lock_status`; `expected_terminal_status`

  = `released` nếu success else `lock_status`. **Pitfall default param**: default `lock_status`

  PHẢI là `"handoff"` (giữ hành vi cũ) — đặt `"released"` làm test cũ

  `test_recovery_handoff_evidence_records_terminal_lock_state` fail ngay.



**Script gỡ lock tay** `python_runner/scripts/release-device-lock.py`:

```

PYTHONPATH=python_runner:. python python_runner/scripts/release-device-lock.py --machine 60 [--serial ...] [--lock-root ...] [--dry-run]

```

- Từ chối active lock (`owner_active=true`, đang chạy thật) → exit 3, KHÔNG đụng.

- Release blocked/handoff/temporarily_skipped/queued, hoặc `running`/`recovery` với PID chết (stale) → exit 0.

- Dùng core `_release_lease_paths` qua **lease stub** (host/pid/lock_id/lock_paths) — không xóa file tay;

  ghi audit `runs/device-lock-release-audit.jsonl`.

- **Pitfall Windows PID liveness**: `os.kill(pid, 0)` KHÔNG đáng tin trên Windows — PID không tồn tại

  có thể trả `PermissionError` (tưởng alive). Dùng `tasklist /FI "PID eq X" /NH` + check số PID trong stdout.

- **Pitfall import**: `scripts/` KHÔNG phải package (không `__init__.py`) → import test bằng

  `importlib.util.spec_from_file_location("release_device_lock", path)` + `exec_module`, không `from scripts...`.



**Smoke verify chuẩn**: tạo lock giả `{host: socket.gethostname(), pid: 999999, status: blocked, owner_active: false}`

trong lock-root tạm → chạy script → exit 0 + file bị xóa + audit ghi. Lock `{owner_active: true, pid: os.getpid()}`

→ exit 3 + file còn nguyên. Chi tiết đầy đủ: `references/lock-retention-and-release-script.md`.



## Chạy reg acc pending (mail chưa reg TikTok) — workflow chuẩn



Task: "máy nào có mail chưa reg → lock máy → reg 1 acc/máy".



1. **Audit nhanh workbook** `taikhoan_dat_v2_updated .xlsx` (sheet "Tài Khoản"): máy có GMAIL nhưng ID rỗng = mail chưa reg (quy tắc vàng #0 — đếm ID thật).

2. **Detector chuẩn** `python -u _detect_clean.py` — đọc 3 workbook (source `gmail_clean_v2.xlsx`, tracking, inventory `taikhoan_run_safe.xlsx`) + policy: source-backed + password-present + TikTok-ID-empty + **max 1 acc/STT**. Ghi `_clean_targets.json`.

   - **Fail closed vì row rác inventory**: `DETECTION_BLOCKED: TARGET_INVENTORY_MISSING_SERIAL: row N` = dòng máy có giá trị nhưng serial None (tàn dư xóa dòng trong Excel) → backup + `delete_rows` dòng đó + chạy lại.

   - **Env override bẫy**: `TIKTOK_SAFE_WORKBOOK`/`TIKTOK_ACCOUNT_WORKBOOK` có thể trỏ inventory tới bản `D:\Taadaa\tiktok-luot nuoi acc\data\...` KHÁC bản OneDrive — sửa nhầm file thì detector vẫn lỗi. In `os.environ` trước khi sửa.

3. **Runner** `python -u _run_all_targets.py --full-scope-takeover` qua `terminal(background=true, notify_on_complete=true)`: tự acquire lock/STT, launch `social_reg_v1.py <serial> <stt> --ss --defer-tracking-write`, verify `tracking_result_*.json` (status=SUCCESS + tiktok_id + proof_xml + proof_screenshot).

   - `--full-scope-takeover` chỉ reclaim lock **inactive**; máy bị feed session ACTIVE (`owner_active=true`) vẫn `SKIPPED (locked)` — ĐÚNG, không giành lock máy đang nuôi acc.

   - Result: `$LOCALAPPDATA/Taadaa/Tiktok_Reg/artifacts/runs/social-batch-all/<ts>/batch_1/stt_XX/stdout.log`.

4. **FINAL_BLOCKED signatures reg** (evidence đủ ở `artifacts/ui_dumps/blocked_*` + `screenshots_social/blocked_*`; KHÔNG retry mù cùng mail): `[7d] DOB initial readback missing` (màn sinh nhật SeekBar), `GMAIL_RECOVERY_CAPTCHA` (Google CAPTCHA khi add account), `OTP_RESEND_NO_FRESH_CODE` (gốc = **Hotmail LoginBlocked**, inbox không đọc được OTP), `[06_email_option] icon_count_0` (login không thấy option email).

5. **`DEVICE_LOCK_STATUS_OWNERSHIP_MISMATCH` ở finish = vô hại** (lock bị thao tác giữa chừng); verdict per-target đã có trong summary — không panic.

6. **Batch toàn máy cùng 1 signature fail (vd DOB) → nghi commit gần đây, NHƯNG diff KỸ từng phần trước khi chốt root cause** (2026-08-11, user phản biện đúng 2 lần):

   - Lỗi `[7d] DOB initial readback missing or unparsable` hàng loạt + log `window_dump_*.xml: No such file` = **uiautomator treo** (lỗi gốc có sẵn, không phải do timeout). Bản mới `1328de2` "UI capture timeout 60s" đổi `UI_XML_COMMAND_TIMEOUT` 8→60s NHƯNG lỗi DOB thật ra do **fail-cứng mới thêm trong `fill_birthday()`**: `if not before_parsed: raise RuntimeError(...)` — bản cũ không raise, fallback estimate ngày hôm nay rồi swipe tiếp.

   - **KHÔNG kết luận theo tên commit**: user bác "tăng 60s cứu đc mà, hay do cái dob nó v? Trc khi update cái 60s có sửa nhiều cái nữa mà". Phải `git diff <commit>^ <commit> -- social_reg_v1.py` soi từng thay đổi (timeout, fail-cứng mới, refactor wheel, `_is_tiktok_dob_picker_surface_xml`...).

   - Quyết định cuối: UN-revert (giữ bản mới + timeout 60s), thêm fallback DOB thay raise, rồi swap `fill_birthday()` về bản cũ theo user ("bản ms kéo dob ngu thì dùng lại bản cũ đi") — GIỮ fix CDP OTP + timeout 60s.

   - **`[01_open] TikTok not foreground` sau launch = uiautomator treo, không phải app lỗi**: mọi dump XML fail → không đọc được màn. Fix = B1 ATX-kill, không tăng timeout.

7. **Sau revert, máy vẫn dính state bẩn từ batch fail trước** (`SignUpOrLoginActivity`/launcher cũ) → fail ở bước khác (`[01_open] TikTok not foreground`, `[02_profile]`) dù code đã đúng. Trước khi rerun: `adb -s <serial> shell am force-stop com.ss.android.ugc.trill` cho từng máy target (giữ login, KHÔNG `pm clear` — farm box điện) rồi chạy lại batch.

8. **User yêu cầu ghi root cause sau khi revert vào handoff.md** ("Lí do tại sao bản cũ dob hết cần ghi lại") — mỗi lần revert fix regression, thêm section `## <date> - Revert <commit> gây <signature>`: triệu chứng + root cause (diff timeout) + xử lý + bài học, rồi mới commit.

9. **OTP reject dù CDP đọc được code → DOM Outlook liệt kê mail MỚI TRƯỚC, CŨ SAU** (2026-08-11, máy 30/57): `_try_get_otp_outlook_cdp` dùng `reversed(candidates)` với giả định cũ "mail mới nhất nằm cuối" → lấy mã CŨ → TikTok reject. User: "mã về khác cái m nhập, m tự chế số ở đâu ra v". Fix: `for code in candidates:` (lấy phần tử ĐẦU = mới nhất). Xác minh bằng **probe CDP DOM thật** (forward port + eval regex 6 số trong node chứa "tiktok", đối chiếu timestamp mail) trước khi sửa — đừng đoán theo comment cũ trong code.

10. **Resume tại màn đang kẹt, CẤM chạy lại từ đầu** (user bắt buộc 2026-08-11): máy qua OTP xong kẹt DOB → `SOCIAL_PREFERRED_EMAIL=<email> python -u social_reg_v1.py <serial> <stt> --ss --defer-tracking-write --resume` (nhánh resume xử lý email form/OTP/DOB/password/name từ màn hiện tại). Trước khi chạy: dọn lock stale (machine+serial lock, status=handoff + owner_active=false + PID chết). KHÔNG `am force-stop` khi resume (mất màn hiện tại = chạy lại từ đầu). Signatures DOB còn lại: `DOB_CONTINUE_NO_TRANSITION` (máy 34 từng FINAL_BLOCKED; budget 2 attempts rồi dừng).



Chi tiết + transcript: `references/tiktok-reg-pending-run-20260811.md`.



## Giữ nguyên trạng thái lỗi — user yêu cầu (2026-08-05)



**Khi nghi ngờ trạng thái máy (report MANUAL_REVIEW/FAILED hoặc post mơ hồ):**

kiểm tra màn hình THỰC TẾ qua ADB trước khi kết luận/chạy lại:



```bash

adb -s <serial> shell dumpsys activity activities | grep -iE "mResumedActivity|mFocusedActivity"

```



Phân biệt:

- `SplashActivity` → TikTok đang mở/load lại (chờ nó về Profile rồi retry).

- `LauncherActivity` (home) → cleanup đã thoát app — trạng thái lỗi KHÔNG được

  giữ, đây là lỗi policy cần ghi nhận + sửa consumer.

- `MainActivity` (feed) hoặc Profile → máy đang ở surface dùng được.



**Hành động đúng:** xác định máy đang ở đâu → nếu home thì ghi nhận vi phạm

giữ-trạng-thái, nếu Splash/Profile thì chờ ổn định rồi retry. Không retry mù

trên máy đang ở home (workflow sẽ mở lại TikTok từ đầu, không tái hiện lỗi gốc).



**Khi user xác nhận đã dọn video trùng** (duplicate cleanup ngoài luồng): baseline

trong post-attempt receipt trở nên stale — `POST_RECHECK_UNAVAILABLE` kéo dài

nhiều lần là dấu hiệu. Xem pitfall `POST_RECHECK_UNAVAILABLE` ở trên: sửa

`pre_post_video_count` trong receipt về số tile thực tế rồi chạy lại (không xóa

fingerprint — đã bấm Post).



## Direct live recovery with a rebinding template (2026-08-10)



For a user-authorized recovery of a small, explicit machine set in `D:\\Taadaa\\Tiktok-video`, when the batch launcher/worker contract says the worker binds the workbook row from `--machine`, **do not create or require `config-machine-N.yaml`**. Use the existing template `D:\\CodexRuntime\\tiktok-video\\config-machine-62.yaml` and pass `--machine N`; require the worker log proof `effective config rebound to this row`.



Mandatory bounded workflow:

1. Read each target's newest `report.json` and confirm `post_submission_state is None` before retrying. Record the exact prior status/reason; do not infer from process exit.

2. Inspect both exact lock aliases (`machine_N.lock.json` and `serial_<serial>.lock.json`) plus their recorded PID/status/owner. A stale takeover requires `status=handoff`, `owner_active=false`, and an independent Windows PID check (`tasklist /FI "PID eq X" /NH`) showing no matching PID. Also scan for a live replacement/competitor **by process metadata**, not substring alone: accept only an actual Python executable (`python.exe`/`pythonw.exe`) whose command line contains `-m tiktok_workflow --machine N`. Bash wrappers (including the current diagnostic shell) can contain those strings and are false positives; never kill or reclaim on a wrapper-only match.

3. Archive only the exact stale aliases for named targets into a timestamped backup/evidence directory; the archived lock payload must contain only `machine_N.lock.json` and `serial_<serial>.lock.json` that passed the matching-field/PID checks. Never archive broad lock globs or foreign/active locks. If a verification script/parser fails, stop before moving anything; fix the verifier and rerun the guard.

4. Launch each target as a separate background process, never a shell loop. For an explicitly authorized full-ladder recovery, the worker must include both `--recovery-mode` and `--allow-device-reboot-recovery`; omitting the allow flag means soft reboot/coordinate stages were not exercised and does not count as evidence against them. Exact worker shape:

   `echo "YES" | PYTHONPATH="D:/Taadaa/Tiktok-video/scripts" "/d/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe" -m tiktok_workflow --config "D:\\CodexRuntime\\tiktok-video\\config-machine-62.yaml" --machine N --no-dry-run --recovery-mode --allow-device-reboot-recovery > /d/CodexRuntime/tiktok-video/recovery-m35-full-ladder-<timestamp>.log 2>&1; echo WORKER_EXIT=$?`

   The template config is intentionally rebound by `--machine N`; require log proof `effective config rebound to this row`. Do not manually substitute ATX kill, reboot, coordinate taps, or Xiaowei UI actions.

5. Wait for every worker, then independently resolve the report path from each recovery log and read the final report. A success claim requires `status=SUCCESS`, `post_verified=true`, and an accepted/verified post state (observed contract: `post_submission_state=ACCEPTED`); `WORKER_EXIT=0` alone is not proof. Record the exact ladder stages that actually appear in the log (ATX kill, force-stop/relaunch 1/2, soft reboot, coordinate fallback). The presence of the allow flag proves authorization/configuration only—not that every stage ran. If the state machine stops at a different classified failure before a later stage, report that fact and stop fail-closed; do not run an outside-script recovery action.

6. Verify final lock state: successful targets should release both aliases; blocked targets retain their locks and must be reported. Do not touch excluded machines or the source repo; do not commit/push.



**Pitfall — B3 vẫn không reboot vì API drift consumer↔core (2026-08-10, v3 m5/35/70):** HEAD 9301585 bỏ qua `DEVICE_LOCK_PROXY_HANDOFF_UNSUPPORTED` (watcher-managed) rồi gọi `reboot_and_restore(..., wait_for_proxy_ready_before_post_reboot=...)`, nhưng venv-core024 đang cài automation-core **0.4.40** chỉ có param `wait_for_proxy_ready_after_reboot` → mọi máy tới B3 chết ngay: `[REBOOT] Guarded reboot recovery failed: reboot_and_restore() got an unexpected keyword argument 'wait_for_proxy_ready_before_post_reboot'` → rơi xuống coordinate fallback/FINAL_BLOCKED. **Guard TRƯỚC launch** — probe ĐÚNG venv vì shell Hermes dính PYTHONPATH/PYTHONHOME làm `python -c "import automation_core"` resolve nhầm automation-core của hermes-agent venv (signature giả):

```bash

env -u PYTHONPATH -u PYTHONHOME "<venv>/Scripts/python.exe" -c "import automation_core, inspect; from automation_core.device_recovery import reboot_and_restore; print(automation_core.__file__); print(list(inspect.signature(reboot_and_restore).parameters))"

```

Xác nhận `__file__` nằm trong venv (không phải `...\hermes\hermes-agent\venv\...`) rồi so từng keyword consumer truyền (grep `reboot_and_restore(` trong `state_machine.py`). Lệch param → **dừng, báo user, KHÔNG hot-edit code** (policy), reconcile pin core trước khi retry. Pin file `requirements-automation-core.txt` ≠ venv đã cài — luôn probe venv.

- **Đã fix từ 43e1825**: consumer từ 43e1825 gọi đúng `wait_for_proxy_ready_after_reboot` (xác nhận probe pass ngày 2026-08-10 với HEAD f58a425 + venv-core024 0.4.40) — drift cũ hết, nhưng QUY TRÌNH probe venv trước launch VẪN bắt buộc (venv có thể lệch pin bất kỳ lúc nào).



**Pitfall — đọc ladder sai:** dòng `[OPEN_TIKTOK] Ladder cạn (relaunch x2 + soft-reboot đã thử)` KHÔNG phải bằng chứng soft reboot đã chạy — v2 log (6ad3cfd) có dòng này mà zero marker reboot thật. Bằng chứng B3 chạy thật = marker `=== SOFT REBOOT RECOVERY (AUTOMATION-CORE) ===` + kết quả `[REBOOT] ...`; nhánh watcher-managed kỳ vọng `proxy_handoff_skipped_watcher_managed` → `after reboot (watcher-managed)` chờ `wait_for_proxy_ready` 90s/poll 30s → `require_android_vpn`. Ghi từng bước ladder thực tế xuất hiện trong log, không suy từ câu chữ "đã thử". Chi tiết + transcript: `references/recovery-v3-core-api-drift-20260810.md`.



See `references/direct-worker-recovery-template-config.md` for the concise operator checklist and evidence schema. See `references/explicit-single-machine-recovery-ladder.md` for full-ladder authorization, process-scan guards, stage-by-stage log interpretation, and fail-closed handling. See `references/concurrent-live-recovery-reconciliation.md` for the recheck/overlap guard and final evidence checklist.



### Concurrent recovery reconciliation and final-proof guard



A stale-lock recovery can race with another launcher, scheduler, or already-started worker. Treat every lock/process observation as a short-lived snapshot:



1. **Do not archive from an old preflight.** Immediately before moving aliases, re-read the exact `machine_N.lock.json` and `serial_<serial>.lock.json` pair for every named target, verify matching machine/serial/project/lock_id, require `status=handoff` + `owner_active=false`, and re-run an independent Windows PID check. If a lock disappears, changes to `running`, or is recreated, stop that target and reconcile rather than reclaiming it.

2. **Scan live process metadata before takeover and before launch.** Accept only a real `python.exe`/`pythonw.exe` process whose command line contains `-m tiktok_workflow --machine N`; do not treat a bash/PowerShell wrapper or a substring-only match as ownership. Never launch a second worker for a machine already represented by a live process, even if an old lock snapshot said stale.

3. **Existing recovery artifacts are authoritative evidence of possible overlap.** If `recovery-*` logs, run directories, or post-attempt receipts appear after preflight, pause and inspect them. A later `post_submission_state=ACCEPTED` receipt/report means the target is not a safe blind upload retry; let the state machine's receipt barrier verify/finalize it, or classify it as already successful.

4. **Wait for all workers, then resolve each report path from its own log.** A success claim requires `status=SUCCESS`, `post_verified=true`, and `post_submission_state=ACCEPTED` (or the documented equivalent). `WORKER_EXIT=0` is not sufficient; if the exit marker is absent, record exit as unknown and use report evidence instead of inventing an exit result.

5. **Final lock invariant:** verified-success targets release both aliases; `MANUAL_REVIEW`/blocked targets retain both aliases as inactive handoff locks. Recheck no target `tiktok_workflow` process remains and verify foreign/registration locks are still present and unchanged. Archive evidence must contain exactly two aliases per authorized target and no excluded alias.



The detailed session-oriented guard and evidence fields are in `references/concurrent-live-recovery-reconciliation.md`.



### Recovery-v4 evidence discipline (2026-08-10)



For a small, explicitly authorized multi-machine recovery, keep four gates separate: fresh report eligibility, exact lock archive, state-machine ladder execution, and final verifier proof.



- Retry only targets whose newest report has `post_submission_state is None` and `post_verified=false`. Success is report-backed: `status=SUCCESS` plus `post_verified=true` and accepted/verified post state. A worker exit code or a newly acquired lock is never completion proof.

- Archive only the exact machine/serial aliases after rechecking expected project/status, `owner_active=false`, and PID liveness with Windows `tasklist /FI "PID eq X" /NH`. Copy every alias first into a timestamped backup, then write timestamped evidence. A foreign lock requires explicit user authorization and an exact release reason; leave all other foreign aliases untouched.

- In logs, distinguish a startup prerequisite failure such as `non_xml_ui_dump` at `CONNECT_DEVICE/close_all_apps_start` from a ladder failure. If the run ends before `WAIT_FEED`, report `ladder_not_entered`; do not infer B1/B2/B3 from `--recovery-mode` or `--allow-device-reboot-recovery`.

- Record only observed markers: feed timeout, splash recovery #1/#2, ATX-kill (B1), force-stop/relaunch (B2), actual soft reboot (B3), post-boot watcher readiness, coordinate fallback, and `MANUAL_REVIEW`. B3 requires both an actual reboot marker and a post-boot watcher/proxy-ready recapture; the flag alone is not evidence.

- Wait for every live process before final reporting. A polling timeout means the worker is still unresolved, not failed or successful. If the runtime/tool budget ends with a worker alive, report `INCOMPLETE_PENDING_WORKER` with its PID/log and do not fabricate a final report or total.

- Keep inactive handoff locks for `MANUAL_REVIEW`/blocked targets; verified-success targets must independently show both aliases released. Never perform manual ADB tap/back/reboot or outside-script coordinate recovery.



See `references/recovery-v4-evidence-discipline.md` for the sanitized three-target marker sequence and classification examples.



### Avatar recovery chạy FULL media pipeline — receipt barrier là chốt chặn (2026-08-10, m36/m38)



`--force-avatar-upload --force-avatar-machines N` KHÔNG giới hạn worker ở ENSURE_AVATAR:

workflow vẫn đi `RESOLVE_NEXT_VIDEO → MEDIA_PUSH → VIDEO_PICK → CAPTION_FILL → POST →

VERIFY_POST → UPDATE_WORKBOOK` rồi MỚI tới `ENSURE_AVATAR`. "Chỉ retry avatar (không retry

post)" nghĩa là receipt barrier chặn repost, KHÔNG nghĩa là pipeline bỏ qua media/post.



- Receipt `verification_pending` + `post_submission_state=ACCEPTED` (m36 video 12): worker

  resolve đúng video đó, push media lại, đi qua composer, barrier finalize — log thấy

  `Workbook updated: Video Đã Đăng = 12` mà KHÔNG tap Post thật. Đúng, không repost.

- Receipt `completed` + ACCEPTED mà worker VẪN re-resolve CÙNG SHA (m38 video 15, SHA

  `92caccd…` trùng receipt) rồi log `tapped exact post button text` → NGHI REPOST. KHÔNG tự

  kết luận; đọc report cuối (post_verified / post_submission_state / tile profile) + receipt

  mới trước khi xác nhận. Artifact-overlap guard: không phóng worker mới tới khi xác minh.

- Trước launch, đọc receipt mới nhất

  (`idempotency/post-attempts/machine_N_video_M.json`) để biết video worker sẽ resolve là

  `verification_pending` (barrier finalize — kỳ vọng) hay `completed` (cờ đỏ nếu re-resolve

  + tap Post). So SHA fingerprint log với `media_sha256` receipt để phát hiện re-resolve.

- Logs/session detail: `references/avatar-recovery-m36m38-20260810.md`.



## VIDEO_PICK normalize-Home: surface video-detail fullscreen (2026-08-11)



Sau MEDIA_PUSH, TikTok có thể resume về **video-detail fullscreen** (mở video từ

Profile — m74 `run_ce061606c21e153d03_20260811_071130`): surface này KHÔNG có

bottom nav nên **không có tab 'Trang chủ' để tap** → normalize-Home cũ fail

`taps=0` + `VIDEO_PICK_HOME_NOT_REACHED` (artifact `media-push-home-normalize-failed.png`).



- **Classifier `_is_video_detail_surface`** (semantic, không tọa độ mù, không

  branch máy): yêu cầu ĐỦ 4 điều kiện — top Back (resource-id `back` hoặc

  desc/text `quay lại`/`back` trong top 30% màn), top related-search bar

  (`Tìm nội dung liên quan`/`Tìm kiếm video liên quan`/`search bar`), marker

  caption/author (`Thêm vị trí`/`Add location`), và KHÔNG có bottom-nav

  (`home_tab`/`following_tab`/`profile_tab` trong strip ≥75%).

- **Nhánh normalize**: detect video-detail → foreground gate TikTok

  (`_package_is_foreground` qua ActivityManager) → Back bounded tối đa 2 lần,

  artifact `media-push-home-video-detail-before.png` + recapture sau mỗi Back →

  xác nhận Profile root CÓ bottom nav → tap `Trang chủ` semantic như nhánh cũ

  → chờ Home + labelled bottom-centre create control. Hết budget vẫn

  video-detail → fail closed `VIDEO_PICK_HOME_NOT_REACHED/VIDEO_DETAIL_STUCK`,

  KHÔNG fallthrough vào VIDEO_PICK. Checkpoint `media_push_home_normalize` ghi

  `taps`/`backs`/`video_detail_stuck`.

- COMPAT entry: `docs/tiktok-ui-compatibility.md` **COMPAT-VIDEO-PICK-005**.

- Chi tiết + transcript: `references/video-detail-normalize-home-20260811.md`.



## VIDEO_PICK fail-closed identity gate — không bao giờ chọn tile theo heuristic (2026-08-11)



Máy 74: `D:\TIKTOK-videonuoinick\585\7.mp4` được push + index bởi media provider,

nhưng picker TikTok không lộ filename và không expose Download album → fallback cũ

`_find_newest_video_tile`/`_find_visual_video_tile` chọn tile bằng duration/top-left

heuristic → tap nhầm VIDEO CŨ tại (180,546).



- **Luật**: khi Download album không mở được, tile chỉ được tap sau khi visual/source

  identity match DUY NHẤT. Không bao giờ chọn theo newest/duration/top-left. Không chứng

  minh được → fail-closed `VIDEO_PICK_TARGET_UNVERIFIED` (sentinel vào `context.error`,

  handler trả False, KHÔNG tap).

- **Pipeline verify**: `_video_tile_candidates(xml)` (bounds từ grid j6k/iht + o79/n8g)

  hoặc `_duration_overlay_regions(screenshot)` (duration overlay CHỈ là bộ lọc candidate)

  → `_video_source_frames(video_path)` extract 5 frame bằng ffmpeg (timestamps

  {0.0, 0.15, 0.35, 0.6d, 0.85d} — sampling DÀY đầu video vì within-video temporal

  correlation có thể tụt tới ~0.47 trên video chuyển cảnh nhanh) →

  `_verify_video_tile_identity` correlation 64x64 grayscale (max theo frame) → tap chỉ

  khi `best ≥ 0.35 AND best − second ≥ 0.05` (single candidate chỉ cần threshold).

  Ngưỡng/margin config: `video_pick_tile_similarity_threshold` / `_margin`.

- **Kiểm chứng ngưỡng bằng đo lường thật TRƯỚC khi chốt**: ma trận self vs cross trên

  chính các file video (7.mp4: self-best 0.992, cross vs 6.mp4 0.866, gap 0.127; 64px

  tách tốt hơn 32px). Đừng chọn threshold theo cảm tính.

- **Legacy helper**: `_find_visual_video_tile()` (không path) giữ nguyên hành vi

  duration-heuristic CHỈ cho unit test cũ; handler live luôn truyền `video_path=...`.

  Đổi hành vi helper = vỡ 2 test legacy (`test_video_pick_visual_fallback_*`).

- COMPAT entry: `docs/tiktok-ui-compatibility.md` **COMPAT-VIDEO-PICK-001**.

- Regression tests: `test_video_pick_ambiguous_grid_fails_closed_without_tap`,

  `test_video_pick_taps_only_source_verified_tile`,

  `test_video_pick_visual_fallback_fails_closed_on_ambiguous_identity`,

  `test_video_pick_visual_fallback_requires_source_identity_not_duration`,

  `test_video_pick_fails_closed_when_source_frames_unavailable`.

- Chi tiết + số liệu: `references/video-pick-identity-gate-20260811.md`.



### Pitfall XML classifier (uiautomator parse) — lặp lại được



- **`" ".join(x.casefold().split() for ...)` → TypeError "expected str instance,

  list found"**: `.split()` trả LIST, join nhận list-of-lists → crash âm thầm khi

  node có cả `text` lẫn `content-desc`. Phải bọc inner join:

  `" ".join(" ".join(normalize(...).casefold().split()) for ...)`.

- **screen_height phải là max bottom của MỌI node (two-pass)**: tính

  `max(bottom, 1)` theo từng node làm bounds filter 30%/75% sai (node back nhỏ

  → height 192 → center_y > 57 → bị skip) → classifier luôn False. Pass 1 lấy

  max height, pass 2 mới duyệt node.

- **Unit test adapter fake không có `_adb`** → `_package_is_foreground` trả None

  → handler bị chặn ở gate. Patch `_package_is_foreground` + `_visual_feed_surface_visible`

  trả True trong test thay vì tin vào gate thật.



### Pitfall patch tool trên file khổng lồ (state_machine.py ~11.7k dòng)



- replace-mode với old_string ngắn có thể match 164 chỗ ("Found 164 matches") —

  dùng **V4A patch mode** neo vào ĐÚNG MỘT dòng duy nhất (vd

  `def _media_push_normalize_machine(self, tmp_path):`) làm anchor.

- Fuzzy matcher có thể làm hỏng indentation cả block (thụt lùi toàn bộ body) —

  sau edit bị lỗi, đọc lại đúng vùng rồi replace lại nguyên block một lần;

  `py_compile` bắt lỗi ngay.

- **Fuzzy matcher hỏng lặp lại (≥2 lần cùng block) → bỏ patch replace, dùng

  python-splice**: đọc file thành `lines`, tìm start/end theo marker `def <tên>(`

  duy nhất, thay đúng span `lines[start:end] = new.split("\n")`, ghi lại giữ CRLF.

  Mỗi lần patch replace thêm vào block đang lỗi càng làm lệch thêm — splice xác

  định và đúng một phát.

- **Chạy test suite từ Hermes shell phải `PYTHONPATH= python -m pytest ...`**:

  Hermes bơm `PYTHONPATH` trỏ hermes-agent venv site-packages → PIL/numpy của

  automation venv hỏng (`cannot import name '_imaging'`, numpy cp311 lib vs cp312

  runtime) → test dùng PIL fail oan. Prefix `PYTHONPATH=` (rỗng) cho automation venv

  thắng; thêm `-p no:cacheprovider` khi `.pytest_cache` Permission denied.

- Patch chèn dòng LF vào file CRLF → normalize lại EOL bằng python one-liner

  (`read_text(...).replace('\r\n','\n').replace('\n','\r\n')` + `newline=''`) trước

  khi `git diff --check`.



## VERIFY_POST false-positive SUCCESS + evidence discipline (2026-08-12, m74)



User bắt 2 lần báo DONE giả: workflow báo `post_verified=True` + ghi workbook +1 nhưng **profile thật không có video mới**. Root cause là chuỗi lỗi VERIFY_POST nhận diện sai:



- **Receipt UNKNOWN ≠ SUCCESS**: tap Post bị ADB timeout → receipt ghi `post_submission_state=UNKNOWN`, `post_submission_accepted=False`, KHÔNG có `post_tapped_at`/`post_submission_accepted_at`. Run sau nhảy thẳng VERIFY_POST (receipt cũ) → đếm tile "3→4" → kết luận success → ghi workbook SAI.

- **Tile-count increment là bằng chứng YẾU khi scan không reliable**: log `[PROFILE_GRID] Không tìm thấy scroll container; dừng ở viewport 1` = chỉ đếm 1 viewport (profile thật 5-6 tile nhưng baseline ghi 3) → `3→4` là chênh lệch đếm sai, không phải video mới lên.

- **So sánh receipt thành công thật (video 6):** `post_submission_state=ACCEPTED` + có đủ `post_tapped_at` + `post_submission_accepted_at`. Mọi báo "đã đăng" phải đối chiếu 3 field này.



### Fix đã commit (720dcd5) — contract mới



1. `_post_submission_state_allows_success()`: UNKNOWN (có post attempt evidence) → chặn success/ghi workbook → MANUAL_REVIEW. Chỉ ACCEPTED mới đủ điều kiện update workbook.

2. `_profile_scan_is_reliable()`: count increment chỉ đáng tin khi `viewports >= 2` (scroll container tìm thấy). Scan 1 viewport = lower bound, không kết luận increment.

3. Generic `SUCCESS` text marker ("đã đăng") → `POST_VERIFY_PROOF_INSUFFICIENT`, không phải publication proof.

4. Regression tests: UNKNOWN blocked even with increment; unreliable scan → không kết luận; ACCEPTED + reliable increment vẫn pass. Suite 350.



### Quy tắc báo cáo cho user (m74 đã dính 2 lần)



- Khi nói "đã đăng xong" cho máy cụ thể: **chụp profile thật qua ADB + vision đếm tile** (trước/sau), kèm `post_submission_state=ACCEPTED` + `post_tapped_at`/`post_submission_accepted_at` từ report. Không bao giờ chỉ dựa vào `status=SUCCESS`/workbook.

- Workflow tự báo success NHƯNG profile không tăng → báo cáo lại như "UNKNOWN/FAILED", revert workbook + archive receipt sai (`machine_N_video_M.json.bak-false-complete-*`) + archive fingerprint `verified_success` sai (`*.json.bak-false-verified-*`) để retry thật được.

- Pattern false positive: `post_submission_state=UNKNOWN` + `completed_at` tồn tại = receipt bị đánh dấu hoàn tất giả.



### CANARY rollout trước khi chạy nhiều máy (user yêu cầu)



Sau khi fix code + suite xanh + audit APPROVED: **không phóng hết batch**, chạy 2-4 máy có `Video Đã Đăng` thấp nhất (có config sẵn, folder đủ 45 mp4) → mỗi máy 1 lần `terminal background` → verify từng report (SUCCESS + ACCEPTED + workbook +1). Mái 74/35/39/13 đều SUCCESS trong canary 2026-08-12 → mới commit push. User: "Chạy code đó upload cho các máy có số video đã đăng ít. Xem có gây lỗi script k".



### Pitfall: live-caught bug mà unit test mock không bắt



`StateMachine._video_frame_tile_similarity(frame, tile)` không phải `@staticmethod` nhưng `_tile_similarity_to_frames` gọi `self._video_frame_tile_similarity(frame, tile)` → runtime `takes 2 positional arguments but 3 were given`, handler VIDEO_PICK fail-closed hàng loạt. Test 350 pass vì mock adapter không chạy path thật. **Bài học: test pass ≠ live pass — chạy ít nhất 1 canary máy thật trước khi kết luận "không gây lỗi script".** Fix: gọi qua class `StateMachine._video_frame_tile_similarity(...)` (giống `_image_correlation`).



### Pitfall: fingerprint stale do run killed



Kill process giữa run để lại:

- `media-fingerprints/<key>.json` status=`reserved` (run mới reserve nhưng chết) → `MEDIA_FINGERPRINT_PENDING` chặn retry → archive `.bak-reserved-killed-*`.

- `verified_success` SAI từ run false-positive → `DUPLICATE_MEDIA_BLOCKED` chặn retry → archive `.bak-false-verified-*`.

- Cả hai: không delete thẳng, `mv` sang `.bak-*` để trace.



> avatar-env-notes.md





## Live retry evidence and ladder-proof guard (2026-08-10)



For a small user-authorized retry, the worker flags `--recovery-mode --allow-device-reboot-recovery` authorize the bounded ladder; they do **not** prove that any ladder stage ran. Read the worker log and report independently:



1. Fresh eligibility is report-based: retry only when the newest report has `post_submission_state is None` and `post_verified=false`. A worker exit code or lock reacquisition is never upload proof.

2. Archive only the exact stale aliases for named targets (`machine_N.lock.json` and `serial_<serial>.lock.json`) after an immediate re-read, matching machine/serial/project/lock_id, `status=handoff`, `owner_active=false`, and two independent Windows PID checks. Copy to a timestamped evidence directory before moving. Never glob/archive foreign locks; explicitly record excluded foreign aliases.

3. The final success predicate is `status=SUCCESS`, `post_verified=true`, and `post_submission_state=ACCEPTED` (or an explicitly documented equivalent). Record the report path, log path, video/account fields when present, and final lock invariant.

4. Record observed stages only. B1 needs an explicit ATX-kill marker; B2 needs a recovery force-stop/relaunch marker; B3 needs an actual soft-reboot marker **plus** post-boot watcher/proxy-readiness evidence. A normal `[OPEN_TIKTOK] Force-stop + relaunch 1/2` line is not automatically B2. A screenshot/coordinate fallback used during ordinary `VIDEO_PICK` is not the post-ladder coordinate fallback. Do not infer stages from flags or phrases such as “ladder exhausted.”

5. If a run stops at `CONNECT_DEVICE` with `non_xml_ui_dump`, classify `ladder_not_entered` unless the log proves the ladder markers. Report whether `timeout=60` is explicitly observable; a repeated signature alone does not prove the runtime waited 60 seconds. If the consumer stops before the required ladder and no outside-script recovery is authorized, fail closed, retain inactive handoff locks, and do not hot-edit code.



See `references/live-retry-reporting-and-ladder-proof-20260810.md` for the sanitized transcript pattern and reporting checklist.



## RULE 3 BƯỚC FIX MỌI LỖI (2026-08-10, phủ all repo + core)



BẤT KỲ lỗi nào (UI dump/capture-invalid/popup/terminal, kể cả không phải UI) → TỰ chạy 3 bước fix NGAY, KHÔNG chờ user nhắc: B1 ATX-kill (chạy khi gặp lỗi bất kỳ) + B2 force-stop + B3 soft reboot (B2/B3 mỗi 1 lần/turn/máy) → lỗi lặp lại chỉ ATX-kill + coordinate fallback có evidence → fail MANUAL_REVIEW. Nguồn: PROJECT_RULES.md các repo Taadaa + automation-core/docs/ui-compatibility-contract.md (commit 2026-08-10).



## ADB load tuning + đo cải thiện PHẢI chạy live, không preflight (2026-08-13, user correction)



**User workflow correction (quan trọng)**: user yêu cầu "test xem có cải thiện không" sau khi tuning ADB → phải chạy **LIVE batch ngay** (manifest mới đúng scope + `-MaxParallel` đã giảm + background + `Peak active runners` confirm + so `summary.csv` signature với batch cũ). Preflight chỉ đo inventory, KHÔNG đo cải thiện — user phản đối rõ: *"chưa chạy mà đo preflight cái đéo gì"*. Không bao giờ trả lời câu hỏi "cải thiện chưa" bằng kết quả preflight.



**Tuning đã áp dụng (13/08)** — chi tiết + số đo: `references/adb-load-tuning-20260813.md`:

- Env User (kibe PC): `ADB_SERVER_SOCKET=tcp:localhost:5037`, `ADB_MDNS_OPENSCREEN=0` — ghim port chuẩn, tắt mDNS dò tìm, chống crash adb.exe `0xc0000409` (`STATUS_STACK_BUFFER_OVERRUN` trong `ucrtbase.dll`) khi nhiều lệnh ADB song song; vô hại với farm USB. Nhật ký + revert: `D:\Taadaa\reports\adb_environment_tuning.md`. Verify: PowerShell `[Environment]::GetEnvironmentVariable(name,'User')`.

- Screencap **exec-out-first** (`device_transport.py::screenshot`): thử `exec-out screencap -p` (1 lệnh ADB duy nhất, stream PNG) TRƯỚC; fallback shell screencap + pull. Đo thật máy 62: 0.98s/416KB. Cũ thử shell+pull trước → thêm 1 cặp lệnh chậm khi nghẽn.

- Launcher `run_tiktok_upload_batch.ps1`: `$MaxParallel` default 30 → 16 (ValidateRange vẫn 1-30).

- **UI capture timeout 60s là ĐÚNG, KHÔNG tăng** (user chốt: để UI load, tránh lỗi UI). Chỉ 2 chỗ dài hơn KHÔNG phải UI capture: `adb push` 120s (`media_manager.py:116`) và reboot recovery `boot_timeout=120`/`verification_timeout=180` (`state_machine.py:4264`). Tăng timeout capture chỉ làm worker chiếm ADB lâu hơn.

- **Multi-port ADB KHÔNG giúp giảm lag**: ADB server chỉ nghe 1 port; mỗi device gắn 1 server; bottleneck là device CPU/USB hub, không phải host port. Đừng đề xuất nhiều `adb start-server -P`.

- Test stale pitfall: `tests/test_machine_inventory.py::test_upload_launcher_core_version_gate...` assert `$defaultAutomationCoreVersion` hardcode (cũ 0.4.35, launcher dùng 0.4.40) → fail oan khi sửa launcher; update test assert cùng lúc bump version gate.



**Kỳ vọng sai: tuning ADB KHÔNG sửa fail-closed gates**. Sau khi giảm tải (MaxParallel 16 + exec-out + env), tỷ lệ lỗi batch Tik2 gần như KHÔNG đổi:

- `VIDEO_PICK_TARGET_UNVERIFIED`: 18/43 (42%) → 19/48 (40%)

- `POST_SUBMISSION_UNKNOWN`: 14/43 (33%) → 17/48 (35%)

- Lỗi ADB/UI-capture thuần (non_xml_ui_dump, idle_state, DEVICE_NOT_PROVISIONED) chỉ ~10% tổng lỗi.



**Lỗi UI capture chia 3 nhóm KHÁC NHAU, đừng quy hết cho ADB lag**: `uiautomator_idle_state_error`/`null_root_node` = ATX/UiAutomator treo (B1 ATX-kill); `DEVICE_NOT_PROVISIONED` = persistent backend chưa provision (retry ADB mù vô ích); `ADB command timeout ... screencap` rồi `exec-out fallback` thành công = transport lag thật.



**Chẩn đoán slot A chạy / slot B fail cùng code (Tik1 vs Tik2, 13/08)**: so cột "Video Đã Đăng" 2 workbook TRƯỚC KHI nghi code. Tik1 73/80 máy đăng 7-15 video (đang vận hành); Tik2 chỉ 1/80 (máy 62) → **Tik2 CHƯA BAO GIỜ chạy được hàng loạt, không phải "giảm sút đột ngột"**. KHÔNG kết luận "máy bẩn/MediaStore stale" khi slot B fail — user bác bỏ ngay: **cùng 1 máy vật lý chạy cả Tik1 lẫn Tik2 (cùng serial)**, Tik1 vẫn OK trên máy đó → khác biệt là DỮ LIỆU (account + folder + NGUỒN VIDEO), không phải trạng thái máy. Nguồn video là biến quyết định: **Tik1 = render tay ("ông A"), Tik2 = render script random** (ffprobe máy 5: Tik1 7.07s/3MB/3.5Mbps/29.97fps vs Tik2 8.3s/5.5MB/5.4Mbps/30fps).

- Receipt cursor drift: `[POST_RECEIPT_CURSOR] Workbook next=1 nhưng receipt đã completed [1,2]; chuyển sang video #3` → máy resolve video #3 dù workbook dang=0.

- Folder thiếu video thật: máy 14 `106\3.mp4 not found` (folder 106 thiếu 3.mp4 + 16.mp4 dù count 45 file = dư/missing).

- Máy có thể VIDEO_PICK OK (similarity 0.608 verified) nhưng vẫn fail ở POST → `POST_SUBMISSION_UNKNOWN: no ACCEPTED evidence` → MANUAL_REVIEW (fail-closed đúng, không phải ADB).



**ROOT CAUSE VIDEO_PICK metric fail trên video render-random (13/08, m45 — bằng chứng đầy đủ: `references/video-pick-metric-render-random-20260813.md`)**: khi log `best similarity=0.09-0.18 < threshold=0.350` nhưng vision xác nhận tile picker GIỐNG HỆT frame video (cùng người mũ chấm bi, emoji, 13s), toàn bộ pipeline data ĐÚNG:

- Push thành công (`ls /sdcard/DCIM/Camera/` thấy file, 12.2MB đúng).

- MediaStore CÓ index: `adb shell content query --uri content://media/external/video/media --projection _id,_display_name,datetaken` trả row đúng file.

- Tile picker hiện ĐÚNG video (không phải tile cũ) — vision so crop tile vs frame extract `ffmpeg -ss 0.15` trùng khớp.

→ Lỗi nằm ở **METRIC**: correlation 64x64 grayscale không chịu được thumbnail TikTok = crop 1:1 vuông + badge thời lượng + vòng tròn + nén mạnh. Video Tik1 thumbnail sạch → correlation cao → pass; video Tik2 render-random (kèm emoji/sticker nội dung + nén) → correlation vỡ dù nội dung đúng 100%. **Hướng fix đúng = đổi metric sang feature match (ORB/SIFT + ratio test hoặc histogram), KHÔNG phải tuning ADB/xoá lock/retry.**

- **Pitfall đo lại correlation ngoài luồng**: `video-pick-target-verify.png` trong run dir là **FULL SCREEN 1080x1920, không phải tile crop** — so full-screen với frame cho corr sai thấp (nền trắng chiếm phần lớn). Phải self-crop tile từ `video-pick-grid.png` theo bounds thật: scan hàng trắng (tab bar trắng std≈0 ở y≈168-340, tile bắt đầu y≈350-700) rồi crop 357x357, mới so được với frame.

- **PITFALL POST_SUBMISSION_UNKNOWN do verify quá sớm**: log m38 `POST 09:37:37 → VERIFY_POST 09:37:37 → submission state UNKNOWN (no ACCEPTED evidence)` — VERIFY_POST chạy ~2s sau tap Post, TikTok chưa kịp xác nhận → UNKNOWN fail-closed. Trước khi kết luận "post fail", check khoảng cách POST→VERIFY trong execution.log; <5-10s = timing issue (chờ/recapture profile đủ lâu), không phải ADB/recovery.



**Kết luận**: ADB tuning giúp phần transport lag; 2 nhóm lỗi lớn của Tik2 là dữ liệu/trạng thái máy (MediaStore stale, receipt drift, thiếu video), không phải ADB. Bước tiếp theo hiệu quả nhất khi nghi picker fail: chụp picker thật 1 máy fail để xem TikTok đang hiện tile gì.



### VIDEO_PICK histogram rescue — ĐÃ IMPLEMENT (2026-08-13)



Hướng "đổi metric" ở trên đã thành code cụ thể. Ghi lại để lần sau không đoán:



- **cv2 / numpy / scipy ĐỀU KHÔNG CÓ** trong venv automation (`import cv2` → ModuleNotFoundError). KHÔNG dùng ORB/SIFT — viết metric bằng PIL thuần.

- **Metric thắng = RGB color-histogram intersection** (32 bin/channel, normalize, min-sum / 3). Robust với crop 1:1 + overlay (badge `00:13`, vòng tròn) + nén mạnh — những thứ làm grayscale-64x64 correlation tụt ~0.13.

- **Đo thực tế máy 45 (video Tik2 354/3.mp4):** SAME-video hist 0.824-0.828, DIFF-video cùng folder 0.504-0.681 (cao nhất 5.mp4 = 0.68). Gap 0.14+ → ngưỡng 0.75 + margin 0.05 tách sạch. Correlation vẫn giữ làm path 1 (video Tik1 sạch vẫn qua correlation).

- **Dual-metric accept** trong `_verify_video_tile_identity`: tap khi `corr ≥ 0.35 AND corr_margin ≥ 0.05` OR `hist ≥ 0.75 AND hist_margin ≥ 0.05`. Cả 2 path đều fail-closed (cần margin over 2nd candidate). Constants: `VIDEO_PICK_TILE_HISTOGRAM_THRESHOLD=0.75`, `VIDEO_PICK_TILE_HISTOGRAM_MARGIN=0.05` + config keys `video_pick_tile_histogram_threshold`/`_margin`.

- `_video_source_frames` đổi từ `convert("L")` → `convert("RGB")` (histogram cần màu; correlation tự convert lại bên trong).

- **Test mới**: `test_video_pick_histogram_rescues_low_correlation_script_render` — corr 0.10/hist 0.85 → verify qua histogram path (`similarity_via == "histogram"`). Khi mock thêm metric vào test cũ, nhớ mock CẢ `_tile_histogram_to_frames` (không chỉ `_tile_similarity_to_frames`) nếu không sort sẽ crash (`<` between dict).

- Recipe đo (PIL-only): crop tile từ `video-pick-grid.png` theo bounds thật (y≈350-700, tile 357x357 — đừng so full-screen 1080x1920!), extract frame `ffmpeg -ss` rồi `hist_sim(tile, frame)`. Source `references/video-pick-histogram-rescue-20260813.md`.



### CẨN THẬN baseline + audit mỗi phase (user correction 2026-08-13)



User rule: **sửa xong 1 phase → gọi audit**. Và: **script cũ đã chạy ổn nên phải quay revert được nếu cần**.

- TRƯỚC sửa: `git stash push -m "pre-<feature>-<date>"` (hoặc commit checkpoint) → có baseline để `git stash apply`/`pop` revert. User thấy rủi ro "fix mới làm hỏng flow cũ (Tik1 vẫn chạy)".

- SAU mỗi phase fix + suite xanh → **gọi audit** (model khác review diff) trước khi chạy live canary.

- **Pitfall dirty working-tree che giấu test failure**: test fail có thể do change CHƯA commit của phase TRƯỚC (vd stale-lock recon) chứ không phải phase hiện tại. Phân biệt: `git stash` changes → chạy test trên clean state; nếu pass → do dirty change; `git show HEAD:<file> | grep` để biết HEAD có dòng đó chưa. Đừng vội sửa test/theo hướng sai.

- **Pitfall CRLF trong test files**: file `tests/*.py` dùng CRLF. Python `str.replace(anchor, ...)` với anchor viết bằng `'\n'` sẽ KHÔNG khớp (file có `'\r\n'`) → assert "ANCHOR MISSING". Fix: viết anchor thay thế bằng `'\r\n'` (hoặc dùng python read → splice span), giữ CRLF khi ghi lại. Khác với patch-tool pitfall (file source LF) — test file là CRLF.

- Kết hợp với CANARY rollout: audit APPROVED → chạy 2-4 máy background → verify report (SUCCESS + ACCEPTED + workbook +1) trước khi phóng toàn batch.

