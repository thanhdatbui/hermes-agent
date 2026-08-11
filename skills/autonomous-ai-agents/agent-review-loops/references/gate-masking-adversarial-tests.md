# Gate-masking trong adversarial tests — recipe + timeline thật (2026-08-11, Phase 3 fleet scheduler)

## Định nghĩa
Test adversarial "passes" (đúng reason) nhưng reject ở gate SỚM hơn branch đang test → suite xanh nhưng test không chứng minh branch reachability. Khi production refactor, test vẫn xanh dù branch đích vỡ.

## 3 dấu hiệu
1. Mutation 1 field nhưng KHÔNG sync dependent fields → entry feed/lock check reject trước source/identity branch.
2. Test chỉ `pytest.raises(ValueError)` — không assert exact reason → không phân biệt được 2 branch cùng reason (vd cả feed-check lẫn source-mapping đều `MAPPING_CONFLICT`).
3. Mutate NHIỀU field cùng lúc → fail ở gate day/topology sớm (vd đổi luôn `day` → day-gate reject, không phải branch đang test).

## Dependent-field sync table
Mutate field → các field phải đồng bộ để payload đi qua các gate trước (entry feed/lock/identity) rồi reject ĐÚNG branch đích:

| Mutate | Sync bắt buộc | Ghi chú |
|---|---|---|
| `machine` | `feed.machines`, `lock.machine`, entry_id + idempotency rehash, block_id rehash, `block.seed` = machine_day_seed(day, machine_moi, payload_seed) | seed dính machine |
| `serial` | `lock.serial` (+ entry_id vì hash có serial) | |
| `account_row` | `feed.row`, entry_id rehash | block_id KHÔNG dùng account_row |
| `account` | block_id rehash, entry_ids, idempotency | giữ nguyên account_row để source.account(new).row ≠ row → reject source-mapping |
| `day` | block_id, session_slots, seed | dễ dính day-gate — tách test riêng assert canonical day gate |
| `seed` | (không có dependent) | reject unconditional kể cả source=None |

Trick account khác source-row khác, không trùng account block khác: `new_acct_idx = (orig_row % 6) + 1` — với fixture rows 1..6 luôn ≠ orig_row (1→2, 2→3, ..., 6→1). Kèm `assert new_acct_idx != orig_row` phòng thủ: nếu fixture đổi sau này, test fail RÕ thay vì pass sai branch.

## Probe xác nhận BRANCH (coordinator, sau khi worker reshape)
```python
import sys, tempfile, traceback
sys.path.insert(0, r"D:\Taadaa\tiktok-luot nuoi acc")
from python_runner.tests.test_hermes_cron_fleet import _pick, fleet_source, fleet_feed, fleet_post, _tamper, _rehash_block_identity
from python_runner.hermes_cron.manifest import validate_manifest
root = tempfile.mkdtemp()
for field in ("machine", "account", "account_row"):
    snap = _pick(fleet_source(), fleet_feed(), fleet_post(), root)
    payload = _tamper(snap.payload, lambda p: None)
    block = payload["blocks"][0]
    be = [e for e in payload["entries"] if e["block_id"] == block["block_id"]]
    # mutate đúng 1 field + sync dependent (theo bảng trên)
    _rehash_block_identity(payload, block, be)
    try:
        validate_manifest(payload, fleet_source()); print(f"{field}: NO REJECT - FAIL")
    except ValueError as ex:
        lines = [l.strip() for l in traceback.format_exc().splitlines() if "manifest.py" in l and "in " in l]
        print(f"{field}: reason={ex.args[0]} reject_line={lines[-1] if lines else '?'}")
```
Kỳ vọng: cả 3 in `reject_line=...manifest.py", line 434` (source-mapping) — đã xác nhận thật 2026-08-11.

## AG Claude audit trả MINOR hypothetical
AG Claude (qua 9router, không đọc được file) có thể trả MINOR dạng "nếu orig_row==0 thì new_acct_idx==orig_row" — false positive: fixture rows 1..6 nên (orig_row%6)+1 luôn khác. Đối chiếu code/probe trước khi dispatch fix; probe evidence + 1-2 dòng assert phòng thủ là đủ đóng MINOR (không cần vòng fix lớn). Re-audit AG trên commit nhỏ chỉ mất ~10s (sonnet-4-6).

## Timeline thật — Phase 3 manifest validation (4 vòng audit cùng class finding)
1. `ea2c76a` build → audit luna: REJECT (block metadata splice: đổi block.account + rehash block_id/entry_id vẫn ACCEPTED — validator chỉ check block tự nhất quán với entry, không bind SourceConfig; entry_ids dùng sorted() nên đảo thứ tự lọt).
2. `fc61be9` fix → re-audit luna: MINOR (source-less `validate_manifest(payload, None)` cho đổi block.seed vì seed check conditional `if source is not None`; test splice gate-masked vì mutate cả day).
3. `edcb71f` fix → re-audit luna: MINOR (3 mutation machine/account/account_row reject ở feed-mapping 411-412 thay vì source-mapping 434 — gate-mask).
4. `904ae86` Claude CLI reshape → AG Claude audit (sonnet): MINOR hypothetical (new_acct_idx) + NIT vô hiệu (feed không có field account).
5. `dd8db90` Claude CLI thêm assert phòng thủ → AG Claude: **APPROVED** (10.5s).

Bài học: gate-masking là CLASS finding, không phải 1 bug — khi audit nhiều vòng ra cùng class dù production đã đúng, đó là vấn đề test-quality: reshape tests (branch-confirmed) rồi re-audit; đừng sửa production để "làm test dễ".
