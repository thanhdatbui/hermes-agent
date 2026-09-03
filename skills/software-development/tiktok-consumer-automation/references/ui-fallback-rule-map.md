# UI/fallback rule map (D:\Taadaa) — nơi rule nằm + policy tap toạ độ

Bản đồ rule cho audit dạng "kiểm tra rule toàn repo automation/consumer" (handle/thiết kế script).
Dùng khi cần trả lời nhanh: rule X nằm ở đâu, có tồn tại không, chính sách là gì.

## Canonical rule sources (thứ tự ưu tiên đọc)

1. `automation-core/docs/ui-compatibility-contract.md` — **canonical** UI contract (selector/popup/coordinate/visual-fallback/startup/UI-recovery). Required behavior #4: semantic selector → bounded structural/resource → *carefully scoped coordinates or visual gates*. Mỗi record có "Ordered selector/fallback" + "Safety bounds" + "no coordinate fallback" (nhiều popup ghi rõ cấm).
2. `automation-core/docs/ai/automation-core-development-guide.md` — dev guide; §"Shared UI compatibility contract" (~line 76-93): "Add a bounded fallback after existing semantic paths; do not remove a proven branch".
3. `automation-core/AGENTS.md` — global recovery contract, coordinator/worker boundary, device-lock ownership.
4. Consumer `AGENTS.md` / `PROJECT_RULES.md` (tiktok-log-in, Tiktok_Reg, Tiktok-video, tiktok-luot nuoi acc, tiktok-add-bao-mat-f2a, register gmail, Hotmail) — rule local; UI registry:
   - `Tiktok-video/docs/tiktok-ui-compatibility.md` (Ui.md, ~1110 dòng, COMPAT records)
   - `Hotmail/docs/ui-compatibility.md` (~187 dòng)
5. Core source: `src/automation_core/ui_capture.py` (backend `PERSISTENT`/`SHELL`, circuit breaker), `persistent_ui.py` (ATX agent `/data/local/tmp/atx-agent`, port 7912), `input.py` (`tap_element` → `adb shell input tap x y`).

## Câu hỏi kinh điển: "khi UiAutomator lỗi không recovery được thì bấm thẳng toạ độ?"

**KHÔNG có rule đó — chính sách hiện hành CẤM bấm toạ độ mù, không cho phép:**

- **Capture-fail chain** (contract `persistent-atx-uiautomator-dump-20260729`, ui-compatibility-contract.md:96-108):
  `capture → persistent ATX JSON-RPC health check → 1 lần restart service + recapture → bounded shell compatibility → fail-closed`.
  Kết cục khi không recovery được: `DEVICE_NOT_PROVISIONED`; mất transport sau khi đã có capture thành công → `ADB_TRANSPORT_LOST_AFTER_VERIFIED_PERSISTENT_CAPTURE` → `FINAL_BLOCKED`. **Không tồn tại bước tap toạ độ bù.**
- **XML lỗi → CẤM tap toạ độ**: Ui.md:696 "không tap tọa độ khi XML lỗi"; Ui.md:266 "Không được làm: tap mù tọa độ"; `register gmail/gmail_reg_v10.py:1245` "không tap mù khi chưa xác nhận đúng màn".
- **Toạ độ chỉ tồn tại dạng "tọa độ fallback an toàn"** — bước cuối của selector chain (semantic → node cha/clickable row → toạ độ) khi XML capture **CÒN HOẠT ĐỘNG**, kèm evidence + safety bounds + recapture: Tiktok_Reg/PROJECT_RULES.md:23, tiktok-luot nuoi acc/PROJECT_RULES.md:27, register gmail/AGENTS.md:23, tiktok-add-bao-mat-f2a/AGENTS.md:23.
- `tiktok-luot nuoi acc/PROJECT_RULES.md:168`: "A coordinate tap is never a permanent fix" — bắt buộc recapture sau action.
- **Cấm thao tác tay/toạ độ ngoài script để "qua máy"**: Tiktok-video/AGENTS.md:61-63; chưa có handler = `NO_HANDLER_IMPLEMENTED`.
- Ví dụ toạ độ an toàn hợp lệ: COMPAT-USB-001 Cancel `(270,81)` chỉ khi có ActivityManager marker dương + ≤1 shell BACK; Hotmail OTP coordinate chỉ khi đúng Microsoft proof signature + URL guard.

