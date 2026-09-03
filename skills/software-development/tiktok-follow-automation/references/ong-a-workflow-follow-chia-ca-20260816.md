# Workflow ông A (follow chia ca) + pivot thiết kế 2026-08-16

User mang workflow nuôi acc của ông A (anh trong nghề, đang chạy ổn) để đối chiếu
với thiết kế follow chéo của farm. Đây là ghi chú phiên 2026-08-16 — tham chiếu
cho section PIVOT trong SKILL.md.

## Workflow ông A (nguyên văn các điểm user kể)

- **Max 40 follow/ngày, chia 2 ca** (không phải nhiều ca — user đính chính).
- **Mỗi ngày chạy 2 nick**: chọn 1 nick mạnh + 1 nick yếu (tik1/tik2 là nick
  mạnh, nuôi sớm; tương đương row 1,2). Ngày 1 chạy tik1 + tik3, ngày 2 chạy
  tik2 + tik4 — xen kẽ.
- **Ngâm account qua đêm**: sau khi chạy xong tik yếu buổi tối, đổi account
  switcher sang nick chuẩn bị cho sáng hôm sau. Ông nói "chuyển sẵn ngâm qua
  đêm thì hôm sau chạy tk khác ổn hơn". → **Phân tích: KHÔNG có lợi kỹ thuật**
  (user đồng ý): công đổi nick y nguyên, chỉ khác thời điểm; session/device
  fingerprint không đổi theo idle. Lợi duy nhất nhỏ = nếu tối đổi xong có mở
  app lướt nhẹ thì sáng giống "tiếp tục phiên" hơn "mở app → hành động ngay".
  Gạt khỏi thiết kế.
- **Nhả follow**: nhả là nhả LIỀN (vài giây sau tap), không có vụ vài ngày sau
  mới nhả. Nếu vài ngày sau mới nhả → nick follower bị die (ban/suspend) →
  kệ nó. → khớp cơ chế đã build: `_confirm_not_released` bắt nhả ngay →
  FOLLOW_FAILED; nhả từ từ = follower die, không cứu được.
- **2 ngày chạy → ngày 3 nghỉ follow** (chỉ lướt/thả tim/friend).
- **Search ≤ 20 nick/ngày** — tìm kiếm nhiều cũng gây ảnh hưởng nick.
- **Follow chéo trong list following (module 2 của ông = follow theo list
  FOLLOWING, chứ KHÔNG phải follower list!)**: nick 1,2 đi follow chéo trong
  danh sách của mình làm chuẩn, KHÔNG follow nguồn ngoài. Lý do không follow
  list follower: 1 acc cắn (nhận 1 đống follow tự nhiên) → mấy nick kia đi
  follow lại đống đó → thành quá nhiều. Còn nếu 1,2 follow chuẩn nội bộ →
  loạt sau follow lung tung theo cũng chả sao; 1,2 follow linh tinh → cả lô dính.

## Phân tích đối chiếu farm (kết luận session)

| Điểm | Kết luận |
|---|---|
| 40/ngày 2 ca | Chặn theo burst/session, không tổng/ngày. Trần cao nhưng nick trưởng thành + nội bộ OK; nick mới/yếu chạm 40 = tự sát |
| Ngâm qua đêm | Không có lợi kỹ thuật (xem trên) |
| Nhả follow | Khớp 100% cơ chế đã build: nhả ngay = FOLLOW_FAILED; nhả từ từ = follower die, kệ |
| 2 ngày chạy 1 nghỉ | Tổng 80/3 ngày = cùng tốc độ 1k với 27/ngày đều. Khác: burst đều hơn; nghỉ = giảm velocity dài hạn nhưng chậm ~33% (90 vs 60 ngày). User CHỐT: 3 phiên/ngày liên tục cap 30, không nghỉ |
| Search ≤ 20 | Mode 1 thuần (15–30 search/ngày) = vượt trần → kế hoạch "module 1 làm nguồn follow chính" SAI |
| Following list thay follower list | điểm sáng: "bạn của bạn" = khám phá tự nhiên, có @uid, không tốn search |

## User chốt (bắt buộc đọc trước khi build)

1. **Budget trên NICK** — CẤM tính tổng farm. Ông A chạy 2 nick vì tik 3,4 yếu,
   không phải "2 là chuẩn".
