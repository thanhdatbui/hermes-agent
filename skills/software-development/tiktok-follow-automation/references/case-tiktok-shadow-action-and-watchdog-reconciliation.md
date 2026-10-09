# TikTok Shadow Action & Watchdog Follow Reconciliation

## 1. Bối cảnh (2026-10-06 — M80 `@kymanzzc4ic`)

### Diễn biến thực tế
- **Feed session:** Runner lướt feed, tự nhiên follow 1 video For-You → `follow_counts.for-you = 1`.
- **Follow hook — Mode 2:**
  - Tap anchor đầu (`@allynkapyej`): Sau tap, `verify_follow.py` dump UI → nút hiện "Đã follow" → ghi nhận **SUCCESS** (counted).
  - Vuốt sang anchor tiếp (`@jiajzjfm6ec`): Nút văng ngược lại → `state.set_follow_failed()` → `FOLLOW_FAILED`.
- **Kết quả `follow_result.json`:**
  ```json
  {"status": "FOLLOW_FAILED", "followed": ["allynkapyej"], "followed_count": 1, "follow_failed": true}
  ```
- **Web TikTok snapshot:** Following của `@kymanzzc4ic` = 1 từ ngày 17/09 đến 06/10, **không tăng lên 2** dù đã bấm được nick đầu.

## 2. Shadow Action — Behavior của TikTok (không phải bug script)

**Định nghĩa:** TikTok Shadow Action là khi app trên thiết bị cho bấm Follow và cache local "Đang follow", nhưng Backend Server **âm thầm drop (không commit)** vào database.

**Cơ chế khi nào TikTok reveal:**
- Lúc bấm xong → dump UI ngay: App cache hiện "Đã follow" → `verify_follow.py` thấy OK → **Không phát hiện được lúc này**.
- Lúc vuốt context sang action tiếp theo (bấm nick thứ 2) → TikTok reload context → Backend reveal "account bị throttle" → Nút văng ngược → `FOLLOW_FAILED`.

**Hệ quả không thể tránh:** `verify_follow.py` sẽ luôn ghi nhận SUCCESS cho các lượt shadow bởi vì nó dump UI ngay sau tap — khi đó server chưa reveal. Reload lại profile sau 30-60s sẽ lộ, nhưng làm vậy creates bot signature và làm chậm session.

**Phân biệt bằng snapshot DB:** Nick bị shadow từ trước $\rightarrow$ `following` trong `tiktok_tracker.db` sẽ không tăng dù many sessions báo SUCCESS. Nếu `following` giữ nguyên ≥ 3-5 phiên liên tiếp → mark nick bị shadow-throttle.

## 3. Logic đối soát Watchdog (cnt == 0 rule) — Đúng theo thiết kế

### Rule hiện tại trong `feed_session_watchdog.py`:
```python
if failed and cnt == 0:
    m_to_reported[str(m)] = 0   # Bị nhả liền ngay phát đầu → trừ sạch follow tự nhiên
    failed_reset_machines.append(str(m))
else:
    m_to_reported[str(m)] = cnt + natural_cnt  # Bấm được ≥1 lượt → giữ follow tự nhiên
```

### Lý do logic này ĐÚNG:
- `cnt == 0` tức là **bị nhả liền phát đầu tiên** → chứng tỏ nick đã bị TikTok khóa *trước khi* vào phiên this → mọi lượt follow tự nhiên lúc lướt feed cũng không hợp lệ → **trừ sạch**.
- `cnt > 0` (như M80 bấm được `@allynkapyej` trước khi bị nhả ở nick thứ 2) → chứng tỏ tại thời điểm lướt feed nick còn sống bình thường → **follow tự nhiên hợp lệ, không được trừ**. Đây là logic của user và đúng.

### Tại sao "Lệch -2" cho M80 là noise, không phải bug:
- Watchdog ghi nhận M80: `reported = 1 (chéo) + 1 (tự nhiên) = 2 lượt` → *đúng logic, không trừ*.
- Bước đối soát TikTok Web: Kỳ vọng web tăng +2 nhưng web thực tế tăng +0 (Shadow Action, server không commit).
- Kết quả: Watchdog báo `Lệch -2` → **đây là noise từ Shadow Action của TikTok, không phải lỗi logic code**.

### Cách đọc báo cáo khi thấy "Lệch":
| Pattern | Nguyên nhân | Action |
|---|---|---|
| `Lệch -N` với máy có `cnt == 0` | Bug code — watchdog không trừ đúng | Fix code |
| `Lệch -N` với máy có `cnt > 0` và `FOLLOW_FAILED` | Shadow Action — TikTok drop backend | Accept as noise, check snapshot DB |
| `Lệch -N` với máy `status: OK`, `cnt == 0` tự nhiên | Nick bị shadow-throttle ngầm từ trước | Kiểm tra snapshot DB nhiều phiên |

## 4. Summary cho M76 — Vì sao không follow được ai

M76 Row 4 (`@loanau4423`) **hoàn toàn đủ điều kiện** (9 video, 42 ngày tuổi, không cooldown). Lý do 0 lượt:
- File `taikhoan_run_safe_combined.xlsx` bị lỗi dồn dòng (xem `combined-safe-workbook-positional-slot-preservation.md`).
- Sau fix combined workbook: Row 4 của M76 trả về đúng `@loanau4423` (budget = 3 lượt).
- Mode 2 chạy trước (anchor Tik1/Tik2), nếu không khớp → Mode 1 Search Follow chạy bù đủ budget (đây là behavior đúng — `mode="both"` trong `follow_engine.py`).
