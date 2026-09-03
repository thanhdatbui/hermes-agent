# Phase 4 block-validation hardening — ĐÃ IMPLEMENT cốt lõi (commit fc61be9, 2026-08-11)

Phần NIT A core của Phase 4 (findings audit: block metadata splice + thứ tự entry_ids)
đã implement ở `python_runner/hermes_cron/manifest.py::_validate_block_structure` +
2 test adversarial trong `python_runner/tests/test_hermes_cron_fleet.py`. Suite 6 file =
**137 passed** (135 baseline + 2 mới). Commit `fc61be9` — "fix(cron): khoa block metadata
splice va thu tu entry_ids canonical" — chỉ gồm manifest.py + test_hermes_cron_fleet.py.
Workflow RED→GREEN + ad-hoc verify: skill `concurrent-workspace-safety` (probe fidelity).

## Contract đã đóng (fail-closed, giữ legacy `blocks == []` return)

Per-block (pass 1):
- Key set chính xác 12 keys; `block_id` regex `block-v1-[0-9a-f]{32}` + unique + khớp
  `manifest.block_id_for(day, block_index, machine, account)` (wrapper của blocks.py).
- `day` parse ISO + `== payload["day"]`; `block_index` int ∈ {1,2,3} (KHÔNG bool);
  `machine` int ≥ 1 (không bool); `serial` str non-empty không space; `account` str;
  `lane` ∈ {A,B} và == `lane_for_day(day)` (check NÀY unconditional — an toàn vì r10
  giữ lane A ngày chẵn).
- `pair_gap_minutes` int ∈ {60,75,90}; `require_row(account_row)`;
  `session_slots` == `[list(s) for s in build_block_sessions(day, index, gap)]` (canonical).
- `seed` int và == `machine_day_seed(day, machine, payload["seed"])` — **CHỈ khi `source`
  không None** (xem quyết định bên dưới).
- Source binding: `source.account(account)` tồn tại + `(account_row, machine, serial)` khớp
  row → `MAPPING_CONFLICT`.

Entries (pass 2): mọi entry `block_id ∈ by_id`, `session_index ∈ {1,2}`.

Per-block (pass 3):
- Đúng 2 entry, `session_index` chính xác `[1, 2]` (sorted theo session_index).
- `account`/`account_row`/`machine`/`serial` của block == CẢ HAI entry.
- `session_slots` == `[[e["slot_time"], e["slot_end"]] ...]` theo (s1, s2).
- `entry_ids` == `[entry_id_for(manifest_id, e["account"], e["machine"], e["serial"],
  e["account_row"], e["slot_time"], e["action_type"], payload["seed"], e["block_id"],
  e["session_index"]) for e in (s1, s2)]` — **EXACT ORDER, không so set**. Reversed
  entry_ids (cùng tập) → `MANIFEST_IDENTITY_MISMATCH`.

Error codes: `SOURCE_CONFIG_INVALID` (schema/types/canonical slots/seed/lane),
`MANIFEST_IDENTITY_MISMATCH` (block_id formula, metadata vs entries, entry_ids order),
`MAPPING_CONFLICT` (source row mismatch, shape machine/serial/account/lane).

## Quyết định thiết kế (đừng đảo ngược)

1. **`payload["seed"]` chứ không phải `e["seed"]`** trong expected_ids — entry KHÔNG có
   key seed (plan v2 warning #1 đã xử lý; đừng áp lại).
2. **Seed check source-gated**: `validate_manifest(forged, None)` PHẢI accept manifest
   machine-999 self-consistent của `test_r10_watcher_cli_requires_source_config_for_self_consistent_machine_999_manifest`
   (forge đổi machine 999 nhưng KHÔNG cập nhật block seed). Nếu check
   `machine_day_seed` unconditional → test đó fail. Chỉ bind seed khi có source.
3. **session_slots bind 2 chiều**: vừa canonical `build_block_sessions`, vừa == slot thật
   của entries — đóng lỗ hổng "đổi slots nhưng giữ session_slots" và ngược lại.
4. `block["day"] == payload["day"]` bắt buộc — picker luôn sinh block day == manifest day
   (kể cả block 3 cross-midnight, session_slots vẫn tính theo day của manifest).

## CHƯA implement từ plan Step 4.3 (nếu cần Phase 4 đầy đủ)

- `machine_blocks` == 3 block/máy; `account_blocks` == 1 block/account (aggregation
  theo machine) — hiện chỉ có account-reuse-trong-cùng-block ở `validate_manifest`
  entries loop.
- MINOR-4: entry block khác chen trong khoảng S1_end → S2_start của block đang xét.
- Inter-block gap ≥ 180 theo block_index.
- Test entry-thứ-7 re-hash id hợp lệ (đi qua `_validate_entry`, reject block-level).

## Adversarial tests (test_hermes_cron_fleet.py)

- `test_validation_rejects_block_metadata_splice_against_source_config` — đổi
  account/machine/serial/account_row/day/lane/seed của block 0, rehash block_id + entry
  ids + idempotency_key + rebuild entry_ids → phải ValueError. Bị chặn ở NHIỀU lớp:
  day ≠ payload day, session_slots ≠ canonical, seed ≠ machine_day_seed, source row
  mismatch, metadata vs entries mismatch.
- `test_validation_rejects_reversed_block_entry_ids` — `list(reversed(...))` cùng tập →
  ValueError.

RED: 2 failed ("DID NOT RAISE"). GREEN: 3 passed (2 mới + canonical picker). Full suite:
137 passed, py_compile OK, git diff --check OK.

## Probe-fidelity incidents trong phiên này (chi tiết: concurrent-workspace-safety/references/probe-fidelity.md)

- Fixture feed-state thừa key `unreserved_reservation` → mọi state invalid → picker skip
  lane → 0 blocks → probe 1 pass giả (legacy path), probe 2 IndexError. Fix: assert
  `len(blocks) == 3` trước khi probe.
- Forge source-less recompute `assignment_id` thiếu skipped accounts trong `account_ids`
  (coverage set = entries ∪ skipped) → MANIFEST_IDENTITY_MISMATCH trong khi r10 test
  canonical pass → probe sai, không phải product. Fix: `account_ids = sorted(entries
  accounts | skipped account_ids)`.