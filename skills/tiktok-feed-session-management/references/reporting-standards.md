# Watchdog & Batch Reporting Standards

## Bắt Buộc Đầy Đủ Mẫu Số & Tỷ Lệ Hoàn Thành
Mọi watchdog hoặc script báo cáo tiến trình (Upload Avatar, 2FA, CheckLive, Render, Reg...):
- **CẤM TUYỆT ĐỐI** chỉ báo cáo số máy còn thiếu hoặc danh sách lỗi mà không có mẫu số tổng quan.
- **BẮT BUỘC** hiển thị rõ ràng:
  1. `Đã đạt / Tổng số acc (%)`
  2. `Còn thiếu / lỗi: N máy (danh sách máy)`

Ví dụ format Telegram chuẩn:
`• Tik N: Đã có A/B (P%) — còn M máy (danh sách máy)`

## Chống Báo Ảo 100% Khi Chưa Gán Nick (tot_cnt == 0)
- Với các Tik chưa gán nick nào trong workbook (`total_accounts == 0`):
  - **Từng Tik:** Bắt buộc hiển thị: `• Tik {tik}: chưa gán nick (0/80 acc)`. Tuyệt đối KHÔNG báo "hoàn tất 100%".
  - **Tiêu đề & Trạng thái Farm:** Đổi sang `HOÀN TẤT CHO CÁC ACC ĐÃ CÓ NICK` kèm `({total_uploaded}/{total_accounts} acc)` để tránh gây hiểu lầm toàn bộ 80 máy đã xong khi thực tế chưa gán nick.

## Tính Tương Thích & Helper Aliases Giữa Admin và Kibe
- Khi merge script watchdog giữa các máy (Admin vs Kibe), các helper functions có thể có return signature khác nhau (`tuple[int, list[int]]` vs `dict`).
- Phải giữ song song cả alias cũ và mới (ví dụ: `get_tik_avatar_status` trả `tuple[total_accounts, unuploaded]` song song với `get_tik_avatar_stats` trả dict và `get_unuploaded_machines` trả list) để runner của cả 2 máy đều chạy an toàn không crash `AttributeError` / `TypeError`.

## Quy Trình Đồng Bộ Watchdog Scripts
Sau khi chỉnh sửa watchdog script trong repo:
1. Chạy `pytest` kiểm thử 100% PASS (ví dụ `python_runner/tests/test_feed_session_watchdog.py`).
2. Với riêng `feed_session_watchdog.py`, BẮT BUỘC đồng bộ đủ 4 vị trí để chống sync drift:
   - `D:\Taadaa\tiktok-luot nuoi acc\scripts\feed_session_watchdog.py`
   - `D:\Taadaa\tiktok-luot nuoi acc\scripts\hermes_cron\feed_session_watchdog.py`
   - `D:\Taadaa\Hermes\deploy\hermes-home\scripts\feed_session_watchdog.py`
   - `C:\Users\<user>\AppData\Local\hermes\scripts\feed_session_watchdog.py`
3. Với các watchdog khác (avatar, checklive, reg):
   - Sync đè sang runtime cục bộ: `C:\Users\<user>\AppData\Local\hermes\scripts\<script>.py`.
   - Sync sang deploy: `D:\Taadaa\Hermes\deploy\hermes-home\scripts\<script>.py`.
   - Sync sang thư mục chia sẻ chung toàn farm: `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\<script>.py`.

## Quy Chuẩn Từ Ngữ Trực Quan: Cấm Thuật Ngữ "Lũy Kế" Gây Lú Lẫn
- **Vấn đề:** Thuật ngữ kế toán "Lũy kế" (`Lũy kế hôm nay`, `Lũy kế đợt này`) khiến người vận hành bực bội, khó hiểu ("Lũy kế là cái éo gì v") và dễ nhầm lẫn số máy thực tế đã xử lý giữa các đợt quét cuốn chiếu lặp lại của cron/watchdog (nhất là khi một đợt quét báo `Đã dọn đợt này: 0 máy` nhưng ngay dưới lại ghi `Lũy kế hôm nay: 74 máy`).
- **Quy tắc bắt buộc:**
  1. **CẤM** dùng thuật ngữ trừu tượng "Lũy kế" không kèm ngữ cảnh tổng thể.
  2. **DÙNG:** Phân định rõ ràng giữa **tiến độ tích lũy trong ngày** và **kết quả riêng của đợt chạy vừa xong**:
     * `• Đã hoàn tất hôm nay: {X}/{Y} máy ({percent}%)` (BẮT BUỘC có mẫu số tổng `{X}/{Y}`).
     * `• Vừa xử lý đợt này: +{N} máy (danh sách)` hoặc `• Đã hoàn tất: 74/80 máy (+2 máy đợt này)`.
  3. **Silent Watchdog khi đợt chạy không có máy mới (`N == 0`):**
     * Tuân thủ triệt để Watchdog pattern: Nếu đợt chạy lại không xử lý thêm được máy nào (`s_count == 0`), script BẮT BUỘC thoát im lặng (`return 0`, stdout rỗng), tuyệt đối KHÔNG in ra `0 máy` để bot spam Telegram.
     * Khi bắt buộc phải in tiến độ (ví dụ lệnh thủ công `--force`), ghi rõ ràng: `Không có thêm máy hoàn tất đợt này (vẫn giữ {X}/{Y} máy đã xong)`.

