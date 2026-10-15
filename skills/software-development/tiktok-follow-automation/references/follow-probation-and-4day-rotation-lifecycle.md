# Follow Probation & 4-Day Rotation Lifecycle (2026-10-15)

## 1. Tinh chỉnh Bậc thang thử thách theo Chu kỳ 4 ngày
- **Vấn đề cũ:** Yêu cầu 2 ca sạch cho mỗi nấc khiến nick mất tới 4 chu kỳ (~17 ngày ngoài đời thực) mới tốt nghiệp lên Khỏe.
- **Quy chuẩn mới (1 Phiên sạch / Nấc):**
  - **Hồi phục 1 (Tân binh / Mới ra tù):** Quota 2 – 4 follows/phiên (`clean_days < 1`).
  - **Hồi phục 2 (Tăng tải an toàn):** Quota 6 – 8 follows/phiên (`clean_days == 1`).
  - **Tốt nghiệp (Khỏe):** Đạt `clean_days >= 2` $\rightarrow$ Tốt nghiệp lên Khỏe (Full Quota 10 – 15 follows/phiên).
- **File thực thi:** `D:/Taadaa/tiktok-follow/follow_runner/core/follow_state.py` và test `test_follow_state.py`.

## 2. Kiểm thử nghiệm thu
- 53/53 tests trong `test_follow_state.py` pass 100%.
- Đảm bảo tính toán độc lập theo từng `(máy, row)`.
