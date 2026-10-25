# Quy chuẩn Phân định Báo cáo Farm Watchdog (Feed vs Follow)

## 1. Bản chất & Mục tiêu khác biệt
- **Report Nuôi Feed (`feed_session_watchdog.py`)**:
  - **Mục tiêu duy nhất**: Giám sát **Flow thiết kế** của ca nuôi tự động (Dynamic Pool Row 0).
  - Giúp phát hiện việc luân chuyển nick giữa các hàng trong Pool ({1,2,7}, {3,4,8}, {5,6}) có bị lệch tải không (ví dụ: máy bị dồn 95% vào một Row).
  - **Dòng bắt buộc**:
    `+ Phân bổ Row ({tot_row_ms} máy): Row X (A máy | B%) | Row Y (C máy | D%)`
    nằm ngay trong khối `• Lướt Feed:`, bên dưới `+ Fail`.
  - **Quy tắc cấm kỵ**: TUYỆT ĐỐI KHÔNG đưa khái niệm "nhả" (nhả follow) hay các bậc follow vào report nuôi feed, vì nuôi feed hoàn toàn không có nghiệp vụ nhả follow.

- **Report Follow Chéo (`follow_session_watchdog.py`)**:
  - **Mục tiêu duy nhất**: Đo lường **Sức khỏe & Tỷ lệ nhả follow** của đàn nick trên từng dải IP/Proxy.
  - **Bắt buộc phân cấp theo Cơ chế Sức khỏe (Health Tiers)**:
    - `💪 Nhóm Khỏe (10+ lượt | X%)`: Danh sách máy follow bền vững.
    - `🌱 Hồi phục 2 (5 - 9 lượt | X%)`: Nick đang phục hồi sau thử thách.
    - `🌱 Hồi phục 1 (1 - 4 lượt | X%)`: Nick đang trong giai đoạn probation.
    - `Nhả follow ({tot} máy | X%)`: Phân nhóm rõ:
      * `- Nhả liền ({cnt} máy | 0 lượt | X%): (M...)`
      * `- Nhả ở Hồi phục 1 / 2 / Cấp Khỏe: (M...)`
    - `Bỏ qua`: Bóc tách Cooldown nhả follow (48h), Chưa đủ điều kiện (under video gate/age gate).

## 2. Ý nghĩa định danh Run ID `row-X-HHMMSS`
- `row-0`: Cơ chế Dynamic Account Selection (Row 0 / Nuôi động theo Pool của Ca), không cố định hàng Excel.
- `row-N` (N > 0): Phiên chạy cố định hàng N (Row 1, Row 2...).
- `HHMMSS`: Giờ kích hoạt phiên chạy (ví dụ `140735` là 14:07:35).
- Thư mục lưu trữ: `D:/Taadaa/runtime/<cluster>/live/<date>/row-<row>-<HHMMSS>/`.

## 3. Trích xuất dữ liệu Row từ Runner
- Khi parse `run_manifest.json` gốc của phiên: trích xuất `account_row` từ `multi_machine_summary` gán vào payload `res_m` của `parser.py`.
- Tự động thống kê `row_counts` trên toàn bộ máy đã thực hiện phiên để tính tỷ lệ %.
