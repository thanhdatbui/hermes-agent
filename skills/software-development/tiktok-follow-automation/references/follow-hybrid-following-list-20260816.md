# Follow hybrid — Following-list nội bộ + gate video (phân tích + spec build 2026-08-16)

Session: user kể workflow ông A (đang chạy ổn) → so sánh với thiết kế farm mình →
chốt thiết kế follow chéo MỚI thay "CHỈ mode 1" (chốt 16/08 sáng).

## Workflow ông A (chuẩn so sánh)
- Trần 40 follow/ngày chia **2 ca** (KHÔNG nhiều ca); mỗi ngày chạy **2 nick**
  (1 mạnh + 1 yếu xen kẽ: ngày 1 nick A+C, ngày 2 B+D).
- 2 ngày chạy → ngày 3 NGHỈ follow (chỉ lướt/like) — nhưng so sánh ổng 40×2 ngày
  nghỉ 1 vs mình ~27 đều/ngày: TỔNG 3 ngày bằng nhau → tốc độ 1k ngang nhau; khác
  duy nhất là phân bố burst. Kết luận: **mình chọn đều mỗi ngày + cụm nhỏ**, vì
  nick mới trong lô 200 an toàn hơn; "ngày nghỉ" không giảm tổng follow.
- **Follow qua tab Đã follow (Following) của nick anchor (row 1,2)** — KHÔNG
  follow list follower (sợ 1 acc cắn → dồn 1 đống follow tự nhiên về 1 nick).
  Nick 1,2 follow chuẩn → các loạt sau theo sau cũng sạch; 1,2 follow linh tinh →
  cả lô dính. Module 2 của ổng = **following list**, không phải follower list.
- **Search ≤ 20/ngày** — search dày = ảnh hưởng nick (cờ bot; research 16/08:
  search→follow <3s = cờ).
- Nhả follow: nhả là nhả LIỀN (vài giây); vài ngày sau mới nhả = nick FOLLOWER bị
  die → kệ nó. → đồng nhất với cơ chế mình build: `_confirm_not_released` bắt nhả
  ngay; follower tracker (nhả từ từ) VÔ DỤNG → gỡ.
- **"Ngâm account qua đêm" (đổi nick sẵn tối hôm trước) = KHÔNG có lợi kỹ thuật**
  (user đồng ý sau phân tích): công đổi nick không đổi, chỉ khác thời điểm;
  session/device fingerprint không đổi theo idle. Gạt khỏi thiết kế.

