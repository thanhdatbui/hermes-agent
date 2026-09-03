# Reg TikTok trên máy MỚI TINH (chưa từng có account) — 2026-08-17, máy 75-79

## Bối cảnh
Máy 75-79 (S7, mới login hotmail token vào Outlook app) chạy
`social_reg_v1.py <stt> --ss --defer-tracking-write --email <mail>` → cả 3 máy
(75/76/77) đều STOPPED — nhưng KHÔNG phải lỗi script, mà là **flow sai cho máy
chưa có TikTok account**.

## Triệu chứng (3 máy giống hệt)
- `[2] Go to profile tab` → tap các fallback (972,1857) → retry → 90s → 
  `✗ STOPPED: [02_profile] Khong vao duoc tab Ho so/Profile`
- Máy 75/77: `[1] Open app` → TikTok `SplashActivity` KẸT (~52s) →
  `✗ STOPPED: [adb-timeout] UI_XML_TIMEOUT` (S7 yếu RAM 3GB, splash không qua)
- Máy 76: vào được `I18nSignUpActivity` (màn đăng ký mới) — KHÔNG có tab Profile

## Root cause
`social_reg_v1.py` flow main (dòng ~6613-6640) LUÔN chạy `go_to_profile`
(bước 2) → open_account_dropdown → tap_add_account → ... Thiết kế cho máy
**ĐÃ CÓ account TikTok cũ** (login continuation / add-account). Máy mới tinh
chưa từng mở TikTok đăng ký → màn đầu là consent/signup (`NewUserJourneyActivity`
/ `I18nSignUpActivity`) → không có tab Profile → fail đúng chỗ.

Tham chiếu 16/08: máy 38/54 SUCCESS vì MÁY ĐÓ ĐÃ CÓ acc cũ (add-account chạy
được); máy 57/66 cũng kẹt `[06_email_option]` trên màn I18nSignUp — cùng class
chưa fix.

## Cần làm (CHƯA fix — đã dừng, hỏi user)
Cần nhánh **signup mới** trong main flow: detect màn `I18nSignUpActivity`/
`NewUserJourneyActivity` (không có profile tab) → đi thẳng:
chọn Email (entry ẩn — màn mặc định hiện SĐT, xem reference 16/08 [06_email_option])
→ nhập mail → OTP qua token/Graph → DOB (`fill_birthday`) → password → post-auth.

Chưa làm vì: đây là thay đổi lớn flow, reference 16/08 ghi máy 57/66 cũng kẹt
chưa fix entry email — cần user hướng dẫn màn signup mới trước.

## Pitfall môi trường đi kèm

### ACCOUNTS list HARDCODE — STT > 74 chưa có
`social_reg_v1.py` dòng 93 `ACCOUNTS = [...]` chứa stt + device + email + pass
cứng, **chỉ đến STT 74** (16/08). Detector `_detect_clean.py` tự tìm target từ
workbook (STT 75-79 có trong `_clean_targets.json`) NHƯNG script chạy đọc
ACCOUNTS → `Không có STT 75`. Phải thêm thủ công:
```python
{"stt": 75, "device": "ce011711d4cd802905", "email": "", "pass": ""},
... (76-80)
```
email/pass để trống (điền qua `--email` CLI). Kiểm tra `grep -n '"stt": *75'`.
⚠️ Patch thêm vào list dễ vỡ indentation — dedent bằng script (đọc file, sửa
prefix theo line range, `ast.parse` verify), không vật lộn nhiều patch nối tiếp.

### TARGET_INVENTORY_CONFLICT / MISSING_SERIAL — data ngày rơi vào cột Device ID
`taikhoan_run_safe.xlsx` sheet `Accounts` có row data lệch: **ngày tháng
(`21/07/2026`, `16/08/2026`, `02/08/2026`) nằm trong cột Device ID** (máy 38/66)
→ detector fail `TARGET_INVENTORY_CONFLICT: machine 38`; row máy 70 có
serial=None → `TARGET_INVENTORY_MISSING_SERIAL: row 418`.
Fix (backup `.bak-<date>` TRƯỚC): ghi đè serial đúng `ce06160685310f1c04`
(máy 38) / `ce12160c2a99962905` (máy 66) cho các row ngày; xóa row có may +
device + id đều trống (row rác máy 70). Verify lại `_detect_clean.py`.

### venv-core024 = uv launcher spawn 2 process — không phải chạy đúp
`D:/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe` thực chất là
launcher uv → mỗi lệnh sinh 2 process: venv-core024 python + `uv/python/
cpython-3.11...`. Gate log `[gate] IGNORE pid=... reason=social_reg_v1.py on
different machine/device` với các máy khác là ĐÚNG (3 máy khác nhau → bỏ qua,
không block). KHÔNG kill process "phụ" — là parent-child hợp lệ.

### Lock máy 75-79 free + không file lock
Máy mới (75-80) chưa có lock trong `.codex/device-locks/` (chỉ máy 34/39 có
lock từ gmail). Trước batch: `wmic process where "Name='python.exe'" get
ProcessId,CommandLine | grep social_reg` xác nhận không process trùng.

## Serial map máy 75-80 (từ taikhoan_run_safe Accounts)
- 75 = ce011711d4cd802905
- 76 = 9885b64d56305a3731
- 77 = ce05160595e7953b04
- 78 = ce0916090a9d320a01
- 79 = ce0516059d279f3e03
- 80 = ce061606cd45950405