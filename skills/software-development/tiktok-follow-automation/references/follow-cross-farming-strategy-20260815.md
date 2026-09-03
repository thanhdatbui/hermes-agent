# Follow chéo (cross-farming) + tốc độ follow — phân tích 2026-08-15

User hỏi: follow 1 account bao nhiêu/ngày là hợp lí, 1k follow mở giỏ hàng,
follow chéo với 480 acc (mỗi IP 6 acc).

## Sự thật cốt lõi (đừng nhầm lần nữa)

- **Follow ≠ Follower.** Follow = hành động đi ra (theo dõi người khác).
  Follower = người theo dõi mình (người về). TikTok Shop mở giỏ hàng cần
  **1.000 FOLLOWER**, không phải 1.000 follow. Follow nhiều chỉ nuôi acc
  "nhìn active", không tự tạo follower.
- **Toán hay nhầm**: 30 follow/ngày × 10 ngày = 300, KHÔNG phải 1k (cần ~33
  ngày). 3 nick × 30 follow = 90 follow/ngày TOÀN HỆ THỐNG — 90 đó không làm
  1 nick nhận 90 follower trừ khi follow chéo nội bộ với ~90 nick khác.

## TikTok chặn theo cơ chế nào (không có số liệu công khai)

- Không có nghiên cứu/paper công khai về ngưỡng follow/ngày — TikTok không
  công bố. Mọi con số đều là ước lượng thực dụng, nói thẳng độ chắc chắn.
- Chặn theo **burst/session**: follow dày trong cửa sổ ngắn (vài phút) là dấu
  hiệu chính — KHÔNG phải tổng/ngày. 15–25 follow liên tiếp 1 phiên = burst
  dày = rủi ro. 8–12/phiên = vùng vừa.
- Tỉ lệ follow:follower lệch + tốc độ tăng follower bất thường = red flag.
- Acc mấy tháng tuổi + nuôi 1 tháng = trust tầm trung.
- Con số `budget_per_day: 30` trong config follow repo là default cũ, không
  phải kết quả nghiên cứu — đừng viện nó làm "căn cứ".

## Follow chéo (cross-farming) — rủi ro graph-liên-kết

- **IP riêng KHÔNG cứu được graph detection**: TikTok detect mạng lưới follow
  (A→B→C→A, follow đối xứng, cùng cửa sổ thời gian) — 480 acc follow lẫn nhau
  = 1 cụm liên kết khổng lồ; 1 acc bị quét → quét CẢ CỤM, dù mỗi IP chỉ 6 acc.
- Pattern chết người: follow chéo thuần 100%, follow đối xứng trong cùng ngày,
  vòng khép kín A→B→C→A, 480 nick cùng follow 1 target trong cửa sổ ngắn.
- An toàn hơn (nếu vẫn muốn follow chéo):
  - Trộn ~70% follow organic (người lạ trong feed/search) + ~30% follow chéo.
  - Không follow đối xứng trong ngày — cách 3–7 ngày mới follow lại.
  - Rải thời gian, dàn đều, không tập trung.
  - Mỗi nick follow chéo tối đa 2–5 nick khác/ngày.
  - Không tạo vòng khép kín.
- Quy mô: 480 acc × 30 follow/ngày = 14,400 follow/ngày → nếu chéo nội bộ
  100% → mỗi nick nhận ~30 follower/ngày → 1k follower ≈ 33 ngày (KHÔNG phải
  10 ngày — 30 × 10 = 300).

## Tốc độ hợp lí cho 1 account (ước lượng, nói rõ là ước lượng)

- Acc mới / mới bắt đầu: 5–10/ngày, ramp dần (mỗi 3–5 ngày tăng 1 mốc).
- Acc vài tháng tuổi, đã nuôi: 20–30/ngày là vùng an toàn (2 phiên × 10–15).
- >50/ngày/account = ép, rủi ro cao. Muốn 50/ngày phải chia nhiều phiên nhỏ
  (VD 5 phiên × 10), không phải 2 phiên to.
- FOLLOW_FAILED > 0 = đã chạm trần → giữ nguyên mốc 1 tuần hoặc lùi 1 mốc.
