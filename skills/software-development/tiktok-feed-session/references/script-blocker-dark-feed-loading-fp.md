# SCRIPT_BLOCKER: dark-feed loading false positive + bounded-slot output contract

Nguồn: session 2026-08-07, incident `20260807-170007` machine_3, slot-2 (deepseek-v4-pro/high).

## Tóm tắt root cause

- Run manifest: `final_status=manual-needed`, `stop_reason="TikTok startup/loading screen detected"`,
  1/24 swipe completed, 10x manual-needed, cleanup skipped `preserve_blocker_screen`.
- Mỗi capture post-swipe (`swipe_1_after` + `loading_retry_1..6` + `back_recheck`):
  `xml_detected_screen=for-you` (conf 0.9, `manual_needed=false`) NHƯNG `detected_screen=manual-needed:loading`
  vì image classifier đè: `classification_source=image-loading-screen`, image conf 0.79,
  markers `[mostly_dark_splash, center_logo_or_spinner, loading_bottom_region]`.
- Nguyên nhân thật: **video feed tối màu (S7, nhẫn/vàng trên nền đen)** bị heuristic
  "loading screen" match nhầm. Kể cả image classifier cũng thấy top-tab `for-you` được chọn
  (`image_loading_selected_top_tab=for-you`), nên XML đã render feed là nguồn tin cậy hơn.
- Asymmetry cũ: khi `capture_handler_verified=true`, `verified-capture-handler-xml` thắng image
  marker → for-you OK; post-swipe `capture_handler_verified=false` nên image thắng → block. Đây
  là lỗi không đối xứng.

## Handler đã chốt (consumer-local, KHÔNG automation-core)

`python_runner/flows/calibrate_screens.py::_merge_xml_classification()`:
thêm nhánh **`verified-feed-xml`** — khi `details.detected_screen == "manual-needed:loading"`
và `screen in {*TOP_TAB_TERMS, *BOTTOM_TAB_TERMS}` và `not manual_needed`
→ trả về chính `screen` (feed/profile), `manual_needed=False`, `classification_source=verified-feed-xml`.

**Fail-closed an toàn (QUAN TRỌNG):** chỉ ưu tiên feed/profile. Khi XML ra
`unknown` / `manual-needed:login` / `manual-needed` (login/OTP/2FA/captcha/security) vẫn quay về
đường chặn ban đầu — KHÔNG BAO GIỜ biến popup login/account thành feed success. Test
`test_loading_marker_still_beats_unknown_and_manual_needed_xml` khóa hành vi này.

- Compat entry: `docs/ui-compatibility.md` mục "Dark-video feed vs screenshot loading marker
  (2026-08-07, SCRIPT_BLOCKER)".
- Base test: `tests/test_calibrate_screens.py` (`test_rendered_feed_xml_beats_dark_feed_loading_false_positive`,
  `test_rendered_profile_xml_beats_loading_false_positive`, `test_loading_marker_still_beats_unknown_and_manual_needed_xml`,
  + cập nhật `test_screenshot_loading_marker_beats_selected_feed_xml`).

## Contract của bounded-recovery slot worker (QUAN TRỌNG — vì sao fix có thể vẫn KHÔNG chạy)

Lesson lớn nhất: **handler đúng + test pass CHƯA đủ — decision phải được EMIT đúng máy-readable để runtime re-run.**

- Runtime (recovery_runtime.py) đọc output worker từ `run_root/deepseek-executor-result.json`
  (slot dir dưới `.ai-runs/schedule-recovery/<incident>/slot-N/`). Khi file đó **rỗng** (`{}`),
  runtime ghi lease `DEEPSEEK_EXECUTOR_NOT_READY` reason `structured-patch-decision-required`
  và KHÔNG tự re-run — kể cả khi patch đã nằm trong working tree.
- Chuỗi cần đúng: `PATCH_READY` decision hợp lệ → `build_strategy_manifest` (strategy_fingerprint
  phải MỚI, không trùng slot trước — nếu trùng sẽ `STRATEGY_NOT_READY`) → `validate_handler_gate`
  → audit → `RECOVERING` → `_run_bound_handler` (re-run live). Nếu `enable_live_recovery=false` →
  `LIVE_GATED` dừng an toàn.
- Khi debug "sao fix chưa chạy": mở `python_runner/runs/schedule-recovery-ledger.jsonl`, lọc theo
  `incident_key`, xem event `PATCH_ATTEMPT_RESERVED` / `*_EXECUTOR_NOT_READY` / `STRATEGY_NOT_READY`
  của từng slot — đây là nguồn sự thật việc runtime có nhận decision hay không.

