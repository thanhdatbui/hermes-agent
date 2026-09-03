# CTA swipe-first + coordinate swipe capture fallback (2026-08-09)

Session evidence cho 2 fix trong `python_runner/flows/feed_swipe_smoke.py` (repo `tiktok-luot nuoi acc`, branch `master`).

## Bối cảnh

User rule (tối cao):
```
exact Mua ngay trong TikTok UI → 1 bounded evidence-gated swipe NGAY
→ recapture + evidence evaluation
→ Đóng dynamic CHỈ fallback nếu CTA vẫn còn
→ không bao giờ tap Mua ngay
```

User nổi nóng khi thấy `manual-needed` lặp lại trong khi fix nằm trong tầm tay:
- "manual needed cái đéo gì v hở tý là manual needed??? dẹp con mẹ nó đi tự sửa đi đm"
- "máy 20 t vừa sswipe tay vẫn qua mày làm kiểu gì v" → automation phải tự swipe như user swipe tay.

## Vòng 1: M20 bị `manual-needed:capture-invalid`

Run đầu `20260809-201348`: fail TRƯỚC khi đọc XML — capture transport:
```
UIAUTOMATOR_BACKGROUND_START_DENIED_FOREGROUND_RECOVERY_V2:
foreground-service recovery reached FINAL_BLOCKED
SHELL_NO_HIERARCHY (dump exit 0 nhưng "null root node returned by UiTestAutomationBridge", cat_bytes 92)
```
Focused = `com.ss.android.ugc.trill` + `SplashActivity`; screenshot classifier báo loading conf 0.92 → fail-closed đúng (splash → không được swipe mù).

## Vòng 2: M20 có XML, 3 swipe chạy, nhưng CTA còn → `manual-needed:popup`

Log trail (run `20260809-201941`):
1. `swipe_1..3` success, XML đọc được hết (`xml_error: none`).
2. `gemphonefarm_blind_popup/shop_cta_close` `gem_blind_probe` **success** — probe `//node[@text="Mua ngay"]` match node `nuf` bounds `[321,1665][524,1722]` (thanh đáy Shop, KHÔNG phải popup CTA lớn).
3. `_gem_blind_action` → `success:false reason:"TikTok Shop CTA core detector did not match; refusing to tap"` (detector cũ đòi pair `Mua ngay`+`Đóng`).
4. Final `attempt_1/ui.xml` vẫn có `Mua ngay:hwh` + `Đóng:hwn` → `manual-needed:popup` "known shop_cta_overlay popup detected".

Verify độc lập (parse lại XML artifact bằng `detect_tiktok_shop_cta_popup`): match= True, `close_element=Đóng com.ss.android.ugc.trill:id/hwn center (540,1106)` → handler ĐÃ có thể tap đúng, chỉ vì cổng probe/action không nối.

**Kết luận:** 2 bug lớp riêng: (A) probe XPath text-only match nhầm node khác (thanh đáy) → detector pair không match → refuse; (B) handler chưa swipe-first. Fix = swipe-first trong `_gem_blind_action` (chỉ gate marker), recapture, dynamic close fallback.

## Fix production (đã áp + compile + test)

Files:
- `python_runner/flows/feed_swipe_smoke.py`:
  - import `has_tiktok_shop_buy_now_marker` từ `core.benign_popup`.
  - `_gem_blind_action` nhánh `shop_cta_close`: gate marker-only → swipe 1 lần → `_capture_xml_text(ctx, f"{step}_probe_after_swipe")` → marker hết ⇒ True; còn ⇒ `detect_tiktok_shop_cta_popup(after_root)` → tap `close_element` động (xpath đầy đủ attrs, không hardcode id) / không match ⇒ fail-closed.
  - `_capture_blocked_attempt(attempt)` (detected_screen ∈ `{manual-needed:capture-invalid, manual-ready:popup}`) + `_capture_coordinate_swipe_fallback(...)` (gate: flag + budget 1/session + require_feed + `_is_feed_confirmed` + TikTok focus; swipe 1 lần; recapture qua `capture_calibration_attempt`).
  - wire vào `_capture_step` sau block force-stop: `if _capture_retry_needed(...) or (require_feed and _capture_blocked_attempt(attempt)):` → fallback.