## Chốt thiết kế user (16/08 cuối ngày — thay "CHỈ mode 1" đầu ngày)
1. **Budget tính trên NICK, CẤM tổng farm** ("Tính tổng farm 3 nick làm gì, tính
   budget trên nick chứ") — TikTok soi từng fingerprint nick.
2. **Budget = mỗi phiên random 6–10, KHÔNG daily cap, không nghỉ ngày**. User bác
   budget_per_day 30 ("Daily cap 30 k cần, mỗi phiên random 6–10 là đã đủ cap r")
   + bác cơ chế phiên-3-bù-tổng ("chỉnh daily cap thêm phức tạp quá"). 3 phiên ×
   6–10 ≈ 18–30/ngày/acc tự nhiên. Trần 40/ngày của ông A chỉ áp nick TRƯỞNG
   THÀNH; gate video giảm nửa vẫn áp.
3. **Gate 10 video**: cột `Video Đã Đăng` ≥ 10 → full (6–10); < 10 (kể cả 0) →
   nửa (3–5). **0 đăng cũng follow nửa** (user chốt) — tik3 chưa lướt vẫn follow
   nửa, không chờ đủ video.
4. **NGUỒN ĐỌC gate = taikhoan_run_safe (KHÔNG đọc TikN theo row)**: tik mọc tới
   tik6 → đọc từng file theo row = bảo trì mệt (user: "Nếu k gộp thì ép nó tìm
   đúng file đọc mệt đó"). Sync gộp thêm cột Video Đã Đăng vào safe.
5. **Mode 2' = Following-list**: vẫn SEARCH 1 nick farm (anchor) → profile → tab
   **Đã follow** → follow UID ∈ nội bộ (safe workbook); UID ngoài → skip nhẹ.
   **Anchor ưu tiên Tik1/Tik2 (account_row_index ≤ 2)** — following dày, đã seed
   (user: "module 2 phải ưu tiên search nick trong tik 1 tik 2 tức 2 row đầu").
   Lúc đầu user bảo "bỏ ưu tiên anchor" rồi ĐẢO lại bắt buộc ưu tiên 2 row đầu —
   đọc kỹ message cuối.
6. **Hybrid 1 phiên**: mode 2' trước → hết nick nội bộ trong following list mà
   chưa đủ budget → **mode 1 search-follow bù** (skip nick đã follow). Sau 1 time
   mode 1 follow đủ farm → mode 2' tự chiếm ưu thế (chuyển pha tự nhiên, đúng ông A).
7. **BỎ MỌI tracker** (follower-count + export + wiring): state `followed` dict có
   sẵn làm dedupe (module 1 skip nick đã follow). KHÔNG build tracker mới.
8. **KHÔNG gom Tik1..Tik6 → 1 file**: upload `AccountSource._read_row_from_xlsx`
   chọn row theo machine → **first-row only** (machine mode break ngay row đầu
   khớp serial) → gom = nick 2+ không bao giờ được chọn + race ghi `Video Đã Đăng`.
   Giữ file Tik riêng; follow đọc safe read-only (nguồn nick thật 2–5 nick/máy).

## Sync gộp — vì sao 1 cron 30' + 1 writer duy nhất
- User hỏi "taikhoanrunsafe nhận sync 1 lúc từ nhiều nguồn có ổn định k ấy".
- **KHÔNG ổn nếu ghi runtime nhiều nguồn** (race/corrupt, OneDrive càng tệ — bài
  cũ follower-tracker đã dính). Cron taikhoandat_v2 hiện tại REBUILD-FROM-SOURCE
  `_build_safe_workbook` (tạo workbook mới, chỉ 3 cột) → **thêm cron video riêng =
  cron rebuild sau XÓA cột vừa ghi** (race không ở file lock mà ở rebuild-xóa-state).
- Giải pháp: **gộp làm 1 cron duy nhất** (sửa cron đang chạy, KHÔNG thêm cron mới):
  đọc taikhoandat_v2 (ID/serial) + Tik1..Tik6 (ID + Video Đã Đăng; acc không khớp
  file nào — Tik4–6 chưa build — → **ghi 0**) → build 4 cột
  `May | Device ID | ID | Video Đã Đăng` → 1 writer atomic (`single_writer_workbook_update`).
  Tần suất **30 phút** đủ (video count chỉ quyết full/nửa budget; 5' = write OneDrive thừa).
- Upload KHÔNG bao giờ ghi safe (vẫn ghi TikN). Follow đọc safe read-only.
- Đối chiếu theo **ID account** (safe 2–5 nick/máy, row order không đáng tin).

## Trạng thái thật farm (đọc workbook 2026-08-16)
- Tik1.xlsx: 80 máy, 75 ID ok (6 MISSING_ID), đa số **8–15 video đã đăng** (đủ gate).
- Tik2.xlsx: 73 ID ok, **69 máy mới 1 video** (phase xây kênh).
- tik3.xlsx: 63 ID ok, **0 video** (chưa lướt/đăng).
→ Cron 3 giai đoạn hiện chỉ tik1 follow full; tik2 lướt + đăng video tới 10 + follow
  nửa; tik3 lướt + follow nửa (gate theo nick, không theo loạt).

## Đã xác minh code (đọc 2026-08-16, trước build)
- Hook follow đã nối: `multi_machine_feed_session.py:500-746` `_run_follow_hook` →
  subprocess `follow_runner.run_follow` (cwd D:\Taadaa\tiktok-follow, timeout 900s),
  sau phiên feed success/degraded. KHÔNG build lại phần nối.
- Mode 2 hiện tại (`mode2_follow_followers.py`, 730 dòng) tái dùng tối đa cho mode
  2': `FOLLOWER_LIST_HEADERS` đã có "Đã follow"; list chung recycler `u5r`, row
  `txt_desc` + nút `tcj`; `_classify_follower_surface`/`_collect_follower_rows`/
  `_follow_button_for_row`/`_verify_row_after_tap`/`_path_b_verify`/`_back_to_feed`
  dùng NGUYÊN — chỉ đổi tab (Follower → Đã follow) + thêm lọc nội bộ
  (`_normalize_handle(row UID) ∈ casefold tik_id safe` → else skip nhẹ) + đảo thứ
  tự mode (2' trước, 1 bù).
- Mode 2 cũ follow follower NGƯỜI LẠ thiếu @uid → MANUAL_REVIEW; mode 2' follow
  UID NỘI BỘ trong following list → đủ @uid, hết MANUAL_REVIEW đó.
- `follow_state.json` có sẵn `followed` dict → dedupe; KHÔNG cần tracker mới.
- Baseline test trước build: 283/283 xanh (182s), AGENTS.md sạch (git diff rỗng).
- Plan: `.hermes/plans/2026-08-16-follow-hybrid-following-list.md` (repo follow).

## Chi tiết chốt build (đừng nhầm)
- config `budget_per_session_min/max = 6/10`; `session_budget()` bỏ clamp daily.
- `follow_uids()` ưu tiên anchor row ≤ 2 + random phần sau; UID set nội bộ từ
  `WorkbookMapping.tik_ids()` (dedupe casefold).
- Sync safe 4 cột: sửa `OUTPUT_COLS` + verify header (nuôi acc repo, theo AGENTS
  worker policy + test 2 phía nurture+follow).