# Batch 2026-09-01 — Root Causes & Fixes

## 1. AdbKeyboard / ATX stub treo → không điền được email vào ô EditText

**Triệu chứng:** ô `EditText` bỏ trống dù broadcast `ADB_KEYBOARD_INPUT_TEXT`; `result=-1` từ AM.
**Root cause:** ATX stub (`com.github.uiautomator`) treo socket ngầm → IME daemon không nhận.
**Fix chuẩn:** restart ATX sạch (xem `atx-agent-primary-ui-xml` § AdbKeyboard IME Socket Hang):
```
pkill -9 -f atx-agent
am force-stop com.github.uiautomator
/data/local/tmp/atx-agent server -d
monkey -p com.github.uiautomator 1
```

## 2. Màn One-tap login / Fast login → tài khoản rác không bị xóa

**Nguyên nhân:** `handle_fast_login_screen` gọi SAU `wait_for_text`; `wait_for_text` thiếu `"Tiếp tục với tên"` → timeout 20s → RuntimeError trước khi xóa rác.
**Fix commit:** Gọi `handle_fast_login_screen` TRƯỚC `wait_for_text` đầu `choose_email_login`; thêm `"Tiếp tục với tên"`, `"Sử dụng tài khoản khác"` vào wait list.
**Logic xóa rác:**
1. Đọc `@handle` từ màn One-tap
2. Đối chiếu với toàn bộ kho Excel (taikhoan_dat_v2, taikhoan_run_safe, gmail_clean_v2, Tik1-4)
3. KHÔNG có → tap menu "Khác" (desc='Khác', rid='z7o') → "Xóa tài khoản" → confirm "Xóa" → "Sử dụng tài khoản khác"
4. CÓ → giữ lại, chỉ tap "Sử dụng tài khoản khác"
**Module canonical:** `automation_core.tiktok.fast_login.handle_fast_login_screen` (adapter pattern, không import trực tiếp consumer). Consumer wrapper gọi core + fallback local.
**Tests:** `automation-core/tests/test_fast_login.py` — 4 tests pass.

## 3. Popup "Tài khoản đã bị đăng xuất" chặn màn đăng nhập

**Triệu chứng:** step [6] dừng, màn hình dialog "Trạng thái tài khoản / Tài khoản của bạn đã bị đăng xuất."
**Fix:** `choose_email_login` check flat XML ngay đầu cho `"tai khoan cua ban da bi dang xuat"` hoặc `"trang thai tai khoan"` → tap OK → sleep 1.5s.

## 4. Không truyền --email xuống tiến trình con → bốc nhầm email

**Máy bị ảnh hưởng:** 57, 62, 63, 69 (Hotmail targets).
**Root cause:** `_run_all_targets.py` không truyền `--email` → `social_reg_v1.py` tự tìm email từ `gmail_clean_v2.xlsx` (không có trên thiết bị).
**Fix:** `_run_all_targets.py`: thêm `--email <email>` vào `build_child_command` khi target có email chỉ định.

## 5. get_ui_xml deadline 35s không đủ → nâng lên 60s

**Lý do:** 3 retry ATX (15s/lần) + reset_atx_agent (15s) + 2 retry sau reset = cần ≥55s.
**Fix:** `UI_XML_TOTAL_TIMEOUT = 60`; dùng `local_deadline - time.monotonic()` floating thay vì `_remaining_timeout` fn cố định.
**Test update:** mock signature `_atx_capture_ui_xml` đổi từ `lambda _device, _remaining_fn` → `lambda _device, *a, **k`.

## 6. Hermes Cron "provider timeout" = false alarm

**Thực chất:** batch `_run_all_targets.py` exit 1 (một số máy FAILED), Hermes hiểu là LLM timeout.
**Kiểm tra thực tế:** `D:\Taadaa\runtime\kibe\artifacts\runs\social-batch-all\<timestamp>\all_results.json`.

## Kết quả batch

- Batch 1 (7 máy, 01/09, sau fix): 7/7 thành công, merge vào workbook OK
- Batch 2 (8 máy, 01/09, chạy lại): 7/8 thành công (máy 71 gặp ATX stub treo; sau restart: thành công)
- Batch 3 (11 máy): 5/11 (46, 71, 73, 76, 79 OK; 4 máy 41/64/65/66 mất ADB cáp)
- Batch 4 (6 máy, 72/74/75/77/78/80): đang chạy
