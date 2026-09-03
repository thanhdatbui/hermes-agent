# TikTok Farm Night Batch & Target Allocation Rules

## 1. Multi-Condition Target Eligibility
1. **Giới hạn cứng $\le 6$ accounts/máy**:
   * Quét bảng tracking (`taikhoan_dat_v2_updated .xlsx`), đếm số lượng TikTok ID thực tế của từng STT máy.
   * Nếu máy đã có $\ge 6$ TikTok ID $\rightarrow$ Loại vĩnh viễn khỏi toàn bộ các lượt reg tiếp theo (`max 6 accs/machine`).
2. **Bắt buộc còn Mail nguồn hợp lệ chưa dùng**:
   * Máy phải còn tài khoản mail trong kho nguồn (`gmail_clean_v2.xlsx`) mà chưa hề xuất hiện trong tracking.
   * Nếu máy hết mail chưa dùng $\rightarrow$ Bỏ qua (`NO_UNUSED_SOURCE_MAIL`).
3. **Không vướng Device Lock / Cooldown**:
   * Máy không có file lock `blocked`/`running`/`queued` hợp lệ còn TTL.
   * Máy không nằm trong danh sách daily cooldown hôm nay (`reg_daily_cooldowns.json`).

---

## 2. Night Batch Configuration & Concurrency Controls
* **Ca đêm (01:00 AM)**: Khung giờ trống máy (01:00 – 03:30) khi cron nuôi acc ngừng hoạt động.
* **Số lượng mục tiêu**: `--max-targets 30` (Tối đa 30 máy / đợt chạy để tránh bị TikTok gắn cờ rate-limit / spam thiết bị).
* **Số luồng cuốn chiếu**: `--max-workers 6` (Chạy song song 6 máy cuốn chiếu, giãn cách 2–8s giữa các máy).
* **Tiến trình chuỗi đêm (`run_night_chain_pipeline.py`)**:
  * Chạy nối đuôi tuần tự (blocking): **Phase 1 (Reg Gmail)** $\rightarrow$ Chờ hoàn tất 100% $\rightarrow$ Nghỉ 10s $\rightarrow$ **Phase 2 (Reg TikTok)**.
  * Tuyệt đối không để 2 phase chạy song song tranh chấp thiết bị.

---

## 3. Triage Các Lỗi Thường Gặp Khi Chạy Batch Đêm
* **Lỗi OTP Gmail (`[otp-gmail] ... khong co trong Gmail account list`)**:
  * Xảy ra với các target cũ dùng Gmail. Gmail cần app Gmail trên điện thoại nhận mã; nếu chưa đăng nhập vào máy thì flow không đọc được OTP.
  * Hotmail OAuth2 chạy ổn định hơn do đọc mã trực tiếp qua PC (Microsoft Graph API).
* **Lỗi ATX UI XML Timeout / Treo**:
  * Thiết bị Samsung S7 bị nghẽn socket hoặc crash Accessibility.
  * Phải reset ATX stub bằng `monkey -p com.github.uiautomator 1` hoặc `reset_atx_agent(client)`.
* **Lỗi Kẹt Màn Hình Khóa Samsung (`com.android.systemui` Keyguard)**:
  * Máy bị khóa màn hình hoặc tắt màn hình ("Vuốt màn hình để mở khóa").
  * Runner cần gửi lệnh mở khóa / đánh thức màn hình (`input keyevent 26` / `input keyevent 82` hoặc vuốt mở khóa) trước khi tìm UI tab Profile.
