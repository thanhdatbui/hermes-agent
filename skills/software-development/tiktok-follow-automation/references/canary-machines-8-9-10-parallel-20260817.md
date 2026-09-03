# Canary máy 8/9/10 song song (2026-08-17) — thứ tự dispatch + nhả-follow TODO

Bối cảnh: sau canary máy 7 OK, user yêu cầu canary máy 8/9/10 (Tik1 row 1),
chạy SONG SONG, báo cáo module nào chạy + số Following tăng (KHÔNG phải video
count — user chửi "chụp video count làm gì, chụp số đã follow chứ").

## Kết quả thật
- **Máy 8** serial `98862733584d384151`, row1 `tolmavhj12k` (7 video → gate nửa 3-5):
  `MANUAL_REVIEW "hồ sơ thiếu handle (@uid) — từ chối tap Following"`, nhưng
  `followed: [lipsellczaw, duongkien1202, thanh.h.dng00, luuhuong2802, trangtran168432]`
  → **mode 1 follow 5 nick trước** rồi mode 2' mới chạy → cạn budget + fail anchor.
- **Máy 9** serial `988627414444594c51`, row1 `thy.nga475` (10 video → gate full):
  `OPEN_TIKTOK_FAILED` — máy đang ở Launcher (app chưa mở) → `_feed_already_open`
  False → force-stop + relaunch → máy yếu mở chậm >60s → timeout. Sau đó app render
  feed bình thường → chạy lại sẽ qua (không cần fix code).
- **Máy 10** serial `988627464e374e3234`, row1 `anhtruong840` (11 video → gate full):
  `VERIFY_IDENTITY fail` — cần debug nick máy 10 (chưa xong, session interrupted).

## ✅ RESOLUTION cuối ngày — sj8 hardcode + máy 9 rerun (commit `43eba98`)
- **ROOT CAUSE máy 8/9 \"hồ sơ thiếu handle (@uid)\" = hardcode `id/sf5` trong
  mode 2'** (không phải layout lạ): `_open_following_tab` + `_path_b_verify` gate
  CỨNG `endswith(\"id/sf5\")` nhưng máy 7/9 render handle = `id/sj8` → profile có
  @uid đầy đủ vẫn bị chặn → **mode 2' CHỈ search, KHÔNG bao giờ vào được list
  Đã follow** (user chẩn đoán đúng: \"mode 2 chỉ tìm kiếm chứ đéo chịu vào list
  đã follow của bất kì nick nào\") → rơi hết xuống mode 1 bù.
- Fix: gate = `profile_identity` có handle + **đúng 1 node @-prefixed** trên màn
  (`at_nodes` đếm text startswith \"@\") — không nhìn resource-id. Cùng pitfall
  sửa ở `_path_b_verify`. Test: `test_open_following_tab_accepts_sj8_handle`.
- **Máy 9 rerun (code mới, sau fix):** `FOLLOW_RESULT status MANUAL_REVIEW
  \"hồ sơ thiếu handle\"` nhưng `followed: 10 nick` (`lipsellczaw`, `duongkien1202`,
  `thanh.h.dng00`, `luuhuong2802`, `trangtran168432`, `ninhy05100`, `thuuy.thy`,
  `dinhlan24076`, `khnh.vyyyy6`, `stevemgjqec`), `follow_failed: False`,
  `budget_used: 10`. Search history UI (stevemgjqec, khnh.vyyyy6, dinhlan24076,
  thuuy.thy, ninhy05100) = mode 1 search-follow → **mode 2' vẫn fail anchor sớm,
  mode 1 bù HẾT budget 10**. (Chưa xác nhận sj8 fix đã qua canary — chạy tiếp
  máy 9 sau `43eba98` để verify mode 2' vào list thật.)
- **Pitfall báo cáo**: status `MANUAL_REVIEW` KHÔNG có nghĩa follow thất bại —
  mode 2' anchor fail set status nhưng mode 1 VẪN chạy bù (chỉ chặn
  FOLLOW_FAILED) và KHÔNG reset status về OK → `followed` đầy budget nhưng status
  vẫn MANUAL_REVIEW. Báo cáo phải đọc state JSON (`budget_used`, `followed`) +
  search history UI (phân biệt search-follow mode 1 vs anchor mode 2) trước khi
  kết luận module nào chạy bao nhiêu nick.

## Bug thứ tự dispatch mode both (fix sau máy 8 → TODO đã sửa)
`run_session` cũ chạy `if mode in ("1","both"): run_mode1` TRƯỚC rồi mới
`run_mode2` → mode 1 ăn hết budget phiên, mode 2' chạy sau cạn budget + fail
anchor (đúng lý do máy 8: follow 5 nick toàn mode 1, user thấy "search 1 nick
follow rồi không vào list following" = đang xem lúc mode 1 chạy).

**Fix (commit chờ, sau dc5dc64)**: đảo thứ tự → mode 2' TRƯỚC, mode 1 BÙ SAU:
```python
if mode in ("2", "both"): ... run_mode2(self, res)
if mode in ("1", "both") and res.status != STATE_FOLLOW_FAILED: run_mode1(self, res)
```
Mode 1 budget giờ TRỪ `len(res.followed)` (bù đúng phần thiếu, không tính lại
full budget):
```python
budget = max(0, min(state.session_budget(...), state.budget_remaining()) - len(res.followed))
```

## ĐÃ FIX — mode 2' nhả-follow swipe verify (commit 5c2522e + 2dab98f)
- Mode 1: sau tap follow → `_confirm_not_released()` = swipe 1 lần + dump lại →
  nút vẫn "Nhắn tin"/"Đã follow" = OK; quay lại "Follow" = FOLLOW_FAILED.
- Mode 2' FIX: `_path_b_verify` chạy sau **MỌI follow** (bỏ sample gate) — mở
  profile → `swipe_feed` 1 lần + dump lại (`recheck_xml`) → `_classify_profile_action`:
  vẫn followed = OK; `not_followed` = nhả → `state.set_follow_failed()` →
  FOLLOW_FAILED + dừng session; unknown = MANUAL_REVIEW.
- **Pitfall test-fixture**: FakeAdapter queue phải thêm 1 dump profile recheck
  SAU dump profile đầu (Path B giờ tiêu 2 profile dump: classify + recheck sau
  swipe). Test cũ push 1 `profile_b` → fail `assert res.followed == [...]` vì
  recheck nhận dump list → sửa queue thành `profile_b, profile_b`.
- Follow-one-follower: nhánh `cls == "followed"` giờ LUÔN gọi `_path_b_verify`
  (không chỉ khi `sample`) — user: "sau follow xong 1 nick bất kì thì vuốt trang
  cá nhân kiểm tra follow có bị nhả k".

## Random anchor (chốt cuối)
- `random.shuffle(engine.anchor_uids())` TRƯỚC `[:3]` (shuffle toàn pool Tik1/Tik2
  rồi lấy 3) — KHÔNG phải `[:3]` rồi shuffle thứ tự chạy (3 cố định mỗi phiên).
- Module 1 random TOÀN farm (shuffle sau follow_uids) → "Tik3 xếp sau" là SAI.