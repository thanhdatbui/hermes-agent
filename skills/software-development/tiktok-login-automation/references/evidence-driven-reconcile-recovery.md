# Evidence-driven recovery cho TikTok reconcile

## Failure class

Reconcile giữ central machine/serial lock xuyên inventory → reboot → login → verify. Sau reboot, proxy watcher có thể phát reconnect event nhưng bị `WATCH_EVENT_LOCK_TIMEOUT` vì reconcile vẫn là live owner. Nếu reconcile sau đó thoát với `recovery`, owner PID chết nhưng watcher cũ có thể không phát event mới; target ở launcher, đã unlock nhưng không còn `tun0`.

Dấu hiệu điển hình:

- Summary ghi `status=recovery`, `login_attempts=[]`.
- Reason là proxy/VPN readiness timeout sau reboot.
- Watcher telemetry có `WATCH_EVENT_DETECTED` rồi `WATCH_EVENT_LOCK_TIMEOUT` trùng thời gian reboot.
- Screenshot/UI XML cho thấy launcher/app drawer, không lockscreen hoặc popup.
- Lock JSON còn `recovery`, cùng host, PID owner đã chết.

## Recovery ladder

1. Không rerun reconcile ngay.
2. Thu riêng cho target: summary JSON, screenshot, UI XML, foreground, Android connectivity, watcher telemetry và sanitized lock metadata.
3. Xác minh target đã unlock và phân loại root cause là VPN recovery bị lock collision, không phải TikTok/login failure.
4. Chỉ takeover nếu central policy chứng minh đầy đủ: cùng host, trạng thái retained được phép và PID đã chết. Không xóa lock file thủ công.
5. Acquire recovery lease bằng public lock API với `allow_takeover=True` và `bypass_proxy_readiness=True`; bypass chỉ hợp lệ vì chính action này có nhiệm vụ phục hồi VPN.
6. Đọc đúng proxy theo cặp machine+serial từ mapping trong memory; không in proxy hoặc full workbook row.
7. Gọi runner ViChanger hiện có (`set_proxy`/`START_VPN`), không tái hiện flow bằng tap thủ công nếu runner đã có primitive.
8. Verify cả hai: `tun0` hiện diện/up và Android connectivity báo VPN `CONNECTED/VALIDATED`.
9. Finish/release recovery lease, recapture proof, xác minh machine+serial locks đã free.
10. Chỉ lúc đó rerun đúng target. Đây là meaningful attempt 2 vì điều kiện đã thay đổi; không phải blind retry.

## Marker stale nhưng VPN live vẫn hợp lệ

Failure này xảy ra **trước khi lease được acquire**: readiness marker thiếu/stale làm `wait_for_proxy_ready()` timeout, dù device proof cho thấy `tun0` UP và Android VPN `CONNECTED/VALIDATED`.

Recovery recipe:

1. Không gọi đây là TikTok failure và không rerun ngay.
2. Dùng bounded recovery lease với `bypass_proxy_readiness=True` để thu foreground, screenshot, XML và VPN proof; bypass không được truyền vào normal login run.
3. Nếu Vi Changer có `No LSPosed access !!!`, dùng XML để xác định modal exact `OK`; tap một lần rồi recapture. Nếu chỉ còn toast/snackbar và VPN live verified, không coi toast là blocker.
4. Nối consumer verifier vào normal gate:
   - `acquire_device_lock(..., live_vpn_verifier=...)`
   - `soft_reboot_and_wait(..., live_vpn_verifier=...)`
   - verifier gọi `check_android_vpn(adb, required=True).allowed`.
5. Bắt `RuntimeError`/`TimeoutError` ở pre-lease boundary và trả per-target recovery outcome, tránh exception thoát qua `future.result()` làm chết batch.
6. Verify bằng targeted test và một live verifier probe; release recovery lease có chủ đích; rerun riêng target là meaningful attempt 2.

## Nếu attempt 2 lỗi UI

Không giao Codex tự loop toàn flow. Dừng autonomous worker khi UI dump treo/non-XML, cùng signature lặp lại, helper loop hoặc không còn proof tiến triển. Kill toàn process tree (wrapper chết có thể để Python/ADB/UIAutomator orphan), rồi xác minh PID owner chết trước khi takeover lock.

Guided loop cho từng action:
1. Foreground + screenshot + bounded XML + VPN/lock proof.
2. Classify màn hình thật.
3. Một action semantic; coordinate chỉ khi có evidence đúng build/resolution.
4. Recapture và ghi state trước/action/state sau.
5. Không lặp action nếu evidence không đổi.

### XML hỏng nhưng screenshot còn khỏe

XML non-XML chỉ loại bỏ selector XML, không tự động cho phép `FINAL_BLOCKED`. Nếu screenshot, foreground và VPN vẫn tốt:
- Tìm coordinate flow đã được chứng minh cho đúng app build/resolution.
- Xác minh display override và dùng vision-derived bounds.
- Thực hiện một tap/swipe rồi recapture screenshot/foreground.
- Với TikTok 46.x/1080x1920, class flow đã chứng minh có thể dùng bottom-right Profile; account switcher mở từ sticky username/header, **không tap person-plus avatar**.
- Không tái sử dụng coordinate trên build/resolution khác nếu chưa có proof mới.

Chỉ sau khi hành vi thực tế đã qua mới dispatch Codex cập nhật script + regression test. `FINAL_BLOCKED` đòi hỏi cả handler instrumentation/XML phù hợp và screenshot-guided handler đã chứng minh (nếu tồn tại) đều cạn meaningful attempts.

## Completion proof

`DONE: result=...` chỉ cho biết artifact đã được ghi. Phải đọc outcome per-target. Thành công cần inventory/login/verification proof; `exit 4`, `recovery`, `FAILED`, hoặc `BLOCKED` sau detection pass đều chưa phải kết luận cuối.

### Exact account-set proof

- Candidate account IDs phải lấy từ safe workbook theo đúng machine+serial scope; credential workbook là nguồn khác và không được thay cho mapping.
- Vision/OCR chỉ là evidence hỗ trợ, không phải nguồn identity duy nhất. Crop và phóng lớn switcher; đối chiếu từng chuỗi với candidate list để tránh nhầm glyph.
- Nếu một ID vẫn mơ hồ, dưới central lock chọn đúng switcher row rồi recapture Profile username/handle; chỉ kết luận `exact_match=true` khi missing/extra thực sự bằng rỗng.

## Worktree commit guard

Trước mọi commit chạy trong đúng path target:

```bash
git worktree list --porcelain
git branch --show-current
git status --short --branch
```

Khi user nói “tree này”, không suy ra root repo/main từ đường dẫn artifact hoặc file vừa chỉnh. Stage file cụ thể. Nếu lỡ commit nhầm branch, cherry-pick semantic sang đúng worktree trước; sau đó phục hồi pointer branch nhầm bằng cách giữ nguyên untracked/dirty state, tránh destructive reset khi không cần.
