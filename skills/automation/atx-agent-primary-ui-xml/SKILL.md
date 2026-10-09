---

name: atx-agent-primary-ui-xml

description: Đưa atx-agent (port 7912) lên làm cơ chế PRIMARY đọc UI XML trên farm Android yếu (S7/Android 7) — khi shell uiautomator dump bị Killed (EXIT=137) và file fallback trả XML stale. Dùng khi flow reg/UI automation fail vì đọc nhầm màn cũ, type nhầm field, hoặc khi cần patch get_ui_xml/ui_xml ở bất kỳ repo automation nào.

---



# TÀI LIỆU THAM KHẢO NÂNG CAO (SUPPORTING REFERENCES)
- `references/triet-tieu-uiautomator-shell-dump-automation-core-20260923.md`: Triệt tiêu vĩnh viễn uiautomator shell dump fallback trong `automation-core/src/automation_core/ui.py` (khóa cứng `REQUIRE_PROVISIONED`, chặn `try_shell`, dọn `am force-stop com.github.uiautomator`).
- `references/remote_adb_atx_curl.md`: Kiến trúc đọc UI XML qua device-local `atx-agent curl` cho Remote ADB Host (Admin Farm `192.168.110.119`), bypass 100% port forward TCP qua LAN và Windows Firewall.

# INVARIANT BẮT BUỘC: 100% SCRIPT CỨU HỘ & WORKER CẤM DÙNG SHELL UIAUTOMATOR DUMP
*User Invariant:* TOÀN BỘ script (kể cả script cứu hộ tạm thời, one-off script, script của worker subagent) CẤM TUYỆT ĐỐI gọi `adb shell uiautomator dump`.
- **Hậu quả nếu vi phạm:** Trên Samsung S7 (Android 7), gọi shell uiautomator dump trên các màn hình phân cấp sâu (Settings, Dropdown, Menu) sẽ bị kernel Android OOM-kill ngay lập tức (`Killed, EXIT=137`), làm tiến trình subprocess bị ngậm timeout 10 phút (600s), treo cứng cả worker lẫn session!
- **Kỷ luật bắt buộc:** 
  1. Mọi thao tác đọc UI XML hoặc tap tọa độ qua script Python cứu hộ BẮT BUỘC dùng `atx-agent` (port 7912):
     ```python
     # Forward port và gọi trực tiếp HTTP/JSON-RPC:
     subprocess.run([ADB, "-s", serial, "forward", f"tcp:{port}", "tcp:7912"])
     # Lấy XML hierarchy: http://127.0.0.1:{port}/dump/hierarchy
     # Click JSON-RPC: http://127.0.0.1:{port}/jsonrpc/0 method: click
     ```
  2. Khi dispatch worker thao tác trên máy thật, Coordinator BẮT BUỘC ghi rõ trong Contract: `CẤM TUYỆT ĐỐI adb shell uiautomator dump — BẮT BUỘC dùng atx-agent (port 7912)`.

- **Gỡ tài khoản Google trên Samsung S7 (`remove_device_google_account.py`) — atx-agent primary chống OOM 137 (2026-09-18)**:
  - Khi script dọn dẹp tài khoản Google DIE hoặc chuyển nhượng trên thiết bị S7, gọi lệnh shell `uiautomator dump /sdcard/window_dump.xml` trên ứng dụng Cài đặt (`com.android.settings`) rất dễ bị Android kernel OOM-kill (`Killed, EXIT=137`) do Settings chứa cây hierarchy phân cấp sâu.
  - Xử lý: Đưa `atx-agent` (TCP port 7912) lên làm primary dump qua port forward `tcp:17999` và endpoint `http://127.0.0.1:17999/dump/hierarchy` để lấy XML trực tiếp qua HTTP. Chỉ fallback sang shell `uiautomator dump` khi atx-agent không phản hồi.

- **Subprocess thiếu timeout & uiautomator dump hang/EXIT 137 làm subagent treo 600s trong script logout (`do_logout_account.py`, Máy 40, 2026-09-19)**:

- **Remote ADB Host (Admin Cluster M201-M280) Dump qua Device-Local Curl (2026-09-23)**:
  - Khi điều khiển cụm Admin qua ADB host từ xa, `adb forward` chỉ bind `127.0.0.1` trên máy remote và bị firewall chặn port động khi gọi từ máy coordinator.
  - Giải pháp: dùng `atx-agent curl` ngay trong thiết bị qua `adb.shell()` thay vì gọi HTTP qua port forwarded. Xem chi tiết tại `references/remote-adb-device-curl.md`.
  - **Hiện tượng**: Subagent chạy batch/logout trên Máy 40 (`ce0418244d10342502`) bị kẹt đến mức chạm trần timeout 600s.
  - **Root cause**:
    1. Trong `D:\Taadaa\tools\do_logout_account.py` và `run_logout_all.py`, các hàm wrapper gọi `subprocess.run([ADB, "-s", serial] + args, capture_output=True, text=True)` hoàn toàn thiếu `timeout=...`.

- **Đột phá xử lý Remote ADB Host (Admin Cluster M201-280) bị Timeout HTTP Forward TCP qua LAN (2026-09-23)**:
  - **Hiện tượng / Lỗi thực tế**:
    - Khi runner từ máy Kibe điều khiển cụm Admin Remote (`192.168.110.119:5037`), batch feed/nurture đồng loạt văng lỗi:
      `capture-invalid:ui_dump_error: ATX_SESSION_UNAVAILABLE` trên 55/56 thiết bị.
    - Test suite `test_persistent_ui.py` fail tại `test_resolve_host_resolution`.
  - **Nguyên nhân cốt lõi (Root Cause)**:
    1. `_resolve_host(adb)` kiểm tra biến global `_ACTIVE_REQUEST_HOST` trước khi kiểm tra `adb.host`, làm stale host từ test trước đè lên host của instance thật.
    2. Khi chạy với remote ADB server, lệnh `adb forward tcp:0 tcp:7912` tạo port forward trên máy Admin nhưng daemon ADB chỉ bind vào loopback `127.0.0.1` của Admin, đồng thời Windows Firewall chặn các port động ngẫu nhiên (50000+).
    3. Máy Kibe gọi HTTP `urllib.request.urlopen("http://192.168.110.119:<port>/...")` bị timeout 100% (3000ms), cạn retry/reset và ném `ATX_SESSION_UNAVAILABLE`.
  - **Giải pháp chuẩn (Device-Local curl CLI Bypass)**:
    - `atx-agent` tích hợp sẵn CLI `curl` ngay bên trong máy Android: `/data/local/tmp/atx-agent curl`.
    - Khi target ADB là remote host (`_is_remote_host(adb) == True`) hoặc khi HTTP forward qua mạng LAN gặp lỗi:
      Thực thi dump trực tiếp qua `adb.shell()` nội bộ trong thiết bị:
      ```bash
      /data/local/tmp/atx-agent curl -X POST --data='{"jsonrpc":"2.0","id":"automation-core-ui-dump","method":"dumpWindowHierarchy","params":[true]}' http://127.0.0.1:7912/session/<pid>:com.github.uiautomator/jsonrpc/0
      ```
    - Output trả về qua stdout của adb shell được parse an toàn (`curl.go:` -> JSON body), tốc độ < 0.5s, KHÔNG cần forward port TCP qua mạng LAN, miễn nhiễm 100% với Windows Firewall và binding restriction.
    2. Hàm `dump_ui` gọi trực tiếp lệnh cấm `uiautomator dump`. Trên Samsung S7 (Android 7), lệnh này bị Android kernel OOM-kill ngay lập tức (`rc=137`) trong 0.62s. Khi adb transport gặp socket stall kết hợp với việc subprocess không có timeout, tiến trình Python bị block vĩnh viễn tới trần 600s của subagent.
  - **Giải pháp chuẩn**:
    1. Luôn set `timeout=10` (hoặc timeout bounded) cho mọi lời gọi `subprocess.run` adb.
    2. Tuyệt đối không dùng `uiautomator dump` trong các script utility/logout; thay bằng `capture_atx_session_ui` (hoặc `dump_ui_atx.py`).
    3. Thêm fallback tọa độ an toàn cho flow logout TikTok trên màn 1080x1920 (Profile: `(972, 1857)` -> Menu: `(1005, 150)` -> Cài đặt: `(540, 1248)` -> Swipe 5 lần -> Đăng xuất: `(540, 1750)` -> Xác nhận popup: `(750, 1100)`).

- **Lỗi HTTP 502 Bad Gateway ngầm của ATX Session & Fallback Exit 137 gây Timeout Cron dọn Cache (`clear-tiktok-cache.py`, Máy 20/76, 2026-09-20)**:
  - **Hiện tượng**: Cron `cron_clear_tiktok_cache.py` chạy qua đêm báo fail/timeout đa số máy (2/3 máy fail: 20 Timeout, 76 Timeout).
  - **Root cause**:
    1. Tại máy 76: Tiến trình `atx-agent` daemon vẫn sống (PID tồn tại) nhưng proxy tới UiAutomator stub bị đứt socket ngầm, trả về `HTTPError: HTTP Error 502: Bad Gateway`.
    2. Fallback thứ cấp trong `dump_ui`: khi ATX lỗi, script rơi xuống `shell(serial, "uiautomator dump /sdcard/tt_cache_dump.xml")`. Trên Samsung S7 (Android 7), lệnh này bị kernel OOM kill ngay lập tức (`exit: 137`), trả về XML rỗng.
    3. Vòng lặp swipe tìm mục *"Giải phóng dung lượng"* / *"Free up space"* trong menu Cài đặt và vòng lặp mở app liên tục gọi `dump_ui` bị trả về rỗng + sleep, làm vắt kiệt thời gian timeout 240s của worker thread.
    4. Tại máy 20: Tiến trình trước đó đã mở popup xác nhận *"Xóa bộ nhớ đệm?"* nhưng chưa nhấn *"Xóa"*, khiến UI kẹt ở trạng thái dialog xác nhận.
  - **Xử lý chuẩn**:
    1. Khi phát hiện `HTTP Error 502: Bad Gateway` từ `capture_atx_session_ui`, BẮT BUỘC gọi `reset_atx_agent(client, timeout=10)` để kill cả atx-agent lẫn stub cũ, sau đó kích hoạt lại nền qua `POST /uiautomator`.
    2. Trong `execute_clear_cache_on_storage_screen`: luôn xử lý trường hợp màn hình đang hiển thị sẵn dialog xác nhận `"Xóa bộ nhớ đệm?"` / `"Clear cache?"` (tap ngay nút "Xóa" bên phải `[541,1024][960,1167]`) thay vì coi là màn hình lạ rồi force-stop.
    3. Cập nhật state file `post_night_clear_cache_state.json` để cron không quét lại các máy đã hoàn tất.

- **Màn hình "Sửa hồ sơ" (ProfileEditActivity) đè mất Profile Root & Navigation Trap (Case 143, 2026-09-17, Máy 40)**:
  - **Hiện tượng**: `go_to_profile()` / `dismiss_profile_overlays()` fail với `RuntimeError: [02_profile] Khong vao duoc tab Ho so/Profile` khi TikTok kẹt ở activity `ProfileEditActivity`. Màn hình hiển thị "Sửa hồ sơ", nút "Quay lại màn hình trước", "Thay đổi ảnh", "Tên người dùng".
  - **Root cause**: `is_profile_tab_selected()` và `_is_profile_screen_xml()` tìm các marker của trang cá nhân chính (`da follow`, `follower`, `thich`, `them tieu su`, bottom nav bar). Màn hình Sửa hồ sơ che khuất toàn bộ bottom nav bar và header chính, trong khi `dismiss_profile_overlays` chỉ xử lý popup đặt tên ban đầu (`tv_content_name`), không xử lý activity sửa hồ sơ con.
  - **Xử lý**: Bổ sung handler nhận diện trong `dismiss_profile_overlays`:
    ```python
    if "sua ho so" in flat and any(k in flat for k in ["quay lai man hinh truoc", "thay doi anh", "ten nguoi dung"]):
        log("   [profile] dismiss ProfileEditActivity (quay lại Profile chính)")
        if not find_text_tap(device_id, "Quay lại màn hình trước", "Quay lai man hinh truoc", wait=D_SHORT):
            keyevent(device_id, 4, wait=D_SHORT)
        time.sleep(D_SHORT)
        continue
    ```

- **`atx-agent server -d` tự ý set `screen_off_timeout = 2147483647` (Không bao giờ tắt màn hình) & Fix `--nouia` (2026-09-16)**:
  - **Hiện tượng**: Dàn máy Samsung S7 farm tự dưng không tắt màn hình khi idle dù đã set timeout hệ thống hoặc tắt màn hình bằng tay, màn hình thức liên tục gây chai pin, nóng máy và phồng pin.
  - **Root cause**: Mặc định lệnh `atx-agent server -d` khi khởi động daemon sẽ tự động gọi mã can thiệp `Settings.System.putInt(..., Settings.System.SCREEN_OFF_TIMEOUT, Integer.MAX_VALUE)` (tức con số `2147483647` ms = 24.8 ngày). Khi PC reset USB bus hoặc runner gọi restart/recovery ATX agent, toàn bộ dàn máy bị ép sáng vĩnh viễn.
  - **Giải pháp**:
    1. Khi khởi chạy daemon `atx-agent`, BẮT BUỘC thêm cờ `--nouia`: `/data/local/tmp/atx-agent server -d --nouia` (trong `automation-core/src/automation_core/persistent_ui.py` gồm `_persistent_capture_attempt`, `_ensure_atx_server_running`, và `recover_persistent_uiautomator_stub`). Cờ này ngăn chặn atx-agent tự can thiệp đổi `screen_off_timeout` của Android.
    2. Kích hoạt stub uiautomator riêng biệt qua endpoint theo chuẩn: `atx-agent curl -X POST http://127.0.0.1:7912/uiautomator`.
    3. Cấu hình chuẩn cho S7 farm: `settings put system screen_off_timeout 600000` (10 phút) và `settings put global stay_on_while_plugged_in 0` kèm `svc power stayon false`.
    4. **Unit test contract (`test_persistent_ui.py`)**: Khi cập nhật `--nouia`, các test mock `shell_calls` cần cập nhật slice assertion tương ứng: `call[-3:] == ["server", "-d", "--nouia"]` và `call[-4:] == [persistent_ui.ATX_AGENT_PATH, "server", "-d", "--nouia"]`.

- **Hỗ trợ Remote ADB Host (`-H <ip>` / `ADB_HOST` / `ADB_SERVER_SOCKET`) trong `automation-core` (`persistent_ui.py` & `adb.py`) (2026-09-21)**:
  - Khi điều khiển thiết bị qua ADB server từ xa (ví dụ Admin PC `192.168.110.119:5037`), lệnh `adb -H <ip> -s <serial> forward tcp:0 tcp:7912` mở dynamic forward port **trên chính máy chủ remote host `<ip>`**, KHÔNG phải trên `127.0.0.1` của local client.
  - Nếu `persistent_ui.py` hardcode `http://127.0.0.1:{port}` trong `_request` hoặc ping probe của `_ensure_forward`, request HTTP JSON-RPC sẽ bị `ConnectionRefusedError` (WinError 10061), dẫn tới lỗi sập đồng loạt toàn bộ dàn máy remote: `capture-invalid:ui_dump_error: ATX_SESSION_UNAVAILABLE`.
  - Khắc phục trong `automation-core`:
    1. Trong `AdbClient.__init__` (`automation_core.adb`): Khi `host` không truyền vào, tự động phân giải từ `os.environ.get("ADB_HOST")` hoặc bóc tách từ `os.environ.get("ADB_SERVER_SOCKET")` (dạng `tcp:<ip>:<port>`).
    2. Trong `persistent_ui.py`: Thêm helper `_resolve_host(adb)` kiểm tra `adb.host` -> `ADB_HOST` -> `ADB_SERVER_SOCKET` -> fallback `"127.0.0.1"`. Mọi endpoint URL HTTP trong `_request` và ping check `_ensure_forward` phải trỏ tới `http://{target_host}:{port}...`.
  - Đồng thời, script độc lập `dump_ui_atx.py` hỗ trợ cờ `--host <ip>` (hoặc biến môi trường `ADB_HOST`). Khi `host` khác `127.0.0.1`, các lệnh adb tự động kèm `-H <host>` và request HTTP JSON-RPC tự động trỏ tới `http://<host>:<local_port>/session/...`.
    1. Trong `automation_core.adb.AdbClient`: Tự động parse `host` và `port` từ `os.environ.get("ADB_HOST")` và `os.environ.get("ADB_SERVER_SOCKET")` (ví dụ `tcp:192.168.110.119:5037`).
    2. Trong `automation_core.persistent_ui`: Triển khai `_resolve_host(adb)` giải quyết IP host remote thay vì hardcode `127.0.0.1` trong `_request` và ping check của `_ensure_forward`.
    3. Standalone helper `dump_ui_atx.py`: Hỗ trợ cờ `--host <ip>` (hoặc biến môi trường `ADB_HOST`). Khi `host` khác `127.0.0.1`, các lệnh adb tự động kèm `-H <host>` và request HTTP JSON-RPC tự động trỏ tới `http://<host>:<local_port>/session/...`.

