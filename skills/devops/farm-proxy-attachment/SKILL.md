---

name: farm-proxy-attachment

description: Verify or configure per-device proxy attachment for the Taadaa Android phone farm via the ViChanger app and the gan-proxy repo. Use when the user asks whether the farm proxy setup is correct/safe/legit ("gắn proxy ổn không", "vichanger fake không", "proxy qua app hay adb"), or when a task touches D:\Taadaa\gan-proxy, vi_changer_runner.py, gan_proxy_fleet.py, or the per-device proxy mapping.

---



# Farm proxy attachment (Taadaa phone farm)

## 🛑 QUY TẮC CỐT LÕI (2026-09-03 — BỎ HOÀN TOÀN VICHANGER)
- **FARM ĐÃ BỎ HOÀN TOÀN VICHANGER:** Toàn bộ 80 máy Kibe chạy qua router MikroTik RouterOS và Container Singbox Mixed Inbound (`20001..20080` tương ứng máy 1..80 tại `192.168.110.2`).
- **CẤM TUYỆT ĐỐI GỌI VICHANGER / gan_proxy_fleet.py run:** Không bao giờ bật ViChanger app hay gửi broadcast `START_VPN` lên máy. ViChanger đã bị xóa khỏi toàn bộ consumer repos.
- **CÔNG CỤ GÁN PROXY CHUẨN DUY NHẤT:** `python D:\Taadaa\AI-Tools\scripts\set_proxy_farm_adb.py --machines <ID>` (gán `http_proxy=192.168.110.2:2000N` và tắt captive portal `captive_portal_mode=0`, `captive_portal_detection_enabled=0`).
- **Repo gan-proxy:** Chỉ giữ lại nguyên trạng làm tư liệu legacy, KHÔNG chạy trên dàn máy live.

## Kiến trúc MikroTik & Sing-box Proxy
- **Gateway LAN IP:** `192.168.110.2`
- **Cụm 80 cổng Sing-box Inbound:** Port `20001..20080` (`20000 + Số máy`)
- **35 Line PPPoE:** Dải upstream `10001..10035` (`admin@1:admin@1`) / Dcom
- **Hardware Kill-Switch:** MikroTik Firewall tự động DROP toàn bộ traffic ra ngoài nếu máy chưa trỏ proxy `192.168.110.2:2000N` qua ADB để chống lộ Direct IP.

## Lệnh vận hành chuẩn
- **Gán proxy ADB cho máy mới/bật lại/toàn farm:**
  `python D:\Taadaa\AI-Tools\scripts\set_proxy_farm_adb.py --machines <ID>` (bỏ trống `--machines` để gán cả 80 máy).
- **Kiểm tra trạng thái & fix Singbox:**
  `python D:\Taadaa\AI-Tools\scripts\mikrotik_manager.py --check` / `--fix`.
- **Xác thực Egress IP từ PC:**
  `curl -s -m 10 -x http://192.168.110.2:<PORT> http://api.ipify.org`
  (Egress IP phải khác Direct IP farm `42.114.218.81`).
- **Xác thực từ thiết bị S7 (qua atx-agent curl hoặc toybox nc):**
  `adb -s <serial> shell "/data/local/tmp/atx-agent curl --timeout=3s http://icanhazip.com"`

## When to use
- Khi máy bị mất proxy, reboot lại hoặc mới cắm vào farm.
- Khi cần kiểm tra / gán lại proxy định tuyến toàn bộ dàn máy Kibe (1..80).
- Task liên quan đến hạ tầng mạng, MikroTik, Singbox, IP proxy của farm.



## MikroTik & Sing-box Proxy Architecture (2026-08-31)

Toàn bộ 80 máy Kibe chạy qua router MikroTik RouterOS (7.18.2) và Container Sing-box:
- **Router Quản trị:** REST API `192.168.110.2:9090` / `mirotik1.taadaa.click` (user `admin`, pass `N0spam@@`).
- **Cụm 80 cổng Sing-box:** Port `20001..20080` (`20000 + Số máy`).
- **35 Line PPPoE:** Dải upstream `10001..10035` (`admin@1:admin@1`).
- **Hardware Kill-Switch:** MikroTik Firewall tự động DROP toàn bộ traffic ra ngoài nếu máy chưa trỏ proxy `192.168.110.2:2000N` qua ADB để chống lộ Direct IP.
- **Tài liệu toàn tập:** `D:\Taadaa\AI-Tools\docs\infrastructure\mikrotik\mikrotik-master-network-handbook.md`.