- `python_runner/run_tiktok.py`: `--allow-coordinate-swipe-recovery` (BooleanOptionalAction default None → chỉ bật khi truyền); wire `config["safety"]["allow_coordinate_swipe_recovery"]`.
- `python_runner/config.example.yaml`: `allow_coordinate_swipe_recovery: false` + comment.

**Test** (`test_feed_swipe_smoke_popups.py`):
- `test_shop_cta_close_swipes_first_on_detecting_buy_now` — `{"__initial__": cta, "shop_cta_close":[EMPTY_XML]}` ⇒ assert `assertCalledOnceWith([... swipe ...])`, reason chứa "swipe".
- `test_shop_cta_close_no_action_without_detector_buy_now` — giữ (no marker ⇒ no action).
- `test_shop_cta_close_taps_dynamic_close_button_for_supported_resource_ids` — đổi sequence `[xml_text, EMPTY_XML]` ⇒ `[xml_text, EMPTY]`… actually `{"__initial__": xml, "shop_cta_close":[xml,EMPTY]}` → calls `[[swipe],[tap 540,10xx]]`.
- `test_shop_cta_close_swipes_then_taps_dynamic_close_from_live_recapture` — `{"__initial__": xml_before(hwh/hwn), "shop":[xml_after(hyq/hyw),EMPTY]}` ⇒ cụm `[swipe, tap (540,1106)]`, selector id = `hyw`, no `/hvm`.
- `CaptureCoordinateSwipeFallbackTests` (4): feed-evidence → swipe 1 lần + budget set; loading frame ⇒ None/không swaspe; flag off ⇒ None; budget dùng hết ⇒ None.
- Popup suite: `36 passed, 5 subtests passed`; focused + benign + recovery parser: `170 passed, 10 skipped`; full: `1024 passed` — 10 fail pre-existing (xem dưới).

## Kỹ thuật kiểm chứng "10 fail có phải do mình không?" — stash chỉ file của mình

```bash
git stash push -- python_runner/flows/feed_swipe_smoke.py python_runner/run_tiktok.py python_runner/config.example.yaml python_runner/tests/test_feed_swipe_smoke_popups.py
MSYS_NO_PATHCONV=1 PYTHONPATH='...' python -m pytest <các test fail> -q   # vẫn 10 fail
git stash pop
```
10 fail xuất hiện CẢ KHI không có thay đổi của mình = pre-existing (test_device_lock × 5, test_device_prepare × 4, test_feed_session_smoke × 1 — do công việc dirty trước đó, KHÔNG đụng trong patch). Kết luận an toàn: tập override của mình giữ nguyên baseline; không được "sửa" test vì bị cuốn hút. Khác với `git checkout HEAD -- <file>` (mất thay đổi chưa commit), stash push theo file giữ nguyên mọi thứ.

## Pitfall edit-script EOL/anchors (CRLF)

- Script edit nhiều bước KHÔNG idempotent: apply spam 1..N-1 rồi chết tại bước 1 không có gì contro → chạy lại fail ngay từ bước đầu (anchor đã bị thay). Mình 3 lần; bài toán đúng: script mỗi vòng chỉ giữ các bước CHƯA áp (hoặc mỗi thay thế kiểm tra `text.count(anchor)==1` và skip nếu 0 nhưng các bước trước đã áp = ok).
- Anchor thật phải lấy repr từ file (không đoán): giữa các import có dòng trắng `detect_tiktok_shop_cta_popup,␊ ␉is_packageinstaller_dialog,` — nhớ `\r\n\r\n`.
- `run_tiktok.py` là file MIXED-EOL có sẵn (CRLF 953 ≠ LF 979 = 26 dòng LF) → đừng assert `text.count('\r\n') == text.count('\n')` cho file này; chỉ giữ CRLF cho block mình chèn.
- `feed_swipe_smoke.py` / test file = CRLF thuần — validate sau khi ghi.

## Trạng thái cuối

