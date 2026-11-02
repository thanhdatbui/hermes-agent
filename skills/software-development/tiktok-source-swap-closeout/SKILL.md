---
name: tiktok-source-swap-closeout
description: "Use when swapping a TikTok account's video source safely."
version: 1.0.0
metadata:
  hermes:
    tags: [tiktok, farm, source-swap, dedup, closeout, evidence]
---
# TikTok Source Swap and Dedup Closeout

Use this class-level workflow when a farm account must move away from a risky or unsuitable source channel. The goal is not merely to launch a downloader: it is to prove the new source is allocated correctly, does not collide with another live account, preserves upload history, and reaches a verified render/UI artifact.

## 1. Resolve the exact target before changing anything
1. Query the tracker DB by username to obtain machine, Tik slot, and host.
2. Read the exact host workbook row. Keep these identifiers separate:
   - `video gốc`: raw download folder.
   - `Folder Video`: render/upload folder.
   - `Video Đã Đăng`: historical upload cursor.
3. **Reconcile all candidate workbook copies before mutation.** If the host workbook, an alternate/legacy workbook, tracker DB, or live Profile snapshot disagree on `Folder Video`, `video gốc`, niche, or posted count, stop as `BLOCKED—SSOT_RECONCILIATION_REQUIRED`; do not run `--clean-old`, update metadata, or infer the source from filenames alone. Record every conflicting value and select the authoritative host workbook only after the conflict is explained.
4. Check both raw and render folders by exact bounded paths. Extra clips/debris or mismatched counts are evidence of drift, not permission to overwrite.
5. Compute `start_seq = Video Đã Đăng + 1`. Never reset the posted count.

### Pre-mutation reconciliation gate
A swap is allowed only when these are explicit and consistent: username → machine/Tik/host; authoritative workbook row; raw folder; render folder; niche/hashtag metadata; posted cursor; and source claim/ledger status. Any conflict across known state stores requires an exact conflict report and a stop before deletion or download. This gate prevents a stale backup workbook or cross-account raw folder from poisoning the target.

## 2. Select a replacement source
1. Prefer a source with enough duration-valid videos for the target pool.
2. Check the known shared ledger and state DB for source claims and downloaded video IDs. Use exact known files/queries only; do not scan the disk broadly.
3. Distinguish states:
   - `source_claimed` = reserved/configured, not proof of a posted duplicate.
   - `downloaded` = source content actually recorded in the ledger.
   - A peer workbook row with zero posted videos is a reserved/configured collision, not a live content collision.
4. Do not treat “no Farm collision” as “copyright safe.” Preserve source-risk warnings separately: watermark, reused-content, and rights-owner exposure remain external risks.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