- **Pitfall `adb pull` với đường dẫn MSYS `/d/...` trên Windows**:
  - Khi dùng `adb.exe` (bản native Win32 như Xiaowei ADB hay GemPhone ADB) trong môi trường shell Git Bash/MSYS, lệnh `adb pull /remote/path /d/Taadaa/...` sẽ ném lỗi:
    `adb: error: cannot create file/directory '/d/Taadaa/...': No such file or directory`.
  - Nguyên nhân: `adb.exe` là tiến trình Windows thuần, không giải mã được mount point POSIX ảo `/d/` của MSYS.
  - Xử lý: Luôn truyền đường dẫn chuẩn Windows dạng `D:/Taadaa/...` hoặc `D:\Taadaa\...` khi gọi lệnh `adb pull` từ bash script hoặc Python.

- **Pitfall `uiautomator dump` shell trực tiếp trong script con / helpers (`hook_chatgpt_register.py`, 2026-09-19)**:
  - Khi chạy flow UI automation kết hợp giữa Chrome và Gmail (như `hook_chatgpt_register.py`), việc module con import `get_ui_xml` từ script cũ nếu thiếu ATX-primary sẽ khiến `adb shell uiautomator dump` bị Android kernel OOM-kill (`Killed, EXIT=137`).
  - Hậu quả: App Gmail không đọc được OTP dù thư xác nhận đã về, dẫn tới timeout giả `FAILED_AT_OTP_FETCH` (OTP_FETCH_TIMEOUT).
  - Khắc phục: Bắt buộc dùng `capture_atx_session_ui` (hoặc helper chuẩn `dump_ui_atx.py`) làm cơ chế PRIMARY đọc XML cả khi chuyển foreground giữa Chrome và Gmail. Khi cần inspect ad-hoc màn hình, TUYỆT ĐỐI KHÔNG gọi `adb exec-out uiautomator dump` hay `/dev/tty` mà hãy dùng HTTP dump endpoint qua `forward tcp:7912` hoặc chụp screenshot screencap.

- **Nhận diện ô input qua thuộc tính `hint` trong XML WebView / Android UI (`node_has_target` hỗ trợ hint, 2026-09-19)**:
  - Trên Chrome WebView (như trang đăng ký ChatGPT `chatgpt.com/auth/login?screen_hint=signup` hoặc các form OAuth/web auth), các ô input `EditText` thường có `text=""` và `content-desc=""` rỗng khi chưa nhập liệu, nhưng lại mang thuộc tính `hint="Email address"` (hoặc `hint="Địa chỉ email"`).
  - Nếu hàm so khớp node `node_has_target(attrs, targets)` chỉ kiểm tra `text`, `content-desc`, và `resource-id`, các node input này sẽ bị bỏ qua khiến flow automation không tìm thấy ô nhập liệu và rơi vào timeout hoặc fallback tọa độ mù.
  - Xử lý chuẩn: Bắt buộc thêm `attrs.get("hint", "")` vào danh sách `values` trong `node_has_target`:
    ```python
    values = [
        attrs.get("text", ""),
        attrs.get("content-desc", ""),
        attrs.get("resource-id", ""),
        attrs.get("hint", ""),
    ]
    ```
  - Đồng thời khi tìm node qua `find_node_in_xml`, bổ sung thêm cả target resource-id phổ biến (như `"email"`) bên cạnh `"Email address"`, `"Địa chỉ email"` để tối ưu độ bền và tỷ lệ nhận diện.

- **Pitfall ripgrep/search_files với đường dẫn Windows có khoảng trắng (`D:/Taadaa/GPM auto/...`)**:
  - `search_files` ripgrep backend trên Windows có thể fail với `The system cannot find the path specified. (os error 3)` khi đường dẫn chứa khoảng trắng (ví dụ `GPM auto`).
  - Xử lý: Dùng `read_file` trực tiếp với absolute path hoặc python one-liner để verify chuỗi target trước khi patch.
- **Ensure atx-agent cho OAuth S7 Pipeline (`run_oauth_s7_pipeline.py`)**:
  - Khi script kết nối vào port `17000 + machine_id` (forward `tcp:7912`) để đọc XML prompt hoặc security code trên S7, nếu daemon `atx-agent` chưa chạy thì request forward sẽ ném ConnectionRefused / 502 Bad Gateway.
  - Bổ sung helper `ensure_atx_agent(serial)` trước khi forward: kiểm tra `ps -A` xem có tiến trình `/data/local/tmp/atx-agent` chưa; nếu chưa thì chạy `/data/local/tmp/atx-agent server -d` kèm timeout ngắn và sleep 0.5s để daemon kịp bind port 7912.
- **Lấy Mã bảo mật 10 số (Google Security Code) trên S7 qua GoogleSettingsLink & atx-agent**:
  - Dùng trong flow 2FA / Web login (`add-gmail-2fa`): khi Google yêu cầu "Nhận mã bảo mật trên điện thoại Galaxy S7".
  - Trình tự gọi UI trên S7:
    1. Wake màn hình (`keyevent 224` + `keyevent 82`).
    2. Mở trực tiếp settings qua component: `am start -n com.google.android.gms/.app.settings.GoogleSettingsLink`.
    3. Đọc XML qua atx-agent port forward `17000 + machine_id`: kiểm tra target email có đang hiển thị ở header hay không (nếu không, tap account picker để switch).
    4. Tap text "Tài khoản Google" / "Quản lý Tài khoản Google".
    5. Chuyển sang tab "Bảo mật" (vuốt ngang hoặc tap tab "Bảo mật" / "Security").
    6. Cuộn và tap "Mã bảo mật" (Security code).
    7. Quét text XML bằng regex trích xuất mã 10 chữ số (`r"^\d{10}$"` hoặc ghép 2 cụm 5 số).
    8. Gửi `input keyevent 3` (HOME) để dọn dẹp và trả focus về bình thường.

# atx-agent primary UI XML capture

