# Follow Hybrid — thiết kế build cuối 16/08 (mode 2' = Following-list nội bộ + module 1 bù)

Mốc: user chốt tối 16/08 sau khi phân tích workflow ông A. THAY THẾ hướng
"CHỈ mode 1, bỏ mode 2" (commit `1d61bb6`, sáng 16/08). Sẵn sàng TDD:
viết test trước (RED) → impl → GREEN → full suite → canary 1 máy budget 1.

## Logic tổng (budget tính trên NICK, cap 30/ngày, không nghỉ)

- Mỗi ngày 3 ca, mỗi ca 1 ACC khác nhau (đã chốt 16/08 sáng), mỗi ca 2–3 phiên
  feed. Follow chạy cuối mỗi phiên qua hook đã nối sẵn:
  `tiktok-luot nuoi acc/python_runner/flows/multi_machine_feed_session.py:500-746`
  `_run_follow_hook` → subprocess `python -m follow_runner.run_follow`
  (cwd `D:\Taadaa\tiktok-follow`, timeout 900). Không build lại phần nối.
- Budget/phiên: phiên 1,2 random 5–10; **phiên 3 bù**: `target = randint(20,30)`,
  `phiên3 = clamp(max(5, target − sum 2 phiên), 0, budget_remaining())`.
  `FollowState.session_budget()` mở rộng để nhận tổng đã dùng (state JSON
  per-machine `runs/state/follow_state_<máy>.json` có `budget_used` theo host
  clock + timezone Asia/Ho_Chi_Minh).
- **Gate video theo nick** — đọc `TikN.xlsx` cột `Video Đã Đăng` theo
  `account_row_index` của máy (Tik1=row1, Tik2=row2, tik3=row3 — xem
  tiktok-workbook-slot-mapping). ≥10 → full; <10 (kể cả 0) → **nửa budget**.
  KHÔNG gom Tik file (AccountSource machine mode = first-row only; race ghi
  cột Video Đã Đăng khi 2 runner cùng file).
- Trạng thái thật 16/08: Tik1 75/80 ID (đa số 8–15 video), Tik2 73/80 (69 máy
  mới **1 video**), tik3 63/80 (**0 video**). Follow state chỉ có máy 1,2,6,11.

## Mode 2' (module chính) — tái dùng từ `mode2_follow_followers.py` (730 dòng)

ĐÃ ĐỌC code (đừng đọc lại toàn bộ): chỉ cần các hằng/nút sau từ skill chính:
- Tab Follower profile: `FOLLOWER_TAB_RESOURCE_ID = com.ss.android.ugc.trill:id/sdn`
  text "Follower". Following nằm trên CÙNG profile, headers có sẵn
  `FOLLOWER_LIST_HEADERS = ("Đã follow", "Follower", "Bạn bè", "Được đề xuất")`.
- List: `FOLLOWER_LIST_RECYCLER_ID = ...:id/u5r`; row username
  `...:id/txt_desc`; nút follow `...:id/tcj` clickable.
- Tái dùng NGUYÊN (không sửa): `_parse_mode2_nodes` (giữ `selected`),
  `_classify_follower_surface` (populated|empty|invalid),
  `_collect_follower_rows`, `_follow_button_for_row`, `_exact_current_row`,
  `_classify_row_button`, `_verify_row_after_tap`, `_path_b_verify`,
  `_back_to_feed` (feed gate trước mỗi seed), `_is_search_history_screen`.
- ĐỔI: `_open_follower_tab` → `_open_following_tab` — sau khi verify @uid,
  tap TAB "Đã follow"/"Following" (semantic text, nhiều máy layout khác nhau
  → dùng `_semantic_text` + `android:id/text1` selected thay vì hardcode id),
  xác nhận surface bằng `_classify_follower_surface` (headers đã gồm "Đã follow").
- THÊM bộ lọc nội bộ: trong vòng follow, row có
  `_normalize_handle(uid row) ∉ farm_set` (`farm_set = {casefold(tik_id) cho
  toàn bộ safe workbook}`) → skip (KHÔNG follow, KHÔNG mark state — như
  semantics `failed_ids`/skip của mode 1).