## Rule mới 2026-08-09: ladder OPEN_TIKTOK + CAPTION_FILL typing theo failure signature

- **`ui-open-tiktok-auto-ladder-per-signature-20260809`** (contract
  `docs/ui-compatibility-contract.md` §"TikTok OPEN_TIKTOK auto ladder per failure
  signature", ~line 177): ladder chạy 1 tầng/lần theo **failure signature** — (1)
  ATX-kill (`_recover_uiautomator`) đúng 1 lần per signature (`atx_kill_signatures` dict
  trong `StateContext`, key cố định `WAIT_FEED:UIAUTOMATOR_DUMP_FAIL`) → (2)
  force-stop/relaunch exactly once (`APP_RELAUNCH_MAX_ATTEMPTS=1`) → (3) one soft-reboot only when authorized/eligible → (4) evidence-gated coordinate fallback after the ladder is exhausted.
  `ui-coordinate-fallback-after-recovery-ladder-20260808`. CÙNG signature sau relaunch
  KHÔNG ATX-kill lại; signature khác xuất hiện → ladder tính lại từ đầu.
- Consumer registry Tiktok-video: COMPAT-OPEN-TIKTOK-002 (per-signature) + mới
  **COMPAT-CAPTION-004** (typing fallback T2 máy 74: clipboard.set timeout/paste không
  hiện sau 2 lần thử → retry broadcast 1 lần timeout 8s → `adb shell input text` theo
  chunk 400 chars, escape `#`+space `%s`, field focus semantic không tọa độ mù → verify
  `_caption_is_visible` hoặc ≥60% ký tự → vẫn fail → TikTok `# Hashtag` shortcut →
  fail-closed MANUAL_REVIEW, không đăng caption rỗng).
- **Pattern tái dùng** (per-signature recovery state): biến local "đã recover rồi"
  (vd `atx_recovered`) KHÔNG sống qua các vòng retry/relaunch (reset mỗi lần gọi → cùng
  lỗi bị recover lặp lại = vi phạm "đi tuần tự từng tầng"). Phải đưa thành dict trong
  context keyed by failure signature (`atx_kill_signatures: dict[str, bool]`), checkpoint
  KHÔNG cần persist thêm field mới.
- **Validator `tools/check_ui_compatibility.py`**: check theo từng CONSUMER — AGENTS.md
  phải chứa canonical name `ui-compatibility-contract.md` + tên registry local, registry
  phải chứa canonical name + tối thiểu 1 marker mỗi concept trong 9 concepts (id/owner,
  ui signature, evidence, selector/fallback, safety bounds, post-action verification,
  regression tests, preserved branches, affected consumers; marker tiếng Việt hợp lệ:
  "Thứ tự xử lý"/"Giới hạn an toàn"/"Xác minh sau thao tác"/"Không được làm"/"Consumer bị
  ảnh hưởng"). Findings từ repo có AGENTS.md dirty của session khác (Tiktok_Reg,
  tiktok-log-in) là PRE-EXISTING → báo cáo trong summary, KHÔNG sửa file dirty. Run:
  `python tools/check_ui_compatibility.py --workspace-root D:\Taadaa` từ automation-core.

## Pitfall tool: search_files với drive path trên Windows host

- `search_files` với `D:/...` hoặc `D:\...` → convert thành `/d/...` mà rg (binary Windows native) không resolve → lỗi "IO error: The system cannot find the path specified" (lặp lại mỗi lần gọi, không phải transient).
- **Workaround**: dùng `terminal` với `rg` + path MSYS `/d/Taadaa/...` (bash resolve được). Ví dụ: `cd /d/Taadaa && rg -n -i "pattern" tiktok-log-in Tiktok_Reg ... --glob '!*.pyc' | head`.
- Audit rule toàn repo: grep keywords song ngữ Việt-Anh (uiautomator|toạ độ|tọa độ|coordinate|fallback|bấm thẳng|tap mù) trên core + các consumer, rồi đọc context dòng quanh hit — đừng chỉ đọc tên file.
