# Session Pipeline & Follow Hook Rules — 2026-08-26

## 1. Chu trình thực thi chuẩn cho mỗi ca / phiên (Pipeline Rules)
User chốt quy tắc vận hành bắt buộc:
- **Phiên nuôi thông thường (Phiên 1 & 2 trong ca):**
  - Thực hiện: **Nuôi Feed (Lướt video For You / Fast Swipe + Deep Inspect) ➔ Follow Hook (`tiktok-follow`)**.
  - Không upload video ở các phiên này.
- **Phiên cuối cùng trong ca (Phiên 3):**
  - Thực hiện đầy đủ 3 bước tuần tự: **Nuôi Feed ➔ Follow Hook (`tiktok-follow`) ➔ Upload Video**.
  - Kể cả khi nuôi feed gặp lỗi nhỏ/degraded, các hook follow và upload vẫn phải kích hoạt theo đúng thiết kế fail-safe.

## 2. Phân định 2 nguồn Follow trong quá trình nuôi
- **Follow tự nhiên (Organic Feed Follow):**
  - Tích hợp sẵn trong repo `tiktok-luot nuoi acc`.
  - Trigger ngẫu nhiên **20%** tại các nhịp Deep Inspect trên tab For You (bù trừ cho Fast Swipe).
  - Tần suất: trung bình ~0.7 follow/phiên (khoảng 2–3 follow/ca/ngày).
- **Follow chéo / Follow danh sách (`tiktok-follow` hook):**
  - Kích hoạt qua subprocess ngay sau khi kết thúc phiên lướt feed (`_run_follow_hook`).
  - Áp dụng Gate Video 3 bậc:
    - `> 5 video`: Full budget (6–10 follow/phiên).
    - `1–5 video`: Nửa budget (3–5 follow/phiên).
    - `0 video` (hoặc None): CẤM follow (0 follow/phiên).

## 3. Nhả Follow (Follow-Release) & Cơ chế cô lập theo Row
- Khi nick bị TikTok nhả nút follow sau khi reload kiểm tra (`FOLLOW_FAILED`):
  - Script lập tức **dừng phiên follow** và ghi nhận cờ `follow_failed: true` vào `follow_state_<machine>_row_<index>.json`.
  - Nick đó sẽ bị **khóa follow trong toàn bộ ngày hôm đó (24h calendar day)**, chỉ được lướt feed, không cố follow tiếp để tránh bị reset thời gian phạt của TikTok.
  - **Cô lập theo Row:** Cờ khóa chỉ áp dụng cho đúng `account_row_index` bị dính (ví dụ Row 2). Các nick khác trên cùng thiết bị (Row 1, 3, 4, 5, 6) hoàn toàn không bị ảnh hưởng, vẫn tiếp tục lịch nuôi và follow bình thường.