- **False SplashActivity Stall Trong Dumpsys Window vs Màn Profile Thật & Scrolled Sticky Header (Case 134, 2026-09-08, Máy 40)**: Khắc phục tình trạng runner chẩn đoán nhầm "TikTok bị kẹt ở SplashActivity không vào được Profile" và ném lỗi `SWITCHER_OPEN_FAILED`. Hai root cause: (1) Trên Samsung S7 (Android 7), WindowManager giữ window token `SplashActivity` trong `dumpsys window` (`mCurrentFocus` / `mFocusedApp`) rất lâu sau khi TikTok đã chuyển cảnh nội bộ sang `MainActivity` và render hoàn chỉnh trang Profile (`id/ok0` selected="true"). Nếu runner chỉ check `dumpsys window` mà không đọc ATX XML thì sẽ kết luận kẹt splash sai lệch; (2) Khi trang Profile đang ở trạng thái cuộn nhẹ (scrolled), username body `:id/sr3` và nút "Thêm tiểu sử" bị đẩy lên trên, tên tài khoản nhảy lên sticky header giữa đỉnh (`:id/pq2` hoặc `:id/pq5` tại bounds `[366, 72][720, 228]`). Giải pháp: Bắt buộc dùng ATX XML dump để xác nhận trạng thái Profile thực tế (`id/ok0` selected="true" hoặc regex username `:id/pq2`/`:id/pke`/`:id/pkh`), không tin cậy `dumpsys window` độc lập; khi mở switcher trên Profile đã cuộn, tap trực tiếp sticky header `:id/pq2` hoặc vuốt nhẹ xuống để lộ body header.
- **Khảo sát Quảng cáo (Sponsored Ad Survey / "Bạn có quan tâm đến quảng..." No/Yes) Trap & Recovery (Case 133, 2026-09-06, Máy 14)**: Khắc phục lỗi dừng phiên oan `"popup is not in the shared TikTok allowlist; manual review required; swipe recovery (2 swipes) still stuck"` khi màn hình feed hiển thị popup khảo sát quảng cáo ("Bạn có quan tâm đến quảng cáo này không?" No/Yes). Root cause: trong `benign_popup.py`, khi classifier gán nhãn `GENERIC_POPUP_SCREEN` hoặc `"manual-needed:popup"`, `_dismiss_feed_ad_overlay_by_swipe` mặc định gán `handler_id = "tiktok_shop_cta_swipe_v1"` và bắt buộc kiểm tra `has_tiktok_shop_buy_now_marker`. Do survey không có nút "Mua ngay", hàm trả về `None` và rơi xuống core allowlist gây fail-closed. Giải pháp 2 tầng: (1) Quét text XML trong `_dismiss_feed_ad_overlay_by_swipe` để nhận diện survey text (`(?i)quan tâm đến quảng cáo`) và bypass điều kiện "Mua ngay", cho phép bounded swipe; (2) Đăng ký typed handler `sponsored_ad_feedback_survey` trong `benign_popup_registry.py` để tap nút `No`/`Không` hoặc swipe thoát video ad: `references/sponsored-ad-feedback-survey-detection-and-swipe-dismiss-20260906.md`. Bổ sung cảnh báo nghiêm cấm dùng `grep -rn`/`find` quét `.ai-runs/` gây timeout 900s.
- **ATX Session Unavailable Tại Bước `sponsored_check`, Fail-Soft Cho Heuristic Feed Checks & Random 2–3 Swipes Canary (Case 131 & 132, 2026-09-06, Máy 36)**: Khắc phục lỗi dừng phiên oan `capture-invalid: ATX_SESSION_UNAVAILABLE` tại artifact `sponsored_check` khi TikTok vẫn ở foreground Home Feed ('Đề xuất' For You). Root cause: trong `feed_swipe_smoke.py`, vòng lặp swipe mỗi video gọi `_sponsored_present(ctx)` -> `_capture_xml_text(ctx, "sponsored_check")`. Khi uiautomator stub hoặc ATX transport bị timeout trên S7, `_capture_xml_text` nhận diện `ATX_SESSION_UNAVAILABLE` là `terminal_recovery` và `raise` exception. Vì `_sponsored_present` thiếu try/except, exception văng thẳng lên `feed_session_smoke`, làm sập toàn bộ phiên lướt feed (`total_swipes_completed: 0`). Giải pháp: Bọc try/except trong `_sponsored_present`, nếu gặp `ATX_SESSION_UNAVAILABLE` khi TikTok foreground thì gọi `reset_atx_agent(ctx.adb, timeout=15)` và retry capture 1 lần; nếu vẫn lỗi thì fail-soft trả về `False` (log `sponsored_check_degraded`) để phiên lướt feed tiếp tục bình thường: `references/atx-session-unavailable-sponsored-check-fail-soft-20260906.md`. Đồng thời cập nhật `scripts/run-feed-session.ps1` để khi nhận tham số `-RecoveryTestSwipes 2` (từ template lệnh B4) sẽ tự động kích hoạt random ngẫu nhiên 2 hoặc 3 swipes (`Get-Random -Minimum 2 -Maximum 4`) theo đúng chuẩn vận hành farm: `references/sponsored-check-atx-session-fail-soft-and-canary-random-swipes-20260906.md`.
- **Profile Verification SystemUI Trap & Xử Lý Thẻ TikTok GO (Case 120, 2026-09-06, Máy 25)**: Khắc phục lỗi dừng phiên `profile verification mismatch: profile account mismatch` khi TikTok đang mở thẻ carousel quảng bá "TikTok GO" ở Trang chủ. Ba root cause: (1) `tap_navigation_target` khi tap tab Hồ sơ (y=1857) bị SystemUI/Nav bar bắt focus, kích hoạt `recover_tiktok_focus_after_systemui_tap` gửi phím BACK hủy mất chuyển cảnh Hồ sơ, giữ app ở Trang chủ; (2) `tap_navigation_target` thấy focus quay về TikTok thì vội vã trả về `ok=True`; (3) `_verify_profile_after_session` thấy `profile_screen_confirmed=False` liền chạy fallback `input swipe 540 600 540 1500 350` (swipe down) ngay trên Trang chủ, làm kéo ngược feed bung thẻ "TikTok GO" và báo mismatch tài khoản. Giải pháp 3 tầng: Bắt buộc retry tap target sau khi recover focus từ SystemUI; Gating cấm swipe down khi chưa xác nhận vào được Profile screen (thay vào đó retry tap Hồ sơ); Đăng ký handler `tiktok_go_card` trong registry để dismiss qua nút "Không quan tâm" (đã loại bỏ "khám phá" tránh nhầm tab bottom) hoặc vuốt lên kèm post-verification: `references/profile-verification-systemui-trap-and-tiktok-go-card-20260906.md`.
- **Lỗi Stall 5 Phút Trong `get_focused_activity`, Pre-tap Settle Retry & Quá Deadline Preflight Switch Anchor (Case 116, 2026-09-05, Máy 40)**: Khắc phục lỗi dừng phiên `run plan max_duration_seconds exceeded before capture profile_preflight_switch_anchor_2_pre_tap_guard attempt 1` khi TikTok vẫn mở bình thường ở Home Feed. Ba root cause: (1) `get_focused_activity` trong `flows/observe.py` gọi `capture_ui_xml` thiếu lightweight options, làm core rơi xuống `_dump_current_ui_unlocked` và kích hoạt chuỗi uiautomator shell recovery ladder với multiple reconnect loops, gây stall 5-6 phút (300s+) mỗi lần gọi; (2) Pre-tap navigation trong `tap_navigation_target` thiếu nhịp settle retry khi WindowManager đang animate sau khi switch account khiến `get_focused_activity` trả về `None` và abort ngay với `"focused package unavailable"`; (3) `_maybe_recover_navigation_from_add_phone` gọi `force_stop_and_relaunch_tiktok` kèm `time.sleep(2.0)` mù quáng (quá ngắn cho S7), làm hỏng chuỗi verify khiến flow nhảy sang attempt 2 và vắt kiệt trần deadline 2100s. Giải pháp: Thay `capture_ui_xml` trong `get_focused_activity` bằng `capture_atx_session_ui(adb, timeout=min(3.0, ...), restart_attempts=0)` và cap dumpsys <= 5s; bổ sung pre-tap focus settle retry (1.0s) và ATX XML fallback trong `tap_navigation_target`; dùng `_relaunch_and_poll_tiktok_focus` có active polling: `references/focused-package-unavailable-atx-session-stall-and-preflight-deadline-20260905.md`.
- **Screen Capture Invalid, Feed Not Confirmed & Fallback Image Feed Controls Cho `ATX_SESSION_UNAVAILABLE` (Case 112 & Case 114, 2026-09-05, Máy 19)**: Khắc phục lỗi dừng phiên oan `screen capture invalid; feed not confirmed` khi TikTok vẫn ở foreground Home Feed. Hai root cause: (1) `calibrate_screens.py` (dòng 834) thiếu `ATX_SESSION_UNAVAILABLE` và `ui_dump_failed` trong danh sách `xml_error_code` degraded cho phép fallback sang `detect_feed_controls(screenshot)`, khiến màn hình feed rõ ràng bị bỏ qua và `detected_screen` thành None; (2) `_capture_step` trong `feed_swipe_smoke.py` thiếu auto-recovery `reset_atx_agent(ctx.adb, timeout=15)` tại chỗ khi TikTok vẫn ở foreground trước khi nhảy sang force-stop/fail-closed. Giải pháp: Thêm `ATX_SESSION_UNAVAILABLE` và `ui_dump_failed` vào danh sách degraded errors và tự động reset ATX stub + recapture khi TikTok foreground: `references/screen-capture-invalid-feed-not-confirmed-recovery-20260905.md` và `references/screen-capture-invalid-feed-controls-fallback-and-atx-recovery-20260905.md`.
- **ATX Session Unavailable Trong Feed Swipe Confirmation & `FEED_CONFIRMED_XML_DEGRADED_ERRORS` (Case 111, 2026-09-05, Máy 41)**: Khắc phục lỗi dừng phiên `feed marker confirmed but XML unavailable: ATX_SESSION_UNAVAILABLE`. Khi video feed đang phát trên S7, screenshot marker xác nhận đang ở TikTok feed (`_is_feed_confirmed` = True) nhưng ATX session dump fail sau retries và reset. Do tập `FEED_CONFIRMED_XML_DEGRADED_ERRORS` thiếu `ATX_SESSION_UNAVAILABLE` / `atx_session_unavailable`, flow fail-stop nhầm thay vì chuyển sang `ExitStatus.DEGRADED`. Giải pháp: Thêm `ATX_SESSION_UNAVAILABLE` vào `FEED_CONFIRMED_XML_DEGRADED_ERRORS` và xử lý case-insensitive để feed session tiếp tục degraded an toàn: `references/feed-confirmed-atx-session-unavailable-degraded-20260905.md`.
- **Focused Package Unavailable, Bypass Focus Recovery & Xiaowei ADB Host Reconnect (Case 110, 2026-09-05, Máy 46)**: Khắc phục lỗi dừng phiên `SAFETY_FAILED` ("focused package unavailable") khi TikTok vẫn mở trên Home Feed. Hai root cause: (1) `_is_launcher_focus_loss` trong `feed_swipe_smoke.py` bỏ qua `"package unavailable"` / `"focused package unavailable"` khi `focus_package` rỗng, làm bypass cơ chế relaunch/recovery; (2) Lệnh `adb -s <serial> reconnect device` trên Xiaowei ADB trả exit code 0 nhưng không reset host socket, khiến nhánh fallback host-side `reconnect` bị bỏ qua trong `_reconnect_device`. Giải pháp: Nhận diện recoverable focus loss cho `"package unavailable"`, luôn thực hiện host-side `reconnect` trong `automation_core/adb.py`, và retry `reconnect` trong `get_focused_activity`: `references/focused-package-unavailable-and-adb-host-reconnect-20260905.md`. Bổ sung nhận diện Photo mode feed detail controls ("bóc tem", "đăng lại", "ảnh", "bookmark") và import `ADBError` tránh NameError (Case 110 & 111): `references/focused-package-unavailable-and-host-reconnect-20260905.md`.
- **ATX Session Unavailable Trong Home Navigation Before Swipe (Case 109, 2026-09-05, Máy 23)**: Khắc phục lỗi dừng phiên tại `feed-session-smoke/home/navigation` do `UIDumpError("ATX_SESSION_UNAVAILABLE")`. Sau khi hoàn tất profile preflight, bước điều hướng về Trang chủ (`home_navigation = tap_navigation_target(ctx, _home_target(), ...)`) bị thiếu cơ chế phục hồi 2 tầng khi ATX socket mất kết nối. Giải pháp: Khi `not home_navigation.ok`, kiểm tra `get_focused_activity`, nếu TikTok vẫn ở foreground và lỗi là `is_atx_failure`, tự động kích hoạt `reset_atx_agent(ctx.adb, timeout=15)`, sleep 1.0s và retry `tap_navigation_target` trước khi kết luận thất bại: `references/home-navigation-atx-session-recovery-20260905.md`.
- **ATX Session Unavailable Trong Navigation Recovery & Bẫy Logic `navigation_error is None` (Case 108, 2026-09-05, Máy 76 & Máy 80)**: Khắc phục lỗi dừng phiên oan do `UIDumpError("ATX_SESSION_UNAVAILABLE")` tại bước `tap_navigation_target`. Khi dump UI bị fail, điều kiện `if point is None and navigation_error is None:` chặn toàn bộ luồng recovery. Đồng thời trong `_navigate_profile_for_preflight`, khi TikTok vẫn ở foreground Trang chủ (Home Feed / SplashActivity) nhưng navigation fail do ATX session lỗi, hệ thống thiếu nhánh `reset_atx_agent(ctx.adb)` và retry, dẫn tới kết luận `manual-needed` sai lệch. Giải pháp: Tách biệt lỗi dump UI với logic target not-found, khôi phục ATX agent qua `reset_atx_agent(ctx.adb, timeout=15)` và retry tap navigation 1 lần an toàn có bounded deadline: `references/navigation-atx-session-unavailable-recovery-20260905.md`.
- **Bẫy Phím BACK Trong Navigation Recovery, Mask Lỗi UIDumpError & Phục Hồi Launcher Focus (Case 105, 2026-09-05, Máy 52)**: Xử lý triệt để lỗi dừng phiên `navigation target profile not found in XML` khi tab Hồ sơ có badge/số thông báo (word-boundary regex matching), nhận diện qua resource-id chuẩn (`:id/ofe`, `com.ss.android.ugc.trill:id/ofe`), bảo toàn exception `UIDumpError` không bị mask thành not-found, an toàn phím BACK tuyệt đối khi đang ở Home/Feed để tránh văng về Launcher và tự động relaunch TikTok khi mất focus: `references/navigation-target-profile-back-trap-and-launcher-recovery-20260905.md`.
- **UIAutomator Stub Foreground Lockout & Landscape Screen Trap (`[01_open] TikTok not foreground after clean launch`, 2026-09-05)**: Khi `reset_atx_agent()` chạy `monkey -p com.github.uiautomator 1`, nó khởi động `MainActivity` của `com.github.uiautomator` lên foreground ở chế độ xoay ngang (Landscape 1920x1080). Giao diện này chiếm trọn màn hình và chặn TikTok lên foreground khi launch qua monkey/am start, khiến consumer quăng `RuntimeError: [01_open] TikTok not foreground after clean launch` trên 100% dàn máy. Chi tiết call chain và trigger logic: `references/uiautomator-stub-monkey-call-chain-and-screen-trap-20260905.md`.
  - *Pitfall cạn budget timeout*: Trong `reset_atx_agent()`, `input keyevent 3` bị guard bởi `if monkey_called and remaining() > 0:`. Nếu `ui_capture.py` truyền `reset_timeout` nhỏ hoặc polling `ps -A` ngốn hết thời gian, `remaining() <= 0` làm rớt lệnh Home, khiến UIAutomator treo vĩnh viễn trên màn hình.
  - *Fix tại core (`persistent_ui.py`)*: Trong `reset_atx_agent()`, loại bỏ hoàn toàn lệnh `monkey -p com.github.uiautomator 1` (chỉ dùng `atx-agent curl POST http://127.0.0.1:7912/uiautomator` để khởi động background stub không có UI activity); sau đó kiểm tra `dumpsys window windows`, nếu phát hiện `com.github.uiautomator` chiếm foreground thì mới gửi `adb.shell(["input", "keyevent", "3"])` (KEYCODE_HOME) để hạ xuống background.
  - *Fix tại consumer (`open_app` trong `social_reg_v1.py` - cơ chế phòng thủ 3 tầng)*:
    1. **Pre-launch Guard**: Kiểm tra trước khi mở app, nếu phát hiện `com.github.uiautomator` trong foreground/XML -> `am force-stop` cả 2 package uiautomator (`com.github.uiautomator`, `com.github.uiautomator.test`) và gửi `input keyevent 3`.
    2. **In-loop Recovery**: Trong vòng lặp 45s chờ TikTok load, nếu uiautomator chen ngang vào foreground -> tự động force-stop uiautomator, HOME, sleep 0.8s, và relaunch TikTok.
    3. **Timeout Else-block Recovery**: Tại thời điểm timeout, nếu foreground/XML vẫn là uiautomator -> kích hoạt nhánh phục hồi: force-stop uiautomator + HOME + relaunch TikTok và chờ tối đa 25s để TikTok lên foreground thay vì raise exception ngay lập tức.
  - *Lỗ hổng phân mảnh tại repo `tiktok-luot nuoi acc` (Audit 2026-09-05)*:
    - Repo này CHƯA CÓ cơ chế vượt qua / recovery khi `com.github.uiautomator` chiếm foreground:
      1. `core/ui_capture.py` (dòng 194): khi 3 lần capture ATX fail, tự gọi `reset_atx_agent()` -> chạy `monkey -p com.github.uiautomator 1` làm bung màn hình ngang tiếng Trung.
      2. `core/capture_recovery.py`: `_direct_shell_recapture` (dòng 4517) gọi `monkey -p com.github.uiautomator 1` khi dính EXIT 137 không dọn dẹp; các dòng 2553, 5319, 5647, 6053 gọi trực tiếp `am start -n com.github.uiautomator/.MainActivity`.
      3. `core/safety.py`: `safety_check()` trả về `SAFETY_FAILED` ("TikTok focus lost") vì `com.github.uiautomator` không thuộc `SYSTEM_OVERLAY_PACKAGES` hay `KNOWN_TIKTOK_PACKAGES`.
      4. `flows/device_prepare.py`: `_verify_tiktok_focus_with_retries` chỉ sleep chờ 10x1.5s thụ động rồi crash với `prepare-tiktok failed to focus TikTok after launch`.
  - *Đã giải quyết phân mảnh tại repo `tiktok-luot nuoi acc` (2026-09-05)*:
    1. Đã dọn dẹp triệt để `monkey -p com.github.uiautomator 1` và `am start -n com.github.uiautomator/.MainActivity` khỏi `python_runner/core/capture_recovery.py`.
    2. Đã thêm hàm `recover_uiautomator_occlusion(ctx, package_name)` trong `flows/observe.py` (`am force-stop com.github.uiautomator` -> `input keyevent 3` -> relaunch TikTok).
    3. Đã tích hợp tự động vào `observe_current_screen()` (ngăn chặn false-alarm `SAFETY_FAILED` / `TikTok focus lost`) và `_verify_tiktok_focus_with_retries()` trong `flows/device_prepare.py` (ngăn kẹt 15s timeout sau launch app).
    4. Bộ unit test mới `tests/test_uiautomator_occlusion_recovery.py` (4/4 passed).
  - *Verification suite*: `tests/test_persistent_ui.py` (core 23/23 passed), `tests/test_open_app_uiautomator_recovery.py` (Tiktok_Reg 4/4 passed), `python_runner/tests/test_uiautomator_occlusion_recovery.py` (tiktok-luot nuoi acc 6/6 passed).
- **UIAutomator Helper App Foreground Occlusion Recovery (2026-09-04)**: Tự động phát hiện và force-stop các app helper/stub (`com.github.uiautomator`, `io.appium.uiautomator2.server`) khi chúng vô tình chiếm foreground/đè màn hình trong các state `OPEN_TIKTOK`, `WAIT_FEED`, `ACCOUNT_SWITCHER`, rồi gọi `bring_to_foreground` để trả quyền điều khiển cho TikTok. Chi tiết: skill `tiktok-upload-ui-recovery` file `references/helper-app-occlusion-live-camera-tab-and-post-selectors-20260904.md`.
- **ATX Screencap & 5-Layer Alert Fallback (2026-09-04)**: Bypass lỗi SurfaceFlinger FB protected (12-byte 0x00), auto-wake uiautomator backend qua `POST /uiautomator` khi gặp 502, `adb reconnect` khi transport nghẽn và fallback lấy ảnh từ session artifact: `references/atx-screencap-and-5layer-fallback-20260904.md`.
- **ATX Stub Temp Instrument & ADB Host Reconnect (2026-09-04, máy 54)**: Xử lý ADB transport timeout do `reconnect device` không reset host socket, lỗi `atx-agent curl` tạo stub tạm chết sau 18s và cơ chế restart stub bền qua `monkey`: `references/atx-stub-temp-instrument-and-adb-host-reconnect-20260904.md`.
- **Gmail Onboarding Trap & Samsung Keyguard Recovery (2026-08-29)**: Xử lý chuỗi Onboarding Gmail mới (`dialog_wrapper`, `welcome_tour`, `action_done`) và phục hồi màn hình khóa Keyguard Samsung (`keyevent 224` + swipe unlock): `references/gmail-onboarding-and-keyguard-recovery-20260829.md` (trong skill `tiktok-registration-ops`).
- **ATX Session Stub Dead & Dynamic Forward Index Fix (2026-08-29)**: Chi tiết root-cause bug parse index forward port và cơ chế monkey fallback trong `reset_atx_agent`: `references/atx-stub-dead-and-dynamic-forward-index-fix-20260829.md`.
- **ATX Session Unavailable Triage & Takeover Canary**: Hướng dẫn xử lý `ATX_SESSION_UNAVAILABLE` (stub chết, agent sống), reset qua `automation_core.persistent_ui.reset_atx_agent` và chạy canary tiếp quản lock với `--full-scope-takeover`: `references/atx-session-unavailable-triage-and-takeover-recovery.md`.
- **Auto-Recovery trong Batch Runner**: Tích hợp `reset_atx_agent(adb_client)` khi gặp 502/RemoteDisconnected; recovery phải giữ foreground an toàn và không được dùng `monkey -p com.github.uiautomator`. Chi tiết: `references/atx-auto-recovery-runner-pattern.md` và `references/atx-control-endpoint-no-monkey.md`.
- **Cắt bỏ Fallthrough xuống UiAutomator khi ATX fail**: Chi tiết triage máy 23 và quy tắc fail-closed không fallthrough sang shell uiautomator: `references/feed-capture-atx-fallthrough-elimination-20260823.md`.
- **Pitfall `reset_atx_agent` dùng monkey làm mất focus TikTok**: Chi tiết lỗi văng sang màn hình UIAutomator phím tắt tiếng Trung khi restart stub: `references/atx-reset-monkey-focus-loss-pitfall-20260823.md`.
- **AdbKeyboard IME Socket Hang / Text Injection Stalled (2026-09-01)**: Khi `AdbKeyboard` broadcast `ADB_KEYBOARD_INPUT_TEXT` không inject được ký tự vào `EditText` (ô nhập text bị bỏ trống / giữ nguyên placeholder), nguyên nhân là daemon `atx-agent` hoặc UIAutomator stub bị treo socket ngầm. Xử lý: `pkill -9 -f atx-agent` & `am force-stop com.github.uiautomator` -> restart `/data/local/tmp/atx-agent server -d` -> kích hoạt lại stub `monkey -p com.github.uiautomator 1`.
- **`_atx_capture_ui_xml` API Change — signature đổi từ `remaining_timeout_fn` sang `timeout, restart_attempts` (2026-09-01)**: Bản cũ nhận `remaining_timeout_fn` (callable); bản mới nhận `timeout=float, restart_attempts=int`. Khi patch theo chuẩn `tiktok-luot nuoi acc`, phải đổi hàm signature đồng thời cập nhật MỌI test mock: `lambda _device, _remaining_fn` → `lambda _device, *a, **k`. Pitfall: test cũ mock positional arg thứ 2 sẽ PASS với lambda nhưng vỡ nếu test assert call signature chặt. Test chuẩn: `monkeypatch.setattr(social, "_atx_capture_ui_xml", lambda _d, *a, **k: xml)`.
- **`get_ui_xml` total deadline nâng lên 60s (2026-09-01)**: `UI_XML_TOTAL_TIMEOUT = 35` không đủ để chạy 3 lần retry ATX (mỗi lần 15s cap) + `reset_atx_agent` (15s) + 2 lần retry sau reset. Nâng lên 60s và dùng deadline floating `local_deadline - time.monotonic()` thay vì `_remaining_timeout` fn để đảm bảo mỗi attempt được cap đúng.
- **Fast Login / One-tap screen phải xử lý TRƯỚC `wait_for_text` (2026-09-01)**: Trong `choose_email_login`, `wait_for_text` cũ tìm `["Đăng nhập", "Email", "Sign up"]` KHÔNG có `"Tiếp tục với tên"` → timeout 20s rồi raise RuntimeError trước khi `handle_fast_login_screen` kịp chạy. Fix: Gọi `handle_fast_login_screen` ngay đầu hàm (trước cả `wait_for_text`), thêm `"Tiếp tục với tên"`, `"Sử dụng tài khoản khác"` vào danh sách wait.
- **`automation_core/tiktok/fast_login.py` — module canonical (2026-09-01)**: Tách `handle_fast_login_screen` ra khỏi consumer script, đưa vào `automation_core.tiktok.fast_login`. API dùng adapter functions (`get_xml_fn`, `tap_fn`, `find_text_tap_fn`, `log_fn`) thay vì import trực tiếp consumer module. Consumer wrapper chỉ gọi core và giữ local fallback. Sau mỗi thay đổi core: `cp -rf src/automation_core/* "/d/Taadaa/python-envs/automation/Lib/site-packages/automation_core/"`.
- **Hermes Cron "provider timeout" là false alarm khi batch script exit 1 (2026-09-01)**: Hermes cron báo "provider timeout" nhưng thực ra batch `_run_all_targets.py` đã chạy xong và exit 1 (do một số máy FAILED). Không phải LLM timeout. Kiểm tra artifact `D:\Taadaa\runtime\kibe\artifacts\runs\social-batch-all\<timestamp>\all_results.json` để xem kết quả thực tế.

