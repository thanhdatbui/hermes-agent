# Preflight Lock + VPN Gates Rollout (21/08/2026)

User rule: "Khi t yêu cầu lock r thì k đc tiến trình nào can thiệp nữa. Chỉ báo cáo là k khởi chạy đc vì lock" + "Cả yêu cầu vpn thông ms đc chạy ... làm ở all script đi".

## Canonical 2-gate preflight block (chèn đầu entrypoint đụng máy, sau khi có serial/device_id)

```python
# 1) Device Lock Gate: user-authorized lock active -> BLOCK, báo rõ, không can thiệp.
try:
    acquire_device_lock(
        machine=<machine>, serial=<serial>,
        project="<repo>", user_authorized=False,
    )
except DeviceLockNeedsUserDecision as exc:
    print(f"BLOCKED: [device-lock] máy {<machine>} ({<serial>}) đang được "
          f"User khóa bởi {exc.owner.get('project', '?')} (pid "
          f"{exc.owner.get('pid', '?')}) — safe-skip, KHÔNG can thiệp.", file=sys.stderr)
    return 2  # hoặc status blocked tương ứng
# 2) VPN Gate (fail-closed): máy mapped bắt buộc VPN live-ip OK.
from automation_core.preflight import (
    require_android_vpn, resolve_proxy_mapping_path,
    serial_is_mapped_in_workbook,
)
from automation_core.adb import AdbClient
mapping = resolve_proxy_mapping_path()
required = serial_is_mapped_in_workbook(
    mapping, <serial>, serial_headers=("phoneId", "deviceId", "serial"))
require_android_vpn(AdbClient(adb_path=<adb_path>, serial=<serial>), required=required)
```

Lưu ý: `verify_live_ip=True` là default của `require_android_vpn` — không cần truyền tay. Máy cột proxy trống → `required=False` tự bypass (đúng rule VPN gate).

## Audit lệnh chuẩn (chạy trong D:\Taadaa hoặc từng repo)

- Lock gate: `git grep -lE 'acquire_device_lock|DeviceLockNeedsUserDecision' -- '*.py' ':!runs/**'`
- VPN gate: `git grep -lE 'require_vichanger_connected|require_android_vpn|check_android_vpn|verify_live_ip|vpn_preflight' -- '*.py' ':!runs/**'`
- Không dùng `grep -R` thường trên toàn root `/d/Taadaa` — kẹt hàng giờ do scan `.ai-runs/`, `build/`, venv, runtime (đã dính 20/08: 2 process grep treo). Luôn `git grep` hoặc giới hạn đường dẫn.

## Bảng trạng thái repo sau rollout 21/08

| Repo | Lock gate | VPN gate | Ghi chú |
|---|---|---|---|
| automation-core | ✅ core (default user_authorized=True — gọi thiếu tham số vẫn tự tạo lock, coi chừng) | ✅ check_android_vpn/require_android_vpn verify_live_ip=True | thêm `check_device_lock_preflight()` read-only |
| tiktok-luot nuoi acc | ✅ run_tiktok + feed session | ✅ require_vichanger_connected | bản mẫu chuẩn |
| tiktok-follow | ✅ (MỚI thêm run_follow.py) | ✅ (MỚI) | trước đó 0 gate trong source! |
| tiktok-log-in | ✅ executor + các entrypoint | ✅ MỚI thêm: account_inventory, password_change, collect_apk_evidence (reconcile/cli có sẵn) | |
| tiktok-add-bao-mat-f2a | ✅ | ✅ MỚI thêm phase_a/phase_b/pilot (run_batch_live_2fa có sẵn) | |
| Tiktok_Reg | ✅ (user_authorized=False đa số) | ⚠️ MỚI thêm tiktok_login_v1/live_login/live_reg; **CÒN THIẾU**: calibrate.py, gmail_machine_audit.py, _run_all_targets.py, scripts/run_social_batch_deferred.py | 16 test fail pre-existing (stash-verified) |
| Tiktok-video | ✅ run_post/state_machine | ✅ | |
| register gmail | ✅ gmail_reg_v10 | ✅ (guarded_device_reboot có verify_vpn) | |
| add mail khoi phuc | ✅ run_add_recovery + recovery_scheduler SKIPPED_LOCKED | ✅ require_vichanger_preflight | |
| gan-proxy | ✅ (DeviceLock + fleet takeover) | n/a (nhà cung cấp VPN) | 77 tests pass |

## Pitfalls đã trả giá 21/08

1. **Patch fuzzy vào file 800+ dòng nhiều lần → HỎNG INDENT** (`account_inventory.py`, `password_change.py` dính `IndentationError` chồng nhau; patch tool ăn nhầm context, thậm chí chèn thụt lề sai). Cách đúng:
   - `git checkout -- <file>` để về sạch
   - chèn 1 lần bằng python script với anchor độc nhất (`assert anchor in t`) hoặc 1 patch duy nhất
   - `python -m py_compile <file>` sau mỗi bước
   - Nếu file đã hỏng giữa chừng: viết lại nguyên function bằng script (`t[:start]+new_fn+t[end:]`) thay vì patch từng dòng.
2. **Biến trùng tên**: gate dùng `mapping`/`adb` tràn ra `main()` đè `mapping` đang xài (test CLI fail: `'WindowsPath' object has no attribute 'get_by_machine'`). Đặt `preflight_mapping`/`preflight_adb`.
3. **Pre-existing test fail**: sau khi sửa code, `git stash push -- <files>` + chạy lại test → nếu fail y hệt thì là fail có sẵn trên HEAD, không phải do mình; chỉ sửa expectation khi khớp chuẩn hiện hành. Ví dụ: `test_follow_engine` assert `clock.value == 90.0` trong khi farm đã nâng `feed_timeout_seconds=900` (15 phút) → cập nhật 90→900, `recovery_started_at 70→70` giữ nguyên (b1 vẫn ở giây 70), v.v.
4. **Cron no_agent script path**: job khai báo tên file tương đối; file PHẢI nằm `~/AppData/Local/hermes/scripts/`. Đặt ở `~/.hermes/scripts/` → "Script not found: C:\Users\Kibe\AppData\Local\hermes\scripts\<file>" lúc execute.
5. **Watchdog phải báo khi CÓ lock** (dù < threshold), không chỉ khi quá hạn — user: "Thấy sai sai r đó" (máy đang lock phải được nhắc mỗi chu kỳ; threshold = nhãn ⚠️).