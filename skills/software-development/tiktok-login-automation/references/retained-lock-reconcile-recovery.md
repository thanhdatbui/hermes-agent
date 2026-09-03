# Reconcile recovery khi giữ lock xuyên reboot/UI

## 1. Deadlock proxy sau reboot

Failure class:

- Reconcile giữ machine+serial lock xuyên inventory → reboot → login → verify.
- Reboot làm mất `tun0`.
- Proxy watcher cần cùng lock để gọi Vi Changer, nên không thể chạy.
- Reconcile chỉ chờ readiness marker và timeout.

Thiết kế đúng:

1. Parent reconcile tiếp tục giữ lock toàn goal.
2. Dùng `automation_core.device_recovery.reboot_and_restore()` với callback `wait_for_proxy_ready_after_reboot`.
3. Callback gọi provider proxy mỏng; provider phải xác minh cả machine/serial lock khớp parent `pid`, `host`, `machine`, `serial`, `lock_id` trước khi làm side effect.
4. Provider đọc mapping scoped trong memory, không in proxy, gọi primitive Vi Changer `START_VPN` hiện có.
5. Chỉ tiếp tục khi `tun0` UP và Android VPN là `CONNECTED/VALIDATED`.
6. Parent-lock mismatch, mapping không unique, timeout hoặc VPN verify fail phải fail closed.

Không nhả lock để watcher chen vào giữa goal. Không truyền proxy trên command line hoặc artifact.

## 2. Readiness marker và live verifier

Một marker `proxy_pending` stale không được chặn target khi VPN live đã khỏe. Khi gọi:

```python
acquire_device_lock(..., live_vpn_verifier=verifier)
```

phải kiểm tra rằng core truyền chính callback này vào `wait_for_proxy_ready(...)`. Regression probe tối thiểu:

- marker vẫn pending;
- verifier trả `True` từ proof `tun0 + CONNECTED/VALIDATED`;
- callback thực sự được gọi;
- lock acquire thành công.

Pitfall từng gặp: core nhận `live_vpn_verifier` nhưng gọi `wait_for_proxy_ready` không truyền callback; timeout xảy ra trước verifier (`calls=[]`). Test phải assert kwargs propagation, không mock wait bằng lambda bỏ qua kwargs.

## 3. UI recovery theo từng lớp

Khi worker báo Profile/switcher failure:

1. Takeover retained recovery lock chỉ sau khi chứng minh cùng host và owner PID chết.
2. Capture foreground + screenshot + bounded XML + VPN proof.
3. Mỗi vòng chỉ một action và recapture.
4. XML non-XML không phải FINAL_BLOCKED nếu screenshot khỏe.

Các lớp đã chứng minh trên TikTok 46.x / override 1080x1920:

- Feed tutorial `Vuốt lên để xem thêm`: swipe up một lần, recapture.
- Android `GrantPermissionsActivity`: dùng core detector `packageinstaller_permission`, chọn semantic deny; không hardcode production coordinate.
- Google re-login sheet: đóng lớp trên cùng trước, recapture rồi mới xử lý lớp sau.
- TikTok login modal che logged-out Profile: đóng modal, recapture để phân biệt logged-out thật.
- Save-login-info modal: policy consumer chọn semantic `Để sau`/`Not now`; chỉ tap khi có marker explicit `Lưu thông tin đăng nhập`/`Save login info`. Generic `Để sau` không đủ bằng chứng.

## 4. Logged-out Profile là inventory rỗng

Nếu Profile có đủ:

- `Hồ sơ`/`Profile`;
- `Đăng nhập vào tài khoản hiện có`/English equivalent;
- CTA `Đăng nhập`/`Log in`;

và không có identity/switcher anchor, inventory phải trả account set rỗng. Không biến trạng thái logged-out thành `account switcher navigation failed` rồi reboot lặp. Reconcile sẽ coi toàn bộ expected IDs là device-missing và đi vào login flow.

## 5. Shared switcher anchor regression

Nếu guided tap name/chevron mở switcher nhưng core `find_switcher_anchor()` trả `None`, đây là shared-core defect:

1. Lưu XML Profile trước tap và screenshot proof sau tap.
2. Chạy resolver trực tiếp trên XML thật để tạo RED repro.
3. Inspect node + parent bounds/resource/class; loại rõ Add Friends/person-plus.
4. Viết regression trong isolated automation-core worktree.
5. Acquire core merge guard, refresh master semantic, bump version, full core tests, build/verify wheel metadata, cài giữa các live runs, test consumer.

Ví dụ UI TikTok 46.2.3: clickable profile-name button resource suffix `sai` trong identity header mở switcher; Add Friends nằm vùng/resource khác. Rule core vẫn phải giữ header bounds và ambiguity gates, không biến thành coordinate fallback rộng.

## 6. Completion

`DONE` hoặc exit code của batch chỉ là artifact signal. Đọc outcome per-target. Chỉ hoàn tất khi login/inventory cuối được verify hoặc target đạt FINAL_BLOCKED sau đầy đủ guided recovery. Một `SKIPPED_LOCKED` do chính guided recovery để lại phải được audit/takeover/release có chủ đích rồi mới rerun target.