# Post-reboot proxy restore khi consumer giữ goal lock

## Circular-wait pattern

Một consumer có thể cố ý giữ machine+serial lock xuyên goal. Nếu nó reboot thiết bị rồi chỉ chờ proxy watcher, hệ thống deadlock logic:
- consumer giữ lock và chờ VPN;
- watcher cần lock để gọi Vi Changer;
- reboot đã xóa `tun0`, nên live verifier không thể cứu;
- consumer timeout, watcher miss event hoặc ghi lock timeout.

## Contract

- Không nhả lock giữa goal chỉ để watcher chen vào.
- Consumer dùng core reboot API có callback post-reboot.
- Callback gọi provider proxy dưới quyền sở hữu parent lock hiện tại.
- Provider xác minh machine+serial lock cùng khớp host, PID, lock ID, machine và serial trước side effect.
- Mapping/proxy ở provider layer; proxy chỉ sống trong memory, không CLI/log/artifact.
- Gọi primitive `set_proxy`/`START_VPN` hiện có và verify cả `tun0 UP` lẫn Android VPN `CONNECTED/VALIDATED`.
- Nếu ownership/mapping/proof sai, fail closed và giữ recovery artifact.

## Phân biệt hai failure class

1. Marker stale nhưng VPN live khỏe: truyền `live_vpn_verifier` cho readiness gate.
2. Reboot làm mất VPN thật: bắt buộc restore callback; chỉ thêm live verifier là fix chưa đầy đủ.

## Completion

Một dòng runner `DONE` hoặc provider broadcast thành công chưa đủ. Proof phải ghi target đúng machine+serial và `vpn_connected=true`; consumer sau đó phải chạy verifier post-reboot trước khi tiếp tục app workflow.
