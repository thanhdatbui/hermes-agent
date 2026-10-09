# Case 80 (04/09/2026) — Máy 34: Post Idempotency fail-closed + UIAutomator helper occlusion + LIVE tab

Nguồn: Farm Alert `[MÁY 34] DỪNG PHIÊN`, `upload_subprocess_nonzero`, serial `ce031603b3158b0b02`, nick `truong.thuy950`, video-number 6. Symptom gốc: receipt idempotency cũ + helper app đè foreground + composer UI mới.

## 1. Post receipt phải fail-closed khi run_id rỗng (P1)
Sai (fail-open, mất idempotency khi reporter chưa có run_id):
```python
if not current_run_id or receipt_run_id != current_run_id:
    receipt = None
```
Đúng — chỉ bỏ receipt khi BIẾT CHẮC khác run:
```python
if current_run_id and receipt_run_id != current_run_id:
    receipt = None
```
Áp dụng ở cả `_handle_post` và `_record_post_intent`. Nguyên tắc: thiếu thông tin → giữ barrier (fail-closed), không bao giờ nullify receipt vì "không biết".

## 2. Chỉ force-stop `com.github.uiautomator`, KHÔNG đụng `io.appium.uiautomator2.server`
`uiautomator2.server` chính là backend mà `dump_ui()` dùng. Force-stop nó = tự bắn vào chân → cascade dump failures, không có restart logic nào cứu được.
```python
# ĐÚNG
if focused_pkg and "com.github.uiautomator" in focused_pkg:
    adapter._adb.shell(["am", "force-stop", "com.github.uiautomator"], timeout=10, check=False)
# SAI: "uiautomator" in focused_pkg.lower() → dính cả uiautomator2.server
```
Detect bằng `focused_pkg` (package foreground thật), không match chuỗi package trong `xml_lower` (dễ false-positive khi XML chứa text/debug chứa tên package).

## 3. LIVE tab detection phải exact-match + yêu cầu có tab ĐĂNG/TẠO
Sai (broad, false-positive trên mọi UI có chữ "live" như "live photo", "go live"):
```python
if any(m in xml_text.casefold() for m in ("phát live", "trung tâm live", 'text="live"')):
```
Đúng — match exact `text="..."` và chỉ switch khi đã thấy tab đích:
```python
if any(m in xml_text for m in ('text="Phát LIVE"', 'text="Trung tâm LIVE"', 'text="LIVE"', 'text="Live"')) \
        and any(m in xml_text for m in ('text="ĐĂNG"', 'text="TẠO"')):
```

## 4. Không giảm timeout một cách tùy tiện trên máy yếu
`prepare_app_for_automation` 60s→30s, `view_bg2` 60s→10s không justification = regression trên máy chậm (đúng đối tượng đang lỗi). Mọi timeout reduction phải ghi lý do + giữ retry loop bounded. Tương tự: xóa one-shot flag (`atx_recovered`) để recover "mỗi 3 lần fail" mà không có upper bound = ATX kill storm.

## 5. Mở rộng Post selector giữ tương thích ngược
Final composer mới dùng `sh8, shd, sox, soz, sp7, rbp, post_action, post_button` — thêm vào set, không thay thế selector cũ. Auto-advance: khi ledger báo `verified_success`, đồng bộ ngay `context.video_path` sang video tiếp theo (bọc try/except, non-fatal).

## Verify
- `py_compile` OK + focused suite `pytest tests/test_tiktok_workflow.py -k "post or media_fingerprint or video_pick or auto_advance"` pass (94 passed trong phiên này).
- Live canary runner chính thức timeout (exit 124) → classify theo stage (target resolution / preflight / runtime-UI), không suy đoán UI lỗi từ wrapper exit code.