- Live M1+M20 (có `--allow-coordinate-swipe-recovery`): **cả 2 success** — 3/3 swipe, `observe success detected=for-you`, `HANDOFF success released`. CTA không xuất hiện lại (prepare relaunch dọn) nên không có `shop_cta_swipe` event — đừng gọi là CTA live verified.
- Commit `266dc5b` (19 files): CTA swipe-first + coordinate fallback + M7 parser/timeout + docs/rules. **10 fail pre-existing** đã chứng minh bằng stash (xem trên), KHÔNG phải của patch.

## Scan toàn farm tìm máy dính CTA (08-09)

User: "áp dụng chạy nốt các máy bị lỗi CTA đó đi? có tự đọc đc k hay t đọc dùm luôn" → tự đọc, không bắt user đọc:

1. Map máy→serial: workbook `D:\OneDrive\Tiktok\Tik1.xlsx` sheet **`TaiKhoan`** (KHÔNG phải 'Tài Khoản'), cột A `Máy` + cột B `device ID` (80 máy).
2. `adb devices` lấy serials online (80/80 lúc đó).
3. `ThreadPoolExecutor(max_workers=12)` scan: `uiautomator dump /sdcard/hermes_cta_scan.xml` (timeout 15) + `exec-out cat` → `"Mua ngay" in xml` → regex `text="Mua ngay"[^>]*resource-id="([^"]+)"` + `text="[ĐD][^"]*óng"` → map serial→machine.
4. Kết quả: **M8/10/15 = `hvg`/`hvm`** (hvm LIVE thật, không phải chỉ legacy!), **M51/58/66/67 = `hwh`/`hwn`** → chạy batch 7 máy.

Batch 7 máy: 6/7 pass ngay (8,15,51,58,66,67 — 3/3 swipe, lock released); **M10 fail lỗi MỚI** → xem mục sau.

## M10: `invalid recovery transition: RECOVERING -> FINAL_BLOCKED` (lỗi capture_recovery, KHÔNG phải CTA)

M10 `final_status=failed`, `total_swipes_completed=0`, `stop_reason=invalid recovery transition: RECOVERING -> FINAL_BLOCKED`, lock giữ `blocked`. Log: `sponsored_check` có `ui_dump_error` ×2 + `adb_transport_recovery_*.json` → ADB transport mất trong `_sponsored_present` capture → `recover_adb_transport` reconnect/probe fail → except branch gọi `trace.terminal(state=RECOVERING, success=False)`.

Root cause: automation-core `results.py` `_TRANSITIONS`: `RECOVERING → {RECAPTURED}` (KHÔNG có FINAL_BLOCKED); `RecoveryTrace.terminal()` → `validate_recovery_transition` raise ValueError → exception trong except lan ra → cả session chết `failed`.

Fix (consumer-side, `python_runner/core/capture_recovery.py` — **file LF THUẦN**, không CRLF!):
```python
except Exception as exc:
    artifact = getattr(exc, "artifact_path", None) or initial_error.artifact_path
    if state == RecoveryState.RECOVERING:
        state = trace.recaptured(state, action="adb_transport_recapture_failed",
                                 recaptured_artifact=str(artifact) if artifact else None)
    state = trace.terminal(state, success=False, ...)
```
Regression: `RecoverAdbTransportTests` trong `test_ui_dump.py` — fake `_ReconnectFailAdb(AdbClient)` (`run(["reconnect","device"]) → ok=False`), assert `result is None` + journal `outcome=FINAL_BLOCKED` + states chứa RECAPTURED & FINAL_BLOCKED + `handler_id="tiktok_adb_transport_reconnect_v1"`. Trước fix: crash `invalid recovery transition`; sau fix: journal 1 file duy nhất (cùng recovery_id ghi đè), outcome FINAL_BLOCKED. 99 passed (ui_dump 75 + recovery handlers + parser).

Retry M10 live sau fix: **PASS** 3/3 swipe, lock released. Commit `b05692e`.

**Bài học rộng:** mọi handler `capture_recovery.py` phải theo chuỗi `begin() → recaptured() → terminal()`; nhánh except nào bỏ qua `recaptured` (state còn RECOVERING) đều crash kiểu này. EOL khi edit: capture_recovery.py LF, feed_swipe_smoke.py/test_ui_dump.py CRLF, run_tiktok.py mixed — đọc bytes `b"\r\n" in raw` TRƯỚC khi chọn anchor.