# Feed/reconcile target-identity binding

## Trigger
Use when a feed session times out during targeted login and falls back to machine-level account reconciliation.

## Proven pattern
A feed runner may select one workbook slot, while reconcile receives only a machine ID. Those are different scopes:

- Feed selection is slot/row scoped: machine + `account_row_index` → physical `source_row` → expected username.
- Reconcile inventory is machine scoped: machine + workbook → all account IDs assigned to that machine, deduplicated.
- Reconcile then selects credentials by exact ID from the login workbook.

If a machine has multiple assigned accounts, a fallback invocation that passes only `--machines N` can target a different username than the feed expected. A missing-credentials error for that second username is evidence of target-scope drift, not proof that the feed target lacks credentials.

## Investigation checklist
1. Read the fresh feed `log.jsonl` first. Capture the exact `expected_account`, `source_row`, `account_row_index`, fast-login command, timeout, fallback command, and reconcile return code.
2. Read the reconcile result JSON/summary and compare its failed account with the feed expected account.
3. Inspect the two relevant workbooks read-only. Record machine, physical row, account ID, and serial; never print passwords or OTPs.
4. Trace code separately:
   - feed workbook selector: machine filter, row-index selection, username extraction;
   - feed recovery launcher: whether expected username/source row is forwarded;
   - reconcile workbook loader: whether it aggregates all accounts for the machine;
   - reconcile missing-account selector: exact-ID credential lookup.
5. Prove the mismatch with a same-machine, different-row example. Do not substitute credentials or touch the device.

## Required conclusion format
State explicitly:
- `feed target`: username + physical source row + slot/index;
- `reconcile target`: username + how it was selected;
- `scope break`: the exact omitted identity fields/arguments;
- `confirmed`, `excluded`, and `unproven` findings;
- no-file-change/no-device-touch status when requested.

## Durable design rule
Fallback recovery must preserve the original target identity. Pass and enforce at least expected username plus physical source row or slot. If reconcile is intentionally machine-wide, it must reject ambiguous fallback calls when multiple accounts exist rather than silently selecting another account.

See this reference for the M40-style evidence pattern and the distinction between machine scope and workbook-row scope.
