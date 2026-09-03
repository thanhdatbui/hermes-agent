# STT30 môi trường chạy live + runner chain (2026-08-11, pha 23:00–00:00)

Bối cảnh: resume reg STT30 (serial ce0217126cd4bc640c, email krystalsophroniaadonis7@hotmail.com) sau khi worker patch xong
nhánh OTP newest-mail. Chuỗi blocker môi trường chứ không phải logic script — mỗi lần tưởng "fix xong" lại vấp lớp kế tiếp.

## 1. Chuỗi blocker đã vấp (theo thứ tự)

1. **PIL crash** — `social_reg_v1.py` import `automation_core.tiktok.image_navigation` → `from PIL import Image` →
   `ImportError: cannot import name '_imaging' from 'PIL' (C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages\PIL\__init__.py)`.
   Env `D:\Taadaa\python-envs\automation` kế thừa site-packages Hermes venv (PIL hỏng). Fix: chạy live bằng
   `D:\CodexRuntime\tiktok-video\venv-core024\Scripts\python.exe` (PIL OK + automation_core import OK).
2. **HotmailProviderUnavailable** — `flows.hotmail_login` nằm ở repo RIÊNG `D:\Taadaa\Hotmail`, KHÔNG có trong Tiktok_Reg.
   `_require_hotmail_function` fail-closed `HotmailProviderUnavailable` khi import `flows.hotmail_login` fail.
   Fix: `PYTHONPATH="D:/Taadaa/Hotmail;."`.
3. **MACHINE_IN_USE gate** — lúc 23:22, gate thấy 5 process social_reg_v1.py 30 (bash wrappers + python con) từ các run
   background trước. Kiểm tra `tasklist` cho thấy: bash wrapper "đã exited" nhưng **python con vẫn sống** (do pipe tail
   + Hermes báo sớm). 2 orphan (22356 Hermes-venv python, 30804 = con của nó chạy venv-core024) thao tác máy song song —
   hệ quả: máy bị logout khỏi feed về SignUpOrLoginActivity giữa chừng. Fix: `taskkill /T /F` python con (cha chết theo),
   verify rỗng bằng liệt kê python, rm lock, chạy lại.
4. **automation-core cũ trong venv-core024** — `TypeError: _dump_current_ui_unlocked() got an unexpected keyword argument
   'expected_marker'` (consumer code gọi API mới, core cài 0.4.40 cũ). Các lần `pip install /d/Taadaa/...whl` trước
   FAIL âm thầm: MSYS mangle `/d/` → `C:\d\Taadaa\...` (OSError), và pipe `| tail -1` nuốt ERROR.
   Fix: `pip install --force-reinstall --no-deps "D:/Taadaa/automation-core/dist/automation_core-0.4.44-py3-none-any.whl"`.
   Note: dist-info trong wheel STALE — "Successfully installed automation-core-0.4.40" dù file tên 0.4.44; và `__version__`
   KHÔNG tồn tại trong module. Verify đúng cách: `inspect.signature(u._dump_current_ui_unlocked)` chứa `expected_marker`.
5. **PYTHONPATH global nhiễu** — session terminal còn `export PYTHONPATH=...\hermes-agent\venv\Lib\site-packages` (từ việc cũ):
   verify import nhảy loạn giữa Hermes venv vs venv-core024 site-packages. Luôn `echo $PYTHONPATH` trước, `env -u PYTHONPATH`
   cho verify thuần.

## 2. Màn "Nhập mã gồm 6 chữ số" + mail verify-LINK → SOCIAL_PREFER_MAGIC_LINK=1

- Màn CommonFlowActivity "Nhập mã gồm 6 chữ số để đặt mật khẩu" + cảnh báo đỏ "⚠️ Nhập đúng mã PIN" + nút "Gửi lại mã".
- Resend KHÔNG tạo mail code mới. CDP probe inbox (scripts/probe_outlook_inbox_rows.py) cho thấy MỌI mail TikTok gần đây
  (10:27, 15:03, 19:16, 23:22) là verify-LINK: "Hoàn tất đăng ký bằng cách xác minh email của bạn ... Xác minh email
  [button] Liên kết có hiệu lực trong 20 phút" — không có 6 số. Mail code cuối cùng: 08:17 (371908) / 09:33 (435509) — hết hạn.
- Nhánh numeric fail-closed `OTP_RESEND_NO_FRESH_CODE` là hành vi ĐÚNG (không nhập code cũ). Nhánh đúng = magic-link:
  `SOCIAL_PREFER_MAGIC_LINK=1` (recovery flag trong code, dòng `forced_magic_link = os.environ.get("SOCIAL_PREFER_MAGIC_LINK") == "1"`)
  → nhánh magic-link mở inbox → tap link xác thực mail mới nhất (deep-link email_verification).

## 3. Lệnh chuẩn

```bash
cd /d/Taadaa/Tiktok_Reg
# pytest
env -u PYTHONPATH /d/Taadaa/python-envs/automation/Scripts/python -m pytest tests/test_login_outlook_magiclink_branch.py tests/test_login_magiclink_classify.py tests/test_login_otp_health_fallback.py -q
# live resume (KHÔNG pipe tail — redirect file)
SOCIAL_PREFERRED_EMAIL=krystalsophroniaadonis7@hotmail.com \
SOCIAL_PREFER_MAGIC_LINK=1 \
PYTHONPATH="D:/Taadaa/Hotmail;." \
/d/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe -u social_reg_v1.py 30 --ss --defer-tracking-write --resume > /tmp/reg30.log 2>&1
```

## 4. PowerShell liệt kê process python (bash mangle `$_` → phải viết .ps1)

Inline `powershell -Command "Get-CimInstance ... | ForEach-Object { $_.ProcessId ... }"` bị bash ăn `$_` → ParserError.
Viết file `.ps1` (write_file) rồi `powershell -NoProfile -ExecutionPolicy Bypass -File list_py.ps1`:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' } | ForEach-Object { Write-Output ($_.ProcessId.ToString() + '|' + $_.CommandLine) }
```

Filter theo command line (`grep -i social_reg`) để tách orphan của mình khỏi process hợp lệ khác (gateway hermes_cli,
tik3 render batch random_batch_render.py). tasklist theo PID: `MSYS_NO_PATHCONV=1 tasklist /FI "PID eq N" /NH`.

## 5. Test stale khi thay seam (nhắc lại từ SKILL.md, bản đầy đủ)

- `test_outlook_browser_login_is_not_skipped_by_inbox_url_bar` fail StopIteration khi: (a) mock tên hàm CŨ
  `_canonical_hotmail_login` trong khi code gọi `_canonical_hotmail_login_with_recovery` (hàm thật chạy, ăn hết pages
  iterator); (b) pages iterator hết giữa vòng poll. Sửa: mock đúng tên hàm + `iter([sign_in] + [inbox]*10)`.
- Riêng lẻ từng test có thể pass nhưng fail khi chạy cùng file (state chung) — chạy cả file, không chỉ test đơn lẻ.