2. **Cap 30/ngày/acc, không nghỉ** (mình k nghỉ như ông A): 3 phiên/ca × 3 ca,
   mỗi phiên random sao cho tổng 20–30:
   - phiên 1,2: random 5–10
   - phiên 3: `max(5, 20−sum(phiên1,2))` → `min(10, 30−sum)` — không vượt cap,
     chạm đủ 30 tối đa
3. **Gate 10 video THEO NICK** (cột Video Đã Đăng trong Tik1/Tik2/tik3):
   - ≥10 → full budget
   - 1–9 → nửa budget
   - 0 → CHƯA chốt (lướt thuần hay nửa?) — hỏi user
   - Track data từ Tik1/Tik2 (đã có); KHÔNG gom file (xem dưới)
4. **Module 1 = phase seed, giữ nguyên** — chạy lúc đầu để nick có tệp following
   đủ dày; mấy loạt sau mới chạy module 2'. ĐẢO chốt "chỉ mode 1" 16/08 sáng.
5. **Module 2' build mới**: vào tab Đã follow (Following) của nick search →
   follow UID ∈ set nội bộ (taikhoan_run_safe), skip UID ngoài. Không tốn search,
   hết MANUAL_REVIEW thiếu @uid (following list có @uid).
6. **Bỏ follower tracker cũ** (follower-count, detect_follower_drop_state).
   Thay bằng **following tracker**: đếm số nick nội bộ đã follow (dedupe state
   per-machine) → biết khi nào following đủ dày → chuyển hẳn module 2'.
7. **Cron 3 giai đoạn** theo tình trạng từng loạt:
   - tik1 (đủ 10 video): lướt + follow module 2' full
   - tik2 (đăng video tới 10): lướt + đăng + follow nửa
   - tik3 (chưa lướt): lướt thuần trước
8. TDD: test trước → RED → GREEN → full suite → canary 1 máy → mở rộng.

## Trạng thái thật farm (đọc workbook 2026-08-16)

- Tik1.xlsx: 80 máy, 75 ID ok, 6 MISSING_ID. Phân bố Video Đã Đăng:
  {5:1, 7:3, 8:24, 9:10, 10:15, 11:16, 12:3, 15:1} → đa số đủ ~10, vài máy mới
  5–7 (chưa đủ gate).
- Tik2.xlsx: 80 máy, 73 ID ok, 8 MISSING_ID. Phân bố: **69 máy mới 1 video**,
  1 máy 2, 1 máy 6 → phase 1–2 (nuôi lâu nhưng chưa đăng nhiều như Tik1).
- tik3.xlsx: 80 máy, 63 ID ok, **18 MISSING_ID**. Phân bố: **0 video** → chưa
  lướt.
- → Hiện tại chỉ tik1 đủ gate follow full.

## Vì sao KHÔNG gom Tik1+Tik2 thành 1 file (đã đọc code Tiktok-video)

- `account_source.py::_read_row_from_xlsx` (dòng 228-304): machine mode =
  **first-row only** (dòng 266-281: chọn row đầu tiên khớp machine rồi break);
  device mode = dòng đầu khớp serial. → nick 2+ trong cùng file KHÔNG BAO GIỜ
  được chọn nếu cùng device.
- Gom 2 nick/máy → 2 runner upload cùng ghi `Video Đã Đăng`
  (`update_video_number`, monotonic cursor) vào 1 file → lost update /
  OneDrive conflict. Tách file hiện tại = cơ chế chống race.
- Follow repo KHÔNG cần gom: đã đọc `taikhoan_run_safe.xlsx` (nguồn nick thật,
  2–5 nick/máy có sẵn Máy/Device ID/ID). Set nội bộ module 2' = chính cái đó.
- Các file Tik chỉ cần để đọc cột Video Đã Đăng (gate theo quy luật row1→Tik1,
  row2→Tik2, row3→tik3).
- Header normalization trong account_source (normalize_header NFKC, aliases) —
  nếu sau này đổi file chỉ cần giữ header chuẩn, nhưng đừng gom row.

## Trả lời câu "search-follow liên tục" của research

Research Gemini 2026-08-16: search→follow ngay <3s = cờ bot; velocity limit
>10–15 follow/phiên ngắn → "You're following too fast". Ổng A chạy 40/ngày ổn vì:
nick giàu trust (nuôi lâu, >30 ngày) + follow nội bộ không qua search + chia ca.
Farm mình: nick >30 ngày đa số (user xác nhận) → không phải nick mới; vẫn giữ
cụm nhỏ + FOLLOW_FAILED làm hàng rào.