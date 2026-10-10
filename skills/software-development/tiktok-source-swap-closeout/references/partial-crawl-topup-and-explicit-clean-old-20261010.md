# Partial Crawl Recovery and Explicit Full Replacement (2026-10-10)

## Observed recovery
A full-replacement request explicitly authorized deleting the old raw/render source and switching one target account to a hot niche. The first bounded crawl from the selected YouTube Shorts channel returned **38 valid MP4 files**, although the source listing exposed 45 entries and the pipeline minimum was 40. The pipeline correctly stopped instead of claiming completion. A continuation downloaded the remaining source entries into fresh numeric slots and produced 48 valid numeric MP4 files.

## Durable procedure
1. Treat an explicit operator instruction to remove the old source as authorization for the bounded `clean-old` mutation; do not ask for routine re-confirmation.
2. Preserve `Video Đã Đăng` and derive `start_seq = posted + 1`; never reset the account cursor during a niche swap.
3. After a partial crawl, continue from the same manifest/channel and append only to the next free numeric slot.
4. Validate each appended file with both a minimum-size check and `ffprobe` video-stream check.
5. Recompute the actual numeric MP4 count from disk after continuation. Also deduplicate source video IDs before final metadata updates; a raw count alone does not prove unique content.
6. Final closeout still requires raw/render/database count equality, correct workbook niche+hashtag metadata, preserved cursor, and visual/device evidence.

## Hashtag rule
A niche swap changes the content label and hashtag pool together. Use a natural, niche-specific pool; never retain the old niche hashtags or generate tags by blindly concatenating a slug.

## Important caution
The observed continuation ended with 48 files for a source listing of 45 because retries/append logic were not deduplicated by source video ID. This is a recovery result, not a recommended target count. Before render/metadata commit, compare the recorded source IDs and remove or quarantine duplicates while preserving the posted cursor.
