# Reconcile giữ lock: phục hồi proxy sau reboot và Profile logged-out

## Failure class: lock/VPN circular wait

Dấu hiệu:
- Reconcile giữ machine+serial lock xuyên inventory → reboot → login → verify.
- Reboot làm mất `tun0`.
- Reconcile chờ readiness/watcher; watcher cần chính lock đang bị reconcile giữ.
- Outcome thường `recovery`, `login_attempts=[]`, reason là post-reboot proxy readiness timeout.

## Thiết kế đúng

Không nhả goal lock cho watcher và không blind-rerun.

1. Consumer dùng `automation_core.device_recovery.reboot_and_restore`, không dùng helper chỉ đánh dấu pending rồi chờ watcher.
2. `wait_for_proxy_ready_after_reboot` gọi provider proxy mỏng trong khi parent reconcile vẫn sở hữu lock.
3. Provider phải fail-closed nếu cả machine/serial lock không cùng khớp: host, parent PID, lock ID, machine, serial.
4. Provider đọc mapping đúng machine+serial trong memory, không in proxy, gọi primitive Vi Changer `START_VPN` hiện có.
5. Chỉ trả về sau proof `tun0 UP` và Android VPN `CONNECTED/VALIDATED`.
6. `verify_post_reboot` kiểm tra VPN live lần nữa trước inventory/login.

`live_vpn_verifier` chỉ giải quyết marker readiness thiếu/stale khi VPN thực tế còn khỏe; nó không thay thế restore callback khi reboot đã làm mất `tun0`.

## Guided recovery khi XML hỏng

XML non-XML không phải blocker nếu screenshot khỏe:
- Capture foreground + screenshot + bounded XML + VPN proof dưới recovery lock.
- Một action mỗi vòng, recapture sau action.
- TikTok 46.x / override 1080x1920: tutorial `Vuốt lên để xem thêm` có thể chặn bottom nav; swipe lên một lần rồi mới tap Profile `(973,1855)`.
- Nếu Google re-login sheet → loading overlay → TikTok login modal xếp chồng, đóng lớp trên cùng từng bước và recapture; không tap xuyên lớp.

## Profile logged-out

Signature semantic phải đủ:
- `Hồ sơ` / `Profile`;
- `Đăng nhập vào tài khoản hiện có` / tương đương tiếng Anh;
- CTA `Đăng nhập` / `Log in`.

Khi đủ signature và không có sticky username/switcher anchor, inventory phải trả account set rỗng. Reconcile sẽ coi toàn bộ expected IDs là device-missing và đi vào login flow. Không coi đây là account-switcher navigation failure để reboot lặp.

## Android permission dialog

`GrantPermissionsActivity` có thể che TikTok và làm navigation fail. Dùng detector automation-core `packageinstaller_permission`; action là semantic `dismiss_deny_button`. Trên evidence S7/1080x1920, node deny ở khoảng `(557,1134)`, nhưng production phải tap theo bounds XML, không hardcode tọa độ. Recapture foreground TikTok sau deny.

## Lock handoff giữa guided recovery và runner

Guided helper thường giữ retained `recovery` lock khi kết thúc. Trước khi chạy runner:
1. Xác minh owner PID cùng host đã chết.
2. Takeover bằng public lock API, không xóa file thủ công.
3. Recapture/verifier xác nhận state cần chuyển giao.
4. Release bằng audit có lý do rõ ràng.
5. Sau đó mới chạy runner; nếu không, outcome chỉ là `SKIPPED_LOCKED`, không phải failure TikTok.