## Quy tắc giao tiếp & Báo cáo lỗi gửi Admin / Bên ngoài (BẮT BUỘC)
Khi người dùng yêu cầu soạn nội dung báo cáo lỗi gửi admin bên ngoài / nhà cung cấp:
- **CHỈ GHI HIỆN TƯỢNG VÀ MÃ LỖI:** Nêu rõ Host, Port, mã lỗi (ví dụ: `Connection Refused`, `Timeout`, `HTTP 407`).
- **CẤM THÊM GIẢI PHÁP / HƯỚNG DẪN:** Tuyệt đối không tự ý viết thêm hướng dẫn fix, bước xử lý hay gợi ý cấu hình router trừ khi người dùng yêu cầu rõ ràng.



## Pitfalls

- Plain `host:port` proxy = bypassable by TikTok. Ensure the Excel mapping uses the authenticated form.

- search_files fails on `D:\` → use terminal find/grep.

- Don't broad-search the filesystem when the user already named the repo.



## VPN gate and host-aware mapping (17/08/2026 — user rule "k bật vpn thì k đc chạy")



**Bug class that must never regress:** `vpn_preflight.DEFAULT_PROXY_MAPPING` in COMSUMER repos

hardcoded the kibe workbook (`D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx`). On the admin

host (máy 200+, `TAADAA_HOST_CONFIG=admin.yaml`, workbook_root trống), `serial_is_mapped_in_workbook`

read the KIBE mapping → admin serials not found → `required=False` → VPN check skipped → **máy admin

không VPN vẫn chạy** (user caught it live on the 06:00 shift: "nhiều máy chưa có vpn vẫn chạy").



**Fix (canonical, all-repo):** mapping MUST resolve per host, never fall back to another host:

- `automation_core 0.4.46` adds `resolve_proxy_mapping_path()` — reads `TAADAA_HOST_CONFIG`

  workbook_root; for kibe → `kibe/PROXYgandienthoai.xlsx`; for admin (no file) → **raise**

  fail-closed (no kibe fallback, no silent exempt).

- Patched in EVERY consumer that hardcodes the mapping path: `tiktok-luot nuoi acc/vpn_preflight.py`,

  `tiktok-log-in` (cli.py + account_reconcile.py), `tiktok-add-bao-mat-f2a`, `add mail khoi phuc`,

  `register gmail` (gmail_reg_v10.py + guarded_device_reboot.py), `Hotmail/hotmail_login.py`,

  `gan-proxy/gan_proxy_fleet.py`, worktree `tiktok-log-in-recovery-adapter-p2-wt`.

  Verify with: `grep -rln "PROXYgandienthoai" --include=*.py D:/Taadaa/ | grep -viE "venv|site-packages|\.git|tests"` → must be EMPTY for runtime code.

- Non-git repos (register gmail, Hotmail, gan-proxy) patched in place (no commit possible).



**Live IP Verification (20/08/2026 — commit `c5036cb` in `automation-core`):**
- Chỉ kiểm tra `tun0 UP` và `dumpsys connectivity` là KHÔNG ĐỦ vì khi upstream proxy chết, `tun0` ở local vẫn `UP`, TikTok tự động fallback ra Direct Wi-Fi IP gây lộ footprint toàn farm.
- `check_android_vpn` và `require_android_vpn` bổ sung `verify_live_ip=True`: bắt buộc gửi broadcast `vn.vichanger.app.GET_IP` tới `vn.vichanger.app/.AdbCaller`.
- Điều kiện PASS: `result=200` và `data="<IP>"` hợp lệ; nếu `result=0` (proxy chết) $\rightarrow$ BLOCK ngay lập tức (fail-closed), tuyệt đối không cho mở TikTok.
- **Phân biệt `result=0` vs `broadcast exception: adb command timed out`**:
  - `result=0`: Upstream proxy sập / chết port / xác thực lỗi $\rightarrow$ kiểm tra port proxy ngoài bằng `curl -I -m 10 http://host:port` (phải trả 407/200, không timeout).
  - `broadcast exception: adb command timed out`: ADB hoặc tiến trình `vn.vichanger.app` trên máy bị nghẽn tạm thời dẫn đến quá thời gian chờ lệnh broadcast. `tun0` và kết nối VPN vẫn đang giữ; kiểm tra lại bằng lệnh broadcast thủ công `am broadcast -a vn.vichanger.app.GET_IP -n vn.vichanger.app/.AdbCaller` nếu trả `result=200` thì VPN và proxy vẫn bình thường.
