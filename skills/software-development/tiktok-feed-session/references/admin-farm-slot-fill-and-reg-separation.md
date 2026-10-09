# Admin Farm — Slot Fill Status & Reg Separation Architecture

## TẠI SAO "Tổng máy xử lý: 80 máy" MÀ THỰC TẾ KHÔNG PHẢI 80 MÁY CÓ NICK?

**Câu hỏi phổ biến:** Watchdog báo `Tổng máy xử lý: 80 máy` nhưng Farm Admin `0 video đã đăng`. Có phải lỗi không?

**Giải thích:**
- `Tổng máy xử lý: N` = số máy vật lý được đưa vào **luồng chạy Ca** (Lướt Feed, Follow, Upload).  
- **Luồng nuôi (Ca)** và **luồng đăng ký nick (Reg)** là 2 hệ thống hoàn toàn độc lập.  
- Khi runner Ca gặp máy thiếu nick ở Slot N, script **Safe-Skip** ngay (ghi `missing_account_id` vào `upload_result.json`) và chuyển sang máy tiếp theo — không dừng, không reg bù.

## SỐ LIỆU SLOT HIỆN TRẠNG DÀNG ADMIN (đo 2026-10-06)

| Slot (Row) | Số máy có nick | Số máy thiếu |
|-----------|---------------|-------------|
| Slot 1    | 80            | 0           |
| Slot 2    | 73            | 7           |
| Slot 3    | 72            | 8           |
| Slot 4    | 17            | **63**      |
| Slot 5    | 69            | 11          |
| Slot 6    | 21            | **59**      |
| Slot 7    | 74            | 6           |
| Slot 8    | 78            | 2           |

*Nguồn: `taikhoan_dat_v2_updated .xlsx` dàn Admin (`D:\OneDrive\TaadaaData\admin\`).*

## TẠI SAO CA NUÔI KHÔNG TỰ ĐỘNG REG BÙ KHI THIẾU NICK?

3 lý do kiến trúc và an toàn cốt lõi:

### 1. Code-path tách biệt hoàn toàn
- Ca nuôi chạy: `multi_machine_feed_session.py` → gọi feed-swipe, follow-hook, upload-hook.
- Reg TikTok chạy: `Tiktok_Reg/_run_all_targets.py` → hoàn toàn riêng repo, logic, config.
- Hai luồng không biết về nhau. Ca nuôi không có quyền gọi sang Reg repo.

### 2. Reg tốn thời gian + rủi ro cao trong giờ nuôi
- 1 nick reg đầy đủ (ngày sinh → mail → OTP → username) mất **5–10 phút/máy**.
- Chèn reg vào lúc Ca đang chạy sẽ:
  - Vỡ khung giờ Ca (mỗi Ca chỉ 2–4 tiếng cho 80 máy).
  - Nếu kẹt Captcha/OTP ở 1 máy → máy đó bị chiếm → các máy sau mất lock → domino.

### 3. Reg chỉ chạy trong khung giờ rảnh (Idle)
- Cơ chế đúng: `post_noon_chain_watchdog.py` trigger Reg sau Ca 2 kết thúc (14:30–17:30).
- Điều kiện bắt buộc: không có feed runner active, không có device-lock active.
- Tức là: **Reg chỉ được phép khi farm hoàn toàn rảnh**, không phải chen ngang Ca nuôi.

## Cách điều phối đúng KHI CẦN LẤP ĐẦY SLOT

1. Chờ kết thúc Ca hiện tại (hoặc đợi khung rảnh giữa 2 Ca).
2. Kích hoạt `Tiktok_Reg/_run_all_targets.py` với `TAADAA_HOST_CONFIG` trỏ đúng dàn Admin.
3. Script sẽ detect các máy thiếu nick từ `taikhoan_dat_v2_updated .xlsx` và `gmail_clean_v2.xlsx` Admin.
4. Sau Reg xong, chạy `sync-tik-workbooks.py` để đồng bộ ID mới vào `Tik6.xlsx` (hoặc slot tương ứng).

## CÁCH PHÂN LOẠI NHÓM TRONG BÁO CÁO WATCHDOG KHI THIẾU NICK

| Nhóm trong báo cáo | Ý nghĩa thực tế |
|---|---|
| `Khác (N)` ở phần Đăng Video | N máy bị skip an toàn vì thiếu nick ở slot đang chạy (`missing_account_id`) |
| `Hết video/Cần cào (N)` | Máy ĐÃ CÓ nick nhưng thiếu file video đã render |
| `Đang dưỡng sinh (N)` | Máy có nick, được chọn nghỉ ngẫu nhiên ~33% ca |
| `Success (0)` | Không phải lỗi nếu phần lớn Khác là `missing_account_id` |
