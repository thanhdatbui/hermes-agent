# Reconcile dưới retained lock và TikTok 46.x

## 1. Tránh deadlock proxy sau reboot

Failure class:

- Reconcile giữ machine+serial lock xuyên inventory → reboot → login → verify.
- Reboot làm mất `tun0`.
- Watcher cần cùng lock để gọi Vi Changer, còn reconcile giữ lock và chờ readiness marker.
- Kết quả là vòng chờ tới timeout.

Contract đúng:

1. Parent reconcile giữ lock toàn goal; không nhả lock cho watcher giữa flow.
2. Dùng `automation_core.device_recovery.reboot_and_restore`, không dùng API chỉ chờ watcher nếu parent phải tự phục hồi proxy.
3. `wait_for_proxy_ready_after_reboot` gọi provider mỏng của proxy project.
4. Provider phải xác minh cả machine/serial lock khớp parent PID, host, machine, serial và lock ID trước khi đọc mapping/call `START_VPN`.
5. Proxy chỉ sống trong memory; không in command line/log/artifact.
6. Verify cả `tun0` UP và Android VPN `CONNECTED/VALIDATED` trước khi tiếp tục.
7. Parent callback `verify_post_reboot` kiểm tra live VPN lại.

### Readiness verifier propagation

Khi `acquire_device_lock(..., live_vpn_verifier=fn)`, core phải truyền chính callback vào `wait_for_proxy_ready(..., live_vpn_verifier=fn)`. Nếu bỏ propagation, marker `proxy_pending` timeout trước khi callback được gọi. Probe chẩn đoán: đếm callback calls; `calls=[]` chứng minh lỗi propagation.

Sau core fix:

- Bump version từ version hiện tại, không đoán số cũ.
- Chạy test với `PYTHONPATH=src` trong isolated core worktree để không import nhầm wheel/venv.
- Full core suite → clean wheel → verify filename/METADATA → install runtime giữa các automation run → verify `importlib.metadata.version` và live lock probe.
- Dùng `tools/core_merge_guard.py` acquire/release quanh integration.

## 2. Profile-to-switcher handoff

Core `open_switcher` hỗ trợ `pre_confirmed_xml` để tránh re-dump/re-navigation làm rơi từ Profile về feed.

Consumer bridge phải làm:

```python
profile_xml = open_profile_root(adapter, attempts=1)
return open_switcher(
    adapter,
    attempts=...,
    load_attempts=...,
    pre_confirmed_xml=profile_xml,
)
```

Không bỏ kết quả `profile_xml` rồi gọi `open_switcher()` trống. Regression test phải assert exact argument handoff.

## 3. TikTok 46.2.x profile anchor

Trên build 46.2.3 / override 1080x1920:

- Bottom Profile semantic node: content-desc `Hồ sơ`, center xấp xỉ `(972,1857)`.
- Account-switcher anchor là clickable profile-name button/resource suffix `sai`, bounds đã thấy `[36,249][375,330]`.
- Add Friends/person-plus nằm vùng khác ở top-right; tuyệt đối không chọn nó.
- Guided tap vào name/chevron mở sheet `Chuyển đổi tài khoản`.

Nếu `find_switcher_anchor()` trả `None` trên XML thật:

1. Chạy resolver trực tiếp trên XML artifact.
2. Inspect node + parent bounds/resource/class.
3. Viết regression RED trong isolated automation-core worktree.
4. Thêm semantic resource rule hẹp; giữ header-region constraints để loại Add Friends.
5. Test bằng `PYTHONPATH=src`, build/install wheel, rồi verify resolver trên chính XML thật.

## 4. UI layers trước inventory

Mỗi action phải recapture.

- Feed tutorial `Vuốt lên để xem thêm`: một swipe up rồi recapture; tap Profile trước khi dismiss có thể không tác dụng.
- Android `GrantPermissionsActivity`: dùng core `packageinstaller_permission` detector, chọn semantic deny button (`Từ chối`); không hardcode tọa độ production.
- Google re-login sheet: đóng lớp trên cùng trước, recapture; sau đó mới xử lý loading/TikTok modal.
- Save-login-info popup: policy login consumer chọn `Để sau`/`Not now`, nhưng chỉ khi XML có marker rõ `Lưu thông tin đăng nhập`/`Save login info`; không tap generic `Để sau`.
- Logged-out Profile: yêu cầu đồng thời `Hồ sơ` + `Đăng nhập vào tài khoản hiện có` + CTA `Đăng nhập`. Khi đủ marker, inventory là tập rỗng để reconcile login expected IDs; đừng coi thiếu switcher là navigation failure.

## 5. Direct diagnosis khi summary quá generic

Nếu summary chỉ ghi `account switcher navigation failed`:

- Không rerun batch.
- Takeover retained lock sau khi chứng minh owner PID chết.
- Capture before screenshot/XML/foreground.
- Gọi trực tiếp `tap_profile()` hoặc `open_account_switcher()` dưới external watchdog.
- Ghi exact action coordinates và exact exception/core error.
- Nếu helper timeout, xác minh toàn process tree chết; đọc artifact cuối. Một failure XML có thể đã được ghi trước khi recapture tiếp theo treo.
- Chỉ đưa fix vào code sau khi guided action thực tế đã chứng minh transition.