## Kỹ thuật kiểm chứng test pre-existing (pitfall)

Để xác định 1 test fail là do patch hay pre-existing:
- KHÔNG dùng `git stash` toàn file test — nó XÓA file khỏi working tree → pytest báo
  `ERROR ... <file>` (collection error), KHÔNG phải kết quả thật. Sai lầm này làm nhầm "pre-existing".
- Đúng: `git checkout HEAD -- <code-under-test>` (chỉ revert file source đang test), GIỮ NGUYÊN file
  test, rồi chạy lại → nếu vẫn fail giống nhau là pre-existing. Xong restore bản patch lại.
  (Lưu ý Windows/CRLF: khi restore dùng `cp <backup>` chứ không để path thiếu đuôi.)

## Reproduce offline trước khi kết luận (kỹ thuật chuẩn, KHÔNG cần device)

Để xác định nhanh 1 complaint SCRIPT_BLOCKER/loading/block là **false positive** hay thật,
chạy CẢ HAI classifier trên artifact đã lưu (offline, không đụng ADB/TikTok) và so sánh:

```bash
PYTHONPATH=python_runner python -c "
import sys, xml.etree.ElementTree as ET; sys.path.insert(0,'python_runner')
from core.classifier import classify_tiktok_screen
import core.classifier as C
from automation_core.tiktok.image_navigation import (
    detect_tiktok_loading_screen, detect_selected_top_tab, detect_top_tab_underline)
base=r'<run_dir>/artifacts/<dev>/<acc>/feed-session-smoke/'
for st in ['before_swipe','swipe_1_after','swipe_1_after_loading_retry_6','swipe_1_after_back_recheck']:
    root=ET.fromstring(open(base+st+'/attempt_1/ui.xml',encoding='utf-8').read())
    cls=classify_tiktok_screen(root)          # XML classifier
    b=open(base+st+'/attempt_1/screen.png','rb').read()
    load=detect_tiktok_loading_screen(b)      # image loading heuristic
    top=detect_selected_top_tab(b)
    print(st, 'xml=',cls.screen, float(cls.confidence), '| img_loading=', 
          round(load.confidence,3) if load else None, '| top_tab=', getattr(top,'tab',None))
"
```

Tiêu chuẩn: nếu **image detector báo loading (conf 0.75-0.8, markers
`mostly_dark_splash`/`center_logo_or_spinner`/`loading_bottom_region`) NHƯNG XML classifier trả
`for-you` conf 0.9 (selected tab + Home)** → FALSE POSITIVE (dark video) chứ không phải màn hình
kẹt. Screenshot thật (vision) là chủ đề: một feed đã render đầy đủ (like/comment/share) chứng minh thêm.
Ở chiều ngược: một màn hình loading/splash thật sẽ cho XML trả `unknown`/rỗng (không đủ markers) →
không bao giờ bị nhầm thành success.

## Frame của slot — đọc đúng tên file thật

- Thư mục advisor slot (`.ai-runs/schedule-recovery/<incident>/slot-N/`) có thể KHÔNG có
  `advisor-plan.txt` — nó chứa **`repair-prompt.txt`** (chính là prompt giao cho slot worker).
  Đừng tìm `advisor-plan.txt` nếu không thấy; nếu chỉ có `repair-prompt.txt` thì validate trực
  tiếp artifact (manifest + log.jsonl + screenshot) thay vì trông chờ plan rời.
- **Fix đúng nhưng runtime vẫn đè**: khi log.jsonl vẫn ghi `classification_source=image-loading-screen`
  NHƯNG working tree đã có nhánh `verified-feed-xml` → nghĩa là fix CHƯA được runtime dùng (slot chạy
  trên bản cũ, hoặc file chưa commit/load). Đây KHÔNG phải lỗi handler; nó là minh chứng lại bài học
  "working-tree fix ≠ live runtime" — xem phần contract bounded-slot bên trên. Luôn đọc `classification_source`
  trong log.jsonl (image-loading-screen vs xml vs verified-*) để biết classifier nào đè lên.

## Chạy test đúng interpreter

- KHÔNG dùng python/PYTHONPATH từ Hermes venv (shadow PIL → `ImportError: _imaging`). Dùng
  interpreter consumer thật:
  `PY="D:/Taadaa/python-envs/automation/Scripts/python.exe"` → `"$PY" -m pytest <tests> -q`.
- Pytest cache warning `Permission denied ... .pytest_cache` = harmless, không phải fail.