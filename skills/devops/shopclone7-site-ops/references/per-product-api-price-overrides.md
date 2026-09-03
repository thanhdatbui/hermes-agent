# API_31 per-product fixed-price override

## Trigger
Use when a supplier must remain on automatic markup (`update_price=ON`) but a small allowlist of API products must keep fixed storefront prices.

## Verified pattern
- API_31 computes `price = api_price + api_price * discount / 100` when `update_price=ON`.
- A direct DB price edit is temporary; the next sync overwrites it.
- Identify products by live `api_id` and exact supplier identity. Local product IDs are for the narrow DB backfill, not the source mapping.
- Apply the fixed-price map after the normal formula in both the new-product insert path and the existing-product update path.
- Guard the map with the exact supplier ID; other suppliers and other API IDs must fall through unchanged.

## Safe implementation sequence
1. Read live supplier identity and target rows; record `api_id`, current price/cost/stock/status/category.
2. Create a failing RED test that asserts every `api_id -> price` mapping exists in both paths.
3. Add the smallest source patch; run the test GREEN, `git diff --check`, and PHP lint.
4. Backup the live sync file and target product rows before any live write.
5. Upload the patched file beside the live file as a temporary file; compare hash, run `php7.4 -l` on the temp file, preserve owner/mode, then atomic `mv`.
6. Update only `products.price` for the exact target IDs after backup. Never change `cost`, `api_stock`, `status`, `category_id`, `api_id`, or `supplier_id=0` rows.
7. Verify final lint, source/live hash, override markers, HTTP 200, target DB rows, and supplier `update_price/discount`.

## Closeout pitfalls
- A worker's empty/completed report is not proof. Inspect git diff, live markers, DB values, backup path, hashes, and lint independently.
- Existing staged changes can be accidentally included even when running `git add <target-file>`. Inspect `git diff --cached --name-status`; if a broad commit occurs, reset only the commit while preserving the working tree, then recommit the exact allowlist.
- Pull/rebase may refuse dirty worktrees. Do not reset/stash unrelated operator changes without permission; `rebase.autoStash=true` can preserve them when the upstream is already known and the paths are confirmed outside scope.
- Local code may be LF while live code is CRLF; PHP accepts either, but hash equality requires deploying the exact bytes and then comparing hashes.

## Session detail
For the verified CloneFBIG case, supplier `id=1` (`API_31`, `https://clonefbig.com`) stayed `update_price=ON`, `discount=100`; source `api_id=16` mapped to local product 56 and fixed `2,650 VND`, while `api_id=3591` mapped to local product 67 and fixed `2,385 VND` at the site's `26,500 VND/USD` rate. The patch was applied in both insert/update branches, linted on VPS, atomically deployed, and independently verified with HTTP 200 and DB readback.