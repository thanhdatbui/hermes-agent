# Follow reconciliation: committed vs attempted

## Contract

- `daily_account_actions` and similar action ledgers may record an attempted follow; they are not proof of server commitment.
- Per-machine terminal `follow_result.json` is the first authority for the session outcome.
- Count only terminal success evidence (`status=OK` plus `followed_count > 0` or explicit `followed` entries) as committed cross-follow.
- `FOLLOW_FAILED`, `follow_failed=true`, a released/"bị nhả" reason, or `followed_count=0` contributes zero committed follows.
- Compare Web Following delta only with committed follows. A zero-vs-zero result is `Khớp 0`, never `Lệch -N`.

## Minimal audit table

| machine | attempted | released/failed | committed | Web delta | verdict |
|---|---:|---:|---:|---:|---|
| M6 | 1 | 1 | 0 | 0 | Khớp 0 |
| M29 | 2 | 2 | 0 | 0 | Khớp 0 |
| M42 | 1 | 0 | 0 | 0 | artifact says no new commit; investigate attribution, do not call natural follow |

Keep released attempts in a separate report category and preserve the exact artifact path. Never turn an attribution/ledger bug into a natural-follow count.

---

## Pitfall: Reconciliation Masking Defect When `follow_failed` Is True (2026-10-02)

### 1. Hiện Tượng Mặt Nạ Đối Soát (Masking Anomaly)
Báo cáo watchdog hiển thị:
- Header Feed: `+ Follow tự nhiên: 30 lượt / 1285 video (2.3%)`
- Header Chéo: `• Follow chéo (0 lượt follow) ... Nhả follow (38 máy)`
- Header Đối Soát: `+ Đối soát TikTok Web (+0 Following thật - Khớp 100% so với script báo)`

### 2. Root Cause Code (`feed_session_watchdog.py`)
```python
failed = bool((all_follows.get(m) or {}).get("follow_failed"))
# A machine that failed/released its follows must not create a
# negative web reconciliation delta from stale reported claims.
m_to_reported[str(m)] = 0 if failed else cnt + natural_cnt
```
- Phép gán `0 if failed else cnt + natural_cnt` được thiết kế để triệt tiêu follow chéo bị nhả (`cnt`), nhưng **vô tình xóa luôn cả `natural_cnt` (30 lượt follow tự nhiên)**!
- `expected_delta` bị reset về 0 trên toàn bộ 38 máy `failed`.
- Web delta cào về = 0. Watchdog so sánh `0 vs 0` và in ra `Khớp 100%`, che giấu hoàn toàn việc 30 lượt follow tự nhiên là **ghost follows** (bị TikTok shadow-drop).

### 3. Chu Kỳ Cooldown Tương Hỗ Giữa 2 Repo (Follow Chéo ↔ Nuôi Feed)
- **Cơ chế liên kết:** `feed_swipe_smoke.py` có hàm `is_account_in_follow_cooldown(ctx)` đọc trực tiếp `follow_state_{m}_row_{r}.json` do follow chéo ghi nhận (`cooldown_until_at`, `cooldown_until_date`).
- **Thứ tự thực thi trong 1 phiên:** Lướt feed (kèm follow tự nhiên) chạy TRƯỚC -> Follow chéo chạy SAU.
  - Do đó ở phiên đầu tiên dính nhả, đầu phiên nick chưa có án phạt nên vẫn roll trúng follow tự nhiên; đến cuối phiên follow chéo mới phát hiện nhả và set cooldown.
- **Hành vi các ngày / phiên kế tiếp (Streak 3-5-7 ngày):**
  - Trong suốt thời gian cooldown, `is_account_in_follow_cooldown` trả về `True`.
  - Hàm `_maybe_follow_video` tự động BỎ QUA 100% lượt follow trên video (`action="follow_video", result="skipped", error="account is in follow cooldown (imprisoned)"`).
  - Hết phiên feed, follow chéo cũng tự động skip an toàn (`follow-released-daily-cooldown`).
  - Nick chỉ lướt feed và thả tim dưỡng sinh cho đến khi mãn hạn cooldown.
