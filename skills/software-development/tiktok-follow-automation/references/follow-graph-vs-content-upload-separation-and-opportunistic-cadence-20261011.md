# Triết Lý & Quy Chuẩn Tách Bạch Độc Lập Giữa Follow Graph & Content Upload (2026-10-11)

## 1. Nguồn Gốc Vấn Đề & Phản Ứng Của Operator
Trong quá trình vận hành lịch chạy xoay tua 4 ngày / 3 ca (bỏ ca 0h đêm), Coordinator từng mắc 2 sai lầm nhận thức:
1. Nhầm lẫn giữa **Follow Cooldown của từng tài khoản** (bị nhả follow) và quyền đăng video: Tưởng rằng nick dính án nhả follow thì phải dừng cả đăng video.
2. Nhầm lẫn giữa **Ngày Dưỡng Sinh xả tải của farm** (`is_rest_day`) và Upload Hook: Trong code runner từng gài `*( ["-AllowUploadHook"] if not is_rest_day else [] )`, khiến những ca chỉ lướt feed để xả tải follow bị tước luôn quyền đăng video.
Operator đã chất vấn trực diện:
> *"Ủa miễn k phải ngày dưỡng sinh. Tức là khi bị nhả follow sẽ k đăng video à?"*

---

## 2. Bản Chất Kiến Trúc Thuật Toán TikTok (Sol Architecture Analysis)

Hệ thống của TikTok vận hành bằng hai "bộ não" phân tích hoàn toàn độc lập:

```
                          USER ACTIONS
                               |
            ---------------------------------------
            |                                     |
   Anti-Fraud System                    Recommendation System
   (Kiểm soát Hành vi & Graph)          (Phân phối Nội dung FYP)
            |                                     |
   "Có gian lận/Spam không?"            "Nội dung này giữ chân ai?"
```

1. **Anti-Fraud System (Bộ lọc chống gian lận & Follow Graph):**
   - Giám sát tốc độ bấm nút, tỷ lệ follow/unfollow, IP proxy, tỷ lệ nhả follow.
   - Khi phát hiện bất thường -> kích hoạt án phạt `follow_cooldown` (chỉ khóa hành vi follow), hoặc cầu dao IP (`trip_ip_breaker`).
   - Anti-Fraud **không trừng phạt việc tài khoản đăng video** nếu tài khoản vẫn có nội dung sáng tạo bình thường.

2. **Recommendation System (Hệ thống phân phối video):**
   - Đánh giá video dựa trên: *Retention rate, Watch time, Completion rate, Rewatch, Share, Comment*.
   - Hoàn toàn **không quan tâm hôm nay tài khoản có đi follow dạo ai hay không**.
   - Thậm chí, việc đăng video vào ngày không đi follow còn gửi tín hiệu sạch hơn về một Creator thực thụ (tín hiệu content không bị pha tạp bởi hành vi growth manipulation).

---

## 3. Quy Chuẩn Vận Hành Độc Lập Bắt Buộc

| Tình trạng | Hành vi Follow | Hành vi Upload Video |
|---|---|---|
| **Nick bình thường (Ngày cày)** | Chạy follow theo budget (10–20/phiên) | Mở Upload Hook (Phiên 1 hoặc Phiên 2) |
| **Nick bị nhả follow (Follow Cooldown)** | **KHÓA FOLLOW 100%** (`_follow_rate = 0`) | **VẪN ĐĂNG 1 VIDEO/NGÀY BÌNH THƯỜNG** |
| **Ngày dưỡng sinh / Ca xả tải (`is_rest_day`)** | **TẮT FOLLOW TOÀN BỘ** (`TAADAA_REST_DAY_NO_FOLLOW=1`) | **VẪN MỞ UPLOAD HOOK** để nick tích lũy mốc video |

---

## 4. Cơ Chế Opportunistic Upload (Phiên 1 hoặc Phiên 2)

### A. Tại sao cấm chỉ đăng ở một phiên cố định (Single Point of Failure)?
- Nếu chỉ cho phép đăng ở Phiên 2: Khi lịch chạy đã được mỏng hóa (chu kỳ 4 ngày), nếu Phiên 2 gặp sự cố mạng/proxy/app crash, tài khoản sẽ **mất trắng lượt đăng của cả ngày**, làm lệch toàn bộ nhịp nuôi kênh.
- Coi **Phiên 1 là Primary attempt** (cơ hội chính) và **Phiên 2 là Fallback attempt** (cơ hội cứu cánh).

### B. Ba Điều Kiện Bắt Buộc Trong Code:
1. **Idempotency cấp ngày (Sổ cái `shift_upload_history.json`):**
   - Đầu mỗi phiên, kiểm tra xem tài khoản đã có video upload thành công trong ngày chưa.
   - Nếu `status == "success"` -> **SKIP NGAY LẬP TỨC** (`already_uploaded_in_shift`). Tuyệt đối không đăng lần 2.
2. **Không Retry Dồn Dập Tại Chỗ:**
   - Nếu Phiên 1 upload lỗi -> Đóng session, ghi log fail, **chờ đến đúng khung giờ của Phiên 2 mới thử lại**. Tránh bắn request liên tục làm TikTok nghi ngờ bot spam.
3. **Upload Hook Luôn Mở (`-AllowUploadHook` vô điều kiện):**
   - Trong `tiktok_runner.py`, tham số `-AllowUploadHook` luôn được truyền cho cả Phiên 1 và Phiên 2, **KHÔNG bọc trong bất kỳ điều kiện `if not is_rest_day` nào**.
   - Trách nhiệm quyết định có đăng hay không được giao hoàn toàn cho sổ cái idempotency của core.
