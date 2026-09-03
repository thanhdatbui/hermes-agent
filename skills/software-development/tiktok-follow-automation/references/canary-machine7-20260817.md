# Canary máy 7 — 2026-08-17 (mode 2' + hybrid + gate video live)

## Kết quả
- `FOLLOW_RESULT`: **status OK**, followed **8 nick thật** (`luuhuong2802`, `trangtran168432`,
  `ninhy05100`, `thuuy.thy`, `dinhlan24076`, `khnh.vyyyy6`, `stevemgjqec`, `bch.ngc.ngc91`),
  skipped 1 (`thanh.h.dng00` — đã follow sẵn), failed_ids `[]`, `follow_failed: False`.
- State máy 7: 9 followed (gồm `duongkien1202` từ lượt trước).
- Cấu hình: `config/machine7.yaml` — mode `both`, budget 6–10, inter-follow delay 30–90s,
  `--account-row-index 1` (`lm.ngc.dip0`, 10 video → gate full budget).

## Lỗi live gặp phải + fix (theo thứ tự xảy ra)
1. **OPEN_TIKTOK_FAILED — dumpsys báo SplashActivity dù feed đã render** (TikTok KHÔNG chuyển
   activity khỏi SplashActivity; dumpsys nói dối):
   - `_feed_xml_is_verified` bỏ gate `activity` — chỉ cần package đúng + XML feed markers
     (ATX-primary). Commit `da97169`.
   - Test cũ `test_feed_verifier_rejects_missing_or_empty_activity_even_with_feed` phải đảo
     semantics → accept feed khi activity splash/empty.
2. **OPEN_TIKTOK_FAILED lần 2 — `prepare_tiktok` (core) LUÔN force-stop + close_recents +
   relaunch** → Splash mới + ATX wedge (XML rỗng 1–2 lần đầu) → timeout dù feed OK:
   - `FollowAdapter.prepare_tiktok` thêm `_feed_already_open()`: dump UI (ATX) có feed markers
     + package đúng → skip relaunch, trả `StartupResult(True...)` dùng feed sẵn.
   - KHÔNG sửa core (`prepare_tiktok_app` hardcode `close_recents=True`) — hook ở follow
     adapter, đúng scope "sửa code đi đúng thao tác".
3. **VERIFY_IDENTITY fail — popup "Follow bạn bè của bạn"** (gợi ý follow bạn bè) chặn account
   switcher. User chốt xử lý **cấp độ core**, 2 bước: **"follow lại xong bấm x đóng"**:
   - `follow_friends_suggest_vi`: markers `("follow bạn bè của bạn", "follow lại")` → tap "Follow lại"
   - `follow_friends_suggest_close_vi`: markers `("follow bạn bè của bạn",)` → tap "Đóng" (X)
   - Sau khi follow xong, nút "Follow lại" biến thành "Gửi .." → hết marker "follow lại" →
     rule 2 match. `dismiss_all` loop 3 rounds xử lý tuần tự. Commit core `1890533`, wheel 0.4.45.
4. **`contacts_permission` trả `detected` thay `dismissed`** — `DismissResult` KHÔNG có field
   `dismissed` (getattr mặc định False = luôn báo "chưa xử lý" → dismiss_all không loop round 2
   cho popup 2 bước). Commit `9279006`.
5. **MANUAL_REVIEW "không thấy đúng một nút Follow"** — profile nick đã follow render action
   button **"Gửi .."** (`id/ff8`) thay vì "Follow"/"Nhắn tin":
   - `FOLLOWED_TEXT` thêm `"Gửi .."`, `"Gửi tin nhắn"`, `"Message"`. Commit `2df2581`.
6. **Kẹt profile tìm kiếm** (profile NGƯỜI KHÁC qua search — có "Nhắn tin", không "Sửa hồ sơ"):
   user hướng dẫn bấm **mũi tên góc trái** (`id/bow` bounds ~(18,84,132,132)) → search history →
   back nữa → feed. KHÔNG dùng hardware Back phím (chỉ về search results, chưa hết). Xem
   SKILL.md pitfall "Kẹt profile tìm kiếm → bấm MŨI TÊN GÓC TRÁI thoát".

## Popup "Follow bạn bè của bạn" — node map (máy 7, TikTok 46.3.3)
- Title `text='Follow bạn bè của bạn'` rid `id/yhd`
- Nút "Follow lại" `id/thb` bounds `(748, 993, 240, 84)` clickable — CHỈ tồn tại khi chưa follow
- Sau follow: nút cùng bounds thành `"Gửi .."` (id/thb) — tiếp tục popup đề xuất nick khác
- X đóng: `id/e63` bounds `(916, 729, 120, 120)` content-desc "Đóng"
- Bấm "Follow lại" = follow bạn gợi ý (hành vi tự nhiên, user OK) — không hại, không phải
  dismiss X ngay từ đầu.

