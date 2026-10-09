# 100% Invariant Path B Verify & Natural Profile Video Engagement (2026-09-18)

## 1. Bài học xương máu: Sự nguy hiểm của Cadence Spot-Check (`verify_sample_every > 1`)
- **Lỗ hổng từng bị cài cắm (Commit `f81c6a0f` ngày 12/09/2026)**:
  - Trước đó, code bị cài `verify_sample_every: 5` và bọc `if sample:` quanh `_path_b_verify` trong `follow_one_follower`.
  - Hậu quả: Bot chỉ mở Profile đối soát ở nick #1 và nick #5, bỏ qua hoàn toàn các nick 2, 3, 4 trên list following của Anchor.
  - Do **Optimistic UI của TikTok Android**, text nút trên list RecyclerView tự động đổi thành "Đang theo dõi" / "Bạn bè" ngay khi tap để tạo cảm giác mượt, trong khi Backend Risk Engine của TikTok âm thầm rollback (`follow = false`).
  - Bot chỉ đọc UI của list thấy "Đã follow" nên tưởng thật, cộng dồn `res.followed.append(...)` và báo cáo hoàn thành 10-15 nick ảo!
- **Invariant bất di bất dịch**:
  - `verify_sample_every` **BẮT BUỘC BẰNG 1** trên toàn bộ hệ thống (từ `core/config.py` đến tất cả file `config/*.yaml`).
  - Trong `follow_one_follower`: **XÓA BỎ HOÀN TOÀN `if sample:`**. 100% mọi nick sau khi tap Follow trên danh sách đều phải mở Profile con (`_path_b_verify`) để đối soát server state.

## 2. Bản chất nhả follow của TikTok: Nhả là nhả toàn bộ
- Hệ thống Anti-Fraud của TikTok gắn cờ theo **Device Fingerprint, IP Subnet và Tài khoản**.
- Khi một tài khoản hoặc máy đã bị gắn cờ hạn chế follow:
  - TikTok **drop triệt để mọi cú follow sau đó**.
  - Không có chuyện nick 1 ăn, nick 2 drop, nick 3 lại ăn tự nhiên. Nếu nick bị phạt, cú follow sẽ bị rollback ngay lập tức.
- Do đó:
  - **Cửa Anchor**: Bắt buộc xem video + tap follow trên video + Pull-to-refresh reload 3.5s. Nếu nút đỏ -> Nhả ngay tại cửa, dừng phiên với 0 lượt.
  - **Cửa List**: Mở profile đối soát từng nick. Nếu nhả -> Dừng phiên ngay tại nick #1.
  - Nếu một tài khoản đạt được 10-15 nick với 100% Path B verify, điều đó chứng minh 100% tài khoản đó thật sự khỏe và ăn thật toàn bộ.

## 3. Hành vi tự nhiên: Engagement ~30% Video trên Profile đối phương
- **Tỷ lệ tối ưu được Sol (:20129) thẩm định**:
  - Khi bot đã vào Profile con và xác nhận nút là `followed` thành công:
    - **~30% (tầm 3-4 nick thì 1 nick)**: Mở video đầu tiên trên profile, ngâm xem 6-10s (random dwell) kèm 30% tỷ lệ thả tim ngẫu nhiên, sau đó back về Profile -> back về List.
    - **70% còn lại**: Ngâm 1.5 - 3.0s rồi back về list.
    - Khoảng cách giãn cách giữa 2 lần follow tiếp theo: 8 - 15 giây.
- **Tại sao là 30% mà không phải 100%?**
  - Mở video là Activity nặng, tốn tài nguyên và thời gian buffer. Nếu 100% nick đều mở video thì thời gian phiên chạy sẽ bị đội gấp đôi, gây nghẽn ca và nóng máy S7. Tỷ lệ 30% vừa đủ tạo độ hỗn loạn hành vi (Behavioral Entropy) phá vỡ chữ ký bot, vừa bảo toàn hiệu năng ca chạy (chỉ tăng thêm ~40s cho cả phiên 10-15 nick).
- **Quy tắc điều hướng Back an toàn (Tránh lạc màn hình)**:
  - Hàm `_maybe_watch_profile_video` bọc `try/except` độc lập: lỗi video thì bỏ qua êm thấm.
  - Luôn kiểm tra State Validation trong `_path_b_verify`: dump UI xác nhận đã về lại `_on_follower_list` mới tiếp tục duyệt nick kế tiếp; nếu kẹt ở Profile mới ấn Back cứu hộ, tuyệt đối không back mù quáng theo timer.
