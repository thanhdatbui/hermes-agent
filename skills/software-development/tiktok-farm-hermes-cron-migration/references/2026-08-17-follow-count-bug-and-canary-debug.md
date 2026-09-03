# 2026-08-17 — follow hook followed_count bug + canary debug evidence

## Bối cảnh
Canary 5 máy (1-5) sau khi fix automation-core 0.4.45 + live-wiring 3 cron job paused.
Kết quả feed: máy 1,2,5 success / máy 3 manual-needed / máy 4 login screen (user bỏ qua).

## Bug 1 — `followed_count` luôn 0 dù follow thật (P1, đã fix)

File: `python_runner/flows/multi_machine_feed_session.py` `_run_follow_hook`

```python
# CŨ (sai):
result["followed_count"] = int(parsed.get("followed", 0) or 0)
# MỚI (đúng):
followed_list = parsed.get("followed")
result["followed_count"] = len(followed_list) if isinstance(followed_list, list) else int(followed_list or 0)
```

- `FOLLOW_RESULT` từ `run_follow.py _result_payload` trả `"followed": [list nick]` — list, không phải int.
- `int(list)` → TypeError → `except (ValueError, TypeError): pass` → count giữ 0.
- **Bằng chứng máy 1 (đợt 73 máy accident)**: `follow_result.json` có
  `{"status":"OK","followed_count":0,"followed":["yabsley1990","bch.ngc.ngc91","m.my7409","songiang07","lamdao01021999"]}`
  trong khi `runs/state/follow_state_1.json` có nick follow 00:23-00:31 (8 nick đầu ~00:23-00:31 theo giờ VN).
- **Bài học**: `follow_state_<máy>.json` = nguồn sự thật (dict `followed: {nick: ISO_timestamp}`),
  `follow_result.json` chỉ là báo cáo. Luôn đối chiếu cả 2.

## Bug 2 — `_is_account_switcher_sheet` quá strict (đã fix, consumer classifier)

File: `python_runner/core/classifier.py`

```python
# CŨ (sai): yêu cầu selected element có class android.widget.button
has_selected_account = any(
    element.attrib.get("selected") == "true"
    and bool(element.text.strip() or element.content_desc.strip())
    and "android.widget.button" in element.attrib.get("class", "").lower()
    for element in element_list
)
# MỚI (đúng): bỏ yêu cầu class — TikTok render nick active là TextView
has_selected_account = any(
    element.attrib.get("selected") == "true"
    and bool(element.text.strip() or element.content_desc.strip())
    for element in element_list
)
```

- Máy 3: switcher mở đúng (title "Chuyển đổi tài khoản", 3 nick `trangtran168432`/`ninhy05100`/`lequynh2043`,
  nick active `ninhy05100` = TextView `selected="true"` bounds [252,1110][900,1170]).
- Trước fix: classifier → bucket khác → `manual-needed`, flow không tới `_find_account_switch_option`
  (feed_swipe_smoke.py:13947) + `tap_expected_account` → sau đó "TikTok focus lost" (extra `detected_screen:
  com.android.systemui`), session fail.
- Sau fix: `classify_tiktok_screen` → `manual-needed:account-switcher` (0.9) + 
  `_is_legitimate_profile_account_switcher_xml(xml, "trangtran168432")` = True. Máy 3 chạy lại (đúng cách
  `-Machines 3` không Preset) → **feed success 29/29**, `verify_profile` "profile matched account".

## Bẫy canary: `-Preset full` chạy cả farm

- Session bash kế thừa env Task Scheduler cũ: `TIKTOK_FEED_ASSIGNMENT_MANIFEST=C:\Users\Kibe\AppData\Local\
  automation-core\assignments\tiktok-feed.json` (resources machine:1-74) + `TIKTOK_FEED_WORKER_ID=taadaa-writer-...`.
- Gọi `-Preset full -Machines 1,2,3,4,5` (không LocalRun) → nhánh Preset bỏ qua `-Machines`, discover toàn bộ
  máy row từ workbook → 73 máy chạy thật 1h, artifact `.ai-runs/20260817-005226/machines/machine_{1..74}`.
- Lợi ích phụ: chính đợt này cho kết quả follow các máy (xem bảng dưới).
- **Đúng**: không Preset không LocalRun + `-Machines 1,2,3` (nhánh else) — assignment gate lọc máy ∈ resources.

## Kết quả follow đợt 73 máy (evidence so sánh follow_result vs state)

| Máy | follow_result.json | follow_state_<máy>.json (thật) |
|---|---|---|
| 1 | OK, followed_count 0, followed [5 nick] | state_1: 13 nick 00:23+ (đợt này follow 8 nick) |
| 2 | MANUAL_REVIEW OPEN_TIKTOK_FAILED — TikTok không load feed sau retry | — |
| 3 (đợt 73) | MANUAL_REVIEW exact profile identity không khớp sau tap | — |
| 5 | CONFIG_ERROR VERIFY_IDENTITY fail nick không khớp @khnh.vyyyy6 | — |

Nhiều máy khác follow thành công đợt đó (state_32: 10 nick 01:45-01:57, state_15: 8, state_71: 9,
state_14: 5, state_17: 6, state_6: 6, state_8: 8, ...) — chứng minh follow hook chạy thật toàn farm,
chỉ follow_result count sai.

## Cấp độ lỗi (fix consumer trước, không đụng core)

- account switcher → consumer `core/classifier.py` (tiktok-follow dùng `core/popup.py` riêng, không qua
  `detect_allowed_generic_popup` → fix consumer đủ).
- follow identity → tiktok-follow repo `verify_follow.py:296` / `mode1_search_follow.py:106`.
- Chạy import kiểm tra: `PYTHONPATH="" python -B ...` — nếu thiếu, python resolve về hermes venv 0.4.43
  thiếu `automation_core.escalation` (chỉ có từ 0.4.45) → nhầm "lỗi automation_core" khi thật ra là
  PYTHONPATH leak. Đã gặp: `flows.feed_swipe_smoke` import `automation_core.escalation` bị ModuleNotFoundError
  khi chạy từ session có PYTHONPATH trỏ hermes.