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

- User gửi file `.gemlogin` (workflow GemLogin / Automa) và muốn kiểm tra logic, tìm lỗi, hoặc port sang consumer automation-core.

- Dùng cho việc port workflow TikTok (follow, tìm kiếm, nuôi acc...) sang

  consumer automation-core.



## Chi tiết Audit Workflow GemLogin (.gemlogin)

Xem cẩm nang checklist chi tiết tại: `references/gemlogin-workflow-audit-checklist.md` (Checklist 5 bẫy lỗi: Graph disconnect/unreachable nodes, Kill-switch ngầm expiration date, Hardcoded Windows user path, Async NextBlock race condition, và TikTok CSP block).



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

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
