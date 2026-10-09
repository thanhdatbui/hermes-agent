# Combined workbook position and follow wiring

## Durable lessons

- A combined Kibe/Admin workbook is a positional mapping artifact, not merely a filtered active-ID list. Preserve physical/source account slots, including blank rows needed by `account_row_index`; compacting rows shifts later accounts to the wrong account.
- Keep machine IDs unchanged while combining. Deduplication must never change a machine's positional row mapping.
- Trace the follow runner's real CLI/config seam before wiring. If `--workbook` is unsupported, make the effective config point to the actual combined workbook; test the effective path for both Kibe and Admin.
- Mode 2 with no usable anchor and no `FOLLOW_FAILED` must fall back to Mode 1 with `mode="both"`. If the first cross-follow is released immediately (`cnt == 0`), natural follows are invalid. If at least one cross-follow succeeds and a later `FOLLOW_FAILED` occurs, natural follows remain valid.
- For bounded delegated tasks, reconnaissance is not completion. If the call budget ends before editing and focused verification, report exact findings and an explicit patch contract; do not imply the fix landed.

## Focused offline regression cases

1. Build temporary Kibe/Admin workbooks containing active rows separated by blank rows. Combine them and assert machine IDs and source row/account-slot indices remain aligned.
2. Exercise the follow command/config builder with both machine ranges and assert the effective workbook is the combined path, not `config.example.yaml`'s default.
3. Cover Mode 2 no-anchor fallback, immediate release (`cnt == 0`), and later `FOLLOW_FAILED` after a successful cross-follow.
