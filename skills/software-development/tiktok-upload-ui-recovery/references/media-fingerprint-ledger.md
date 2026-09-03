# MEDIA_FINGERPRINT ledger — cấu trúc & stale-release (2026-08-07)

Nguồn: `tiktok_workflow/media_fingerprint.py` + điều tra live trên máy 44/48/54.

## Cấu trúc ledger

- Dir: `D:\CodexRuntime\tiktok-video\idempotency\media-fingerprints\`
- **Per-fingerprint file** (không phải append-only): `<sha256>.json` — tạo exclusive (`open("x")`) để reserve atomic giữa worker song song, không cần lock thứ 2.
- Entry JSON:
```json
{
  "key": "<sha256>", "machine": "44", "target_account": "v.th.thoooo",
  "sha256": "...", "video_number": 5, "run_id": "run_...",
  "source_path": "D:\\TIKTOK-videonuoinick\\345\\5.mp4",
  "status": "reserved" | "verified_success",
  "reserved_at": "2026-08-05T01:29:55.558584"
}
```
- `status=verified_success` = video ĐÃ đăng thành công (post-verified) — không đăng lại.
- `status=reserved` = worker đang xử lý (push media → post). Nếu worker crash/kill giữa chừng, run không finalize → reserved kẹt mãi.

## Bug cũ: reserved kẹt vĩnh viễn

- `reserve()` dùng `path.open("x")`; FileExistsError → đọc entry → `verified_success` thì DuplicateError, **còn lại thì PendingError** (kể cả reserved cũ mấy ngày).
- 12 entry kẹt từ 08-04/08-05/08-07 (máy 1,8,10,13,22,30,35,44,48,51,54,70) → máy chọn đúng video đó lần sau fail-closed mãi: `MEDIA_FINGERPRINT_PENDING`.

## Fix: stale-release trong reserve()

Patch `reserve()` thêm `stale_after_seconds: float = 1800`:
- Trong nhánh FileExistsError, nếu `status == "reserved"` và `age > stale_after_seconds` → **ghi đè entry mới** (release + re-reserve) thay vì raise.
- Age tính từ `reserved_at` (datetime.fromisoformat); parse fail → age=inf (không release — fail-closed).
- An toàn: previous attempt hoặc crash trước Post hoặc run kết thúc không proof; post-verifier (`POST_RECHECK`) guard duplicate publication riêng.
- Cũng thêm `import logging` + `logger = logging.getLogger("tiktok_workflow.media_fingerprint")` — module KHÔNG có logger sẵn → dùng `logger.warning` sẽ NameError.

## Verify + probe

```python
from tiktok_workflow.media_fingerprint import MediaFingerprintLedger, MediaFingerprintPendingError, MediaFingerprintDuplicateError
l = MediaFingerprintLedger(r'D:\CodexRuntime\tiktok-video')
try:
    r = l.reserve(machine=54, target_account='kimm.ngnn614', video_number=5,
                  source_path=r'D:\TIKTOK-videonuoinick\425\5.mp4', run_id='probe-<ts>')
    print('RESERVE OK — stale released:', r.sha256[:16])
except MediaFingerprintPendingError as e:  # vẫn reserved < 30 phút
    ...
except MediaFingerprintDuplicateError as e:  # đã verified_success
    ...
```

Kỳ vọng log: `[MEDIA_FINGERPRINT] Releasing stale reservation age=275660s sha=ce8041984cce...`

**Pitfall probe**: `run_id='probe-...'` ghi đè entry THẬT. Sau test phải reset entry (`run_id=''`, `reserved_at` để cũ) để worker thật re-reserve — nếu không, run_id giả dính trong ledger, và `rebind_reserved` (retry có receipt) sẽ không khớp `previous_run_id`.

## Cách đọc ledger cho 1 máy (biết video nào đã đăng)

Mỗi máy: N entry `verified_success` (video 1..N) + có thể 1 entry `reserved` (video N+1 treo). 
- `verified_success` count = số video đã đăng thật.
- Nếu máy fail `MEDIA_FINGERPRINT_PENDING` → tìm entry `reserved` của máy đó, video_number = video nó đang kẹt. Sau patch, retry tự release nếu >30 phút.
