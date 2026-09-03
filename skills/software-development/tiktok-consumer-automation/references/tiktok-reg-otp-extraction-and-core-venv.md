# Tiktok_Reg: OTP extraction bug + core-pin venv isolation (2026-08-06)

Session: chạy reg TikTok 10 máy (mỗi máy 1 acc) qua
`scripts/run_tiktok_recovery_new_handler.py`. Kết quả detection pass:
10/10 FINAL_BLOCKED, 0 success — nhưng 1 root cause là bug thật trong
consumer (OTP extract), phần còn lại là blocker đã biết.

## 1. Bug OTP extract: regex bắt nhầm số trong email address (STT 34)

### Triệu chứng log

```
[otp-gmail] opened message markers: tiktok=Y verification=Y six_digit=Y link_action=Y
[otp-gmail] Skip stale opened-message code [REDACTED] (timestamp='07:02')
[otp-gmail] Skip stale opened-message code [REDACTED] (timestamp='07:02')
...
[otp-gmail] Không có code 6 số → thử magic link
[otp-gmail] Skip stale magic link (timestamp='07:02')
[otp][OTP_REJECTED_NO_FRESH_CODE] stt=34
```

OTP thật `097038` là mã MỚI (07:02) — nhưng bị skip hết.

### Root cause (đã tái hiện offline bằng XML thật)

`extract_recent_tiktok_otp_from_gmail_conversation` (social_reg_v1.py:5486):
- Gom toàn bộ `text`/`content-desc` của mọi node trong conversation thành 1
  chuỗi `combined` (dòng 5500-5507).
- `code_match = re.search(r"(?<!\d)(\d{6})(?!\d)", combined)` (dòng 5509).
- `time_labels` = node time ĐẦU TIÊN (dòng 5510-5511) → `timestamp`.

XML thật (run 20260806-065254 / stt_34,
`gmail_opened_tiktok_message_truongthuy111034_gmail.com_..._070230_532705.xml`)
chứa:
- `07:02` (time node đầu — email TikTok mới)
- `097038 là mã TikTok của bạn` (OTP thật)
- `Xác minh email của bạn Nhấp vào liên kết này hoặc nhập mã 097038`
- `truongthuy111034@gmail.com Chào Thuy, ...` → chuỗi `111034` là 6 số trong
  địa chỉ email!
- `06:58` (time email cũ)

Regex trên chuỗi gộp tìm thấy `111034` (từ email) TRƯỚC `097038` → extract
code sai. Replay offline:

```python
code, meta = s.extract_recent_tiktok_otp_from_gmail_conversation(
    xml, now=datetime(2026,8,6,7,3), not_before=datetime(2026,8,6,7,1))
# → code: '111034' | meta: {'code': '111034', 'timestamp': '07:02', 'excluded': False}
```

`111034` không nằm trong node có marker TikTok/verification → các điều kiện
khác (marker, not_before) không cứu được vì code sai đã thoả regex.

### Kỹ thuật chẩn đoán (offline replay — không cần máy)

1. In thứ tự node có time hoặc 6 số:
   `re.finditer(r'<node[^>]*>', xml)` → regex `text="([^"]*)"` → lọc
   `\d{1,2}:\d{2}` hoặc `(?<!\d)\d{6}(?!\d)`.
2. Gọi extract với `now`/`not_before` cố định, in `code, meta`.
3. So code trả về với OTP trong node marker (`mã TikTok` / `verification`).

### Hướng fix

- Ưu tiên: quét code 6 số trong node có `text` chứa `tiktok`/`mã tiktok`/
  `verification`/`xac minh` — không gom toàn chuỗi.
- Loại pattern email: nếu code nằm trong chuỗi khớp `[a-z0-9._%+-]+@...`
  thì bỏ qua.
- Chỉ fallback regex toàn chuỗi khi KHÔNG có node marker.
- `time_labels`: lấy time của node gần code nhất (hoặc node chứa marker),
  không lấy node time đầu tiên.
- Thêm regression test replay XML thật (test hiện có
  `tests/test_gmail_preview_otp_freshness.py` chỉ dùng XML giả đơn giản —
  chưa cover email-address-chứa-6-số).

## 2. Core pin ≠ env chung — venv riêng + pitfall `flows`

### Vấn đề

- Runner pin `REQUIRED_CORE_VERSION = "0.4.31"` (wheel:
  `D:\Taadaa\_core031_build\dist\automation_core-0.4.31-py3-none-any.whl`).
- Env automation chung = 0.4.34, đang bị scheduler khác dùng
  (`D:\Taadaa\tiktok-log-in\scheduler.py --live`, feed recovery_runtime).
- Cài đè 0.4.31 vào env chung = phá consumer khác + bị đè ngược lại.

### Fix đã dùng

