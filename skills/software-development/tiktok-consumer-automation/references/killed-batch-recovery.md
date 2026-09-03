# Phục hồi batch TikTok bị kill giữa chừng (2026-08-03)

Launcher `run_tiktok_upload_batch.ps1` chạy `Start-Job` song song; khi Hermes
bị interrupt / process bị kill giữa chừng, batch con chết để lại trạng thái
dở dang. Quy trình phục hồi đúng (không debug lẻ từng máy, không chạy mù):

## 1. Xác định trạng thái thật — checkpoint là nguồn sự thật

```bash
cd /d/CodexRuntime/tiktok-video/runs
python -c "
import json, glob, os
for m, s in [('45','ce0716071586c80602'), ('54','ce12160c81c8acae0c')]:
    dirs = sorted([d for d in glob.glob(f'run_{s}_*') if os.path.isdir(d)])
    d = dirs[-1]
    rp = os.path.join(d,'report.json')
    st = 'NO-REPORT'
    if os.path.exists(rp):
        r = json.load(open(rp, encoding='utf-8'))
        st = f\"{r.get('status')} verified={r.get('post_verified')}\"
    c = json.load(open(os.path.join(d,'checkpoint.json'), encoding='utf-8'))
    print(f'{m}: report={st} | ckpt={c.get(\"last_state\")} post_tap={c.get(\"post_tap_attempted\")} verified={c.get(\"post_verified\")}')
"
```

Ý nghĩa checkpoint:
- `post_tap_attempted=true` + state `VERIFY_POST` → **đã bấm Post, chưa verify**:
  chạy lại sẽ recheck profile (cơ chế hậu kiểm post mơ hồ), KHÔNG repost mù.
- `post_tap_attempted=false` + state trước POST → chưa post, chạy lại bình thường.
- `status: MANUAL_REVIEW` + `post_verified=true` trong checkpoint → post xong,
  avatar fail (xem avatar section); chạy avatar smoke riêng.

## 2. Lock stale — verify PID chết rồi mới takeover

Lock: `C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json`.

```bash
cat /c/Users/Kibe/.codex/device-locks/machine_45.lock.json | python -c "import json,sys; d=json.load(sys.stdin); print(d.get('pid'), d.get('owner_active'))"
tasklist /FI "PID eq <pid>" | grep -iE 'python|powershell'   # rỗng = PID chết = stale
```

- PID chết → lock stale → chạy lại với `--recovery-mode` (takeover hợp lệ).
- PID còn sống → đừng chạm (có thể là process khác như `social_reg_v1.py`,
  `tiktok-luot nuoi acc` đang giữ máy).

## 3. Fingerprint stale — phân loại trước khi xoá

Ledger `idempotency/media-fingerprints/<key>.json` giữ `status: reserved` từ run
chết → run sau fail `MEDIA_FINGERPRINT_PENDING` ở RESOLVE_NEXT_VIDEO.

- Chưa từng post (`post_tap_attempted=false`, không có
  `idempotency/post-attempts/machine_X_video_N.json`) → reservation stale →
  **xoá entry** rồi retry.
- Đã bấm Post → **giữ** reservation, để recovery recheck (tránh repost).
- Xoá: `python -c` đọc từng entry, lọc machine+video+status, unlink.

## 4. Chạy lại ĐỒNG LOẠT, không lẻ

User yêu cầu rõ: "tôi yêu cầu làm đồng loạt mà sao làm 45 riêng 64 riêng".
Sau khi xác minh checkpoint + lock, phóng lại **tất cả máy còn dở song song**:

```bash
for m in 45 54 64 74; do
  printf 'YES\n' | python scripts/run_workflow_cli.py --config \
    "D:\CodexRuntime\tiktok-video\config-machine-62.yaml" \
    --workflow-workbook "D:\OneDrive\Tiktok\Tik1.xlsx" --machine $m \
    --no-dry-run --recovery-mode --allow-device-reboot-recovery \
    --avatar-source-root "D:\TIKTOK-videonuoinick" &
done
```

Mỗi máy resume từ checkpoint riêng; 45/37 recheck profile (không repost),
54/64/74 tiếp tục flow. `--recovery-mode` cho phép takeover lock stale +
soft-reboot recovery. `--avatar-source-root D:\TIKTOK-videonuoinick` để avatar
lấy từ kho output (đã fix bằng YOLO), không phải `D:\video goc`.

## 5. Verify per-target, không dựa vào process exit

- `process exit 0` KHÔNG = thành công; đọc report.json:
  `status == 'SUCCESS' and post_verified == true` (live mode).
- `avatar_status == 'SUCCESS'` / `AVATAR_SMOKE_SUCCESS` cho avatar smoke.
- Workbook `Tik1.xlsx` cột `Video Đã Đăng` là chốt cuối (atomic-update + verify
  trong workflow).

## 6. Pitfall: terminal timeout kill launcher giữa batch (2026-08-05)

Chạy `run_tiktok_upload_batch.ps1` qua `terminal` với `timeout=600` (foreground)
bị **kill giữa chừng** khi batch > ~10 phút — 14 máy song song + verify từng máy
vượt 600s. Hậu quả: `summary.csv` không được ghi, job con chết, máy đang
`VERIFY_POST` để lại `verification_pending`, workbook có thể chưa cập nhật dù
bài đã đăng. Đã xảy ra 2 lần trong cùng đêm.

- Batch 14 máy × ~3-5 phút/máy song song 10 → >15 phút; retry 3-6 máy cũng
  thường vượt 600s. KHÔNG dùng foreground timeout 600s cho batch ≥ 6 máy.
- Đúng: `terminal(background=true, notify_on_complete=true)` — launcher tự viết
  `summary.csv` + exit code khi xong, không cần canh foreground.
- Nếu bị kill: xác minh bằng report.json per-machine (đã có `Report saved:` trong
  `machine-<N>.out.log`) — không chờ summary.csv; batch dir không có summary.csv
  = launcher chưa kết thúc, không phải batch fail. Kiểm tra process
  (`wmic process where "Name='python.exe'" get CommandLine | grep tiktok_workflow`)
  trước khi kết luận đã chết.
