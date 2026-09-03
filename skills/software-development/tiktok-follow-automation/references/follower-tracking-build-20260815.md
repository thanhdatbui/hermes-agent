# Build 2026-08-15: random budget + follower tracker (follow repo) — write-at-end

Trạng thái: ĐÃ implement theo design CHỐT (write-at-end), `pytest follow_runner/tests`
= 283 passed (16 test mới: random budget + follower tracker + export CLI). CHƯA canary
live — chờ nuôi acc xong hook nối. File plan: `.hermes/plans/2026-08-15_feed-then-follow.md`.

> ⚠️ Bản đầu của reference này mô tả `upsert_follower` ghi thẳng Excel từng máy —
> **ĐÃ BỊ THAY** giữa session vì user đúng: nhiều máy song song ghi chung 1 Excel =
> race/corrupt. Design cuối = write-at-end (state JSON per-machine + export 1 lần).

## Mục tiêu (user chốt)
- Follow chéo nối sau feed-session nuôi acc (3 phiên/acc/ngày account-block).
- Range follow chéo mỗi phiên: **5–10** (user nâng từ 5–7, chấp nhận rủi ro để
  hoàn vốn nhanh — ông anh chạy 50/ngày).
- Đếm follower mỗi acc (theo dõi tiến độ 1k + phát hiện nhả follow từ từ) —
  user đọc bằng Excel (export cuối ngày).

## Thay đổi 1: random budget/phiên
- `config.py` FollowConfig thêm `budget_per_session_min: int|None = None`,
  `budget_per_session_max: int|None = None`. Validate: nếu set 1 trong 2 →
  `0 < min <= max`.
- `follow_state.py` thêm `session_budget()`:
  ```python
  def session_budget(self) -> int:
      self._roll_day()
      remaining = self.budget_remaining()
      if remaining <= 0: return 0
      min_s = getattr(self.cfg, "budget_per_session_min", None)
      max_s = getattr(self.cfg, "budget_per_session_max", None)
      if min_s is not None and max_s is not None and int(min_s) <= int(max_s):
          pick = random.randint(int(min_s), int(max_s))
      else:
          pick = int(self.cfg.budget_per_session)
      return min(pick, remaining)
  ```
- `mode1_search_follow.run_mode1`: `budget = min(state.session_budget(),
  state.budget_remaining())` (thay `int(cfg.budget_per_session)`).
- PITFALL test: helper `_cfg` default `budget_per_day=5` → cap mọi pick về 5,
  test random range phải set `budget_per_day=30` mới thấy range.

## Thay đổi 2: follower tracker (module mới)
`follow_runner/core/follower_tracker.py` + `tests/test_follower_tracker.py`:

### Selector (tái dùng kiến thức stat counters)
- 3 stat chung 1 resource-id trên profile: "Follower N" / "Đã follow N" /
  "Thích N" — `id/sdn` (máy 1), `id/shq` (máy 2).
- `extract_follower_count` chỉ chấp nhận node có text chứa "Follower"/
  "Người theo dõi" — KHÔNG nhầm "Đã follow"/"Thích" (cùng id).
- UIElement (automation_core.ui) là dataclass: dùng `.resource_id`/`.text`,
  KHÔNG có `.get()` (AttributeError nếu dùng .get như dict).

### parse_count edge cases (đã test)
| Input | Kết quả | Logic |
|---|---|---|
| "127 Follower" | 127 | plain |
| "1.2K Follower" | 1200 | K → ×1000, dấu chấm = thập phân |
| "12,5K Người theo dõi" | 12500 | dấu phẩy = thập phân EU khi có K |
| "1,024 Followers" | 1024 | dấu phẩy 3 số = phân tách nghìn (không K) |
| "127 Đã follow" | None | label không phải follower |
| "356 Thích" | None | label không phải follower |

Regex tách: `^([\d.,\s]+[KM]?)\s*(.*)$` (IGNORECASE).

### Design write-at-end (CHỐT — thay upsert Excel trực tiếp)
- **Runtime (mỗi máy, không race):**
  - `record_follower_in_state(machine, cfg, tik_id, count)` → ghi vào
    `follow_state_<máy>.json` map `followers[tik_id] = {count, date}` (upsert field,
    atomic tmp+os.replace). KHÔNG đụng Excel.
  - `detect_follower_drop_state(machine, cfg, tik_id, current, threshold_pct=10)`
    → so với entry cũ trong CHÍNH state JSON máy đó.
- **Export (1 lần, write-at-end):** `follow_runner/export_follower_tracking.py`
  CLI `--state-dir runs/state --output <xlsx>` → `collect_followers()` đọc mọi
  `follow_state_*.json` → `export_follower_tracking()` ghi 1 Excel
  `("May","ID","Follower","Ngày ghi")`. Pattern barrier giống
  tiktok-reg/gmail-reg `merge_success_results` — chạy sau khi hết máy, 1 process.
- **BẮT BUỘC không ghi vào `taikhoan_run_safe.xlsx`**: nuôi acc
  `scripts/sync-safe-workbook.py` assert header đúng 3 cột
  `OUTPUT_COLS = ("May", "Device ID", "ID")` (dòng ~175-176) → thêm cột = vỡ sync.

### Wiring
`verify_follow.verify_after_tap` → helper `_track_follower(engine, uid, xml)`:
- Gate `engine.cfg.extra.get("follower_tracking", False)` — tắt mặc định nếu config
  không bật.
- Gọi ở 2 nhánh success: trong `_confirm_not_released` (sau swipe confirm) +
  success trực tiếp sau `classifier(_dump()) == "followed"`.
- Fail-silent: lỗi tracking không ảnh hưởng kết quả follow (try/except pass).

## Cần làm nốt (chưa commit)
- Config mẫu `config.example.yaml` ĐÃ thêm: `budget_per_session_min: 5`,
  `budget_per_session_max: 10`, `follower_tracking: true`.
- Commit chưa làm (chờ user; AGENTS.md có diff sibling — giữ nguyên, commit file riêng).
- Nuôi acc sau: organic rate 5→10–12%, hook cuối phiên gọi
  `run_follow.py --machine N --config ...`, cuối ngày chạy export_follower_tracking.

## Ghi chú session
- AGENTS.md bị sibling subagent thêm "session-start context" block giữa session
  — `git diff AGENTS.md` thấy, giữ nguyên (không revert).
- UI-first: follower count đọc từ UI profile đang xem (target nick), không phải
  nick mình đứng — đúng kiểu ghi #2 user chọn (update theo nick tìm kiếm).
- Nhả-follow 2 dạng: (a) nhả NGAY sau tap → `_confirm_not_released` bắt ~5–10s;
  (b) nhả TỪ TỪ sau giờ/ngày → chỉ thấy bằng follower count giảm → tracker daily.
