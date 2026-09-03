# Khôi phục proxy sau reboot khi consumer giữ parent lock

## Phân biệt hai failure class

### Marker stale nhưng VPN còn sống

- `tun0` UP.
- Android connectivity có VPN `CONNECTED/VALIDATED`.
- Readiness marker thiếu/stale.

Handler: truyền scoped `live_vpn_verifier` vào lock/readiness gate. Không chạy lại Vi Changer nếu proof live đã đủ.

### VPN thực sự mất sau reboot

- Boot complete và device online/unlocked.
- `tun0` không tồn tại hoặc Android không có VPN agent.
- Watcher có thể miss reconnect vì parent consumer giữ machine+serial lock.

`live_vpn_verifier` không thể sửa class này. Chờ watcher trong khi vẫn giữ lock tạo lock cycle.

## Contract không deadlock

Khi consumer phải giữ lock toàn goal:

1. Dùng `reboot_and_restore`, không dùng helper chỉ đánh dấu pending rồi chờ watcher.
2. Truyền callback app-neutral `wait_for_proxy_ready_after_reboot`.
3. Callback gọi provider proxy mỏng dưới parent lock hiện hữu.
4. Provider xác minh cả hai lock khớp parent `host`, PID, `lock_id`, machine và serial.
5. Chỉ sau ownership proof mới load đúng mapping machine+serial trong memory và gọi primitive Vi Changer `START_VPN`.
6. Verify `tun0` UP và Android VPN `CONNECTED/VALIDATED`.
7. Không expose proxy qua argv/stdout/artifact.

Không để provider acquire lock lần hai. Provider là child action được parent lock ủy quyền có kiểm chứng, không phải watcher event độc lập.

## Safety/failure

- Parent PID phải lấy từ lock/lease thật, không dùng wrapper PID suy đoán.
- Parent-lock mismatch, mapping không unique, provider timeout hoặc VPN proof thiếu → fail closed và giữ recovery artifact.
- Nếu consumer không cần giữ lock xuyên reboot, watcher event lease vẫn là mô hình phù hợp; không áp dụng parent callback tràn lan.
- Trước khi rerun consumer sau guided recovery, release/takeover retained recovery lock có audit; nếu không, rerun chỉ tạo `SKIPPED_LOCKED` giả.

## Verification

- Unit test provider: matching parent ownership cho phép `set_proxy`; mismatch không gọi `set_proxy`.
- Consumer test: post-reboot callback được wire vào `reboot_and_restore` và verifier chạy sau restore.
- Live proof: reboot làm mất VPN → callback phục hồi → `tun0 + CONNECTED/VALIDATED` trước khi app workflow tiếp tục.
