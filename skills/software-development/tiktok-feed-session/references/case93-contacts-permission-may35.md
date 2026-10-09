# Case 93 — May 35: popup xin quyen danh ba tab Ho so ("Khong cho phep" vs "Mo cai dat")

Alert text (modal in-app TikTok, tab Ho so):
- Body: "De ket noi voi nhung nguoi ban biet tren TikTok, hay cho phep truy cap vao danh ba cua ban trong muc cai dat thiet bi."
- 2 nut: "Khong cho phep" (trai, DENY) | "Mo cai dat" (phai, OPENS SETTINGS — TUYET DOI KHONG CHAM).

## 1. Handler co san (Case 75) chua du
`contacts_settings_permission_prompt` (priority 91) trong
`python_runner/flows/benign_popup_registry.py` da ton tai tu Case 75 (May 52),
nhung May 35 lo ra 2 khe ho:
1. Detection chi match chu co dau → OCR/XML mat dau (ASCII) thi miss.
2. Dismisser dung 1 label-set chung (`Khong cho phep` + `Huy`/`Cancel` lan lon)
   → nguy co bam nham nut generic khi ca 2 nut deny deu hien.

## 2. Fix chuan (Case 93)
File: `python_runner/flows/benign_popup_registry.py`
- `_detect_contacts_settings_permission`: them keyword ASCII fallback
  (`de ket noi voi nhung nguoi ban biet`, `danh ba cua ban trong muc cai dat`)
  + so sanh accent-stripped (unicodedata NFD, loai Mn) ca 2 chieu.
- `_dismiss_contacts_settings_permission`: tim 2 vong
  - Vong 1 (primary, bat buoc truoc): `khong cho phep` / `khong cho phep` ASCII /
    `don't allow` / `dont allow` / `deny` / `tu choi` / `tu choi` ASCII.
    Dam bao May 35 bam DUNG nut trai.
  - Vong 2 (fallback, chi khi vong 1 miss): `huy` / `cancel` / `de sau` / `not now`.
  - Khong bao gio tap `Mo cai dat` / `Open settings` (chi dung lam marker detection).
  - Cuoi cung fallback phím Back (send_device_back_key).

## 3. Phan biet ket qua canary
- `blocked-vichanger-vpn` (proxy port closed/refused, vi du serial ce061606c3322c1603)
  la blocker HA TANG preflight — session dung TRUOC khi toi modal danh ba.
  Khong duoc ket luan "handler sai" tu blocker nay.
- Chi danh gia handler qua: unit test + gia lap dismisser (muc 4), khong phai
  qua canary bi chan VPN.

## 4. Recipe kiem chung (chay tu `python_runner/`, PYTHONPATH=.)
```bash
python -c "
from flows.benign_popup_registry import find_matching_handler
xml35 = '<hierarchy><node text=\"Để kết nối với những người bạn biết trên TikTok, hãy cho phép truy cập vào danh bạ của bạn trong mục cài đặt thiết bị.\" /><node text=\"Không cho phép\" /><node text=\"Mở cài đặt\" /></hierarchy>'
m = find_matching_handler(xml35, ''); print(m.name, m.priority)
# ky vong: contacts_settings_permission_prompt 91
"
python -c "
from unittest.mock import MagicMock
from flows.benign_popup_registry import _dismiss_contacts_settings_permission
ctx = MagicMock()
ctx.dump_hierarchy.return_value = '''<hierarchy>
  <node text=\"Để kết nối với những người bạn biết trên TikTok, hãy cho phép truy cập vào danh bạ của bạn trong mục cài đặt thiết bị\" bounds=\"[100,800][980,1000]\" />
  <node text=\"Không cho phép\" clickable=\"true\" bounds=\"[120,1100][520,1230]\" />
  <node text=\"Mở cài đặt\" clickable=\"true\" bounds=\"[560,1100][960,1230]\" />
</hierarchy>'''
ctx.adb = MagicMock(); ctx.adb.shell.return_value = MagicMock(ok=True)
res = _dismiss_contacts_settings_permission(ctx)
print(res.dismissed, res.reason, ctx.tap.call_args_list)
# ky vong: True dismissed_contacts_settings_permission_prompt [call(320, 1165)]
# (320,1165) = center nut 'Khong cho phep', khong phai 'Mo cai dat'
"
python -m pytest tests/test_benign_popup_registry.py -q -k contacts
```

## 5. Pitfall da gap trong session nay (ghi de session sau tranh)
- Co subagent khac (sa-0-*) cung sua `benign_popup_registry.py` song song →
  patch tool bao "modified by sibling subagent". Luon re-read doan can sua
  ngay truoc patch, va giu baseline `git diff --stat` sach truoc khi sua.
- `git stash pop` keo theo conflict第十七 lan ở HANDOFF.md/config/workbook —
  phai `git checkout HEAD -- .` de tra ve baseline truoc khi tiep tuc (mat het
  diff Case 92/93 neu khong can than). Quy tac: khong stash/pop giua chung
  khi chi can kiem tra lich su — dung `git show <sha> -- <path>`.
- `uiautomator dump` tren may farm yeu bi Killed (EXIT=137) la binh thuong;
  dung `dumpsys window windows | grep mCurrentFocus` + `dumpsys activity top`
  de xac nhan TikTok focus thay vi co dump XML.
