# Claude quota preflight — hành vi đã verify (PS 5.1 + weekly gate)

Script: `D:\Taadaa\tools\claude-quota-preflight.ps1` (chạy TRƯỚC mỗi lần gọi Claude).
Ledger: `D:\CodexRuntime\<project-id>\audit\claude-quota-ledger.jsonl`.

## BẮT BUỘC: tham số `-LedgerPath` (hit 2026-08-20)

Chạy thiếu `-LedgerPath` → `MissingMandatoryParameter: LedgerPath` (exit 1) — KHÔNG phải quota block.
Gọi đúng (ledger có sẵn từ các lần trước, vd automation-core):
```bash
powershell -NoProfile -ExecutionPolicy Bypass -File "D:\Taadaa\tools\claude-quota-preflight.ps1" -LedgerPath "D:\CodexRuntime\automation-core\audit\claude-quota-ledger.jsonl"
```
Không có ledger sẵn → tự tạo thư mục `<project-id>\audit\` trước khi chạy (script append, không tạo dir).
Nếu repo chưa từng chạy Claude, dùng ledger mới `D:\CodexRuntime\<repo>\audit\claude-quota-ledger.jsonl` — script tự append entry.

## Exit codes

| Exit | Nghĩa | Hành động |
|------|-------|-----------|
| 0    | ALLOW — `used_5h < 85%` VÀ `used_weekly < 90%` (weekly có trong /usage) | gọi Claude |
| 20   | BLOCK — 5h ≥ 85% | chờ reset 5h HOẶC fallback OpenCode → Codex |
| 22   | BLOCK — weekly ≥ 90% | **dừng hẳn Claude cả tuần**, không chờ reset 5h |
| 21   | QUOTA_STATUS_UNAVAILABLE (probe fail/stale/không verify được) | block, fallback |

- Weekly không xuất hiện trong `/usage` → `used_weekly_percent: null`, chỉ 5h gate áp dụng.
- Reading >60s = stale → block. CLI/auth availability KHÔNG phải quota proof.
- Event ledger: `CLAUDE_QUOTA_THRESHOLD_REACHED` (20), `CLAUDE_WEEKLY_QUOTA_THRESHOLD_REACHED` (22), `CLAUDE_QUOTA_STATUS_UNAVAILABLE` (21).

## Format output `/usage` THẬT (quan trọng — regex phải khớp)

Chạy: `claude -p '/usage' --no-session-persistence --permission-mode dontAsk --output-format json`

```
You are currently using your subscription to power your Claude Code usage

Current session: 0% used
Current week (all models): 72% used · resets Aug 7, 6am (Asia/Bangkok)
```

- Dòng 5h: `Current session: NN% used`
- Dòng weekly: **`Current week (all models): NN% used`** — KHÔNG phải `Weekly usage:`.
  Regex: `(?mi)^\s*Current week(?: \(all models\))?:\s*(?<used>[0-9]+(?:\.[0-9]+)?)%\s+used\b`
- Ledger fields: `used_5h_percent`, `remaining_5h_percent`, `used_weekly_percent`, `remaining_weekly_percent`, `observed_at` (UTC), `source_id`, `maximum_used_percent` (85), `maximum_weekly_used_percent` (90).

## Pitfall PS 5.1: `[Convert]::ToHexString` KHÔNG tồn tại

Máy này chạy **Windows PowerShell 5.1** (.NET Framework) — `[Convert]::ToHexString`
chỉ có từ .NET 5+/PowerShell 7. Trước khi fix, mọi preflight throw
`Method invocation failed ... ToHexString` → exit 21 → **Claude bị block oan mọi lần**.

Fix (đã áp dụng vào script):
```powershell
$hexBytes = $sha256.ComputeHash($identityBytes)
if ('ToHexString' -in [System.Convert].GetMethods().Name) {
    $accountContextId = [Convert]::ToHexString($hexBytes).ToLowerInvariant()
} else {
    $accountContextId = [BitConverter]::ToString($hexBytes).Replace('-', '').ToLowerInvariant()
}
```

**Quy tắc**: mọi script PowerShell mới/sửa cho máy này phải test chạy bằng PS 5.1
thực tế (`powershell -NoProfile -ExecutionPolicy Bypass -File ...`), không chỉ
parser syntax check. Verify ad-hoc bằng script tạm `hermes-verify-*.ps1` trong
`%TEMP%` rồi dọn.

## Verify pattern (ad-hoc, không suite)

1. Test regex trên output `/usage` THẬT (lấy sample bằng lệnh trên), đừng tự bịa format.
2. End-to-end chạy preflight với ledger tạm; assert `account_context_verified:true` (bắt crash ToHexString), `used_weekly_percent:\d+`, `decision`, `exit_code`.
3. Freshness: `observed_at` vs now (UTC) < 60s — cẩn thận parse timezone (`[datetime]` convert sai cho giá trị âm; so sánh chuỗi UTC trực tiếp).

## Trạng thái verify 2026-08-03

- Lần 1 (sai regex `Weekly usage:`): test mock pass nhưng **end-to-end thấy weekly=null** → mở `/usage` thật → nhận ra format đúng là `Current week (all models):`.
- Sau fix regex: end-to-end thật trả `used_weekly_percent:72`, `ALLOW_CLAUDE`, exit 0 (5h 0% + weekly 72% < 90). Quota lúc đó: 5h 0%, weekly 72% (resets Aug 7 6am Bangkok).
- ToHexString fix: 7/7 pass (hash 64 hex lowercase deterministic + script end-to-end không crash).
- Bài học: **đừng giả định format output CLI** — chạy lệnh thật lấy sample trước khi viết regex.