- **Bẫy Underage Lockout khi DatePicker chọn nhầm năm sinh trên Samsung S7 (`tiktok-registration-ops`, 2026-09-19)**:
  - Khi reg TikTok đến màn Ngày sinh, DatePicker có thể mặc định năm gần hiện tại (vd 2015). Nếu bấm Tiếp tục, TikTok gắn cờ Underage và khóa cứng email đó vĩnh viễn (kể cả sau đó sửa năm thành 1999 cũng bị từ chối). Bắt buộc dùng ATX XML đọc text năm sinh, cuộn lùi năm (`swipe 840 1200 840 1500`) tới năm <= 2004 trước khi tap Tiếp tục. Chi tiết: `skills/software-development/tiktok-registration-ops/references/tiktok-signup-dob-underage-lockout-trap-20260919.md`.

## 🛑 STOP GATE (bắt buộc — chi tiết: skill taadaa-farm-ops-rules)
Máy live + script chạy/lỗi → KHÔNG tự sửa code, KHÔNG tự chạy lại, KHÔNG tự probe/tay khi chưa được user yêu cầu.
Lỗi → screencap → gửi ẢNH THẬT (MEDIA:<path> dòng riêng, KHÔNG bọc markdown, KHÔNG gửi đường dẫn text) → DỪng chờ user hướng dẫn.
User hướng dẫn bước nào → encode bước đó vào script + test → mới chạy lại. Nghi ngờ → HỎI.

## Trigger

- Flow reg/login/UI automation fail vì `get_ui_xml`/`ui_xml` trả XML cũ/stale (màn không khớp — type email vào password field, tap trật nút)

- Shell `uiautomator dump` bị `Killed` (EXIT=137) hoặc timeout khi đổi app foreground

- Máy yếu (S7/SM-G930*, Android 7, RAM 3.6GB) — uiautomator service chết vĩnh viễn sau khi app foreground đổi nhiều lần (bug Android 7 accessibility: `UiAutomationShellWrapper.connect` fail)



## Vấn đề gốc (evidence máy 38, 2026-08-15)

- Shell `uiautomator dump /dev/stdout` → `Killed` (EXIT=137), kể cả `--compressed`, file /sdcard — mọi biến thể

- File fallback `/sdcard/window_dump.xml` → **XML STALE** (màn cũ) — flow đọc "Nhập địa chỉ email" trong khi màn thật "Tạo mật khẩu" → type email vào password field (lỗi "gõ quá 20 ký tự")

- atx-kill ladder (skill android-device-automation L387): `pkill -9 -f atx-agent` + `am force-stop com.github.uiautomator` → phục hồi TẠM, không bền

- **`capture_ui_xml` (automation_core.ui) qua atx-agent service (TCP port 7912) SỐNG** — atx tự quản lý/restart UiAutomation, trả XML TƯƠI (len 43788/74319 vs shell 12244 stale)

- Tool 投屏 (数控安卓投屏/微卫安卓控屏 = **tool xiaowei**, ADB `C:\Program Files (x86)\xiaowei\tools\adb.exe`, XWCaptureScreen.jar) **luôn bật toàn farm** → atx-agent có trên mọi máy



## Patch chuẩn (mẫu `social_reg_v1.py::_atx_capture_ui_xml`)

```python

def _atx_capture_ui_xml(device_id, remaining_timeout_fn):

    try:

        from automation_core.adb import AdbClient

        from automation_core.ui_capture import ProvisioningPolicy

        from automation_core.ui import capture_ui_xml as _cap

        client = AdbClient(

            adb_path=ADB_PATH, serial=device_id,

            default_timeout=remaining_timeout_fn("atx", cap=45),

        )

        cap = _cap(

            client,

            timeout=remaining_timeout_fn("atx", cap=40),

            retries=1, retry_delay_seconds=0.8,

            provisioning_policy=ProvisioningPolicy.REQUIRE_PROVISIONED,

        )

        if cap is not None and cap.xml and "<hierarchy" in cap.xml:

            return cap.xml

        return None

    except Exception as e:

        log(f"   [ui-xml] atx exception {type(e).__name__}: {str(e)[:120]}")

        return None

```

Trong `get_ui_xml`/`ui_xml`/tương đương: **atx PRIMARY đầu hàm** (return ngay nếu OK) → shell exec-out → file fallback. atx fail KHÔNG raise — rơi xuống shell. `ADB_PATH` phải có sẵn.



## ATX session dump — tầng PRIMARY MỚI trong automation-core (0.4.46, commit e57436b, 2026-08-17)



Core `try_persistent` (ui.py) giờ chạy 3 tầng: **ATX session dump** (`persistent_ui.capture_atx_session_ui`,

backend `CaptureBackend.ATX_SESSION="atx_session"`) → persistent cũ `/jsonrpc/0` (`capture_persistent_ui`,

giữ làm fallback) → shell uiautomator → file. Consumer gọi `capture_ui_xml`/`dump_current_ui` KHÔNG cần

đổi gì — session tier tự chạy trước rồi rơi xuống đúng chuỗi cũ.



- Endpoint (verified live máy 31 ce0416041bdb271305, SM-G930F, 2026-08-16): **pid-scoped**

  `/session/<pid>:com.github.uiautomator/jsonrpc/0`, method `dumpWindowHierarchy` **params [true]**

  (full depth) → XML đầy đủ; `click(x, y)` → true. Forward `adb forward tcp:7912 tcp:7912` tương thích.

- Discovery pid: `ps -A` → ĐÚNG 1 process `com.github.uiautomator` (exact-match ` com.github.uiautomator ` có

  khoảng trắng 2 bên TRƯỚC; chỉ dùng `.test` khi không có exact — `.test` có thể cùng tồn tại và KHÔNG được

  shadow); ambiguity → fail closed xuống persistent, KHÔNG đoán pid.

- Forward: `forward --list` kiểm tra TRƯỚC và PHẢI match theo serial — entry chỉ reuse khi thuộc ĐÚNG máy

  đang xử lý. **Batch nhiều máy: mỗi máy 1 local port ĐỘNG riêng** (`adb forward tcp:0 tcp:7912`; adb forward

  tcp:0 KHÔNG in stdout → parse local port từ `forward --list` theo serial). Entry stale của máy khác →

  `forward --remove` rồi tạo mới.

  ⚠️ **Fix `9044b91` (2026-08-17)** — bản cũ reuse entry 7912 đầu tiên bất kể serial → chạy batch tuần tự,

  máy B/C/D gọi `127.0.0.1:7912` vẫn trỏ máy A → dump nhầm màn hình → `OUTLOOK_APP_PASSWORD_FIELD_NOT_FOUND`

  đồng loạt 5 máy. Verify live: M75 port 55564, M76 port 55656 đều VERIFIED_HEALTHY dump đúng từng máy.

  Dùng chung 1 local port cho cả farm là race — KHÔNG bao giờ.

- `atx-agent server -d` chỉ chạy trên primary path khi `ps -A` chưa thấy agent — primary KHÔNG kill;

  kill ladder `_recover_uiautomator` vẫn là recovery riêng, ngoài tầng primary.



**Test update bắt buộc (MỞ RỘNG từ bản 08-15):** mọi test mock `capture_persistent_ui` giả lập máy

không-atx mà assert số `shell_calls`/`run_calls` phải mock THÊM `capture_atx_session_ui`

(`lambda *a, **k: PersistentCaptureResult(None, UNAVAILABLE, ({"failure_signature": "ATX_SESSION_UNAVAILABLE"},))`)

— session tier chạy ADB thật (ls/pm/ps/forward) trước khi rơi xuống mock persistent, phá assertions kiểu

`len(shell_calls) == trước` (VD `test_replay_verified_persistent_capture_then_serial_disappears...` phải patch 2026-08-17).



Chi tiết implement (discovery/forward/capability) + catalog test: `references/atx-session-primary-capture-20260816.md`.

Batch multi-máy + forward per-device + hotmail list-runner + token Graph OTP (2026-08-17): `references/batch-atx-forward-hotmail-token-20260817.md`.



### ⚠️ False-positive transport timeout làm ATX KHÔNG BAO GIỜ primary (fix `727b6d4`, 2026-08-17)



Triệu chứng: `capture_ui_xml`/`capture_atx_session_ui` báo `health=UNAVAILABLE` + `failure_signature=ADB_TRANSPORT_TIMEOUT`

dù atx-agent + stub chạy đầy đủ → rơi thẳng xuống uiautomator (bị OOM kill) → ATX primary vô hiệu trên MỌI máy S7.



**Root cause:** `classify_adb_transport_failure` dùng marker substring `"timeout"`, và **`ps -A` trên Samsung S7 in

`poll_schedule_timeout` ở gần như MỌI dòng kernel-thread** (sdp_cryptod, connfwexe, at_distributor, webview_zygote32,

wpa_supplicant, adbd...) → probe ATX capability match nhầm `ADB_TRANSPORT_TIMEOUT` → fail-closed.

Sửa (đã merge vào `ADB_TRANSPORT_FAILURE_MARKERS`): bỏ marker `"timeout"` lỏng, chỉ giữ `"adb command timed out"` / `"timed out"`.

**Quy tắc marker:** KHÔNG bao giờ dùng substring 1 từ chung (`timeout`, `error`, `fail`) cho transport-failure classification —

output `ps -A`/`dumpsys` chứa đủ thứ; phải là phrase riêng của adb (`device offline`, `timed out`, `device not found`).

Verify live máy 31 sau fix: `capture_atx_session_ui` → `VERIFIED_HEALTHY` xml 28-29KB; `capture_ui_xml` → `backend=atx_session`.



- **`ATX_SESSION_STUB_NOT_RUNNING` / `UIAUTOMATOR_BACKGROUND_START_DENIED` trên Android 8+**:
  - Triệu chứng: `SHELL_EXIT_137` khi rơi xuống shell dump, hoặc `Error: app is in background` khi `am startservice`.
  - Fix chuẩn: Kích hoạt stub nền qua control endpoint `POST /uiautomator` của daemon `atx-agent` (CẤM dùng `monkey` vì sẽ khởi chạy `MainActivity` xoay ngang cướp focus của TikTok).
  - Port động: Luôn dùng `adb forward tcp:0 tcp:7912` để PC cấp local port ngẫu nhiên cho từng máy, không bao giờ dùng chung 1 local port gây tranh chấp giữa 80 máy.

- **`ATX_SESSION_STUB_NOT_RUNNING` — agent chạy nhưng stub UiAutomationService không chạy (máy 19 row 5, 2026-08-17; Cập nhật 2026-09-05: CẤM DÙNG MONKEY)**: `capture_atx_session_ui` trả `attempts` có `agent_running: true` (PID tồn tại, LISTEN 7912) NHƯNG `failure_signature: ATX_SESSION_STUB_NOT_RUNNING` + `stub_process_lines: []` (không tìm thấy `com.github.uiautomator` trong `ps -A`) → session dump không lấy được XML. Chẩn đoán phân biệt: (a) agent CHẾT → `agent_running: false` → restart `atx-agent server -d`; (b) agent CHẠY nhưng stub CHẾT → restart atx-agent cũng cần force-stop + relaunch stub qua `POST /uiautomator` (CẤM dùng `monkey -p com.github.uiautomator 1` vì sẽ bung giao diện Landscape đè mất TikTok).

- **Restart stub chuẩn hóa (2026-09-05 update — dùng `atx-agent curl POST /uiautomator`, CẤM `monkey`)**:
  - `am startservice com.github.uiautomator/.UiAutomatorService` → fail `Error: Not found; no service started`.
  - `monkey -p com.github.uiautomator 1` → CẤM DÙNG vì làm văng sang `MainActivity` tiếng Trung xoay ngang, gây mất focus TikTok hàng loạt máy farm.
  - **Cách chuẩn duy nhất**: Khởi động daemon `/data/local/tmp/atx-agent server -d` rồi kích hoạt stub qua `adb shell "/data/local/tmp/atx-agent curl -X POST http://127.0.0.1:7912/uiautomator"`. Sau đó poll `ps -A` chờ tiến trình `com.github.uiautomator` xuất hiện. Nếu stub chạy nhưng session vẫn **HTTP 502 Bad Gateway** = atx-agent proxy tới stub thất bại (lệch handle) → kill CẢ HAI (`pkill -9 -f atx-agent` + force-stop `com.github.uiautomator`) rồi `server -d` + `POST /uiautomator` lại từ đầu.

- **Lọc `com.android.systemui` trong `get_focused_activity` khi dùng ATX XML**:
  - Khi đọc UI XML qua ATX-primary (`flows/observe.py::get_focused_activity`), node đỉnh màn hình `[0,0][1080,72]` chứa các icon pin/sóng/thông báo của `com.android.systemui`.
  - Nếu regex chỉ lấy package đầu tiên xuất hiện trong XML (`package="..."`), hàm sẽ trả về `com.android.systemui` khiến flow tưởng lầm TikTok bị mất focus và dừng máy (`preserve_blocker_screen`).
  - **Fix**: Luôn quét danh sách package trong XML, ưu tiên trả về package TikTok mục tiêu (`com.ss.android.ugc.trill`, `com.zhiliaoapp.musically`, `com.ss.android.ugc.aweme`) nếu tồn tại; nếu không có thì lọc bỏ `com.android.systemui` rồi mới lấy package chính.

- **`dumpsys window` CŨNG bị stale — get_focused_activity cần ATX-primary (máy 6, 2026-08-16)**



Nguồn stale KHÔNG chỉ là shell uiautomator dump: **`dumpsys window` (mCurrentFocus) báo SplashActivity CŨ trong khi feed đã render** — TikTok giữ window activity splash, chỉ đổi nội dung UI → flow nhìn dumpsys tưởng "kẹt splash" → manual-needed sai, recovery chạy vô ích. `screencap`/ATX XML cho thấy feed đầy đủ.