- **TUYỆT ĐỐI KHÔNG BỎ GATE NÀY:** Khi user hỏi *"có nên bỏ kiểm tra trên máy / chỉ check bên ngoài"* khi thấy nhiều máy báo `MissingVpnRecoveryError`: Phải giải thích rõ việc kiểm tra `GET_IP` trên máy là chốt chặn cuối cùng ngăn Android fallback về direct Wi-Fi. Khi nhiều máy dừng phiên cùng lúc, kiểm tra phân nhóm host mapping (`PROXYgandienthoai.xlsx`) bằng `curl -x` và `am broadcast ... GET_IP` để xác định chính xác cụm proxy nào đang sập (ví dụ: `mirotik1.taadaa.click` hoặc `khoalee.duckdns.org` mất mạng/chết port) thay vì tắt gate bảo vệ.
**Quy trình chẩn đoán khi nhiều máy báo MissingVpnRecoveryError / TimeoutError proxy readiness:**
  1. Đọc mapping `D:\\OneDrive\\TaadaaData\\kibe\\PROXYgandienthoai.xlsx` nhóm theo host (`test.taadaa.click`, `mirotik1.taadaa.click`, `khoalee.duckdns.org`).
  2. Test `curl -x http://user:pass@host:port https://api.ipify.org` (hoặc Python `urllib.request.ProxyHandler`) bên ngoài theo cụm port để xác định box nào đang sập toàn diện hay chỉ chết port lẻ.
  3. Kiểm tra DNS DDNS của box (`nslookup <host>`) và ping/port check để phân biệt sập nguồn/mất mạng WAN với lỗi xác thực auth (407) hay rate-limit.
  4. Bắn broadcast trực tiếp: `adb -s <serial> shell am broadcast -a vn.vichanger.app.GET_IP -n vn.vichanger.app/.AdbCaller`. Lưu ý: Khi `tun0` chưa lên, `GET_IP` có thể trả về chính Direct IP của mạng Wi-Fi farm (`result=200, data="<Host Direct WAN IP>"`). Luôn đối chiếu với Host Public IP để phát hiện Direct IP Leak.
  5. Nếu proxy upstream timeout/sập: Báo cáo danh sách cổng chết / box chết cho user kiểm tra box/nguồn/sim, KHÔNG sửa code hay bypass gate bảo vệ. Sau khi box online lại, Watcher sẽ tự gán lại VPN và giải phóng hiện trường.

**Cách check proxy đúng cho nhiều máy cùng lúc (học từ 2026-08-23):**
- `tun0 UP` + `ping 8.8.8.8 OK` + thiếu `default route qua tun0` **KHÔNG CÓ NGHĨA là proxy die** — ViChanger không push default route kiểu OpenVPN, routing của nó hoạt động qua VpnService tunnel. Cấm kết luận proxy hỏng dựa trên `ip route` hay `wget/curl` trên shell Android.
- `wget` / `curl` / `python3 urllib` trên shell Android cũng **không lấy được public IP** vì ViChanger intercept traffic ở tầng VpnService của Android apps, không hook command line shell.
- **Cách đúng duy nhất:** broadcast với `-n vn.vichanger.app/.AdbCaller` và đọc `result=200` + `data="<IP>"`:
  ```python
  import subprocess, re
  r = subprocess.run([adb, "-s", serial, "shell", "am", "broadcast",
      "-a", "vn.vichanger.app.GET_IP",
      "-n", "vn.vichanger.app/.AdbCaller"],
      capture_output=True, text=True, timeout=10)
  match = re.search(r'data="([^"]+)"', r.stdout)
  ok = "result=200" in r.stdout and match
  ip = match.group(1) if match else ""
  ```
