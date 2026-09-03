# Reconcile dưới parent lock và guided UI recovery

## Post-reboot VPN deadlock

Failure class:

1. Reconcile giữ machine+serial lock xuyên inventory → reboot → login → verify.
2. Reboot làm mất `tun0`.
3. Proxy watcher cần cùng lock để gọi Vi Changer `START_VPN`.
4. Reconcile vẫn giữ lock và chỉ chờ readiness marker/VPN.
5. Hai phía chờ nhau đến timeout.

Live VPN verifier chỉ giải quyết marker stale khi VPN thực tế còn `CONNECTED/VALIDATED`; nó không phục hồi VPN đã mất.

### Thiết kế đúng

- Parent reconcile không nhả lock cho watcher giữa goal.
- Dùng `automation_core.device_recovery.reboot_and_restore()` với callback `wait_for_proxy_ready_after_reboot`.
- Callback gọi provider mỏng của proxy consumer để phục hồi VPN dưới chính parent lock.
- Provider phải xác minh cả machine và serial lock khớp `host + parent PID + lock_id + machine + serial` trước khi đọc mapping hoặc gọi `START_VPN`.
- Proxy chỉ tồn tại trong memory; không đưa proxy lên command line, stdout, artifact hoặc chat.
- Sau `START_VPN`, verify cả `tun0` UP và Android VPN `CONNECTED/VALIDATED`; chỉ sau đó mới tiếp tục inventory/login.
- Parent-lock mismatch, mapping không unique, provider timeout hoặc VPN proof thiếu đều fail closed.

Không thêm API core mới nếu `reboot_and_restore` đã có callback phù hợp. Shared core giữ callback app-neutral; mapping/Vi Changer policy nằm ở consumer/provider.

## Guided recovery khi XML/UI worker thất bại

Worker failure là detection pass. Giữ/takeover retained lock sau khi chứng minh owner PID cùng host đã chết, rồi mỗi vòng:

1. Capture screenshot, bounded XML, foreground và VPN proof.
2. Phân loại topmost UI thật.
3. Thực hiện đúng một semantic action; coordinate chỉ khi screenshot/build/resolution có proof.
4. Recapture trước action tiếp theo.
5. Sau khi behavior thực tế qua, đưa handler vào code + regression test + `docs/ui-compatibility.md`.

### TikTok 46.x / 1080x1920 patterns đã chứng minh

- Feed tutorial `Vuốt lên để xem thêm` chặn bottom navigation: vuốt lên một lần, recapture, rồi tap Profile bottom-right.
- Android `GrantPermissionsActivity`: dùng core benign-popup detector `packageinstaller_permission`, chọn semantic deny button; không hardcode coordinate production.
- Google re-login sheet và loading overlay có thể xếp lớp: đóng lớp trên cùng trước, recapture từng lớp.
- Profile logged-out: cần đủ markers `Hồ sơ/Profile` + `Đăng nhập vào tài khoản hiện có` + login CTA. Khi đủ, inventory trả account set rỗng thay vì coi thiếu account-switcher là navigation failure.
- Save-login-info modal có thể làm `tap_profile` thành công về mặt hình ảnh nhưng verifier fail. Với policy consumer chọn `Để sau/Not now`, chỉ tap khi có marker explicit `Lưu thông tin đăng nhập/Save login info`; generic `Để sau` không đủ bằng chứng.
- Sau khi dismiss save-login popup, recapture và retry Profile đúng một lần.

## Retained-lock handoff

Guided helpers thường kết thúc process nhưng để lock `recovery`. Trước khi chạy lại worker:

- xác minh owner PID thật trong lock đã chết (không suy từ wrapper PID);
- recapture state cuối;
- takeover bằng public lock API;
- release có audit với lý do chuyển state sang reconcile runner;
- không để worker tiếp theo chỉ trả `SKIPPED_LOCKED` vì lock của chính guided recovery.

`DONE: result=...` hoặc exit code 4 chỉ là artifact completion. Luôn đọc per-target outcome và `login_attempts` trước khi kết luận tiến độ.