Fix (repo `tiktok-luot nuoi acc`, commit `1a33a14`, `flows/observe.py::get_focused_activity`): **ATX-primary đầu hàm** — gọi `automation_core.ui.capture_ui_xml(client, timeout=..., retries=1, retry_delay_seconds=0.8, provisioning_policy=ProvisioningPolicy.REQUIRE_PROVISIONED)`; nếu `cap.xml` có `<hierarchy` → regex lấy `package="..."` → return ngay (package TikTok = app đã lên, dù window activity vẫn splash). dumpsys window/activity giữ làm fallback. Canary máy 6: hết kẹt splash, lướt 19 swipe success.



Pitfall kèm: **xác nhận màn hình thật bằng ảnh/ATX trước khi kết luận "máy kẹt"** — đừng tin mỗi `dumpsys window`; 2 cơ chế (window activity vs UI thật) lệch nhau trên TikTok.



## Test update bắt buộc khi chuyển atx lên PRIMARY

- **Test mock `capture_ui_xml` cũ bị vỡ khi consumer bỏ fallback chuyển sang 100% ATX session (2026-08-23, repo `tiktok-add-bao-mat-f2a`)**:
  - Khi consumer nâng cấp `dump_current_ui` loại bỏ hoàn toàn `capture_ui_xml` (chỉ gọi `capture_atx_session_ui` + `reset_atx_agent`), các test contract cũ kiểu `test_adapter_requires_provisioned_persistent_capture` (mock `core.ui_dump.capture_ui_xml` hoặc assert `ProvisioningPolicy.REQUIRE_PROVISIONED`) sẽ FAIL vì `capture_ui_xml` không còn được gọi.
  - Fix: Cập nhật test mock sang `automation_core.persistent_ui.capture_atx_session_ui` trả về `SimpleNamespace(xml="<hierarchy />")` để verify hàm trả về đúng XML từ ATX session.

Các test cũ mock `_exec_out`/`shell` (giả lập máy không atx, test shell fallback) sẽ FAIL vì atx-primary chạy TRƯỚC loop — `_atx_capture_ui_xml` gọi automation_core THẬT (exception → None, nhưng thứ tự gọi lệch). Fix chuẩn (đã áp dụng `tests/test_ui_xml_timeout.py`):

```python

monkeypatch.setattr(social, "_atx_capture_ui_xml", lambda *_a, **_k: None)

```

thêm vào MỌI test giả lập máy không-atx trước khi gọi `get_ui_xml`. Assert thứ tự shell fallback giữ nguyên.



**Nuance (Hotmail 2026-08-17): nếu probe ATX đi qua `AdbClient.shell(...)` TRỰC TIẾP (không qua `run_adb`) thì test cũ mock `run_adb` KHÔNG vỡ** — probe với serial giả fail nhanh (adb trả lỗi → None) rồi rơi xuống fallback mà test mock vẫn assert đúng; test mới mock `AdbClient` + `requests.post` (demo: repo Hotmail `tests/test_atx_primary_ui.py`). Chỉ bắt buộc monkeypatch khi test mock ĐÚNG hàm probe dùng (vd `social_reg_v1` probe qua `_exec_out`/`shell` của consumer). Chọn đường probe theo repo: qua `run_adb` = dễ mock/test nhưng vỡ test cũ; qua `AdbClient.shell` = test cũ yên, test mới mock 2 lớp. Probe trực tiếp cũng giúp máy thật fail nhanh không treo (giữ timeout nhỏ: shell 20s, http 30s).



## Rollout toàn repo automation (user directive 2026-08-15)

Tool 投屏 (xiaowei/微卫安卓控屏) luôn bật toàn farm → atx-agent có trên MỌI máy → atx-primary an toàn cho tất cả repos. Quét phạm vi:

```bash

cd /d/Taadaa && grep -rln "uiautomator.*dump\|def get_ui_xml\|def ui_xml\|capture_ui_xml" --include="*.py" */ 2>/dev/null | grep -v test | grep -v .ai-runs | grep -v site-packages | grep -v node_modules | grep -v .codex-work | grep -v runs/

```

**CẢNH BÁO: grep toàn cây `*/` timeout (backup/worktree/venv quá nhiều)** — loop từng repo thay vì 1 lệnh toàn cây (danh sách 9 repo + kết quả chi tiết từng file: `references/rollout-20260815.md`).

Repos: `automation-core`, `tiktok-video`, `Tiktok_Reg`, `Hotmail`, `tiktok-follow`, `tiktok-log-in`, `tiktok-luot nuoi acc`, `tiktok-add-bao-mat-f2a`, `register gmail`. Mỗi repo: đọc AGENTS.md → phân loại hit → patch (chỉ khi cần) → regression → COMPAT entry → commit riêng. BỎ QUA `.ai-runs/`, `.codex-work/`, `runs/`, `build/lib`, `Temp/`, test files.



**Phân loại hit `uiautomator dump` (KHÔNG phải hit nào cũng cần sửa):**

- File ĐÃ gọi `capture_ui_xml(...)` → atx-primary sẵn (core tự persistent-first) → CHỈ verify + COMPAT entry, không sửa code

- Shell dump trong hàm đọc UI (get_ui_xml/dump_ui/ui_xml) → PATCH: thêm atx-primary đầu hàm, shell giữ làm fallback

- Recovery ladder handlers (VD `ADB_SHELL_FEED_*`/`ADB_SHELL_FEED_DUMP_BACKEND` trong capture_recovery.py) → fallback tầng cuối có scope riêng — KHÔNG đụng

- Debug tool độc lập (VD `tiktok-follow/tools/dump_selectors.py` có `_guard_read_only`) → shell có chủ đích — ngoài scope

- Shell dump còn lại BÊN TRONG `capture_ui_xml` (ui.py) → fallback hợp lệ — grep thấy ≠ cần sửa



## Chẩn đoán + restart atx-agent trong consumer (tiktok-video avatar, 2026-08-15)



Consumer đã dùng `capture_ui_xml(..., provisioning_policy=REQUIRE_PROVISIONED)` (persistent-first) mà vẫn fail

`PROFILE_ROOT_NOT_CONFIRMED` / `non_xml_ui_dump` / `uiautomator_null_root_node`, và log KHÔNG có dòng

persistent/ATX nào → nghi atx-agent chết/wedged chứ không phải thiếu cơ chế.



1. **Probe trực tiếp** bằng persistent API (không qua flow):

   ```python

   from automation_core.adb import AdbClient

   from automation_core.persistent_ui import capture_persistent_ui

   r = capture_persistent_ui(AdbClient(adb_path=..., serial=...), timeout=30)

   # health=UNHEALTHY + attempts có HTTPERROR = atx-agent wedged

   # (dù `ps -A | grep atx-agent` THẤY process ở futex_wait_queue_me/do_wait)

   ```

2. **Restart atx-agent — chạy RIÊNG một lệnh, không chain**:

   ```bash

   adb -s <serial> shell '/data/local/tmp/atx-agent server -d'   # → "atx-agent listening on :7912" rc=0

   ```

   `pkill -9 -f atx-agent; sleep 1; ... server -d` gộp chung 1 shell = RACE — không có process sống sót.

   Verify: `capture_persistent_ui` → `VERIFIED_HEALTHY` (xml có `<hierarchy`) rồi mới rerun batch.

3. **Pitfall: ladder B1 ATX-kill của chính workflow giết atx-agent** (`_recover_uiautomator` = pkill -9, chạy liên

   tục mỗi lỗi UI) → sau 1 run fail, atx-agent chết lại. Restart atx-agent TRƯỚC mỗi lần rerun.

   **Fix bền (in-code, Tiktok-video commit b9351b7):** wire `_restart_atx_agent(adb)` NGAY SAU mọi call

   `_recover_uiautomator` trong consumer (state_machine có 4 call sites) — helper chạy

   `["/data/local/tmp/atx-agent", "server", "-d"]` + sleep 1.5 + verify `capture_persistent_ui` trả

   `<hierarchy` → `ok`. Khi audit consumer diff thấy `pkill atx-agent` mà không có restart đi kèm → bug.

4. **Scope (đừng kỳ vọng quá):** restart atx chỉ cứu lỗi dump/provisioning — máy 26 PASS avatar sau restart.

   KHÔNG cứu: `VPN_REQUIRED_NOT_CONNECTED` (lỗi riêng — reboot máy + watcher tự reconnect, xem android-device-automation),

   hay "Restored TikTok subpage detected; Back recovery 12/12 fail" (lỗi logic account switcher — TikTok restore

   subpage sau switch, XML đọc được nhưng không phải profile root — cần debug `_leave_tiktok_subpages`, không phải dump).



## Cơ chế cài atx-agent + uiautomator trên máy mới (trả lời user 17/08: "khi cài máy mới làm sao bọn nó có")

Không cài tay — **automation-core `provisioning/` tự cài khi script chạy**:

