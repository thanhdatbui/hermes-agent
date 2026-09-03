# Account switcher / profile tab — máy 34 (2026-08-07)

Session: reg acc truongthuy111034 trên máy 34 (SM-G930K, TikTok 46.x) lỗi
`SWITCHER_ANCHOR_AMBIGUOUS` suốt nhiều giờ. Kết luận cuối: **3 lớp root cause
rời nhau, đừng gộp**.

## Lớp 1 — Tap profile tab lệch tọa độ (root cause thật, đã fix)

- `COORD["profile_tab"]` hardcode `(972, 1857)` nhưng tab "Hồ sơ" bounds thật
  là `[864,1864][1080,1903]` → center `(972, 1883)`. Tap 1857 cao hơn 26px
  TRÊN bounds → trượt → máy nằm lại feed.
- Hệ quả: `go_to_profile` log "profile selected" là DƯƠNG TÍNH GIẢ
  (`_profile_tab_node` trả node coord từ dump, không phải tap thật ăn).
- Fix: `COORD["profile_tab"]` → `(972,1883)` + `_profile_tab_node` clamp
  `if cy < 1870: cy = 1883` (dump node có thể lệch vài px vs tap thật).
- **Pitfall: tọa độ bottom-nav hardcode có thể lệch vài chục px theo device;
  verify bằng screenshot/vision_analyze sau khi tap, không tin dump.**

## Lớp 2 — uiautomator dump STALE khi TikTok chạy lâu (chưa fix triệt để)

- Sau reboot: dump E=0 sạch (launcher idle). Sau khi TikTok foreground lâu:
  `uiautomator dump` bị kill (E=137) HOẶC trả nội dung CŨ (feed "Tây Ninh")
  dù màn thật là profile yobi (verify bằng screenshot).
- `pkill -9 -f atx-agent` + `am force-stop com.github.uiautomator` KHÔNG đủ
  khi uiautomator đã treo — dump vẫn stale.
- **Kỷ luật chẩn đoán: khi dump vs thực tế mâu thuẫn, `screencap` + pull +
  vision_analyze làm ground truth — đừng kết luận "máy không render profile"
  từ dump stale (đã kết luận sai 1 lần).**
- LSPosed popup ("No LSPosed access !!!") che màn sau boot → tap OK trước khi
  dump; nếu không, dump trả popup thay vì launcher idle.
- Máy để ngôn ngữ khác (Hàn) → launcher text khác ("KT고객지원"), không lạ.

## Lớp 3 — core `coordinate_fallback` hook chưa implement (fix đang làm)

- automation-core `open_switcher` (account_switcher.py ~dòng 679): khi anchor
  semantic (tên user yobi) không đọc được trong dump → gọi
  `adapter.coordinate_fallback("switcher")` → nếu None → `SWITCHER_ANCHOR_AMBIGUOUS`.
- Consumer `_SocialAccountSwitcherAdapter` CHƯA implement hook này → luôn None.
- Fix consumer-only hợp lệ: thêm
  `def coordinate_fallback(self, action=None): if action == "switcher": return (540, 150); return None`
  (540,150 = tap tên user header mở dropdown — verified live 2026-08-07).
- **Kiểm tra: tests/test_login_method_entry.py:8 assert `not hasattr(adapter,
  "coordinate_fallback")` — guard cũ ngăn consumer override core policy; thêm
  method sẽ BREAK test → phải đổi sang `hasattr` + thêm test
  `coordinate_fallback("switcher")==(540,150)` + `("unknown") is None`.
- Rule: consumer chỉ cung **adapter primitives** (hook core đã support sẵn),
  KHÔNG tự thêm switcher coordinate/anchor tay — đọc core trước, tìm hook.

## Flow chiến thắng đã chứng minh (run 182529)

Máy ở MÀN LOGIN → runner skip-profile → email → OTP (không cần profile tab).
Profile tab không đáng để cày khi máy có thể vào thẳng màn login.

## Audit (opencode longcat-2.0-free) bắt đúng

- MINOR_FIXES, P0: test guard `not hasattr` sẽ break — verify code thật trước
  khi nói "false positive" (bài học cũ: audit "dead code" từng là false
  positive — verify từng finding bằng read_file).