## Wheel rebuild + pip install path pitfall (MỚI, bắt buộc nhớ)
- follow repo import `automation_core` từ **site-packages (wheel cài)**, KHÔNG phải source ở
  `D:/Taadaa/automation-core/src` — sửa core phải **rebuild wheel + pip install** mới có hiệu lực.
- **bash `python -m pip install /d/Taadaa/...` → pip nhận `c:\d\Taadaa\...`** (MSYS convert sai
  vì python là Windows binary) → `OSError: No such file or directory`. FIX: dùng Windows path
  `python -m pip install "D:\\Taadaa\\automation-core\\dist\\automation_core-0.4.45-...whl"`.
- `pip install --force-reinstall` có thể **âm thầm không ghi đè** (mtime file không đổi) →
  `pip uninstall -y automation-core` trước rồi install sạch.
- Verify sau cài: `import automation_core.tiktok_popup` + đếm `TIKTOK_POPUP_RULES` + grep file
  site-packages; xóa `__pycache__` site-packages nếu vẫn thấy code cũ.

## ATX-primary rule (user hỏi "tao cài rule dùng ATX service thay ui automator, có làm theo chưa")
- Core `capture_ui_xml` ĐÃ ATX-primary: ưu tiên `ATX_SESSION` (pid-scoped `dumpWindowHierarchy`)
  trước, persistent/uiautomator fallback (commits `e57436b`, `727b6d4`, `9044b91`). Follow
  adapter `dump_ui()` → `capture_ui_xml` → tuân theo ✅.
- NHƯNG `get_focused_activity` (core `usb_debugging.py`) **vẫn dumpsys-only** → báo SplashActivity
  sai. Hệ quả: **feed verify KHÔNG được gate trên activity** (fix mục 1); nếu sau này muốn
  focused_activity ATX-primary, phải sửa chính core.

## Còn lại sau canary
- ✅ Mode 2' + hybrid + gate video + popup core: chạy thật OK máy 7 (1 máy, 8 follow).
- ⏳ Chưa chạy: canary rộng (2–3 máy), máy 1 row 1 `lipsellczaw` (nick khỏe, following dày)
  là ứng viên tiếp theo.

## ANCHOR CHỐT CUỐI 17/08 (user chốt sau canary, commit `dc5dc64`)
User xác nhận flow mode 2' đúng 3 bước: search anchor (Tik1/Tik2) → tab Đã follow →
follow nick farm trong list. Rồi chốt giới hạn anchor:

- **Anchor CHỈ Tik1/Tik2** — `engine.anchor_uids()` = account_row_index 1-based ≤2,
  KHÔNG search Tik3+ làm anchor (following mỏng → list gần như rỗng nick farm →
  lãng phí lượt search, ăn trần search 20/ngày của ông A).
- **Max 3 anchor/phiên** (`uids = anchor_uids()[:3]`): user phân tích 2-3 vs 3-5 →
  chốt 3: "cứ anchor 3 lần thôi còn lại cho đi module 1 hết cho đủ budget phiên đó".
  Lý do: Tik2 còn mỏng (69/73 máy mới 1 video) → search thêm anchor dễ lãng phí;
  module 1 = "lướt an toàn", mỗi lượt search đều có follow.
- **KHÔNG skip anchor đã follow** (user correction — tôi từng đề xuất filter
  `not state.is_followed(u)` rồi bị bác): anchor follow 300 nick → mình mới follow
  6-7 → list VẪN còn ~290 nick farm chưa khai thác; skip anchor vì đã follow = bỏ
  phí mỏ + đẩy qua module 1 oan. `state.is_followed` CHỈ áp cho nick TRONG list
  (không follow lại nick đã follow trong list), KHÔNG áp cho anchor.
- **Chiến lược tổng (user)**: module 1 follow nhiều trước → following list của
  Tik1/Tik2 dày nick farm → module 2 sau này càng khỏe — vòng tự củng cố. Turn đầu
  nick 1 chưa có following nhiều → kiểu gì cũng cần module 1.
- Tests mới: `test_anchor_already_followed_still_searched` (anchor đã follow VẪN
  được search), `test_max_three_anchors_then_mode1` (chỉ 3 anchor đầu mở). Mocks
  `_Engine` (cả 2 test file) phải thêm `anchor_uids()` = `list(self._uids)`.
- Full suite 277/277 xanh.