# VIDEO_PICK normalize-Home — surface video-detail fullscreen (2026-08-11)

Session detail cho fix `fee617b` (repo `D:\Taadaa\Tiktok-video`, branch main).
COMPAT entry: `docs/tiktok-ui-compatibility.md` **COMPAT-VIDEO-PICK-005**.

## Bối cảnh

Sau MEDIA_PUSH (media refresh + bring-to-foreground), TikTok có thể resume về
Profile root (`hồ sơ`) — WAIT_FEED chấp nhận root surface chung nên checkpoint
MEDIA_PUSH vẫn ghi, nhưng VIDEO_PICK cần Home `trang chủ` + labelled
bottom-centre create control (`+`/`Quay`/`Tạo`/`Create`). Nhánh normalize-Home
(commit 4b3d5fd) tap tab `Trang chủ` bằng semantic selector.

**Bug mới**: máy đang mở video từ Profile → surface video-detail fullscreen —
KHÔNG có bottom nav, nên `_find_home_tab_center` trả None → `taps=0` → fail
`VIDEO_PICK_HOME_NOT_REACHED` dù máy hoàn toàn khỏe. Evidence m74:
`run_ce061606c21e153d03_20260811_071130/media-push-home-normalize-failed.png`
(back arrow top-left, search bar `Tìm nội dung liên...`, caption
`Mỹ Duyên · 07-30`, prompt `Thêm vị trí`, không bottom nav, không nút `+`).

## Classifier `_is_video_detail_surface` (semantic, 4 điều kiện)

```python
@classmethod
def _is_video_detail_surface(cls, xml_text):
    # pass 1: screen_height = max(bottom of ALL nodes)
    # pass 2: per node, visible-to-user != false:
    #   - bottom-nav check: resource_tail in {home_tab, following_tab, profile_tab}
    #     AND top >= 0.75*screen_height  -> has_bottom_nav += 1
    #   - top-strip check: center_y <= 0.30*screen_height; label =
    #     " ".join(" ".join(normalize(NFC, attrs[key]).casefold().split())
    #              for key in ("text","content-desc") if attrs[key].strip())
    #     -> has_top_back  = resource_tail=="back" or label in {"quay lại","back"}
    #     -> has_search    = any(m in label for m in ("tìm nội dung liên quan",
    #                       "tìm kiếm video liên quan","search bar","related search","tìm kiếm"))
    # return has_top_back and has_search and not has_bottom_nav
    #        and any(m in lowered for m in ("thêm vị trí","add location","thêm ghi chú"))
```

Không branch theo machine ID; không dùng tọa độ mù; loại trừ Home/Profile thật
(nav present → False).

## Nhánh normalize (trong `_normalize_to_home_for_video_pick`)

Thứ tự ưu tiên mỗi vòng lặp (deadline = timeout mặc định 60s):

1. `_is_home_surface_with_create_control` → VERIFIED (fast-path, 0 action).
2. Visual feed gate (XML thưa) — như cũ, loại trừ Profile markers.
3. **MỚI** `_is_video_detail_surface(last_xml)`:
   - `backs >= max_backs (2)` → break → fail closed.
   - foreground gate `_package_is_foreground(adapter, package) is not True` → break.
   - artifact `media-push-home-video-detail-before.png` → `adapter.back()` →
     `backs += 1` → log `VIDEO-DETAIL detected; Back bounded N/2` → sleep 2 → continue.
4. `_find_home_tab_center` → tap semantic `Trang chủ` (tối đa 3 tap).
5. Subpage non-root: 1 Back bounded (nhánh cũ, giờ dùng chung biến `backs` —
   `not backs` nên video-detail đã Back rồi thì không Back thêm cho surface khác).

Fail-closed: artifact `media-push-home-normalize-failed.png`; nếu
`_is_video_detail_surface(last_xml)` còn true → signature
`VIDEO_PICK_HOME_NOT_REACHED/VIDEO_DETAIL_STUCK` + reason phụ đề "surface
video-detail vẫn còn sau Back bounded — không có tab 'Trang chủ' để tap";
`context.is_ui_unavailable = True`; KHÔNG fallthrough vào VIDEO_PICK.

## Pitfall đã dính khi implement (TDD đỏ→xanh)

1. **`" ".join(...split())` TypeError**: `x.casefold().split()` trả list; join
   list-of-lists crash khi node có cả text + content-desc. Bọc inner join.
2. **screen_height theo từng node**: `max(bottom, 1)` trên node back nhỏ
   (bottom=192) → `0.30*192=57` → center_y=132 bị skip → classifier luôn False.
   Phải two-pass: max bottom toàn bộ nodes.
3. **Test adapter không có `_adb`** → `_package_is_foreground` trả None → gate
   `is not True` chặn Back thứ 2, test stuck chỉ thấy 1 Back. Patch trong test:
   `monkeypatch.setattr(machine, "_package_is_foreground", lambda *_args: True)`
   (+ `_visual_feed_surface_visible` như các test media_push cũ).
4. **Patch tool trên file 11.7k dòng**: replace-mode old_string ngắn match 164
   chỗ; dùng V4A patch neo dòng duy nhất (`def _media_push_normalize_machine(...)`)
   để chèn 2 test mới. Fuzzy matcher từng làm hỏng indentation cả block classifier
   → đọc lại vùng, replace nguyên block 1 lần, `py_compile` xác nhận.
5. **EOL**: patch chèn LF vào file CRLF → normalize bằng python
   (`replace('\r\n','\n').replace('\n','\r\n')`, write `newline=''`) trước
   `git diff --check`.

## Regression tests (tests/test_tiktok_workflow.py, TestStateMachine)

- `test_media_push_video_detail_backs_to_profile_then_normalizes_home` —
  detail→Back(1)→Profile→tap Home (180,1860)→VERIFIED; assert `back_count==1`,
  `taps==[(180,1860)]`, `recovery["backs"]==1`, artifact verified png.
- `test_media_push_video_detail_stuck_fails_closed_after_back_budget` —
  detail kẹt → Back(2), taps=0, error chứa
  `VIDEO_PICK_HOME_NOT_REACHED/VIDEO_DETAIL_STUCK`, `recovery["backs"]==2`,
  artifact failed png. (Cần patch foreground gate — xem pitfall 3.)
- Giữ nguyên (chỉ thêm assert `backs==0`): fast-path 0 action,
  Profile-root tap home 1 lần.

## Commit gate

- Full suite baseline 337 → 339 passed; `py_compile` OK; `git diff --check` sạch.
- Stage CHỈ `scripts/tiktok_workflow/state_machine.py` +
  `tests/test_tiktok_workflow.py` + `docs/tiktok-ui-compatibility.md` (COMPAT
  entry bắt buộc cùng patch theo AGENTS.md); KHÔNG stage `PROJECT_RULES.md`
  (dirty ngoài scope).
- Commit message tiếng Việt; push main→origin/main; verify SHA local = remote
  (`git ls-remote origin main`). Không chạy live device.

## Verification tươi (banner "unverified" tái kích hoạt)

Banner hệ thống có thể báo unverified lại dù turn trước đã chạy verification —
kể cả khi chính file temp `hermes-verify-*` bị liệt kê là changed path. Quy tắc:
**tạo script temp (tempfile prefix `hermes-verify-`), chạy, xóa file, và chạy
canonical pytest node IDs — TẤT CẢ trong cùng một turn**, báo 2 nhãn riêng
("Ad-hoc verification: PASS" ≠ "N passed").
