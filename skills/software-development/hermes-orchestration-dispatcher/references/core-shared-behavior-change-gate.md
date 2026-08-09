# Core shared-behavior change gate — jitter `tap_element` rollout (2026-08-08)

Case thật: thêm random jitter ±4-6px vào `automation-core\src\automation_core\input.py::tap_element` (default-ON, opt-out `jitter_max_offset=0`) để phủ anti-detect cho MỌI consumer. Đây là shared-core behavior change → Sol gate bắt buộc; Sol bắt đúng 3 fix CHUẨN cho class task này.

## Verdict chain (ghi lại để không lặp vòng lặp audit)

| Vòng | Model (qua 9router) | Verdict | Fix áp |
|---|---|---|---|
| luna v1 | `oc/deepseek-v4-flash-free` (configured -- port 20128, body file via curl) | Conditional Approve | 1) evidence exact-coordinate tests giữ literal — KHÔNG relax range; 2) dismiss_pop pass-forward param; 3) test tap_selector pass-through; 4) double-jitter check ALL types. |
| luna v2 | oc-free | APPROVED (4/4) | — |
| sol v1 | `cmc/gpt-5.6-sol` → NO_CONTENT, v98/gpt-5.4 429 → `oc/deepseek-v4-flash-free` (Sol-prompt) | SOL_APPROVE_WITH_FIXES | (1) scan TOÀN BỘ test literal (test_core.py etc) — chỉ test_tiktokol tự tap_element cần fix; (2) CHANGELOG + pyproject bump + __init__ export check; (3) test dismiss forwards jitter. |
| sol v2 (oc-free) | SOL_APPROVED (3/3) | — | dispatch worker |

## 3 fix chuẩn (mọi core behavior change tương tự phải có sẵn trong plan NGAY VÒNG ĐẦU)

1. **Versioned artifacts** — `CHANGELOG.md` entry (vd `## 0.4.38 - <date>` mô tả thay đổi) + `pyproject.toml` version bump + check `src/automation_core/__init__.py` export (đổi signature keyword-only có default = backward-compatible → KHÔNG cần sửa export, chỉ verify).
2. **Scan TOÀN BỘ test file có assert literal/behavior liên quan** — `rg -l '"input", "tap"' tests/` (không chỉ "file liên quan"):
   - Assert evidence-bound (COMPAT-USB-001 `(270,81)`, popup X coordinates) → GIỮ NGUYÊN literal: truyền opt-out (`jitter_max_offset=0`) tại call-site TEST — mục đích test = verify coordinate selection đúng evidence. KHÔNG relax thành range khi chưa user sign-off.
   - Test shell-direct path (usb_popup/usb_debugging/device_recovery gọi `adb.shell(["input","tap",...])` trực tiếp — không qua tap_element) → KHÔNG bị jitter, KHÔNG cần sửa. Phải xác minh bằng đọc code (rg `tap_element` trong src file đó) trước khi cho là "không đụng".
   - Test mới: (a) jitter range (50 lần assert |d|∈[4,6]); (b) jitter=0 giữ literal center; (c) pass-through (tap_selector); (d) forwarding qua hàm trung (dismiss_popup jitter=0 → literal, default → range). KHÔNG dùng `random.seed` global (side-effect vào RNG state test khác).
3. **Thiết kế default-ON + opt-out keyword param** cho evidence-bound; param keyword-only (`*, jitter_max_offset: int = 6`) — backward-compatible call sites.

## Transport lộ: curl `--data @file` (urllib 502 chết)

- Python `urllib.request` POST prompt ~6KB+ unicode → 502 `k.messages.map is not a function` (9router translate bug). Cùng body qua curl `--data @body.json` chạy OK. Recipe: python `json.dumps` → file tạm → `subprocess.run(["curl","-s","-m","300","-X","POST","http://127.0.0.1:20128/v1/chat/completions","-H","Authorization: Bearer $NINEROUTER_API_KEY","-H","Content-Type: application/json","--data","@body.json"], cwd=...)`.
- Parse tolerant: response nhiều JSON dính → đếm depth `{`/`}`, chọn object có `choices[].message.content` non-empty.
- Model routing order 2026-08-08: `v98/gpt-5.4` 429 (`Something wrong`) — v98 throttled từ sweep bulk-test; `cmc/deepseek/*` 429 weekly-plan (3m+); `cmc/gpt-5.6-sol` NO_CONTENT (không route cmc pool). `oc/deepseek-v4-flash-free` là fallback cuối ổn định — ghi model thật dùng trong verdict file.

## Scope thực thi (worker leaf spec được audit APPROVED)

- 6 file: `src/automation_core/input.py` (+`import random`, `_jitter(coord,max_offset)` = `coord + random.choice((-1,1))*random.randint(4,max_offset)`, `tap_element(..., *, jitter_max_offset=6)`, `tap_selector` pass-through); `src/automation_core/tiktok_popup.py` (`dismiss_popup(..., *, jitter_max_offset=6)` → 2 call `tap_element`); `tests/test_tiktok_popup.py` (evidence call → `jitter_max_offset=0`); `tests/test_input_jitter.py` (4 test mới); `CHANGELOG.md`; `pyproject.toml` (0.4.37→0.4.38).
- KHÔNG sửa: `usb_popup.py`, `usb_debugging.py`, `device_recovery.py`, `test_usb_*.py`, `test_ui_dump.py`, `__init__.py`, consumer repos (Tiktok_Reg/register gmail đã jitter local — 1 twos, không double).
- Verification: `PYTHONPATH=src python -m pytest tests/test_tiktok_popup.py tests/test_input_jitter.py -q` + `tests/test_usb_popup.py tests/test_usb_debugging.py tests/test_ui_dump.py -q` (không regress) + py_compile + `git diff --stat` = đúng 6 file + double-jitter grep `rg -n '"input", "tap"'` consumer repos tất cả .py/.ps1/.bat/.sh.

## Verdict kết luận từng vòng và tài trợ (cho người audit mang tin)

- Audit lead: `dùng oc-free fallback` (Sol không routable) — chấp nhận vì bắt được CHANGELOG/version/scan-all/forward-test cùng tier với Sol.
- `Conditional / APPROVE_WITH_FIXES` = SỬA PLAN (không implement); `REJECT` = re-plan; chỉ `APPROVED`/`SOL_APPROVED` mới dispatch worker.