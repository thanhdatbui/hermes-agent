# Outlook CDP anchor-rect probe + tap fix (magic-link)

## Triệu chứng (live STT30, attempt 2, 2026-08-11)

Handler `_read_outlook_magic_link_with_evidence` tìm được semantic node 'Xác minh email'
bounds=[99,1872][978,1920] (đúng vị trí anchor thật) nhưng tap KHÔNG gây transition:
recapture sau tap vẫn `packages=[com.android.chrome, ...]` → fail closed
`OUTLOOK_MAGIC_LINK_ACTION_NOT_VERIFIED`. Màn hình thật sau tap: mail Outlook TikTok
mở ở Chrome, không có popup/dialog, không có nút link nào hiển thị.

## Root cause (3 lớp chồng nhau)

1. **Anchor web nằm DƯỚI viewport**: CDP probe cho anchor 'Xác minh email' rect CSS
   [33,545,293,44] → device [99,1875][978,2007] — vượt màn 1920. Tap vào y~1896 rơi
   ra ngoài content hiển thị.
2. **IME đang mở che vùng tap**: `dumpsys input_method` → `mInputShown=true`,
   `mIsInputViewShown=true`; uiautomator XML có keyboard overlay
   `[0,1795][1080,1920]` (package com.github.uiautomator) — khung soạn thư reply
   (quickCompose `editorDiv` focused) của Outlook mở sẵn khi vào mail.
3. **uiautomator KHÔNG expose `<a>` clickable trong WebView**: semantic node tap được
   là text node bình thường không phải anchor thật; anchor chỉ thấy qua CDP.

## Probe CDP (recipe, không cần pip websocket)

```bash
adb -s <serial> forward tcp:9224 localabstract:chrome_devtools_remote
curl -s http://127.0.0.1:9224/json | python -m json.tool
# tìm tab: url chứa "outlook.live.com/mail/0/inbox/id" (mail đang mở)
```

WebSocket handshake + Runtime.evaluate viết tay (pip `websocket` KHÔNG có trên máy):
GET `/devtools/page/<id>` HTTP/1.1 + Upgrade: websocket, gửi frame masked
`{"id":1,"method":"Runtime.evaluate","params":{"expression":...,"returnByValue":true,"awaitPromise":true}}`,
đọc response id=1. Dùng sẵn helper `_cdp_evaluate()` của `social_reg_v1.py` khi probe trong repo.

Expression tìm anchor magic-link + viewport:

```js
(() => {
  const vw = window.innerWidth, vh = window.innerHeight, dpr = window.devicePixelRatio;
  const out = [];
  for (const a of document.querySelectorAll('a[href]')) {
    const href = a.href || '';
    if (!/email_verification|tiktok\.com/.test(href)) continue;
    const r = a.getBoundingClientRect();
    out.push({text:(a.innerText||'').trim().slice(0,60), href:href.slice(0,90),
              rect:[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)]});
  }
  const mask = document.getElementById('x_mask_email_link');
  return JSON.stringify({vw, vh, dpr, anchors:out, maskRect: mask ? (()=>{const r=mask.getBoundingClientRect();return [Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)];})() : null});
})()
```

Kết quả thật STT30: `{vw:360, vh:518, dpr:3, anchors:[{text:"Xác minh email",
href:"https://www.tiktok.com/ucenter_web/deeplink/email_verification?SHORTCUT_NEED_LOGIN=...",
rect:[33,545,293,44]}], maskRect:[47,466,266,58]}`.

## Map CSS → device px

- WebView content top offset = **240 device px** (toolbar rỗng phía trên; XML xác nhận
  mask device [138,1635][939,1796] tương ứng CSS [47,466,266,58] → `device_y = 240 + css_y*3`).
- `device_x = css_x * dpr` (không có offset ngang).
- Anchor [33,545,293,44]@dpr3 → device [99,1875][978,2007] (ngoài màn 1920).
- Sau scroll → [33,317,293,44] → device [99,1191][978,1323] (trong viewport) → tap (538,1257).

## Fix đã merge (social_reg_v1.py, 2026-08-11)

Thứ tự trong helper trước tap link:
1. `_outlook_dismiss_ime`-style: BACK keyevent 4 có giới hạn, recapture, yêu cầu hết
   keyboard overlay / `mInputShown="true"` trong XML (regex
   `(?:mInputShown|mIsInputViewShown|...)\s*=\s*["']?true["']?`). KHÔNG bao giờ tap
   khi IME che vùng tap.
2. CDP probe rect THẬT anchor (href chứa `email_verification`; fallback `tiktok\.com`),
   map sang device px.
3. Nếu `y2 > 1795` → **scroll BẰNG UI swipe** (`input swipe` trên content, kéo nội
   dụng lên: từ (540,1500) → (540,500), duration 600ms) → CDP **re-probe rect MỚI**
   tới khi `y2 <= 1795`, recapture evidence. **KHÔNG dùng `window.scrollBy`/`window.scrollTo`**:
   Outlook web mail scroll nằm trong container div riêng (không phải window), nên
   scroll JS vô tác dụng — live STT30 2026-08-11: rect_css giữ nguyên [33,545,293,44]
   sau 3 lần scrollBy → fail closed `CDP anchor vẫn ngoài viewport sau scroll`.
   Anchor CSS y=545 chỉ cần cuộn ~100-200 CSS px là vào viewport (anchor sau scroll
   thật: [33,317,293,44] → device [99,1191][978,1323]).
   Implement (2026-08-11): `_cdp_scroll_outlook_anchor_into_view` +
   `_OUTLOOK_MAGIC_LINK_CDP_SCROLL_JS` **XOÁ hẳn** (JS scroll vô dụng thì bỏ, không
   giữ fallback); helper `_swipe_outlook_magic_link_content_down` + constants
   `_OUTLOOK_MAGIC_LINK_CONTENT_SWIPE_START/END/DURATION`; loop trong
   `_outlook_magic_link_cdp_tap_target`: probe → y2>1795 → swipe → sleep 1.2 →
   re-probe rect MỚI (không dùng rect cũ) → tối đa `_OUTLOOK_MAGIC_LINK_CDP_SCROLL_ATTEMPTS`=2
   → vẫn ngoài viewport → fail closed None.
4. Chỉ tap khi rect trong viewport + khớp khoảng hợp lệ; tap xong verify transition
   như cũ (`_verify_visual_magic_link_transition` + open-with dialog).

## Ràng buộc

- **KHÔNG CDP JS click** (`el.click()`) — audit cấm: querySelector click navigate tab
  Chrome sang TikTok web, bypass deep-link app; CDP chỉ dùng để ĐỌC rect.
- Anchor href không phải `email_verification` → fail closed, không tap.
- Probe CDP trả None / rect ngoài viewport sau scroll giới hạn → fail closed, không tap.
- Tests: `tests/test_login_outlook_magiclink_branch.py` — IME mở → handler đóng keyboard
  trước tap; anchor ngoài viewport → scroll + re-probe; rect trong viewport → tap đúng
  tọa độ + MAGIC_LINK khi transition verified; probe None → None.