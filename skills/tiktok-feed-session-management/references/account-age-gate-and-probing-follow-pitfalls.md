# TikTok Farm Account Age Gate & Probing Follow Pitfalls

## 1. Dữ Liệu Thực Tế Farm (Account Age vs Follow Success)
Dữ liệu đối soát thực tế từ SQLite `tiktok_tracker.db` và hơn 500 state files (`follow_state_*_row_*.json`):

| Nhóm tuổi | Tỷ lệ follow được | Tỷ lệ fail / bị cờ follow_failed | Follow TB / acc | Đánh giá vận hành |
| :--- | :--- | :--- | :--- | :--- |
| **< 30 ngày** | **0.0%** | **100.0%** | 0.0 | Bị chặn tuyệt đối bởi ByteDance Risk Engine |
| **30 – 59 ngày** | 12.0% | 42.3% đang bị cờ | 1.8 | Rất bất ổn, đa số bị nhả ngay sau 1-2 follow |
| **60 – 89 ngày** | 24.4% | **82.9% đang bị cờ** | 1.2 | Đỉnh điểm kẹt tù: 96.7% từng dính fail, dồn streak |
| **90 – 119 ngày** | 38.1% | 39.7% | 5.1 | Điểm uốn (Inflection point): Bắt đầu follow ổn định |
| **>= 120 ngày** | **83.0%** | 14.2% | **73.7** | Tốt nghiệp (Graduated), tích lũy hơn 10.300 follows |

---

## 2. Cạm Bẫy 1: "Ngâm Chết Acc" (Inactive / Zombie Account)
Đề xuất ngâm tài khoản trên máy 3 tháng không lướt feed, không đăng video là sai lầm nghiêm trọng:
1. **Phân loại rủi ro (Risk Profiling):** ByteDance coi tài khoản không hoạt động nhiều tháng rồi đột ngột mở lên đi follow là hành vi của "Zombified / Compromised Account" hoặc nick bot được kích hoạt hàng loạt $\implies$ Trảm action hoặc checkpoint lập tức.
2. **Auth Token & Session Expiration:** Bỏ xó app 90 ngày khiến refresh token hết hạn, TikTok bắt re-login, kích hoạt chuỗi xác minh Hotmail OTP (dễ dính khóa token Graph API/GPM) hoặc captcha trượt khó.
3. **Thâm hụt Video Gate:** Sau 3 tháng nick vẫn có 0 video, lại phải mất thêm hàng tháng đăng video từ đầu mới đủ chuẩn vào phễu follow.

---

## 3. Cạm Bẫy 2: "Follow Dò" Với Backoff Tăng Tiến (Probe Follow Trap)
Ý tưởng "cứ cho đi follow dò, nếu nhả thì cơ chế khóa 3-5-15 ngày sẽ tự bảo vệ":
1. **Vết sẹo Trust Score:** Mỗi lần bấm follow bị nhả (Optimistic UI bị revert qua Path B verify) là một lần server ByteDance ghi nhận vi phạm ngưỡng rủi ro (`action_risk_spike`). Tần suất 15 ngày/lần không làm TikTok bỏ qua, mà chỉ duy trì nhãn "tài khoản có hành vi tự động hóa thăm dò".
2. **Bóp Reach / 0-View Video:** Kênh đang đăng video nuôi, nhưng khi dính cờ vi phạm action follow thì hệ thống phân phối nội dung của TikTok đồng thời bóp reach (shadowban), video chỉ đạt 0 view hoặc vài view lẹt đẹt.
3. **Kẹt Tù Probation Vĩnh Viễn:** Khi nick bị nhả follow liên tục, `fail_streak` dồn lên $\ge 3$. Nick bị kẹt trong `probation_clean_days = 0`, trần budget bị ép xuống 1-2 follow và không bao giờ đủ điều kiện tốt nghiệp (`is_graduated`).
4. **Hiệu ứng Kéo Chùm (IP Circuit Breaker):** Nhả follow liên tiếp trên 1 proxy có thể kích hoạt `ip_circuit_breaker`, làm ngắt proxy và khóa oan các nick già khỏe mạnh khác chạy chung dải proxy trên farm.

---

## 4. Chiến Lược Chuẩn Mực Cho Farm (Decoupled Nurture & Age Gating)
- **Tách bạch 100% giữa Nuôi Feed và Follow:**
  * **Nuôi feed & Đăng video:** Chạy đều đặn theo đúng vòng Shift-Pool `{1, 2, 7}`, `{3, 4, 8}`, `{5, 6}`. Tích lũy hành vi Active Consumer (watch time, like, interest tags) và tích lũy đủ 10–15 video.
  * **Hành động Follow:** Khóa cứng tuyệt đối (Hard Gate) với mọi nick có `account_age_days < 90`. Tuyệt đối cấm follow dò.
  * **Cơ chế:** Khi đến bước follow, bot tự kiểm tra tuổi nick và skip với reason: `status: "skipped", reason: "under-age-90d-quarantine"`.
- **Hiệu quả:** Đúng ngày thứ 90, tài khoản bước ra với hồ sơ "sạch tinh", độ trust cao, có sẵn lịch sử xem video và video tự sản xuất, tỷ lệ follow thành công đạt ngay mức cao nhất mà không bị gậy.