- `result=0` (không có `.AdbCaller` hoặc broadcast không có `-n`) → không có IP → sai kết quả. Luôn dùng `-n vn.vichanger.app/.AdbCaller`.
- **Phát hiện lộ IP gốc (Direct IP Leak):** Luôn so sánh IP lấy từ ViChanger với Host Public IP (`https://api.ipify.org`). Nếu trùng (ví dụ các port `mirotik1.taadaa.click:1000x` trỏ về router nội bộ không qua 4G/Dcom), máy đang dùng direct IP farm. TikTok có thể cho reg 1 acc nhưng sau đó rate-limit toàn bộ các máy khác cùng IP.
- **Tự động gắn lại proxy qua Watcher sau reboot:** Khi reboot máy, watcher `gan_proxy_fleet.py watch` (chạy ngầm trên PC) sẽ tự động bắt sự kiện thiết bị online và gán lại proxy theo `PROXYgandienthoai.xlsx`.
- **Cảnh báo Serial Drift:** KHÔNG lấy serial từ log cũ hoặc manifest tạm. Luôn tra cứu serial chuẩn từ file `D:\OneDrive\Tiktok\Tik1.xlsx` (hoặc `PROXYgandienthoai.xlsx`), vì một số file tracking/manifest tạm (như `taikhoan_run_safe.xlsx`) có thể bị ghi đè ngày tháng vào cột serial (ví dụ `23/08/2026`). Dùng `Tik1.xlsx` sheet `TaiKhoan` làm single source of truth cho `STT ↔ Serial ADB`.
- **Môi trường Python khi chạy probe/script:** Trên host Windows này, các thư viện `openpyxl`/`requests` nằm trong virtualenv `D:\Taadaa\python-envs\automation\Scripts\python.exe`. Khi gọi bằng subprocess/terminal, cần `env -u PYTHONPATH -u PYTHONHOME` để tránh xung đột binary/C-extension với venv của Hermes CLI.
- **Tiêu chuẩn nhịp độ Reg TikTok an toàn:** Mỗi ngày chỉ reg **tối đa 1 acc / máy / ngày** (trên proxy sạch 4G/Dcom xoay IP). Không dùng IP direct của farm để reg hàng loạt tránh bị TikTok quét dải IP.



**Recovery ladder (core `recover_missing_android_vpn`, wired in `vpn_preflight.require_vichanger_connected`):**

VPN fail on a MAPPED machine → (1) GanProxy reassign (`proxy_pending` + wait `wait_for_proxy_ready` 60s) → (2) **Stage-2 Direct Proxy Reconnect** (đọc mapping `PROXYgandienthoai.xlsx` → gọi `vi_changer_runner.set_proxy` trực tiếp tại chỗ → verify `verify_live_ip=True`) → (3) soft-reboot 1× (`soft_reboot_and_wait`: reboot → unlock → wait proxy/VPN) → (4) still fail → `MissingVpnRecoveryError` FINAL_BLOCKED (never runs VPN-less). Chi tiết: `references/stage2-direct-proxy-reconnect-and-live-ip-20260824.md`. Bounded reboot "1-2 lần tránh loop lỗi do gan proxy" is the user's framing — do NOT loop reboot beyond the core ladder.



## References

- `references/mikrotik-singbox-phone-farm-proxy-guide.md` — Sổ tay vận hành MikroTik RouterOS & Sing-box Mixed Inbound Proxy (port 20001..20080) và quy tắc báo cáo lỗi cho Admin.
- `references/network-level-pbr-and-transparent-proxy-gateway.md` — Kiến trúc định tuyến Policy-Based Routing (PBR) & Transparent Proxy Gateway trên RouterOS / MikroTik / Mini PC thay thế gán proxy trên S7.
- `references/mobiproxy-web-ops-and-auth-troubleshooting.md` — MobiProxy Web UI (test.taadaa.click), xử lý lỗi 407 Proxy Authentication Required và quy trình chuẩn hóa `host:port`.
- `references/proxy-upstream-death-and-live-ip-gate-20260820.md` — Lỗ hổng Proxy sập nhưng `tun0 UP` ảo + TikTok fallback Direct IP leak & cơ chế xác thực Live IP (`GET_IP` broadcast != Direct IP).
- `references/9router-antigravity-and-mobiproxy-sync.md` — Chi tiết quy trình xử lý khi Box MobiProxy đổi IP WAN / sập mạng & tự động phục hồi Proxy Pools trên 9Router.
- `references/proxy-special-chars-url-encoding.md` — Chuẩn hóa URL encode/unquote idempotent cho proxy có ký tự đặc biệt (`#`, `@`, `!`, `:`) tránh lỗi 407 và fragment cắt cụt URL.
- `references/samsung-s7-global-proxy-subnet-and-toybox-nc-probing.md` — Quy trình gán global http_proxy + captive portal mode 0, xử lý lỗi lệch subnet kibe 1 (192.168.10.x) / kibe 2 (192.168.110.x), và kỹ thuật test live egress IP qua toybox nc trên Samsung S7.
- `references/two-step-proxy-attachment-and-lock-handling-20260903.md` — Quy trình 2 bước gán proxy (ADB global → ViChanger VPN) + xử lý Device Lock conflict khi job TikTok khác đang chạy.
- `references/vichanger-cleanup-plan-20260903.md` — **PLAN: Xoá ViChanger hoàn toàn khỏi toàn bộ codebase**, chỉ giữ Singbox/MikroTik transparent proxy. Files to delete/rewrite, verification method, current status.

