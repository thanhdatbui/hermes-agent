# TikTok Registration Batch Sizing, Multi-Condition Target Eligibility & Reviewer Gates

## 1. Giới Hạn Cứng 6 Acc TikTok / Máy
- **Mục tiêu lô:** 80 máy $\times$ 6 acc = **480 tài khoản tối đa**.
- **Quy tắc:** Máy đã có $\ge 6$ TikTok ID trong tracking workbook (`taikhoan_dat_v2_updated .xlsx`) phải bị loại vĩnh viễn khỏi detector / runner, tuyệt đối không cấp thêm mail thứ 7.

## 2. Điều Kiện Chọn Target Kép
- Một máy chỉ được đưa vào danh sách đăng ký khi thỏa mãn đồng thời:
  1. `Số tài khoản TikTok hiện có < 6`.
  2. `Còn mail nguồn hợp lệ chưa dùng` trong `gmail_clean_v2.xlsx` (chưa xuất hiện trong sheet tracking).
- Nếu máy $< 6$ acc nhưng hết mail nguồn dư $\rightarrow$ **Skip**.
- Nếu máy còn mail nguồn nhưng $\ge 6$ acc $\rightarrow$ **Skip**.

## 3. Quy Mô Ca & Concurrency An Toàn (Tránh Bị Quét)
- **Giới hạn ca:** Chạy tối đa **30 máy / ca** (`--max-targets 30`).
- **Giới hạn concurrency:** Hạ xuống **6 workers cuốn chiếu** (`--max-workers 6`, stagger 2–8s giữa các máy) thay vì chạy 40 máy ào ạt.
- **Chia ca trong ngày:** Chia 2 ca/ngày (Ca 1 đêm 01:00 AM: 30 máy, Ca 2 ngày: 30 máy).
- **Lợi ích:** Tránh TikTok phát hiện traffic đột biến gây rate-limit "truy cập quá thường xuyên", captcha trượt hoặc gắn cờ thiết bị.

## 4. Daily Cooldown & Lock Inter-Process
- Mỗi máy chỉ reg thành công tối đa 1 lần / ngày.
- Ghi nhận `record_machine_reg_success` vào `reg_daily_cooldowns.json` có hạn tới ngày kế tiếp.
- Cơ chế Check-and-Reserve bằng token UUID và Kernel file lock (`msvcrt` / `fcntl`) bảo vệ an toàn đa tiến trình, fail-closed khi schema lỗi.

## 5. Reviewer Approval Gate
- Khi có code change được review độc lập (`plan-review` qua 9Router), nếu reviewer trả `REJECT`, bắt buộc phải tiếp tục sửa và phản biện qua các vòng đến khi nhận `APPROVED`.
- Tuyệt đối không commit/push khi review chưa thông qua hoặc test chưa pass 100%.
