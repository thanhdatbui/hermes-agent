# Batch Error Aggregator: Dual-Threshold Systemic Failure Detection & Upload Hook (2026-09-07)

## Problem & Context
On a farm fleet with 40–80 devices running batch workloads (upload video, avatar, follow, reg), per-machine alerts cause Telegram alert fatigue when 1–2 devices encounter transient glitches (sporadic network glitch, local app delay). Conversely, when systemic platform breaks occur (TikTok UI layout shift, account lockouts, broken CDN), manual log audits delay detection.

`automation_core.batch_aggregator` solves this with automated clustering and dual-threshold classification.

---

## Dual-Threshold Systemic Error Invariant
A failure cluster is classified as **systemic** if and only if:
$$\text{rate} \ge 10\% \quad \text{AND} \quad \text{count} \ge 3$$

- **Sporadic (< 10% rate OR < 3 machines):** Silent Skip. No alert sent to Telegram; prints:
  `[Silent Skip] Fleet error rate below threshold. No alert sent.`
- **Systemic ($\ge 10\%$ rate AND $\ge 3$ machines):** Triggers `should_alert = True` and dispatches a consolidated Telegram alert with:
  1. Fleet impact statistics (total machines, succeeded, failed, cluster count).
  2. Normalized error signature and affected serial list.
  3. Actionable Canary Recovery command targeting the first candidate machine:
     `python D:/Taadaa/tools/inspect_machine.py <canary_machine>`
  4. Up to 1–2 representative evidence snapshots (`snapshot_png` / `snapshot_xml`).

## Overall-rate display rule (2026-09-11 fix: 100% fail misread as 75%)

Per-signature rate alone misleads: with 80/80 machines failed (60 sig A + 20 sig
B), the alert showed only `75% (60/80)` and readers concluded "only 75% failed".
The alert MUST therefore carry three separate numbers:

1. Header: `Tổng tỷ lệ thất bại toàn batch: <b>X%</b> (failed/total máy)` —
   `overall = failed_count / total_machines` (guard divide-by-zero). 80/80 shows
   `100.0%`.
2. Per signature: `Tỷ lệ trên toàn batch: <b>X%</b> (n/total máy)` where
   `batch_rate = sig_count / total_machines`.
3. Per signature: `Tỷ lệ trong số máy lỗi: <b>Y%</b> (n/failed máy lỗi)` where
   `fail_share = sig_count / failed_count`. Never reuse the old ambiguous label
   `Tỷ lệ ảnh hưởng`.

Regression: `TestOverallBatchFailureRate` in
`automation-core/tests/test_batch_aggregator.py` (full 80/80 → 100% overall;
partial 5/40 → 12.5% overall / 100% fail-share).

## Script Name on Alert Header Rule (User chốt 11/09/2026)
User yêu cầu: **"Sửa lại thông báo đầu tiên phải ghi rõ script lỗi lên trên đầu của farm alert"**.
Khi phát `[BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG`, dòng đầu tiên ngay dưới banner tiêu đề BẮT BUỘC phải ghi rõ quy trình/script đang chạy:
```html
🚨 <b>[BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG</b>
• Quy trình / Script: <b>{resolved_script_name}</b>
• Quy mô batch: <b>{total_machines} máy</b> | Thành công: {succeeded_count} | Thất bại: {failed_count}
• Tổng tỷ lệ thất bại toàn batch: <b>{overall_fail_rate:.1%}</b> ({failed_count}/{total_machines} máy)
• Số cụm lỗi hệ thống: <b>{len(systemic_signatures)}</b>
```

- **Cơ chế resolve:** Tự động tra cứu `_resolve_script_meta` từ `automation_core.alerts` để map alias (`multi-machine-feed-session`, `tiktok-video`, `tiktok-follow`, `Tiktok_Reg`, `register-gmail`, `tiktok-add-2fa`, `clear-tiktok-cache`...) sang tên tiếng Việt chuẩn hóa.
- **Nguồn lấy tên script:** 
  1. Tham số `--script` từ CLI `batch_aggregator.py`.
  2. Tự động extract từ `run_manifest.json` (`mode`, `account`, `script`, `pipeline`, `workflow`) hoặc `summary.txt` / run directory path.
  3. Fallback `Chưa rõ quy trình` nếu không nhận diện được.
- Tuyệt đối không để alert batch thiếu tên script khiến người vận hành nhìn thấy alert 76/80 máy fail mà không biết batch của quy trình nào bị lỗi.

---

## Error Signature Normalization
To prevent machine-specific variables from fracturing identical systemic errors into separate buckets, `normalize_error_signature()` regex-strips:
- Device serials: `m\d+`, `DEV-[A-Za-z0-9_-]+`, alphanumeric hardware serials, emulator IPs.
- Vietnamese device prefixes: `May #?\d+`, `máy \d+`.
- Timestamps: ISO-8601, HH:MM:SS, YYYY-MM-DD, epoch seconds (1.5B–1.9B).
- UI coordinates & bounds: `[x1,y1][x2,y2]`, `(x, y)`, `x=... y=...`.
- Process IDs & hex memory addresses: `pid: 1234`, `0x7ffee45`.

---

## Data Ingestion: Summary CSV & JSON Reports
`load_results_from_csv(path: Union[str, Path]) -> list[MachineResult]`:
- Reads runner `summary.csv` via `csv.DictReader`.
- Columns:
  - `Machine` or `serial` $\rightarrow$ serial.
  - `Status` & `Verified` $\rightarrow$ `succeeded` when verified $\in$ `("true", "1")` or status $\in$ `("verified-success", "success", "ok")`.
  - `Reason` / `SkipReason` $\rightarrow$ error reason / type.
  - `Report` $\rightarrow$ path to detailed machine `report.json`.
- Automatic Snapshot Discovery:
  - Checks fields in `report.json`: `snapshot_png`, `screenshot`, `snapshot`, `image`.
  - Falls back to scanning sibling files in `report.json` directory: `*<serial>*.png` or `*.png`.

---

## Canonical Hook in `run_tiktok_upload_batch.ps1`
Placed immediately after CSV export:
```powershell
$summaryPath = Join-Path $batchDir "summary.csv"
$results | Sort-Object Machine | Export-Csv -LiteralPath $summaryPath -NoTypeInformation -Encoding UTF8

# Batch error aggregation hook with dual-threshold alert
try {
    python -m automation_core.batch_aggregator "$summaryPath" --telegram
} catch {
    Write-Warning "batch_aggregator hook error: $_"
}
```

---

## Verification Commands
```bash
# Run unit tests
cd /d/Taadaa/automation-core && PYTHONPATH=src pytest tests/test_batch_aggregator.py -p no:cacheprovider

# Test batch aggregator CLI directly against a summary CSV
python -m automation_core.batch_aggregator "D:/CodexRuntime/tiktok-video/runs/.../summary.csv" --telegram
```