- Hybrid: mode 2' chạy trước (0 search, follow nick farm trong following của
  anchor). Hết UID nội bộ trong list mà chưa đủ budget → nối `run_mode1`
  (đã có: search → profile → follow → `_confirm_not_released`) bù đủ budget
  phiên. `run_session` hiện chạy `mode1 rồi mode2` → ĐẢO: mode 2' TRƯỚC, mode 1
  sau (bù). Dòng `if mode in ("2","both")` + `_mode2_module_available` giữ.
- **Ưu tiên anchor**: nick Tik1/Tik2 (following dày, đã seed). KHÔNG anchor
  tik3 mới → list trống → rơi hết vào mode 1 = đúng cái cần tránh (search dày).
- Search bù: ưu tiên search nick trong Tik1/Tik2 list (following dày), không
  search random nick mới.

## Bỏ follower-count tracker, thêm following tracker

- Gỡ: `verify_follow._track_follower` + wiring 2 nhánh success trong
  `_confirm_not_released`; `core/follower_tracker.py`
  (`extract_follower_count`, `record_follower_in_state`,
  `detect_follower_drop_state`); `export_follower_tracking.py`; test tương ứng.
  Lý do (user chốt): nhả liền → `_confirm_not_released` bắt; nhả từ từ sau
  vài ngày = nick follower die (ban), không cứu được → kệ. Theo dõi vô ích.
- THÊM following tracker (đếm nick farm đã follow): state JSON per-machine,
  field `following_count` (hoặc reuse `followed` map + tool đếm). Mục đích
  DUY NHẤT: biết khi nào following đủ dày → chuyển hẳn mode 2' (không cần
  mode 1 bù). KHÔNG export Excel bắt buộc.
- Config: bỏ `extra.follower_tracking: true` khỏi config.example.yaml;
  `FOLLOWED_TEXT`/selectors giữ nguyên.

## TDD plan (thứ tự test → code)

1. `test_follow_state.py` mở rộng: `session_budget()` phiên 3 bù
   `max(5, target−sum)` clamp daily remaining (inject clock).
2. `test_mode2_follow_followers.py` (rename semantics): `_open_following_tab`
   tap tab "Đã follow" + surface đúng; bộ lọc nội bộ skip UID ngoài (Fake
   XML dump có row ngoài + row trong → chỉ follow row trong, row ngoài
   skipped, KHÔNG mark state); hybrid: following hết → mode 1 bù.
3. `test_verify_follow.py`: gỡ `_track_follower` (assert không gọi follower
   tracker; following mark vẫn chạy).
4. `test_cli.py`: mode 2' chạy trước mode 1 khi `mode: both` (thứ tự loop).
5. Full suite `pytest follow_runner/tests` + `py_compile` + `git diff --check`.
6. Canary máy thật budget 1 (theo Live canary discipline skill chính).

## Pitfall đã biết khi build

- `mode2` cũ từng fail "hồ sơ thiếu handle (@uid)" khi follow FOLLOWER người
  lạ → following list nội bộ có @uid đầy đủ nên HẾT lỗi này (không phải sửa
  gì thêm — chỉ chắc chắn `_open_following_tab` verify @uid trước tap như cũ).
- `FOLLOWER_LIST_HEADERS` gồm cả "Đã follow"/"Following" — `_classify_follower_surface`
  hiện fullmatch regex `^(follower|followers|người theo dõi)...` → PHẢI mở rộng
  regex label thêm "đã follow"/"following" khi chuyển tab, nếu không surface
  trả `invalid` → dừng.
- Swipe list dùng `swipe_feed` (1) đã đủ; max_scrolls 40 giữ.
- Budget nhân với gate: nửa budget = phiên 3 bù tính TRƯỚC khi nhân 0.5 (làm
  tròn lên tối thiểu 1 follow nếu nick <10 video nhưng budget bù > 0).