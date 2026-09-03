# Run reg pending (mail chưa reg TikTok) — 2026-08-11

Session: check máy thiếu acc → detect pending mail → lock → reg 1 acc/máy.

## Workbook audit: đếm theo ID THẬT, không đếm dòng

File chính `D:\OneDrive\Tiktok_Reg\taikhoan_dat_v2_updated .xlsx` (sheet "Tài
Khoản", cột: Máy | Tik | ID | PASS | 2FA | GMAIL | ...) có 80 máy × 6 dòng
placeholder (mỗi máy 6 slot, "Tik" là STT toàn cục 1..626). Nhiều dòng là
placeholder **ID=None** — máy 75–80 có đủ 6 dòng nhưng TOÀN BỘ ID=None (chưa
có acc thật).

- **Pitfall (user sửa trực tiếp: "kiểm tra kiểu gì v mấy con 76-80 làm gì đủ")**:
  đếm `len(rows per máy)` = 6/6 → kết luận "đủ acc" là SAI. Phải đếm số dòng
  có ID thật (không None, không rỗng, không bắt đầu bằng `http`):
  ```python
  acc_ok = {m: 0 for m in range(1, 81)}
  for r in rows:
      m = str(r[0]).strip(); acc = r[2]
      if acc and str(acc).strip() and not str(acc).strip().startswith('http'):
          acc_ok[m] += 1
  # máy thiếu tik2/tik3 = acc_ok[m] < 3; máy 75–80 = 0 acc
  ```
  Kết quả 11/8: 31(1), 38(2), 66(2), 67(2), 70(2), 73(1), **75–80 (0 acc)**.
- File nuôi acc `taikhoan_run_safe.xlsx` (sheet Accounts, May|Device ID|ID)
  cùng bẫy: máy có 6 dòng nhưng cột ID rỗng = chưa reg.

## Detector `_detect_clean.py` fail closed vì row rác trong inventory

`python -u _detect_clean.py` → `DETECTION_BLOCKED: TARGET_INVENTORY_MISSING_SERIAL:
row 418`: inventory workbook có dòng máy có giá trị nhưng serial None (dòng
rác sau khi xóa dữ liệu trong Excel). Loader `scripts/target_inventory.py`
fail-closed với BẤT KỲ dòng máy-thiếu-serial nào → detect toàn bộ chết.

Fix: backup file rồi `ws.delete_rows(rn)` cho dòng `may != None and serial is
None`, save, chạy lại detector.

**Pitfall env override — sửa nhầm file**: `project_paths.py`:
`TARGET_INVENTORY_WORKBOOK = TIKTOK_REG_TARGET_INVENTORY_WORKBOOK |
TIKTOK_SAFE_WORKBOOK | TIKTOK_ACCOUNT_WORKBOOK | default OneDrive copy`.
Môi trường đang set `TIKTOK_SAFE_WORKBOOK` + `TIKTOK_ACCOUNT_WORKBOOK` =
`D:\Taadaa\tiktok-luot nuoi acc\data\taikhoan_run_safe.xlsx` (KHÁC bản
OneDrive). Trước khi sửa inventory phải in `os.environ` các biến đó; sửa
nhầm bản OneDrive thì detector vẫn lỗi row cũ.

## Chạy reg: `_run_all_targets.py --full-scope-takeover`

- Detector chuẩn chọn target: source-backed + password-present +
  TikTok-ID-empty + **max 1 acc/STT** (đúng yêu cầu "mỗi máy reg tối đa 1
  acc"). Output `_clean_targets.json` → `artifacts/pending/...`.
- Runner tự acquire lock per STT (`project="Tiktok_Reg/run_all"`), launch
  `social_reg_v1.py <serial> <stt> --ss --defer-tracking-write`, env
  `SOCIAL_PREFERRED_EMAIL`, `SOCIAL_RECOVERY_HANDLER` theo type.
- **`--full-scope-takeover` chỉ reclaim lock INACTIVE** (status blocked/
  handoff + owner_active=false). Máy đang bị feed session ACTIVE
  (`status=queued_v2`, `owner_active=true`) vẫn `SKIPPED (locked)` — ĐÚNG,
  không giành lock máy đang nuôi acc.
- Result dir: `$LOCALAPPDATA/Taadaa/Tiktok_Reg/artifacts/runs/social-batch-all/<ts>/batch_1/stt_XX/stdout.log`.
- Chạy qua `terminal(background=true, notify_on_complete=true)` — batch reg
  kéo dài hàng chục phút; foreground bị chặn 600s.

## FINAL_BLOCKED signature lớp reg (evidence đủ, đừng retry mù cùng mail)

Kết quả 11/8: 6/6 FAILED, ai dính blocker nào:
- `[7d] DOB initial readback missing or unparsable` (30, 39) — màn "Thêm
  ngày sinh" SeekBar, script không parse được giá trị ban đầu.
- `GMAIL_RECOVERY_CAPTCHA` (34) — Google CAPTCHA khi add existing account.
- `OTP_RESEND_NO_FRESH_CODE` (38, 54) — gốc là **Hotmail LoginBlocked** trên
  canonical flow → inbox không đọc được OTP → hết lượt resend.
- `[06_email_option] icon_count_0` (66) — màn login không thấy option
  email/username.
- Evidence: `artifacts/ui_dumps/blocked_*_...xml` + `screenshots_social/blocked_*.png`.

## DEVICE_LOCK_STATUS_OWNERSHIP_MISMATCH ở finish — vô hại

Runner kết thúc `lease.finish(...)` ném
`DeviceLockTransactionError: DEVICE_LOCK_STATUS_OWNERSHIP_MISMATCH` khi lock
bị thao tác giữa chừng (consumer khác/scheduler chạm lock file) — KHÔNG đổi
kết quả per-target (mỗi máy đã có verdict riêng trong summary và
`tracking_result_*.json`). Lock các máy reg cũng đã được dọn.

## ROOT CAUSE THẬT: DOB fail hàng loạt — KHÔNG phải timeout 60s (user phản biện đúng)

Lần chạy đầu 11/8: máy 30/39 dính `[7d] DOB initial readback missing or
unparsable` — log lộ dấu hiệu: `[adb warn] ls/cat: /sdcard/window_dump_*.xml:
No such file or directory` (uiautomator dump không sinh file).

- **Kết luận SAI lúc đầu (đã sửa)**: tưởng commit `1328de2` (UI capture timeout
  60s) làm uiautomator treo → revert cả commit. **User phản biện: "Ui nhiều
  case tăng 60s cứu đc mà, hay do cái dob nó v? Trc khi update cái 60s có sửa
  nhiều cái nữa mà"** — và đúng: diff `1328de2^..1328de2` cho thấy 2 yếu tố:
  1. **uiautomator treo là lỗi gốc có sẵn** (10-14 lần fail `window_dump` để)
     → `get_ui_xml` trả XML rỗng — KHÔNG do timeout.
  2. **Bản mới thêm fail-cứng** trong `fill_birthday()`:
     `if not before_parsed: raise RuntimeError("[7d] DOB initial readback
     missing or unparsable")`. Bản cũ KHÔNG raise — rỗng thì fallback estimate
     ngày hôm nay rồi swipe tiếp → không bao giờ fail cứng.
- **`[01_open] TikTok not foreground` (38/39/54) cũng là uiautomator treo**:
  launch xong mọi dump XML fail → không đọc được màn → không xác nhận
  foreground. Fix đúng = B1 ATX-kill (`pkill -9 atx-agent` + `am force-stop
  com.github.uiautomator` + `/data/local/tmp/atx-agent server -d`), không phải
  app lỗi.
- **Quyết định cuối (user chốt "Ok")**: UN-revert (giữ bản mới + timeout 60s),
  thêm fallback DOB thay raise, rồi theo yêu cầu "bản ms kéo dob ngu thì dùng
  lại bản cũ đi" → swap `fill_birthday()` + helpers DOB về bản cũ
  (`1328de2^`), GIỮ NGUYÊN fix CDP OTP + timeout 60s. Script swap: dùng ast
  xoá hàm DOB top-level mới, chèn hàm DOB bản cũ trước `def
  extract_otp_from_xml`; giữ lại `_is_tiktok_dob_picker_surface_xml` (recovery
  path vẫn gọi).
- **Bài học chốt**: khi 1 commit sửa NHIỀU thứ (timeout + refactor + fail-cứng
  mới), phải diff KỸ từng phần rồi mới chốt root cause — đừng kết luận theo
  tên commit. Bằng chứng DOM/UI thực tế (probe CDP, dumpsys) > suy luận.
  User sẽ phản biện kết luận sai; sửa handoff.md ngay khi có thông tin đúng.
- **Pitfall sau revert — state bẩn máy**: máy còn kẹt màn
  SignUpOrLoginActivity/launcher từ batch fail trước → fail ở bước khác. Fix:
  `adb -s <serial> shell am force-stop com.ss.android.ugc.trill` cho từng máy
  target (giữ login, KHÔNG `pm clear` farm box điện) rồi chạy lại batch.

## CDP OTP lấy NHẦM MÃ CŨ — DOM Outlook liệt kê mail MỚI TRƯỚC (fix 2026-08-11)

Máy 30/57 fail `OTP_REJECTED_AFTER_FRESH_RETRY` dù CDP đọc được code. User chỉ
ra: "mã về khác cái m nhập, m tự chế số ở đâu ra v".

- **Probe DOM thật** (forward `chrome_devtools_remote` + `_cdp_evaluate`):
  `T TikTok 1:07 AM → 310726 là mã...` hiện TRƯỚC `T TikTok 1:05 AM → 630427
  là mã...`. **Outlook DOM liệt kê mail TikTok MỚI NHẤT TRƯỚC, cũ sau.**
- **Bug**: `_try_get_otp_outlook_cdp` dùng `reversed(candidates)` với giả định
  cũ "mail mới nhất nằm cuối conversation" → lấy mã CŨ (630427) → TikTok
  reject. Fix: `for code in candidates:` (lấy phần tử ĐẦU = mã mới nhất), sửa
  luôn comment JS "return result.slice(0, 10)".
- **Probe script**: forward port → liệt kê tab outlook.live.com/mail → chạy
  expression regex 6 chữ số trong node chứa "tiktok" (lấy mẫu text 120-140 ký
  tự để đối chiếu timestamp mail). Chi tiết: `references/` probe pattern trong
  `scripts/` (nếu có) hoặc tái tạo từ `_try_get_otp_outlook_cdp`.
- **Reg kiểm chứng**: sau fix, máy 30 qua OTP (trước reject 2 lần) — chứng
  minh đúng hướng.

## `--resume` — chạy TIẾP tại màn hiện tại, CẤM chạy lại từ đầu (user bắt buộc)

User: "Chạy ngay tại trạnh thái hiện tại đéo đc chạy lại từ đầu... cấm chạy
lại từ đầu" khi máy 30 qua OTP xong kẹt màn DOB.

- **Lệnh**: `SOCIAL_PREFERRED_EMAIL=<email> python -u social_reg_v1.py <serial>
  <stt> --ss --defer-tracking-write --resume` — skip các bước đăng ký đầu,
  tiếp tục từ màn hiện tại (email form / OTP / DOB / password / name đều có
  nhánh resume trong register flow).
- **Trước khi chạy**: dọn lock stale nếu worker cũ chết —
  `machine_<stt>.lock.json` + `serial_<serial>.lock.json`, điều kiện an toàn:
  `status=handoff` + `owner_active=false` + PID chết (tasklist 1 slash).
- **Không `am force-stop` khi đang resume**: force-stop = mất màn OTP/DOB
  hiện tại = chạy lại từ đầu, vi phạm rule.

## DOB_CONTINUE_NO_TRANSITION — signature đã biết (máy 34), budget 2 attempts

Resume tới màn DOB, wheel kéo đúng (1/1/1999), nút "Tiếp tục" enabled/clickable
nhưng tap (edge + center + input tap tay + sau ATX-kill) KHÔNG chuyển màn →
`[7d] DOB Continue did not transition; still on birthday screen`. Đây là
signature máy 34 từng FINAL_BLOCKED nhiều handler (handoff có ghi) — hết budget
2 attempts → dừng, báo user, không retry mù.