- `bundle.py`: bundle chứa artifact `atx-agent` (binary ~10MB, kind="atx-agent") + `uiautomator.apk` (app `com.github.uiautomator` v2.4.0, kind="apk"), mỗi artifact kèm **sha256 + signer cert digest** (chống cài nhầm/giả). Bundle manifest mẫu: `automation-core/examples/provisioning/manifest.example.json`.
- `workflow.py`: `check(serial)` → dò máy đã có chưa (version/checksum); `provision(serial)` → chưa có thì push binary xuống `/data/local/tmp/atx-agent` + `am install` app uiautomator; `repair(serial)` → version lệch cài đè. Sau cài: `atx-agent server -d` → port 7912.
- `fleet.py`: `provision_all()` → quét + cài cả dàn máy 1 lần.
- Tool xiaowei (投屏 GUI, `C:\Program Files (x86)\xiaowei\`) KHÔNG chứa atx-agent — nó chỉ là bộ điều khiển; binary/app do provisioning core quản lý. Máy đã cài rồi nhưng stub process chết → xem mục `ATX_SESSION_STUB_NOT_RUNNING` (restart bằng `monkey -p com.github.uiautomator 1`).

## Git gotchas gặp khi commit loạt này

- `git add -A ':!/.codex_spreadsheet_tmp'` (pathspec exclude) KHÔNG stage gì trong git-bash MSYS → `nothing added to commit` sai lầm. Stage file RÕ RÀNG từng file.

- `git status --short` trả rỗng nhưng work chưa commit = session khác/đồng nghiệp ĐÃ commit tự động — check `git log --oneline -3` trước khi kết luận "mất work".

- `git diff HEAD --stat` rỗng = working tree sạch thật.



## Quy trình 3 bước fix UI (bắt buộc)

1. Patch handler (atx-primary hoặc fix cụ thể)

2. Regression test đầy đủ repo (Tiktok_Reg 69, Hotmail 152, + automation-core, tiktok-video)

3. COMPAT entry vào `docs/ui-compatibility.md` (ID: `atx-agent-primary-ui-xml-20260815`) + `git diff --check` sạch



## Pitfalls

- **Bẫy Chuỗi NFD Tiếng Việt & System Notification Overlay Trên Outlook/Android Farm (2026-09-18)**:
  - *Lỗi Unicode NFD*: Text hiển thị trên UI Android (đặc biệt các nút điều hướng Outlook, Samsung UI như `"THÊM TÀI KHOẢN"`) thường sử dụng chuẩn ký tự tổ hợp rời (NFD, ví dụ `A\u0300` thay vì precomposed `\u00c0` NFC). Nếu regex hoặc substring search dùng chuỗi tiếng Việt chuẩn gõ từ bàn phím PC (NFC), flow sẽ không tìm thấy element và timeout. Bắt buộc chuẩn hóa qua `unicodedata.normalize("NFD", text)` và strip accents (`strip_accents`) để so khớp dạng không dấu (`them tai khoan`).
  - *System Notification / Status Bar Trap*: Khi app Outlook chuyển cảnh hoặc có thông báo hệ thống nền (`gemphone đang chay ngam`, `com.android.systemui`), các node text ở thanh thông báo đỉnh ($y \le 200$) có thể chứa keyword và bị nhận nhầm thành nút hành động trong vòng lặp click. Bắt buộc lọc bỏ các node thuộc package `com.android.systemui` hoặc có tọa độ $y < 200$ khi tìm action buttons của ứng dụng.

- **Bẫy `raise UIDumpError` Trong Heuristic Checks & Fail-Soft Cho `sponsored_check` (Case 121, 2026-09-06, Máy 36)**:
  - Khi uiautomator stub hoặc ATX session transport bị ngắt kết nối trên Android 7 (Samsung S7), `capture_required_ui` ném `UIDumpError("ATX_SESSION_UNAVAILABLE")`.
  - Trong `_capture_xml_text`, exception này bị đánh dấu `terminal_recovery = True` và lập tức `raise` ra ngoài để bảo vệ các bước kiểm tra danh tính profile.
  - Tuy nhiên, các hàm kiểm tra phụ trợ như `_sponsored_present` trong vòng lặp lướt feed nếu không bọc `try/except` sẽ làm exception văng thẳng lên `feed_session_smoke`, gây dừng phiên oan (`manual-needed`) dù TikTok feed vẫn đang phát bình thường trên màn hình.
  - Bắt buộc: Heuristic feed checks phải bọc `try/except`. Khi gặp `ATX_SESSION_UNAVAILABLE` mà TikTok vẫn ở foreground, gọi `reset_atx_agent(ctx.adb, timeout=15)` và retry 1 lần. Nếu retry vẫn thất bại, bắt buộc fail-soft trả về `False` (log `sponsored_check_degraded`) để phiên lướt feed tiếp tục bình thường, tuyệt đối không để crash session.

- **Stall 5-6 phút trong `get_focused_activity` do gọi `capture_ui_xml` không có lightweight keys (Case 116, 2026-09-05, Máy 40)**:
  - Khi đọc foreground package/activity bằng ATX XML trong `flows/observe.py::get_focused_activity`, TUYỆT ĐỐI KHÔNG gọi `from automation_core.ui import capture_ui_xml` mà không có lightweight probe keys.
  - Trong `automation_core.ui:1420`, `capture_ui_xml` thiếu lightweight keys sẽ rơi thẳng vào `_dump_current_ui_unlocked`, kích hoạt toàn bộ legacy recovery ladder (shell uiautomator dump attempt 1, 2, uiautomator process kill, app relaunch x3 với monkey, và adb transport reconnect loops). Khi thiết bị lag hoặc uiautomator stub ngưng phản hồi, mỗi lần gọi `get_focused_activity` bị stall từ 300s đến 360s (5 đến 6 phút).
  - Chuẩn: Luôn gọi trực tiếp `from automation_core.persistent_ui import capture_atx_session_ui` với timeout nhỏ `min(3.0, float(ctx.timeout("adb_seconds", 15)))` và `restart_attempts=0`. Nếu ATX session không trả XML hợp lệ, chỉ fallback sang dumpsys shell commands nhanh (`dumpsys window`, `dumpsys activity activities`) với timeout `<= 5.0s`, tuyệt đối không fallthrough vào `_dump_current_ui_unlocked`.

- **Pre-tap focus settle retry & ATX XML fallback trong `tap_navigation_target` (Case 116, 2026-09-05)**:
  - Sau khi tap account switcher hoặc chuyển cảnh app, WindowManager có thể tạm thời chưa cập nhật window focus (`focus.get("package") is None`).
  - Nếu `tap_navigation_target` chỉ kiểm tra focus 1 lần duy nhất rồi abort ngay với `SAFETY_FAILED` ("focused package unavailable"), navigation sẽ fail sớm dù app TikTok vẫn ở foreground.
  - Fix: Thêm nhịp settle retry pre-tap (nếu `not focus.get("package")`: `time.sleep(1.0)` và gọi lại `get_focused_activity(ctx)`). Nếu vẫn `focused package unavailable`, thử đọc XML nhanh qua `capture_atx_session_ui` xem có node package TikTok không trước khi abort.

- **Bổ sung `ATX_SESSION_UNAVAILABLE` vào fallback feed controls & auto-recover ATX trong `_capture_step` (Case 112, 2026-09-05, Máy 19)**:
  - Khi uiautomator stub / ATX socket bị timeout hoặc disconnect trên Android 7 (Samsung S7), `capture_required_ui` ném `UIDumpError("ATX_SESSION_UNAVAILABLE")`.
  - Trong `calibrate_screens.py`, nhánh fallback `detect_feed_controls(screenshot)` ban đầu chỉ kiểm tra các mã lỗi shell cũ (`"uiautomator_idle_state_error"`, `"ui_dump_file_missing"`, `"ui_dump_command_failed"`, `"uiautomator_null_root_node"`). Thiếu `"ATX_SESSION_UNAVAILABLE"` khiến flow bỏ qua ảnh screenshot hợp lệ và để `detected_screen = None`, dẫn tới `SCREEN_CAPTURE_INVALID_REASON` ("screen capture invalid; feed not confirmed").
  - Trong `feed_swipe_smoke.py`, tại `_capture_step()`, nếu `_capture_retry_needed` do capture invalid hoặc feed not confirmed mà TikTok vẫn ở foreground (`focus_package in KNOWN_TIKTOK_PACKAGES`), phải gọi `reset_atx_agent(ctx.adb, timeout=15)` và recapture trước khi force-stop hoặc fail-closed.

- **Bẫy logic `_is_launcher_focus_loss` bỏ sót `package unavailable` & Xiaowei ADB Host Reconnect (Case 110, 2026-09-05, Máy 46)**:
  - Khi ADB transport bị stall/timeout, `get_focused_activity` trả về `{"package": None, "activity": None}`, `safety_check` ném `SAFETY_FAILED` kèm lý do `"focused package unavailable"`.
  - Nếu `_is_launcher_focus_loss` chỉ kiểm tra `if focus_package:` và các keyword `"tiktok focus lost"` / `"focus lost"`, nó sẽ trả về `False` khi `focus_package` rỗng. Toàn bộ cơ chế recovery (reconnect / relaunch) bị bypass và script crash ngay lập tức. Bắt buộc kiểm tra:
    ```python
    if "package unavailable" in reason_lower or "focused package unavailable" in reason_lower:
        return True
    ```
  - Trên Xiaowei ADB (`C:\Program Files (x86)\xiaowei\tools\adb.exe`), lệnh `adb -s <serial> reconnect device` trả exit code 0 nhưng KHÔNG thực sự reset host transport socket. Do đó trong `automation_core.adb._reconnect_device`, bắt buộc luôn gọi `adb -s <serial> reconnect` (host-side) bất kể exit code để giải phóng kênh truyền. Đồng thời trong `get_focused_activity`, nếu dumpsys fail ở attempt đầu, gọi `ctx.adb.reconnect()` trước khi thử lại.

- **Consumer BẮT BUỘC dùng `AdbClient` chuẩn của `automation_core.adb` (2026-08-27)**:
  - Khi consumer gọi `capture_atx_session_ui(adb_client)` hoặc `reset_atx_agent(adb_client)`, đối tượng `adb_client` **phải là instance của `automation_core.adb.AdbClient`** (hoặc triển khai đầy đủ phương thức `.run(cmd, ...)` bên cạnh `.shell()` và `.exec_out()`).
  - Lỗi gặp phải (repo `register gmail`): Tạo class giả lập `_CoreUiAdb` chỉ có `.shell()` và `.exec_out()` $\rightarrow$ ATX session dump ném `AttributeError: '_CoreUiAdb' object has no attribute 'run'` khi setup port forward động `forward tcp:0 tcp:7912` $\rightarrow$ capture trả về XML rỗng trong im lặng, làm sập toàn bộ preflight trên 15 máy.
  - Luôn khởi tạo: `adb_client = AdbClient(adb_path=ADB_EXE, serial=device_id, default_timeout=20)`.

- **CẤM fallback bấm tọa độ mù khi không tìm thấy node điều hướng trong XML (2026-08-21)**:
  - Khi điều hướng đáy (`Trang chủ`, `Hồ sơ`, v.v.), BẮT BUỘC chỉ click khi tìm thấy UI Node thật từ ATX XML (`bounds` chính xác).
  - TUYỆT ĐỐI KHÔNG dùng fallback tọa độ pixel/tỷ lệ màn hình (ví dụ `(540, 1800)` hay `(972, 1857)`) vì rất dễ bấm trúng nút Quay video (+) hoặc nút LIVE ở đáy màn hình khi có popup/modal đè.
  - Khi XML không có node hoặc modal che khuất: dừng an toàn hoặc gửi phím BACK đóng modal trước, không click mù.

- **Bắt buộc Word Boundary `\b` khi so khớp text/content-desc từ XML (2026-08-22, vụ máy 45 Closer)**:
  - Khi tìm element/nút đóng popup bằng text/desc (`_find_clickable_text`), TUYỆT ĐỐI KHÔNG dùng substring lỏng kiểu `term.lower() in value.lower()`.
  - Các từ khóa ngắn tiếng Anh/Việt như `"close"`, `"save"`, `"đóng"` sẽ bị va chạm chuỗi con (substring collision) với tên bài hát, video (ví dụ bài hát `"Closer"` có content-desc `"Âm thanh: Closer của hppr"` chứa `"close"` -> nhận nhầm nút đĩa nhạc là nút Đóng và click vào tâm node `(999, 1712)` làm văng sang trang chi tiết âm thanh Sound Detail).
  - Bắt buộc dùng regex word boundary `r"(?i)\b" + term + r"\b"` cho các từ khóa độc lập. Đồng thời đăng ký handler `sound_detail_overlay` (Back key) để tự phục hồi nếu vô tình chạm vào đĩa nhạc.

- **ATX control endpoint — cấm monkey và kiểm tra foreground (2026-08-24)**:
  - `monkey -p com.github.uiautomator 1` bị cấm trong recovery/test vì có thể mở UiAutomator lên foreground hoặc làm thiết bị rơi về Launcher.
  - Khi `ATX_SESSION_STUB_NOT_RUNNING`, chỉ được dùng control-plane nội bộ của atx-agent (`POST /uiautomator`), sau đó rediscover PID/forward và gọi pid-scoped `dumpWindowHierarchy([true])`.
  - Sau control call và sau capture bắt buộc verify package/activity; nếu foreground đổi ngoài dự kiến thì preserve-scene và fail-closed, không tự relaunch TikTok/HOME/BACK.
  - Thử nghiệm endpoint chỉ được chạy trên đúng một máy đã chứng minh rảnh bằng lock metadata; phải có pre/post focus + ATX health/XML evidence. Chi tiết: `references/atx-control-endpoint-no-monkey.md`.

- **ATX 100% và chính sách bỏ hoàn toàn shell uiautomator fallback (2026-08-22)**:
  - Toàn farm dùng `ProvisioningPolicy.REQUIRE_PROVISIONED` ưu tiên 100% `atx_session` qua JSON-RPC `dumpWindowHierarchy [true]` (port động `tcp:0` -> `tcp:7912`).
  - **TẮT HOÀN TOÀN SHELL UIAUTOMATOR FALLBACK Ở TẤT CẢ CONSUMER REPOS (FEED/REG/LOGIN/FOLLOW/VIDEO/MAIL)**: Tuyệt đối không cho phép fallback sang `uiautomator dump /dev/stdout` hoặc `/sdcard/window_dump.xml`. Việc rơi xuống shell dump khi ATX lỗi sẽ đọc phải file XML rác/stale hoặc bị kernel OOM-kill (137) gây khóa Accessibility Service.
  - **CẤM SÓT FALLTHROUGH XUỐNG LEGACY CAPTURE / UIAUTOMATOR RECOVERY (2026-08-23)**:
    - Khi cài đặt retry ATX 3 lần + `reset_atx_agent` + retry sau reset, nếu vẫn không lấy được XML, BẮT BUỘC fail-closed trực tiếp (raise `UIDumpError("ATX_SESSION_UNAVAILABLE")` hoặc trả rỗng).
    - TUYỆT ĐỐI KHÔNG để fallthrough rơi xuống `capture_ui_xml(lightweight=True)` hoặc các recovery ladder cũ (`recover_uiautomator_foreground_service`, `recover_uiautomator_direct_capture_after_shell_exit`, `recover_capture_stack`), vì sẽ kích hoạt shell uiautomator -> OOM kill (137) -> `UIAUTOMATOR_BACKGROUND_START_DENIED_FOREGROUND_RECOVERY_V2`.
    - Rà soát toàn bộ consumer repos (`tiktok-luot nuoi acc`, `tiktok-follow`, `tiktok-log-in`, `Tiktok-video`, `Hotmail`, `add mail khoi phuc`, `register gmail`, `tiktok-add-bao-mat-f2a`) đảm bảo không còn sót bất kỳ lời gọi fallback `capture_ui_xml` / `uiautomator dump` nào.
  - **Hàm chuẩn trong `automation_core.persistent_ui`**: `reset_atx_agent(adb, timeout=20)`
    - `am force-stop` các package stub (`com.github.uiautomator`, `com.github.uiautomator.test`).
    - `pkill -9 -f atx-agent` & `pkill -9 -f uiautomator` để giải phóng handle/socket kẹt.
    - Chạy `/data/local/tmp/atx-agent server -d`.
    - **Kích hoạt background stub không có UI**: Gọi control endpoint `POST /uiautomator` qua `atx-agent curl`. CẤM dùng `monkey -p com.github.uiautomator 1` vì sẽ bung `MainActivity` làm xoay ngang màn hình và cướp foreground của TikTok.
    - **Active polling chờ stub sẵn sàng**: Vòng lặp quét `ps -A` tối đa 8s cho đến khi tìm thấy tiến trình `com.github.uiautomator` rồi sleep tối đa 0.5s (bounded theo remaining deadline) để bind socket JSON-RPC.
    - **Foreground guard**: Quét `dumpsys window windows`, nếu phát hiện package uiautomator trong foreground window thì gửi `input keyevent 3` để giải phóng màn hình.
  - **Mẫu chuẩn áp dụng ở consumer `get_ui_xml(adb)`**:
    ```python
    from automation_core.persistent_ui import capture_atx_session_ui, reset_atx_agent
    import time
    for _ in range(3):
        try:
            atx = capture_atx_session_ui(adb, timeout=15)
            if atx.xml and "<hierarchy" in atx.xml:
                return atx.xml
        except Exception:
            pass
        time.sleep(0.3)

    # Sau 3 lần fail -> hard reset ATX agent + stub
    reset_atx_agent(adb, timeout=15)
    time.sleep(1.0)
    try:
        atx = capture_atx_session_ui(adb, timeout=20, restart_attempts=1)
        if atx.xml and "<hierarchy" in atx.xml:
            return atx.xml
    except Exception:
        pass
    return ""
    ```
  - **Xử lý bottom sheet 'Chuyển đổi tài khoản' che thanh điều hướng đáy (`navigation target profile not found in XML`)**:
    - Khi bắt đầu phiên hoặc navigate Profile (`_navigate_profile_for_preflight`), nếu màn hình đang mở sẵn sheet Switcher, thanh bottom bar ở y>=1400 sẽ bị che khuất khiến XML thiếu tab Profile.
    - Phải có bước `_dismiss_account_switcher_if_open`: tap nút `X`/`Đóng` hoặc gửi phím `BACK` để hạ sheet trước khi tìm tab Hồ sơ.
  - **Bẫy Phím BACK Trong Navigation Recovery, Mask Lỗi UIDumpError & Phục Hồi Launcher Focus (Case 105, 2026-09-05, Máy 52)**:
    - Khi `tap_navigation_target` không tìm thấy target trong XML hoặc ATX dump lỗi, việc gửi phím BACK mù quáng khi đang ở Home/Feed làm TikTok bị đóng và văng ra Samsung Launcher (`com.sec.android.app.launcher`).
    - Lỗi mask exception: Nuốt `UIDumpError` (`ATX_SESSION_UNAVAILABLE` hoặc adb timeout) và gán cứng reason thành `"navigation target profile not found in XML"` làm đánh lừa runner. Bắt buộc bảo toàn exception gốc.
    - Mở rộng selector: `_find_navigation_element` cần hỗ trợ nhận diện tab Profile qua resource-id chuẩn (`:id/ofe`, `com.ss.android.ugc.trill:id/ofe`) và word boundary matching cho content-desc có badge/thông báo.
    - Relaunch phục hồi: `_navigate_profile_for_preflight` phải kiểm tra `get_focused_activity(ctx)`. Nếu văng Launcher thì tự động relaunch TikTok đưa về foreground và thử lại tap navigation thay vì fail-closed `manual-needed`.
    - Chi tiết: `references/navigation-target-profile-back-trap-and-launcher-recovery-20260905.md`.

  - **Cơ Chế Khôi Phục 2 Tầng Cho `ATX_SESSION_UNAVAILABLE` Trong Navigation & Preflight (Case 108, 2026-09-05, Máy 76 & Máy 80)**:
    - *Tầng 1 (`tap_navigation_target` trong `calibrate_screens.py`)*: Khi `capture_required_ui` ném `UIDumpError`, kiểm tra `get_focused_activity`. Nếu `focus_pkg in tiktok_pkgs`, tự động gọi `reset_atx_agent(ctx.adb, timeout=15)`, sleep 1.0s và retry `capture_required_ui`. Khi thành công, xóa `navigation_error = None`. Nếu target không có trong XML, Case 105 guard bắt buộc bỏ qua phím BACK nếu đang ở Home/Feed (`is_home_or_feed`).
    - *Tầng 2 (`_navigate_profile_for_preflight` trong `feed_swipe_smoke.py`)*: Khi `navigation.ok` trả về False nhưng TikTok vẫn ở foreground (`actual_pkg in tiktok_pkgs`) và lỗi là `is_atx_failure` (`ATX_SESSION_UNAVAILABLE`, `UI_DUMP_FAILED`, `uidumperror`), gọi `reset_atx_agent(ctx.adb, timeout=15)` và retry `tap_navigation_target` lần 2 trước khi kết luận thất bại.
    - *Pitfall Unit Test Mocking*:
      + `CalibrationTarget` nằm trong module `flows.calibrate_screens` (KHÔNG nằm trong `core.image_navigation`). Khi viết unit test, import: `from flows.calibrate_screens import CalibrationTarget, NavigationResult, tap_navigation_target`.
      + Mocking `get_focused_activity` cho test bỏ qua ATX recovery khi mất focus (`test_tap_navigation_target_skips_atx_recovery_when_not_tiktok_focus`): `tap_navigation_target` gọi `get_focused_activity` tại entry check và tại recovery check trong `except UIDumpError`. Bắt buộc dùng `side_effect=[{"package": "com.ss.android.ugc.trill", "activity": ".MainActivity"}, {"package": "com.sec.android.app.launcher", "activity": ".Launcher"}]` thay vì static `return_value` để không bị abort ngay tại entry check (`'fail' != 'ATX_SESSION_UNAVAILABLE'`).
      + Chi tiết: `references/navigation-atx-session-unavailable-recovery-20260905.md`.

  - **Phục Hồi ATX Session Cho `home_navigation` (Before Swipe) & Pitfall Mock Module Attribute Trong Unit Test (Case 109, 2026-09-05, Máy 23)**:
    - *Vị trí & Cơ chế*: Tại `feed_swipe_smoke.py`, bước điều hướng về Trang chủ trước khi lướt feed (`home_navigation`) sau profile preflight. Nếu `not home_navigation.ok`, kiểm tra `get_focused_activity`. Nếu TikTok vẫn foreground và lỗi là `is_atx_failure`, log `action="home_navigation_atx_recovery"`, gọi `reset_atx_agent(ctx.adb, timeout=15)` bọc trong `try/except` (log warning `home_navigation_atx_reset_failed` nếu reset fail), sleep 1.0s và retry `tap_navigation_target(_home_target())`.
    - *Pitfall Mocking Module-Level Import Trong Test*: Khi viết unit test cho hàm helper/flow, nếu import hàm trực tiếp (`from flows.calibrate_screens import tap_navigation_target`), `patch("flows.calibrate_screens.tap_navigation_target")` sẽ KHÔNG tác động tới symbol cục bộ đã được bind trước khi patch. Bắt buộc gọi qua module attribute (`import flows.calibrate_screens as cs; cs.tap_navigation_target(...)`) để mock có hiệu lực tại runtime.
    - *Verification test*: `PYTHONPATH="D:\Taadaa\automation-core\src;D:\Taadaa\tiktok-luot nuoi acc\python_runner" python -m unittest python_runner/tests/test_navigation_atx_recovery.py` (9/9 passed).
    - Chi tiết: `references/home-navigation-atx-session-recovery-20260905.md`.

- **CẤM truyền `lightweight=True` hoặc lightweight probe keys vào `capture_ui_xml` (2026-08-17, repo tiktok-follow)**: Trong `automation_core.ui:1420`, `capture_ui_xml` kiểm tra: nếu có `lightweight=True` hoặc bất kỳ key nào trong `lightweight_keys` (`deadline_seconds`, `max_local_recaptures`, `foreground_probe`, `expected_foreground`...) thì core **BỎ QUA TOÀN BỘ ATX PRIMARY / ATX SESSION** và ép chạy thẳng vào `_dump_current_ui_lightweight` (chính là shell `uiautomator dump`!) → dính ngay `ERROR: could not get idle state` khi TikTok đang phát video animation. Consumer gọi `capture_ui_xml(self._adb, timeout=..., provisioning_policy=ProvisioningPolicy.REQUIRE_PROVISIONED)` CHỈ truyền timeout + policy để core tự route qua ATX session primary (port 7912).

- **TikTok 46.x Account Switcher: Nhận diện Display Name vs Handle (`matches_switcher_identity`) & Synthetic Click 100ms (Case 142, 2026-09-17, Máy 14/71/72)**:
  1. **Lệch Display Name vs Handle**: Trên các phiên bản TikTok mới, danh sách Account Switcher bottom-sheet thường hiển thị Tên hiển thị người dùng (Display Name tiếng Việt như `"Anh Hoang"`, `"Anh Pham"`) thay vì `@username` (như `@hong.bo.anh83`, `@ngc.anh.phm33`).
  2. **False Missing Trigger Auto-Login**: Nếu code matcher (`matches_switcher_identity` trong `account_switcher.py`) chỉ so khớp tiền tố/handle đơn giản, hệ thống sẽ đánh trượt các tài khoản này -> kết luận sai là tài khoản bị văng -> tự động kích hoạt `reconcile_tiktok_accounts.py` -> kẹt màn hình 2FA OTP hoặc chạm trần 8 tài khoản.
  3. **Giải pháp 2 tầng trong `matches_switcher_identity`**:
     - *Tầng 1 (Token Overlap)*: Bóc tách token chữ cái không dấu qua `unicodedata.normalize('NFKD')` và so khớp giao thoa token giữa tên hiển thị và handle.
     - *Tầng 2 (Master DAT Alias Fallback)*: Tự động tra cứu prefix email đăng ký từ master DAT workbook (`taikhoan_dat_v2_updated .xlsx`) qua `_get_dat_workbook_alias_map()`. Khi display name khớp trọn vẹn trong email prefix (ví dụ `"Anh Hoang"` nằm trong `hoangthibaoanh3009...`), xác nhận chính xác danh tính tài khoản.
  4. **Synthetic Click Duration 100ms Cho `_tap_ui_element`**:
     - Khi chạm vào dòng tài khoản trong Switcher, lệnh `input tap {x} {y}` (0ms touch) thường xuyên bị nuốt bởi custom RecyclerView / Compose buttons (Case 2026-09-07).
     - Fix chuẩn: Thay `input tap {x} {y}` bằng synthetic click swipe `input swipe {x} {y} {x} {y} 100` trong `_tap_ui_element` (`feed_swipe_smoke.py`).
  5. **Bẫy Magic Link & One-Tap Fast Login 2FA Recovery**: Khi tài khoản bị thiếu trên switcher nhưng còn lưu trong cache One-Tap ("Chào mừng bạn trở lại"), BẮT BUỘC tự động lấy OTP (từ TOTP Secret hoặc Outlook app) điền ngay lập tức; CẤM dừng lại hỏi user khi đang mở màn hình 2FA để tránh bị TikTok kích hoạt bẫy Magic Link rate limit 900s: `references/tiktok-46x-account-switcher-fast-login-and-2fa-recovery-20260917.md`.

- **TikTok 46.x Account Switcher layout mới + verify nick ở Profile root (2026-08-17, máy 10; Case 72, 2026-09-02, máy 60; Case 77, 2026-09-03, máy 2)**: 
  1. TikTok layout mới: profile root chưa scroll thì tên nằm lệch TRÁI (x<300), không có anchor giữa đỉnh -> `find_switcher_anchor` báo `SWITCHER_ANCHOR_AMBIGUOUS`. Body username `id/sr3` ở $y=370..415$ chỉ là nút copy handle, TUYỆT ĐỐI KHÔNG fallback tap vào node này làm switcher anchor.
  2. Cách mở Switcher: Vuốt nhẹ vừa phải (từ y=0.65h lên y=0.42h, ~400px trong 200ms) -> tên `:id/pke` / `:id/pkh` nhảy lên sticky header chính giữa trên cùng ($y \le 250$, $300 \le x \le 780$) -> tap vào để bung bottom-sheet "Chuyển đổi tài khoản". CẤM vuốt quá mạnh (>1000px) làm tuột trang.
  3. So khớp danh tính fuzzy/prefix (`matches_switcher_identity`): UIAutomator trên màn hình chưa cuộn có thể nối thêm số badge vào display name/username (VD: `crystal.1.11` / `crystal.1.15`). Khi so sánh với text trên sticky header (`crystal.1.1`), bắt buộc dùng prefix/fuzzy matching để không bỏ sót anchor.
  4. Verify sau khi switch: Khi màn hình đang ở trạng thái scrolled thì username `@...` bị đẩy khuất lên trên (chỉ còn display name). Hàm `verify_selected_account` phải vuốt ngược nhẹ xuống (từ y=0.25h xuống y=0.75h) để đưa profile root về đỉnh thì mới đọc được text `@username` trong XML.
  5. Bounded recursion auto-login recovery: Khi gọi lại `verify_and_switch_profile` sau khi chạy login reconcile, bắt buộc truyền `allow_auto_reconcile=False` để chặn đệ quy vô hạn. Chi tiết: `references/profile-unscrolled-body-username-exclusion-and-fuzzy-header-20260902.md`.
  6. **Case 77 (2026-09-03, Máy 2) — Help Center Webview & Word-Boundary Filtering**: Tự động nhận diện & dismiss Webview Trợ giúp / "Tài khoản được đề xuất" (`inapp_browser_overlay`) qua nút back/close hoặc phím BACK. Khi loại trừ các anchor trợ giúp/đề xuất khỏi switcher (`_EXCLUDED_SWITCHER_TERMS`), BẮT BUỘC dùng regex word-boundary `\b` để tránh loại trừ nhầm các username hợp lệ (như `helpme123`, `shelper`). Chi tiết: `references/help-center-webview-and-switcher-word-boundary-20260903.md`.lại `verify_and_switch_profile` sau khi chạy login reconcile, bắt buộc truyền `allow_auto_reconcile=False` để chặn đệ quy vô hạn. Chi tiết: `references/profile-unscrolled-body-username-exclusion-and-fuzzy-header-20260902.md`.
    6. **Case 77 (2026-09-03, Máy 2) — Help Center Webview & Word-Boundary Filtering**: Tự động nhận diện & dismiss Webview Trợ giúp / "Tài khoản được đề xuất" (`inapp_browser_overlay`) qua nút back/close hoặc phím BACK. Khi loại trừ các anchor trợ giúp/đề xuất khỏi switcher (`_EXCLUDED_SWITCHER_TERMS`), BẮT BUỘC dùng regex word-boundary `\b` để tránh loại trừ nhầm các username hợp lệ (như `helpme123`, `shelper`). Chi tiết: `references/help-center-webview-and-switcher-word-boundary-20260903.md`.

- **CẤM tự gọi `uiautomator dump` trực tiếp bằng tay khi debug** (kể cả `adb shell uiautomator dump` / exec-out `/dev/stdout`) — user nhắc lại LIVE 2026-08-17 ("cấm dùng uiautomator trước, t cài trong rule r mà sao mày vẫn cứ xài"): debug UI phải qua ATX — `dumpWindowHierarchy` [true] endpoint session, hoặc `capture_ui_xml`/`capture_atx_session_ui` trong automation_core. uiautomator chỉ tồn tại làm fallback code, không phải công cụ debug tay. Khi dump UI bằng tay: dùng automation_core `capture_ui_xml` (qua venv farm + `env -u PYTHONPATH`), hoặc script standalone `scripts/dump_ui_atx.py <serial> [out.xml]` (zero-dependency standard library urllib, tự cấp dynamic forward, tự kích hoạt background stub qua `POST /uiautomator` nếu chưa chạy và parse dumpWindowHierarchy), TUYỆT ĐỐI KHÔNG gõ `uiautomator dump` shell (sẽ bị Killed EXIT=137 do tranh chấp accessibility).
- **Auto-Resolve ATX PID & Phục hồi HTTP 404 trong Standalone Automation Scripts (2026-09-18)**:
  - Khi viết standalone helper/script (ví dụ `change_email_m2.py`, ad-hoc probes), việc lưu biến `ATX_PID` toàn cục rất dễ gây crash `urllib.error.HTTPError: HTTP Error 404: Not Found` nếu gọi `get_xml()` / `atx_click()` khi chưa gọi `ensure_atx()` hoặc sau khi stub bị Android tự restart đổi PID.
  - Bắt buộc: Trong `get_xml()` và `atx_click()`, nếu `not ATX_PID`: tự động gọi `ensure_atx()`. Đồng thời bọc khối gọi urllib trong `try/except HTTPError as e:`: nếu `e.code == 404`, tự động refresh lại `ensure_atx()` và retry request 1 lần trước khi raise lỗi.
  - Mở Switcher trên TikTok 46.x: Khi Profile ở trạng thái chưa cuộn (unscrolled), node handle nằm ở body (`:id/sxa`). Thực hiện vuốt nhẹ `input swipe 540 1200 540 800 200` (~400px) làm sticky header `:id/pmf` xuất hiện tại `[366,117][720,183]` (tâm `(543, 150)`). Tap node này bung sheet "Chuyển đổi tài khoản" (`id/fxs`), quét danh sách tài khoản qua `:id/lli` và `:id/n7z`.
- **Live ATX PID/forward parsing must be column-aware and target-scoped**: `ps -A` output is whitespace-delimited and may not contain the exact spacing assumed by a regex. Parse columns, require the final process-name column to equal `com.github.uiautomator`, exclude `com.github.uiautomator.test`, and require exactly one match before using its PID. Gọi session endpoint với stale PID (sau khi stub bị restart hoặc PID thay đổi) sẽ ném `HTTP Error 404: Not Found`; luôn chủ động re-query PID mới nhất từ `ps -A` trước khi dump hoặc click. For forwarding, first inspect `forward --list`, match the exact target serial plus remote `tcp:7912`, and reuse that serial's dynamic local port. Never run `forward --remove-all` on a live farm merely to simplify discovery; stale forwarding cleanup must be serial-scoped.
- **Loại trừ Node Tiêu đề Sửa Tên (:id/pkh, :id/pke) khỏi Switcher Anchor (2026-09-02)**:
  - Khi tài khoản chưa đặt `@username` (chỉ có display name "Huy Mập") hoặc giao diện header giữa, `find_switcher_anchor` / `_find_sticky_profile_header` có thể nhận nhầm node tiêu đề tên `com.ss.android.ugc.trill:id/pkh` / `pke` làm switch anchor.
  - Tapping trúng node này kích hoạt trang "Đổi tên" (`tv_content_name`) và bật bàn phím ảo thay vì mở sheet Switcher $\rightarrow$ lặp dismiss/tap và dừng phiên.
  - Fix: Bắt buộc lọc bỏ các resource-id `:id/pkh`, `:id/pke`, `:id/pau`, `:id/s9b`, `tv_content_name` khỏi tập ứng viên switcher header.

- **Check Gmail Live qua ATX XML (2026-08-21):** Khi kiểm tra tài khoản Google/Gmail live (trong repo `add mail khoi phuc` hoặc flow login/reg), BẮT BUỘC dùng ATX session để đọc node *"Đăng nhập"* và *"TIẾP THEO"* lấy bounds chính xác, CẤM tap mù/tọa độ đoán để phát hiện chính xác màn reCAPTCHA ("Tôi không phải là người máy").

- **Bẫy Header Email Đè Password Challenge trong Google OAuth (2026-09-15, ChatGPT/Gmail Reg)**:
  - *Hiện tượng*: Flow đăng ký/đăng nhập Google OAuth (như `hook_chatgpt_register.py`) kẹt ở `FAILED_AT_ACCOUNT_SELECT` dù Chrome đã chuyển sang màn nhập mật khẩu `accounts.google.com/v3/signin/challenge/pwd`.
  - *Root cause*: Trên màn hình nhập mật khẩu, Google hiển thị email tài khoản ở phần header (`headingText` / TextView). Nếu code kiểm tra `find_node_in_xml(xml, email)` (nhánh Account Chooser) TRƯỚC nhánh kiểm tra password (`"challenge/pwd" in xml` hoặc `"Hiện mật khẩu" in xml`), script sẽ luôn tìm trúng node header email và tap liên tục vào header cho đến khi hết timeout.
  - *Xử lý*: BẮT BUỘC kiểm tra màn hình mật khẩu (`challenge/pwd`, `Hiện mật khẩu`, `Enter your password`) TRƯỚC khi tìm node email của Account Chooser. Sau khi điền mật khẩu, ưu tiên tìm và tap nút `"Tiếp theo"` / `"Next"` trong XML thay vì chỉ phụ thuộc vào `keyevent 66`.

- **Atx query tay khi atx-agent chạy mà /wd/hub 404**: atx-agent 0.10.1 KHÔNG expose WebDriver /wd/hub — endpoint là JSON-RPC pid-scoped `/session/{pid}:com.github.uiautomator/jsonrpc/0`; method dump đúng = `dumpWindowHierarchy` params **[true]** (không phải `uiautomator.dump`/`dumpHierarchy` — trả "method not found"); `click(x,y)` OK; KHÔNG có method text — gõ qua `adb shell input text` sau khi tap focus. Khám phá method: gọi method sai → `-32601`; method đúng nhưng thiếu params → `-32602`.

- ⚠️ **ATX `click` là cách DUY NHẤT tap được nút WebView trong Outlook Reading Pane / mail HTML và nút Switcher cứng đầu trên TikTok 46.x**:
  - Outlook Reading Pane: `adb shell input tap <x,y>` KHÔNG ăn nút `<a href>` render trong OneAuth/Outlook WebView (intercept), dù tọa độ trúng bounds. ATX click (JSON-RPC `click`, đi qua UiAutomator) → `result: True` → link kích hoạt.
  - TikTok 46.2.3 Account Switcher (`id/l9b`): 0ms `input tap` không đổi tài khoản. Chi tiết: `references/atx-click-vs-input-tap-custom-ui-20260907.md`.
  - Helper ATX click: lấy pid `com.github.uiautomator` từ `ps -A` → `adb forward tcp:7912 tcp:7912` → `POST /session/{pid}:com.github.uiautomator/jsonrpc/0 {"method":"click","params":[x,y]}` → check `result is True`.

- **Popup packageinstaller deny → verify focus quá sớm (0.8s → 2.5s, máy 19 2026-08-17)**: sau tap TỪ CHỐI trên dialog contacts/permission (core detect OK: resource-id `permission_message`/`permission_deny_button` + text "Cho phép TikTok truy cập vào danh bạ"), `_sleep_and_recapture` (flows/benign_popup.py) chỉ sleep 0.8s rồi capture → dialog chưa fade-out + app chưa kịp trả foreground → vẫn `com.android.systemui` → false "TikTok focus lost" (log: `dismiss_<popup> success` ngay sau `*_after_*_dismiss | observe | failed`). Fix: sleep 2.5s. Lỗi là TIMING sau deny, không phải detect/deny — đừng sửa nhầm handler popup.\n\n- **Consumer ép `lightweight=True` chặn ATX-primary (tiktok-luot nuoi acc `core/ui_capture.py::capture_required_ui_result`, 2026-08-17)**: hàm này gọi `capture_ui_xml(..., lightweight=True, deadline_seconds, max_local_recaptures, foreground_probe...)` → core (ui.py:1420) thấy lightweight keys là BỎ QUA toàn bộ ATX session primary, ép `_dump_current_ui_lightweight` (shell uiautomator) thẳng → dính idle_state_error khi video animation. Theo plan upgrade-atx-primary-all-repos: thêm ATX-primary block ĐẦU hàm TRƯỚC lightweight path — `capture_atx_session_ui(adb, timeout=bounded_deadline, restart_attempts=1)` → nếu xml có `<hierarchy` return ngay. ⚠️ CaptureResult constructor BẮT BUỘC đủ field (xml, backend, capture_id, attempts, artifact_path, diagnostics) — thiếu backend/capture_id → TypeError; `CaptureBackend.ATX_SESSION` tồn tại trong automation_core.ui_capture (giá trị "atx_session").\n\n- **Xử lý Màn hình khóa Samsung (Keyguard / Emergency Call) trước khi điều hướng (2026-08-28)**:
  - Khi thiết bị bị tắt/khóa màn hình Samsung Keyguard (`Vuốt màn hình để mở khóa`, `com.android.systemui:id/emergency_call_button`), lệnh `input keyevent 3` (Home) không thể mở khóa.
  - Phải gọi `prepare_android_for_automation(client)` ngay đầu `open_app()`, hoặc gửi `keyevent 224` (WAKEUP) + vuốt mở khóa `input swipe 540 1500 540 300 300` khi phát hiện text Keyguard để tránh bị kẹt không vào được tab Profile.

- **Giới hạn Timeout Bounded cho ATX Session Dump (2026-08-28 & 2026-09-04)**:
  - CẤM để timeout một lần capture ATX quá dài (>30s) vì nếu socket bị nghẽn, nó sẽ ngốn hết tổng thời gian `UI_XML_TOTAL_TIMEOUT` trước khi kịp gọi `reset_atx_agent`.
  - Chuẩn: Giới hạn mỗi lần thử ATX tối đa 15-20s qua `capture_atx_session_ui(client, timeout=min(15.0, rem))` với `rem = max(0.1, bounded_deadline - (time.monotonic() - loop_start))`. Sau 3 lần fail, gọi `reset_atx_agent(client, timeout=15)`, sleep 0.5s cho socket JSON-RPC bind, rồi mới thử lại tối đa 2 lần với `min(20.0, rem)` trước khi fail-closed.
  - **`is_connection_lost` cho curl stderr (2026-09-04)**: Khi `stderr` chứa `curl:` hoặc `curl.go:`, kiểm tra danh sách curl-specific markers (`error: device`, `device not found`, `adb: error`, `cannot connect to daemon`, `no devices/emulators found`, `adb command timed out`) và `return any(...)` dứt khoát để không bị fallthrough sang generic `CONNECTION_LOST_MARKERS` gây false-positive.

- **`UI_XML_TIMEOUT` + `uiautomator_null_root_node` khi chuyển app foreground (máy 78, 2026-08-21)**:
  - Triệu chứng: `social_reg_v1` / runner báo `[adb-timeout] UI_XML_TIMEOUT ... detail=attempt2:fallback-timeout:/data/local/tmp/_ui.xml` kèm `uiautomator_null_root_node` do `com.github.uiautomator` bị treo/crash khi chuyển từ Launcher sang TikTok splash.
  - Xử lý: (1) Diệt & khởi động lại ATX stub qua daemon endpoint `POST /uiautomator` (CẤM dùng monkey) kèm restart ladder `pkill -9 -f atx-agent` + `am force-stop com.github.uiautomator` rồi `/data/local/tmp/atx-agent server -d`; (2) Dọn sạch stale device lock file trong `~/.codex/device-locks/` nếu tiến trình cũ bị ngắt đột ngột để giải phóng lock cho lượt chạy tiếp theo.

- **KHÔNG dùng file fallback làm nguồn chính trên máy yếu — luôn stale**

- atx fail phải fallback shell chứ không raise (máy không atx vẫn chạy)

- `capture_ui_xml` cần `ProvisioningPolicy.REQUIRE_PROVISIONED` (máy có atx-agent mới provision)

- **Cập nhật source ở repo KHÔNG tới được runtime batch (COPY install)**: venv farm `D:\Taadaa\python-envs\automation` cài automation_core dạng COPY (không editable) — `cp -rf src/automation_core/* "/d/Taadaa/python-envs/automation/Lib/site-packages/automation_core/"` sau mỗi commit rồi mới chạy batch hoặc test các consumer repo.

- **Dynamic forward port assertion trong unit tests**: Core chuyển sang cấp port local động (`forward tcp:0 tcp:7912`) để tránh conflict giữa các máy farm chạy song song/tuần tự -> các mock `AdbClient.run` trong unit test cần assert `["forward", "tcp:0", "tcp:7912"]` thay vì port cứng `7912`.
  ⚠️ **Bug index parsing `adb forward --list`**: Chuỗi output có format `<serial> <local_port> <remote_port>` -> local port động nằm ở `parts[1]` (ví dụ `parts[1].split(":")[1]`), KHÔNG phải `parts[2]` (cổng remote `7912`). Parse nhầm `parts[2]` khiến request JSON-RPC gửi tới cổng 7912 sai lệch dẫn đến 502 Bad Gateway hoặc timeout.

- **Kích hoạt stub an toàn trong `reset_atx_agent` (2026-09-05 update)**:
  - CẤM dùng `monkey -p com.github.uiautomator 1` trong `reset_atx_agent` vì `MainActivity` chiếm trọn foreground xoay ngang và làm vỡ layout của TikTok.
  - Sử dụng `POST /uiautomator` của `atx-agent` để kích hoạt background stub (không có UI activity).
  - Chủ động poll `ps -A` để xác nhận tiến trình `com.github.uiautomator` đã xuất hiện.
  - Kiểm tra `dumpsys window windows` ở cuối hàm, gửi `keyevent 3` nếu phát hiện uiautomator trong foreground.
  - Trong consumer `ui_capture.py`: sau khi reset, cho phép retry capture 3 lần với backoff 0.5s để đảm bảo socket JSON-RPC đã bind hoàn toàn.

- **Nguyên tắc "Fix máy" từ User**: Khi user yêu cầu "fix máy XX", BẮT BUỘC phải phân tích root-cause, sửa và lưu trực tiếp vào codebase/script (`automation-core`, consumer runners), cập nhật `docs/farm-automation-cases.md` (Gate 0.5), chạy test suite và live canary chứng minh script tự động xử lý được. TUYỆT ĐỐI KHÔNG chỉ chạy lệnh ad-hoc bằng tay cho qua phiên mà không lưu code fix.

- **Host-aware proxy mapping resolution**: `automation_core.preflight.resolve_proxy_mapping_path` là hàm chuẩn để lấy path file `PROXYgandienthoai.xlsx` theo `TAADAA_HOST_CONFIG` (fail-closed, không fallback kibe). Consumer repo cần import hàm này từ `automation_core.preflight`.\n- **`ime list -s` ≠ `ime list -a -s` khi verify AdbKeyboard**: `-a` liệt kê CẢ IME chưa enable → check nhầm tưởng đủ điều kiện, flow `type_text(sensitive=True)` check `-s` (enabled) vẫn fail `refusing unsafe password input`. Sau cài APK phải `ime enable com.github.uiautomator/.AdbKeyboard`; verify `ime list -s | grep AdbKeyboard` (case-sensitive, không lowercase).

- **`PYTHONPATH` env toàn cục của Hermes session override site-packages venv**: session Hermes set `PYTHONPATH=C:\\Users\\Kibe\\AppData\\Local\\hermes\\hermes-agent;...\\venv\\Lib\\site-packages` (không có trong .bashrc — do Hermes tự prepend). Hệ quả: chạy `D:/Taadaa/python-envs/automation/Scripts/python.exe` (venv farm) vẫn import `automation_core` từ HERMES venv (bản cũ — chạy `import automation_core; print(automation_core.__file__)` để phát hiện). Fix: `env -u PYTHONPATH D:/Taadaa/python-envs/automation/Scripts/python.exe ...` hoặc `PYTHONPATH="D:\\Taadaa\\automation-core\\src"` (path Windows, không MSYS). **Bắt buộc khi verify runtime ATX-primary** — nếu không, ATX mới không bao giờ chạy dù code core đã sửa.

- `capture_ui_xml` trả xml RỖNG (không raise UIDumpError) → vẫn phải fallback: `ui_xml` (Hotmail) cũ `return capture_ui_xml(...).xml` — capture trả `xml=""` (service sống nhưng dump rỗng) → return "" NGAY, bỏ qua exec-out fallback → provider đọc màn rỗng fail. Fix (đã merge `7267201`): check `captured is not None and captured.xml and "<hierarchy" in captured.xml` → có thì return; rỗng/None → rơi xuống exec-out retry 5×. Test: `test_ui_xml_empty_capture_falls_back_to_exec_out` mock capture trả `SimpleNamespace(xml="", ...)` + `run_adb` side_effect `["", "<hierarchy...>"]`. Cùng class: mọi wrapper `capture_ui_xml(...).xml` đều phải guard None/rỗng.

- 2 cơ chế đọc UI KHÁC NHAU: shell dump (chết) vs atx-agent (sống) — đừng kết luận "máy hỏng" khi 1 cơ chế fail

- BACK keyevent từ mail-detail Outlook = thoát app (dùng back-arrow in-app)

- Rotation: luôn `settings put system accelerometer_rotation 0` + `user_rotation 0` sau mỗi phiên



### Test trên consumer repos (nhầm import automation_core)

Consumer test thường import NHẦM `automation_core` từ hermes venv (`C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages` — bản cũ, thiếu symbol mới → ImportError khi collection). Chạy với:

```bash

PYTHONPATH="D:\\Taadaa\\automation-core\\src" /d/Taadaa/python-envs/automation/Scripts/python.exe -m pytest tests/...

```

**BẮT BUỘC path Windows (`D:\...`) — MSYS `/d/...` bị mangling thành `D:\d\...` và không trỏ đúng.** venv `python-envs/automation` cài automation_core dạng COPY (không editable) nên local source change luôn cần PYTHONPATH.

**Chứng minh test fail/treo là pre-existing**: `git stash` → rerun → `git stash pop`. Fail cả khi stash = không do patch (áp dụng cả test fail lẫn test treo do atx path kết nối ADB thật trong test cũ không mock — test cũ mock `_exec_out`/`shell` nhưng atx-primary chạy automation_core THẬT trước loop). Test cũ như vậy cần `monkeypatch.setattr(social, "_atx_capture_ui_xml", lambda *_a, **_k: None)` — xem mục "Test update bắt buộc".



**`ZoneInfo("Asia/Ho_Chi_Minh")` trong consumer cần `tzdata` package trên Windows (proven 2026-08-15, tiktok-luot hermes_cron blocks/models):** Python Windows không ship IANA timezone data → module-level `TZ = ZoneInfo("Asia/Ho_Chi_Minh")` raise `ZoneInfoNotFoundError` tại COLLECTION khi chạy file lẻ (full suite chạy được vì conftest/cwd khác — triệu chứng phân mảnh). Fix: thêm `tzdata` vào `requirements-automation-core.txt` của consumer (không phải lỗi code). **Pitfall môi trường:** venv `python-envs/automation` có thể báo `pip show tzdata` OK nhưng `import tzdata; print(tzdata.__file__)` trỏ hermes venv (`...hermes-agent\venv\Lib\site-packages\tzdata`) → venv đó THỰC SỰ thiếu; chạy test với hermes python (`C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe`, có tzdata) để verify, hoặc cài bằng absolute-path python.



### WIP của agent khác + commit chồng

- `git status --short` TRƯỚC khi sửa file; file đích có uncommitted changes (VD stash `codex-pre-integration-*` + device_lock/executor bẩn) → **HỎI user trước khi commit chồng**; được duyệt thì commit nguyên file + message minh bạch ghi rõ "gồm WIP <agent> + patch atx"

- Consumer có WIP đòi symbol core chưa merge (VD `DeviceLockNeedsUserDecision`) → test collection fail. **Resolution path (user-approved 2026-08-15):** tìm branch feature trong core worktrees (`for wt in automation-core-*-wt; do grep -rln "Symbol" $wt/src; done`) → HỎI user → được duyệt thì:

  1. **Dry-run conflict check TRƯỚC**: `git merge-tree --write-tree master <branch>` — ra tree hash (không có `<<<<<<<`) = merge SẠCH, an toàn. Verify tree giữ patch mình: `git show <treehash>:<file> | grep -c "capture_ui_xml"`.

  2. `core_merge_guard.py acquire --repo "D:\\..." --owner <who>` → merge --no-ff → test core (device_lock + user_lock_gate + usb_popup + ui_dump) → release guard.

  3. **Merge 3-way KHÔNG mất patch atx trên master**: branch fork từ trước patch, không sửa vùng đó so với merge-base → git giữ version master. Chỉ 3 file feature thay đổi.

  4. Consumer test chạy lại — fail còn lại là WIP test cũ đang cập nhật theo behavior mới → để chủ WIP hoàn tất, KHÔNG sửa thay.

  → **Trường hợp user nói "1 mình m làm thôi / xử lý hết"**: hoàn tất WIP luôn. Sau merge core, mọi consumer test device_lock vỡ theo catalog lặp lại (release_with_audit, lock_protocol_version, queued_v2, jitter, summary index, dismiss count) — xem catalog đầy đủ ở `automation-core-consumer` §"Consumer device_lock test migration khi core đổi behavior". Chạy full suite từng repo, phân loại từng fail theo catalog, sửa test, commit riêng từng repo. Bỏ qua untracked rác không phải mình (`_vpn_probe*.py`, `_wbmap.py`, `.hermes/plans/`, `reap-*.py`) — không commit.

- `tools/core_merge_guard.py` cũng cần `--repo "D:\\..."` native (git -C với MSYS path fail exit 128)

- `git stash show -p stash@{0} -- <file>` trả RỖNG qua MSYS path mangling → dùng `git diff HEAD stash@{0} -- <file>` để đọc nội dung stash

- `git diff --stat <file>` gồm cả uncommitted WIP có sẵn — phân biệt phần mình bằng `git diff <file> | grep capture_ui_xml|uiautomator|...`

- Bỏ shell dump → capture_ui_xml (không tạo file /sdcard tạm) → bỏ luôn `try`/`finally` rm-cleanup; KHÔNG để `finally` rỗng (IndentationError); nếu giữ `try` thì dedent toàn bộ thân hàm



## Verify

- `get_ui_xml(dev)` trả len lớn (43K-76K = màn thật) thay vì 12K (stale)

- Test: full pytest repo xanh, `git diff --check` sạch

- Evidence: log `[ui-xml] atx primary OK len=...` xuất hiện



## Sizing max_workers bằng load test ATX thật

Khi cần chọn số máy chạy song song (feed session multi-machine): test bằng ATX API thật (port 7912 `POST /uiautomator`) + mô phỏng phiên đầy đủ (mở TikTok + chờ load S7 ~8s + 15 lần đọc UI/swipe), KHÔNG dùng ping nhẹ hay shell uiautomator (farm chuyển ATX hết). Kết quả 16/08: 30 máy song song 0 lỗi → max_workers=30; 40 bắt đầu 2 lỗi. Recipe đầy đủ: `references/atx-load-test-max-workers.md`.

