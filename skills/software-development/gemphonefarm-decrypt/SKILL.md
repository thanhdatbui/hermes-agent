---
name: gemphonefarm-decrypt
description: "Giải mã file workflow GemPhoneFarm dạng Protected (.gemphonefarm) — tìm hiểu cấu trúc flow, selectors, params của workflow TikTok mua/Taadaa. Kèm cách bẻ cơ chế mã hoá từ app.asar nếu password đổi."
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [gemphonefarm, decrypt, tiktok, workflow, crypto-js, asar]
    related_skills: [automation-core-consumer]
---

# Giải mã GemPhoneFarm Protected workflow

## 🛑 STOP GATE (bắt buộc — chi tiết: skill taadaa-farm-ops-rules)
Máy live + script chạy/lỗi → KHÔNG tự sửa code, KHÔNG tự chạy lại, KHÔNG tự probe/tay khi chưa được user yêu cầu.
Lỗi → screencap → gửi ẢNH THẬT (MEDIA:<path> dòng riêng, KHÔNG bọc markdown, KHÔNG gửi đường dẫn text) → DỪng chờ user hướng dẫn.
User hướng dẫn bước nào → encode bước đó vào script + test → mới chạy lại. Nghi ngờ → HỎI.

## Trigger

- User gửi file `.gemphonefarm` (thường tên `..._Protected.gemphonefarm`)
  và muốn đọc/giải mã script.
- Dùng cho việc port workflow TikTok (follow, tìm kiếm, nuôi acc...) sang
  consumer automation-core.

## Cấu trúc file

```json
{
  "extVersion": 2, "name": "...", "icon": "...", "table": [],
  "version": "1.0.0",
  "drawflow": "<base64 — MÃ HOÁ nếu Protected, JSON object nếu không>"
}
```

- Protected: `drawflow` là chuỗi base64 của CryptoJS AES-256-CBC (passphrase
  mode, OpenSSL EVP_BytesToKey/MD5, prefix `Salted__`, PKCS7), bắt đầu bằng
  `U2FsdGVkX1` sau base64. Giải mã ra JSON object `{nodes:[...], edges:[...]}`.
- Block name nằm ở **node.label** (trigger, touch, element-exists, type-text,
  javascript-code, excel, loop-data, repeat-task...), KHÔNG phải data.name.

## Password (rút từ app.asar bản cài 2026-08-11)

- **Workflow "Encrypt script": `!#gemlogin$#&^%*`** (hàm `$9e` trong
  `resources/web/assets/index-*.js`: `s.drawflow = rv.encrypt(JSON.stringify(n.drawflow), "!#gemlogin$#&^%*")`).
- Credentials/quota của app: `*#12345*()` (hàm `JNt`, format `sig65 + ciphertext`).
- Rút ra từ: `C:\Users\Kibe\AppData\Local\Programs\GemPhoneFarm\resources\app.asar`
  (giải nén bằng `npx -y @electron/asar extract ...`), logic nằm ở
  `resources/web/assets/index-*.js`, renderer là web app (main.js chỉ chứa
  license decrypt).

## Cách giải mã (tool có sẵn)

Repo `D:\Taadaa\tiktok-follow`:

```
python tools/decrypt_gemphonefarm.py <file_Protected.gemphonefarm> [out_prefix]
```

- Output: `<prefix>_decrypted.json` + `<prefix>_unprotected.GemPhoneFarm`.
- Tool tự dùng openssl trước (`openssl enc -d -aes-256-cbc -md md5 -k '!#gemlogin$#&^%*'`),
  fallback pycryptodome EVP_BytesToKey thuần python.
- Nếu openssl "bad decrypt" → có thể password đã đổi theo app version: mở lại
  app.asar, tìm hàm export có `rv.encrypt(JSON.stringify(...), "<password>")`.

## Phân tích nhanh flow

Flow follow qua tìm kiếm (TÌM-KIẾM) đã phân tích + verify line ref đầy đủ:
`references/tiktok-follow-flow-analysis-2026-08-11.md` (selectors, follow
button states Follow/Follow lại/Đã follow, identity @-prepend, tab Follower
= 0 matches trong flow gốc, cái gì là user-added).

```python
import json, collections
d = json.load(open(out_decrypted, encoding="utf-8"))
nodes = d["drawflow"]["nodes"]
print(collections.Counter(n.get("label") for n in nodes))
# toàn bộ xPath/selector:
for n in nodes:
    for k in ("xPath","selector"):
        v = (n.get("data") or {}).get(k)
        if isinstance(v, list):
            for i in v: print(i.get("value"))
        elif v: print(v)
```

## Pitfalls

- ASCII dấu tiếng Việt trong tên file: git-bash có thể mangle — xử lý qua
  python hoặc quote cẩn thận; git hiển thị tên 8-bit (`T\303\214M...`).
- Chỉ 1 selector "Tìm kiếm" nghĩa là flow chủ yếu tap toạ độ/resource-id ngắn
  — port sang automation-core nên ưu tiên selector semantic + core popup
  handler, không copy toạ độ mù.
- File decrypted có thể chứa JS check hết hạn (vd `2026-11-28`) — bản mua có
  hạn, bản tự build không cần.
- Scan credential trước khi commit: grep `pass|otp|token|secret|cookie|2fa`
  trong file giải mã.