## Quy Chuẩn Khối Đối Soát (Reconciliation): Chỉ Báo Nick Lệch, Cấm Spam Nick Đã Khớp
- **Vấn đề:** Trong các khối đối soát (như `Đối soát TikTok Web`, `Đối soát Following / Follow chéo`, `Đối soát Avatar / Bio`), việc liệt kê hàng loạt dòng cho các nick đã khớp 100% (`script báo 0 | web tăng +0 (KHỚP; chênh lệch +0)`) làm loãng báo cáo, spam tin nhắn và che khuất các nick lỗi thực sự. Người vận hành yêu cầu: *"mấy nick k lệch đừng có báo vào report"*.
- **Quy tắc bắt buộc:**
  1. **CHỈ in chi tiết từng dòng cho nick có sai lệch thực tế (`Lệch != 0`, `delta != 0`, `mismatch`):**
     ```text
     + Đối soát TikTok Web (+0 Following thật | Lệch -4 so với script báo 4):
       - M51 (@sweatfbsxdj): script báo 3 | web tăng +0 (Lệch -3)
       - M63 (@nhumai1595): script báo 1 | web tăng +0 (Lệch -1)
     ```
  2. **KHÔNG in chi tiết từng dòng cho nick khớp:** Nick không lệch (`chênh lệch +0`, `KHỚP`) BẮT BUỘC lọc bỏ khỏi danh sách chi tiết. Chỉ được phép đếm tổng số lượng ở dòng tóm tắt (ví dụ: `(Khớp: 18 nick | Lệch: 2 nick)`).
  3. **Khi 100% khớp (0 nick lệch):** Chỉ in 1 dòng tóm tắt duy nhất: `+ Đối soát TikTok Web: Khớp 100% ({N}/{N} nick)` và kết thúc, tuyệt đối KHÔNG liệt kê danh sách nick.

## Quy Chuẩn Báo Cáo Sức Khỏe Follow Theo Tầng (Health-Tiered Follow Reporting)
- **Cấu trúc chuẩn Telegram:**
  ```markdown
  • Follow chéo ({total} lượt follow) [Module 2 (Anchor): {m2} | Module 1 (Bù): {m1}]:
    + Thành công ({n} máy | {succ_pct}%):
      💪 Nhóm Khỏe (10+ lượt | {pct}%): (M2, M39)
      🌱 Hồi phục 2 (5 - 9 lượt | {pct}%): (M18, M28)
      🌱 Hồi phục 1 (1 - 4 lượt | {pct}%): (M1, M52)
    + Nhả follow ({n} máy | {rel_pct}%):
      - Nhả liền (0 lượt | {pct}%): (M26)
      - Nhả ở Hồi phục 1 (1 - 4 lượt | {pct}%): (M39)
      - Nhả ở Hồi phục 2 (5 - 9 lượt | {pct}%): (M...)
      - Nhả ở Cấp Khỏe (10+ lượt | {pct}%): (M...)
    + Lỗi script / kết nối: (M54)
    + Bỏ qua:
      - Đang Cooldown nhả follow từ các ngày trước: {N} máy
      - Đang dưỡng sinh ({N} máy)
      - Chưa đủ điều kiện / Dưới 6 video ({N} máy)
  ```
- **Kỷ luật định dạng:**
  1. **Range lượt & % nhóm:** BẮT BUỘC ghi rõ range lượt và tỷ lệ % của từng phân tầng.
  2. **Danh sách máy trong ngoặc đơn:** Chỉ ghi danh sách máy `(M1, M2...)`, TUYỆT ĐỐI CẤM ghi chi tiết số lượt từng máy riêng lẻ `(M1 (4 lượt), M2 (5 lượt))` gây rối mắt.
  3. **Tách bạch Module 2 (Anchor) vs Module 1 (Bù):** Giúp người vận hành kiểm soát ngay tình trạng cạn anchor hay bot phải dùng Module 1 cày bù.


