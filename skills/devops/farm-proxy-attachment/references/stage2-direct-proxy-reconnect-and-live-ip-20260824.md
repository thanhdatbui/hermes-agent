# Stage-2 Direct Proxy Reconnect Fallback & Live IP Verification (2026-08-24)

## 1. Bối cảnh & Nguyên nhân lỗi Proxy rớt
Trên farm Android (Samsung Galaxy S7), thiết bị sau khi reboot hoặc khi bị hệ điều hành tối ưu RAM ngầm có thể gặp tình trạng:
- Tiến trình `vn.vichanger.app` bị dừng ngầm.
- Card mạng ảo `tun0` bị sập (mất kết nối VPN), thiết bị tự động fallback về mạng Wi-Fi thường.
- Nếu tool tự động chỉ kiểm tra `tun0 UP` mà không kiểm tra `verify_live_ip=True` qua broadcast `vn.vichanger.app.GET_IP`, lưu lượng mạng sẽ bị lọt trực tiếp (Direct IP Leak), gây lộ IP farm và dẫn đến TikTok shadow-ban / nhả follow hàng loạt.

## 2. Kiến trúc Phục hồi Proxy 4 Lớp tại Tầng Core (`automation-core`)
Vị trí thực thi: `automation_core.device_recovery::recover_missing_android_vpn`.

### Luồng xử lý:
1. **Lớp 1 — Preflight Check nhanh (`check_android_vpn`):**
   - Kiểm tra `tun0 UP` + Broadcast `vn.vichanger.app.GET_IP` lấy IP proxy thật.
   - Nếu PASS (`result=200` và có IP proxy hợp lệ) -> Cho phép chạy ngay (không mất thời gian).
   - Nếu FAIL -> Kích hoạt `recover_missing_android_vpn`.

2. **Lớp 2 — Chờ GanProxy Watcher (Stage 1):**
   - Đánh dấu `mark_proxy_state(target, "proxy_pending")`.
   - Gọi `wait_for_proxy_ready(timeout=60.0)` nhường quyền ưu tiên cho tiến trình giám sát nền `gan_proxy_fleet.py watch` tự động gán lại proxy.
   - Nếu watcher xử lý thành công -> `VERIFIED_SUCCESS` và tiếp tục.

3. **Lớp 3 — Direct Proxy Reconnect Fallback (Stage 2 — MỚI):**
   - Nằm ngay sau khi hết 60s chờ Watcher và trước khi thực hiện Soft-Reboot.
   - Đọc mapping thiết bị từ `resolve_proxy_mapping_path()` (`PROXYgandienthoai.xlsx`).
   - Gọi trực tiếp `vi_changer_runner.set_proxy(adb_path, serial, proxy_str, timeout=30)` để mở lại ViChanger và bắn intent kết nối proxy tại chỗ.
   - **Bắt buộc verify:** Gọi lại `live_vpn_verifier(target)` (`verify_live_ip=True`).
   - Nếu có IP -> Trả về `VERIFIED_SUCCESS` (cứu được phiên làm việc trong 3–5 giây, không cần mất 3–5 phút để Reboot máy).

4. **Lớp 4 — Soft-Reboot Fallback & Final Blocked (Stage 3 & 4):**
   - Nếu Direct Reconnect vẫn thất bại (do proxy nhà mạng chết thật hoặc ViChanger trên máy không lên được `tun0`): Thực hiện soft-reboot 1 lần duy nhất (`soft_reboot_and_wait`).
   - Sau reboot, nếu Watcher daemon `gan_proxy_fleet.py watch` không chạy ngầm trên host để gán lại proxy, `wait_for_proxy_ready` sẽ hết thời gian chờ -> Bắn ngoại lệ `MissingVpnRecoveryError (TimeoutError: proxy readiness timed out)` và chuyển lock sang `blocked` (giữ hiện trường TTL 2h), tuyệt đối không mở TikTok.
   - **Lưu ý bẫy GET_IP khi `tun0` DOWN**: Khi ViChanger chưa kết nối hoặc `tun0` chưa lên, lệnh broadcast `GET_IP` vẫn có thể trả về `result=200` mang chính Direct Wi-Fi IP của host farm (`42.116.228.253`). Do đó `verify_live_ip` bắt buộc phải kiểm tra `tun0 UP` và đối chiếu loại trừ Direct Host IP.
