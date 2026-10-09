# Phase 2a Reg TikTok — Root Causes & Fixes (09/09/2026)

## Incident: FAILED: 21/26 trong night-chain-reg-pipeline

### Root Cause A — detect_after_continue() false positive (11 máy)

**Lỗi:** `RuntimeError: [07] Tat ca 1 email cua STT {stt} da co TK TikTok` (sai)

**Nguyên nhân:** `form_hints` chứa `"nhap dia chi email"` — chuỗi này trùng với **tiêu đề tĩnh**
của màn hình TikTok nhập email. Khi click "Tiếp tục", nút loading spinner text="", nhưng header
vẫn còn → `detect_after_continue` trả ngay `form_still_visible` → fallback keyevent 4 (BACK)
→ abort đăng ký → raise sai là "email đã có TikTok".

**Fix áp dụng (commit 9cc00dd, social_reg_v1.py):**
```python
# Cũ:
form_hints = ["nhap dia chi email", "hop le", "khong hop le", "invalid email", "valid email"]

# Mới — CHỈ dùng chuỗi error thực sự, TUYỆT ĐỐI KHÔNG dùng tiêu đề màn hình:
validation_error_hints = [
    "nhap dia chi email hop le",
    "dia chi email khong hop le",
    "email khong hop le",
    "enter a valid email",
    "invalid email",
    "valid email",
]
```
Đồng thời thêm `had_form_error` flag để differentiate lỗi validation vs lỗi "tất cả email đã reg".

**Quy tắc rút ra:** Bất kỳ chuỗi nào trong `detect_after_continue()` PHẢI được kiểm tra xem
có trùng với text tĩnh của màn hình không (header, placeholder, disclaimer). Chỉ dùng text lỗi
validation RIÊNG BIỆT (chứa thêm từ như "hợp lệ", "không hợp lệ", "valid", "invalid").

---

### Root Cause B — machine_counts bỏ sót slot không có tiktok_id (1 máy: STT 61)

**Lỗi:** `RuntimeError: [04_add_account] MACHINE_FULL_8_ACCOUNTS: Thiết bị đã đạt giới hạn 8 tài khoản`

**Nguyên nhân:** `load_registered_mailboxes()` dùng `if tiktok_id and stt_idx...` → chỉ đếm
slot ĐÃ CÓ tiktok_id. Máy 61 có 8 dòng tracking nhưng dòng 8 chưa điền tiktok_id → đếm chỉ 7
→ detector chọn máy 61, mở TikTok thấy đã đủ 8 acc → crash.

**Fix áp dụng (commit 9cc00dd, scripts/tiktok_target_eligibility.py):**
```python
# Cũ:
if tiktok_id and stt_idx is not None and stt_idx < len(row):
    ...machine_counts[m] += 1

# Mới — đếm tất cả row có stt hợp lệ, kể cả tiktok_id trống:
if stt_idx is not None and stt_idx < len(row):
    raw_stt = row[stt_idx]
    if raw_stt is not None and str(raw_stt).strip():
        try:
            m = int(raw_stt)
            machine_counts[m] = machine_counts.get(m, 0) + 1
        except (TypeError, ValueError):
            pass
```

**Quy tắc rút ra:** `machine_counts` = số slot đã CẤPPHÁT cho máy (cả slot trống), không phải
số slot đã có TikTok ID. Eligibility check = tổng slot allocated < max_accounts_per_machine.

---

### Root Cause C — Alert Phase 2a bắn sai khi batch vận hành bình thường

**Lỗi:** Bắn alert `[FARM ALERT: LỖI SCRIPT / PIPELINE]` dù chỉ có machine fail thông thường,
không phải lỗi script/pipeline.

**Nguyên nhân:** `_run_all_targets.py` trả exit code 1 bất cứ khi nào có `fail_count > 0`.
Phase 2a thiếu guard `if total > 0 → không alert` (Phase 1 Gmail đã có guard này).

**Fix áp dụng (commit 9cc00dd, scripts/run_night_chain_pipeline.py):**
```python
# Mới:
if tiktok_reg_code != 0:
    tiktok_reg_details = parse_tiktok_details(tiktok_reg_out)
    if not (isinstance(tiktok_reg_details, dict) and int(tiktok_reg_details.get("total", 0) or 0) > 0):
        if "Total targets: 0" not in tiktok_reg_out and ...:
            _send_night_chain_alert(...)
```

**⚠️ Rủi ro Fix C (Claude Opus đánh giá):** Nếu batch chỉ chạy được 1-2 acc rồi crash giữa chừng
(total > 0 nhưng vẫn nghiêm trọng), alert bị suppress → cần thêm log rõ ràng:
`"[night-chain] Alert suppressed: exit={code} nhung total={total}>0"`.

---

### Root Cause D — Lỗi mạng vật lý (9 máy: STT 03, 07, 09, 25, 28, 32, 42, 44, 45)

**Lỗi:** `RuntimeError: [07] Khong the kiem tra email do loi mang ('Khong co ket noi Internet')`

**Nguyên nhân:** Sự cố proxy 4G giờ cao điểm 01:00-01:10. UI XML xác nhận:
`content-desc="Tín hiệu Wi-Fi đủ.,Không có Internet."` (có WiFi nhưng captive portal/proxy down).

Đây là lỗi hạ tầng, không phải bug code. Watchdog proxy tự reconnect trong chu kỳ ban ngày.

---

## Test Suite Kiểm Chứng
File: `D:/Taadaa/Tiktok_Reg/tests/test_detect_after_continue.py`
```bash
D:/Taadaa/python-envs/automation/Scripts/python.exe -m pytest \
  D:/Taadaa/Tiktok_Reg/tests/test_detect_after_continue.py \
  D:/Taadaa/Tiktok_Reg/tests/test_fill_email_continue_btn.py \
  D:/Taadaa/Tiktok_Reg/tests/test_night_chain_summary.py \
  --timeout=30 -q
# Kết quả: 14 passed in 5.42s
```