```bash
# 1) venv kế thừa site-packages
python -m venv --system-site-packages "D:\Taadaa\python-envs\tiktok-reg-recovery"
# 2) force-reinstall wheel đúng pin (--no-index --no-deps)
env -i PATH="/c/Windows/system32:/c/Windows:/d/Taadaa/python-envs/tiktok-reg-recovery/Scripts:/c/Users/Kibe/AppData/Local/Programs/Python/Python312" \
  HOME="C:\\Users\\Kibe" USERPROFILE="C:\\Users\\Kibe" \
  "/d/Taadaa/python-envs/tiktok-reg-recovery/Scripts/python.exe" -m pip install \
  --no-index --no-deps --force-reinstall "/d/Taadaa/_core031_build/dist/automation_core-0.4.31-py3-none-any.whl"
```

Verify: `python -c "import importlib.metadata as m; print(m.version('automation-core'))"` → 0.4.31.

### Pitfall `flows` (ModuleNotFoundError)

`social_reg_v1.py:74-76` import:
```python
from flows.hotmail_login import login as _canonical_hotmail_login
from flows.hotmail_login import check_mailbox_alive as _canonical_hotmail_check_alive
from flows.hotmail_login import resolve_adb as _canonical_hotmail_resolve_adb
```
- `flows` KHÔNG nằm trong automation-core wheel — nó là package
  `taadaa-hotmail` (dist 0.1.0, repo `D:\Taadaa\Hotmail`) cài trong env
  automation site-packages.
- `--system-site-packages` kế thừa được `flows` — nhưng `check_mailbox_alive`
  có thể THIẾU trong bản site-packages cũ (`ImportError: cannot import name
  'check_mailbox_alive'` từ site-packages) trong khi repo Hotmail HEAD có hàm
  này (dòng 869).
- Fix chạy runner với `PYTHONPATH="D:\Taadaa\Tiktok_Reg;D:\Taadaa\Hotmail"`
  (đường dẫn repo đè site-packages), verify import trước live:
```bash
env -i PATH="...tiktok-reg-recovery/Scripts;...automation/Scripts;..." \
  HOME="C:\\Users\\Kibe" USERPROFILE="C:\\Users\\Kibe" \
  PYTHONPATH="D:\\Taadaa\\Tiktok_Reg;D:\\Taadaa\\Hotmail" \
  "/d/Taadaa/python-envs/tiktok-reg-recovery/Scripts/python.exe" -c \
  "from flows.hotmail_login import check_mailbox_alive, login, resolve_adb; print('hotmail flows OK')"
```

### Lệnh chạy runner (tham khảo)

```bash
env -i \
  PATH="/c/Windows/system32:/c/Windows:/d/Taadaa/python-envs/tiktok-reg-recovery/Scripts:/c/Users/Kibe/AppData/Local/Programs/Python/Python312" \
  HOME="C:\\Users\\Kibe" USERPROFILE="C:\\Users\\Kibe" \
  PYTHONPATH="D:\\Taadaa\\Tiktok_Reg;D:\\Taadaa\\Hotmail" \
  TIKTOK_REG_WRITER_ID="tiktok-reg-runner" TIKTOK_REG_EXPECTED_WRITER_ID="tiktok-reg-runner" \
  "/d/Taadaa/python-envs/tiktok-reg-recovery/Scripts/python.exe" -u \
  scripts/run_tiktok_recovery_new_handler.py \
  --stt <list> --target-file "_clean_targets.json" --max-workers 10 \
  --full-scope-takeover --recover-after-failure
```
Chạy qua `terminal background=true, notify_on_complete=true` (batch dài
30-60 phút; foreground bị chặn 600s).

## 3. Ghi chú khác từ run 20260806-065254

- Lock cross-project (hotmail-change-info, tiktok-upload, tiktok-luot nuoi acc)
  giữ machine_30/31/36/38/54/55/66 — runner `--full-scope-takeover` chỉ
  reclaim khi owner PID chết (đúng policy); lock `status: running +
  owner_active: true` nhưng PID chết → stale.
- Mail-die/captcha-delete tự xoá mail khỏi source kèm backup:
  `workbook-backups/gmail_clean_v2_before_captcha_delete_*.xlsx` +
  `taikhoan_dat_v2_updated _before_mail_die_audit_*.xlsx` — sau khi xoá PHẢI
  chạy lại detector để refresh manifest (xem mục "Manifest cũ sau khi xoá
  mail").
- STT 31: Gmail search "TikTok" timeout 150s — không phải thiếu OTP; UI dump
  treo (`window_dump_*.xml: No such file or directory` lặp). Retry khi máy
  ổn định.
- `tasklist /FI "PID eq X"` (1 slash) dùng được trong git-bash; `//FI` bị
  MSYS nuốt thành path.
