# Verify worker edits on dirty multi-session repos (D:\Taadaa)

Proven 2026-08-08 (UI coordinate-fallback rule change, 8 rule files, 1 worker,
repos dirty by 3+ parallel sessions). Trong môi trường nhiều session cùng sửa
repo, `git diff` vs HEAD KHÔNG dùng được để verify worker — nó trộn thay đổi
pre-existing của session khác với thay đổi của worker. Nguồn sự thật = **backup
trước-worker**.

## Quy trình chuẩn (yêu cầu worker làm TRƯỚC khi sửa)

1. **Baseline snapshot** (trước dispatch/sửa, lưu NGOÀI repo — vd `D:\Taadaa\coordfallback-baseline-<ts>.txt`):
   - `git -C <repo> status --short` từng repo
   - `git -C <repo> diff --stat` từng repo — dùng làm chứng cứ "file dirty cũ không đổi"
   - EOL từng file đích (`file <path>` — nhưng lưu ý: `file` báo "CRLF" cả khi file MIXED)
2. **Backup file đích** vào dir NGOÀI repo (`D:\Taadaa\<task>-backup-<ts>\`), tên có prefix số
   (`01-automation-core-docs-x.md`) để tránh trùng basename giữa repo. Backup = byte gốc trước worker.
3. Worker sửa xong → **verify bằng diff backup-vs-current**, không dùng `git diff`.

## Verify byte-level (script `hermes-verify-*` trong Temp, chạy xong dọn)

Cho từng file đích, mở cả 2 bản `rb`:

- **EOL — check DELTA, không check tuyệt đối**: file gốc có thể đã MIXED sẵn
  (git lưu LF thuần trong repo, working tree checkout ra CRLF+LF — gặp thật ở
  `automation-core/docs/ui-compatibility-contract.md`: HEAD 315 LF thuần,
  backup 290 CRLF + 25 LF đơn). Check đúng:
  - file LF (vd register gmail/AGENTS.md): `count(b"\r\n") == 0`
  - file CRLF: `count(b"\n") - count(b"\r\n") ==` SỐ LF ĐƠN CỦA BACKUP (không tăng)
  - CRLF count tăng ĐÚNG bằng số dòng thêm (`cur_crlf - bak_crlf == số dòng insert/replace net`)
- **CRLF count "preserved" = FALSE POSITIVE**: thêm dòng → CRLF count phải TĂNG, không bằng.
- **Không double-CR**: `b"\r\r\n" not in cur`.
- **delete=0** (worker không xoá dòng nào); **replace count == số vùng spec** — spec amend
  là phép REPLACE (thay cụm), nên "pure additive (replace=0)" là check SAI; kỳ vọng replace=1..3
  theo từng file, insert=0..1.
- **Marker/canonical ID count chính xác** từng file (`cur_b.count(CANON.encode())`).
- **In unified diff backup-vs-current** (difflib trên decoded lines) để đối chiếu mắt với spec —
  replace ở đúng vùng spec, không đụng vùng khác.
- Worker lệch spec kiểu **insert thay vì replace**: chấp nhận được nếu nội dung đúng + additive
  (không xoá dòng cũ).

## Chứng cứ "file dirty cũ không đụng"

- `git diff --stat` hiện tại so **baseline snapshot** (so số cột +/-). VD: 6 file dirty core
  baseline 23/8/2/2/4/50 → sau worker vẫn y hệt → worker không đụng. Đừng regex bắt tên file
  trong output `git diff --stat` — cột tên bị cắt/escape, dễ MISSING dù file có mặt (fail thật).
- Repo bẩn sẵn (Tiktok_Reg, tiktok-log-in, register gmail... có 15-30 file modified từ trước):
  `git diff` của AGENTS.md/PROJECT_RULES.md sẽ hiện cả thay đổi session khác — đừng quy cho worker.

## Validator findings — phân loại pre-existing trước khi đổ lỗi

- `tools/check_ui_compatibility.py` báo findings (vd `agents_missing_canonical_binding`) →
  check `git -C <repo> show HEAD:<file> | rg -c "binding"` — nếu HEAD đã thiếu → **pre-existing**,
  không phải regression do worker. (Thật: Tiktok_Reg/AGENTS.md + tiktok-log-in/AGENTS.md thiếu
  binding từ HEAD dù repo có sẵn `docs/ui-compatibility.md`.)
- KHÔNG tự sửa file đang dirty bởi session khác (rủi ro đè) — báo cáo pre-existing, đề xuất fix
  riêng khi session kia xong.

## Pitfall khác

- `decode()` + `splitlines()` che mất thay đổi EOL — so EOL bằng bytes, so NỘI DUNG bằng decoded lines.
- 9router audit (luna/sol) transient 502/401: retry — `gpt-5.6-sol` 502 → 401 → 200 (upstream
  token refresh). Smoke-test model trước khi chạy audit dài; deepseek family hay 429 đồng loạt.
- Worker chậm đáng ngờ không phải treo: theo dõi tiến độ qua filesystem (baseline/backup dir đã tạo
  chưa, marker count trong file đích), không poll delegate handle.

## Ad-hoc verification evidence capture (Hermes "edited code chưa verify" gate)

- Script `hermes-verify-<task>.py` trong Temp: chạy in TOÀN BỘ output + `EXIT_CODE=$?`, rồi **xoá ở
  LỆNH RIÊNG** (không cùng lệnh với python) — xoá cùng lệnh làm hệ thống capture nhầm output FAIL
  của script trước đó → báo "verification stale" loop dù lần chạy mới PASS (dính 3 lần 2026-08-08).
- .md rules không có suite canonical → nói rõ "ad-hoc, không phải suite green"; validator
  (`tools/check_ui_compatibility.py`) là bằng chứng chính, findings pre-existing phải nêu riêng.
- Dọn mọi script tạm (`audit_*.py`, `hermes-verify-*.py`) khi xong — chúng xuất hiện trong
  "changed paths" tracker của hệ thống.
