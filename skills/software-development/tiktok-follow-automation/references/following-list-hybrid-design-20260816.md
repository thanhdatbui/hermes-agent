# Follow hybrid — Following-list nội bộ (workflow ông anh + thiết kế chốt 2026-08-16)

Nguồn: user chia sẻ workflow nuôi acc đang chạy ổn của "ông anh" (người làm cùng
nghề) + phân tích + chốt thiết kế. Plan APPROVED 2 vòng audit AG Opus
(`ag/claude-opus-4-6-thinking`): vòng 1 MINOR_FIXES (3 MAJOR + 4 MINOR + 2 NIT) →
fix → vòng 2 APPROVED (+1 MINOR clamp canary). Plan file:
`.hermes/plans/2026-08-16-follow-hybrid-following-list.md` (commit `509f8ae`).
Build CHƯA implement khi viết reference này — đọc plan trước khi code.

## Workflow ông anh (đã chạy ổn, dùng làm chuẩn tham chiếu)

- **Follow max ~40/ngày, chia 2 CA** (không nhiều ca). Ngày chạy 2 nick (1 mạnh +
  1 yếu), xen kẽ: ngày 1 = nick1+nick3, ngày 2 = nick2+nick4. Nick mạnh được nuôi
  sớm, nick yếu chạy cường độ thấp.
- **Ngày thứ 3 nghỉ follow** (chỉ lướt/like/friend) sau 2 ngày chạy liên tiếp.
  So với "follow ít đều mỗi ngày": tổng 3 ngày bằng nhau (80), khác biệt chỉ là
  phân bố burst. Đều + cụm nhỏ an toàn hơn cho nick mới; kiểu ổng áp được khi nick
  đã giàu trust.
- **Search ≤ 20 nick/ngày** — search dày cũng gây ảnh hưởng nick (tín hiệu bot;
  research cùng xác nhận search→follow <3s là cờ). Hệ quả: follow chéo KHÔNG được
  đi qua search toàn bộ.
- **Follow chéo nội bộ qua tab Đã follow (Following) của nick 1,2** — KHÔNG follow
  nguồn ngoài, KHÔNG follow theo tab Follower:
  - Lí do bỏ Follower-list: follower của 1 nick lạ = nguồn ngoài, "1 acc cắn" →
    cả đống nick đi follow lại đống đó = quá nhiều. Following của anchor = nick
    nội bộ ĐÃ follow sẵn → nguồn sạch.
  - Lí do không search random: nick tik sau (tik3,4) mới, following ít → search
    random ra nick mới không có following dày. Phải ưu tiên search trong danh sách
    Tik1/Tik2 (nick đã follow nhiều).
  - Điều kiện tiên quyết: nick 1,2 phải seed trước (follow đủ nick nội bộ) → các
    loạt sau follow theo list đó. "1,2 follow chuẩn thì loạt sau đi lung tung cũng
    chả sao; 1,2 bẩn thì cả lô dính."
- **Nhả follow**: nhả LIỀN vài giây sau tap = TikTok không nhận follow (chặn) →
  confirm gate `_confirm_not_released` bắt được → FOLLOW_FAILED dừng session. Nhả
  TỪ TỪ sau vài ngày = nick FOLLOWER die (ban) → kệ, không theo dõi làm gì →
  **bỏ follower-count tracker**.
- **"Ngâm account qua đêm"** (đổi account switcher tối hôm trước cho sáng hôm sau):
  KHÔNG có lợi kỹ thuật — session token/device fingerprint không đổi theo idle.
  Công đổi nick vẫn y nguyên, chỉ khác thời điểm. Lợi nhỏ duy nhất là pattern hành
  vi (tối dùng nick này → sáng tiếp tục) + thuận vận hành. User đồng ý gạt khỏi
  thiết kế.
- **Gate video**: 1 nick phải đi 3 quá trình: nuôi lướt → xây kênh đăng ~10 video
  → mới follow. Chưa đủ 10 video → giảm follow 1 nửa (kể cả 0 video vẫn follow nửa).

## Thiết kế chốt (follow repo, plan APPROVED)

1. Mode 2' = search anchor → profile → tab **Đã follow** → follow UID ∈ nội bộ
   (safe workbook); UID ngoài skip KHÔNG persist (chỉ log).
2. Anchor ưu tiên Tik1/Tik2: `account_row_index` 1-based (workbook.py đếm từ 1),
   row ≤ 2.
3. Hybrid: mode 2' trước → hết nguồn chưa đủ budget → mode 1 search-follow bù.
   CÙNG state instance in-memory (không reload disk giữa 2 mode) chống double-follow.
4. Budget: phiên random 6–10, KHÔNG daily cap; clamp `min(max, canary_max)`.
   Inter-follow delay 30–90s (audit MAJOR-2 velocity); FOLLOW_FAILED → stop,
   không retry session.
5. Gate video: đọc cột `Video Đã Đăng` từ safe workbook theo ID; ≥10 full;
   <10 (kể cả 0) nửa; cột thiếu → default 0 + warning, không crash.
6. Gỡ follower-count tracker (follower_tracker.py + export_follower_tracking.py +
   wire verify_follow._track_follower + config.example) — bắt buộc `rg` hết caller
   trước khi xóa + `python -c "import follow_runner"` sau xóa.
7. Sync gộp (repo nuôi acc, phase B): 1 cron 30' duy nhất đọc taikhoandat_v2 +
   Tik1..Tik6 (ID + Video Đã Đăng, thiếu → 0) → build safe 4 cột
   `May | Device ID | ID | Video Đã Đăng`; single-writer atomic; upload KHÔNG đụng
   safe. Deploy trước hoặc cùng follow code (nếu không → gate default 0 → toàn bộ
   nửa budget tạm thời).

## Findings audit đáng nhớ (đã đóng trong plan)

- Selector tab Following phải spec text rõ (`FOLLOWING_TAB_TEXT = ("Đã follow",
  "Following")`), giữ `FOLLOWER_TAB_RESOURCE_ID=id/sdn` anchor + fallback locale;
  cần probe máy thật canary trước khi tin.
- Velocity: 6–10 follow liền trong phiên ngắn chạm biên trên vùng block
  (research ~10–15/phiên) → delay 30–90s giữa follow.
- Skip UID ngoài ghi `skipped` = phình state (480 acc × sessions × hàng trăm skip)
  → KHÔNG persist, chỉ log.
- Gate đọc cột chưa tồn tại: default 0 + warning (không KeyError crash).
