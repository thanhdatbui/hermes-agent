# Chuỗi Đêm 3 Phase (Gmail -> TikTok -> Add 2FA) & Quy Tắc Re-run Farm

## 1. Kiến Trúc Chuỗi Đêm 3 Phase (`run_night_chain_pipeline.py`)

Chuỗi tự động ban đêm chạy lúc 01:00 sáng mỗi ngày qua cron launcher `night_chain_reg_pipeline_launcher.py`:

1. **Phase 1: Reg Gmail (`register gmail/run_all.ps1`)**
   - Tạo Gmail sạch bằng ADB trên các máy đạt cooldown (>= 5 ngày).
   - **Quy tắc gõ Họ/Tên:** Mã hóa khoảng trắng thành `%s` khi gọi `adb shell input text` để hỗ trợ họ tên 2–4 từ (tên đệm `DEM_POOL`).
   - **Quy tắc Username:** Dùng 100% tên Việt Nam. Tự động thử lại tối đa 5 lần (`handle_username_entry`) khi Google báo trùng username (`đã được sử dụng`), tăng dần độ dài số ngẫu nhiên (3–4 số) và salt để đảm bảo duy nhất 100%.
   - **Quy tắc Mật khẩu:** Dùng symbols an toàn (`@`, `#`, `!`, `$`) và escape ký tự đặc biệt shell trong `human_type`.

2. **Phase 2: Reg TikTok (`Tiktok_Reg/_run_all_targets.py`)**
   - Đăng ký nick TikTok từ nguồn mail sạch trong `gmail_clean_v2.xlsx`.
   - Chuẩn farm 80 máy x 6 nick = 480 slot (`taikhoan_run_safe.xlsx`), bỏ qua các slot thừa trong `taikhoan_dat_v2_updated .xlsx`.
   - Tự động áp dụng kết quả deferred (`apply_deferred_tracking_results.py`) và sync sang `taikhoan_run_safe.xlsx`.

3. **Phase 3: Bật 2FA TikTok (`tiktok-add-bao-mat-f2a/python_runner/run_batch_live_2fa.py`)**
   - Tự động chạy batch bật 2FA (tối đa 40 workers song song) cho các tài khoản **đã có ID TikTok** nhưng **chưa có mã 2FA** trong Excel.
   - **Quy luật ca chạy hôm trước:** Lúc 1h–2h sáng, ưu tiên quét bật 2FA cho các nick thuộc ca vừa chạy của ngày hôm trước (vd hôm trước chạy ca lẻ $\rightarrow$ quét slot lẻ 1, 3, 5) vì các nick này đang active trên máy.
   - **Bắt buộc Host Config (`TAADAA_HOST_CONFIG`):** Module `run_batch_live_2fa.py` gọi `_resolve_proxy_mapping()` ở cấp top-level import. Pipeline cha (`run_night_chain_pipeline.py`) và launcher (`night_chain_reg_pipeline_launcher.py`) BẮT BUỘC phải export `TAADAA_HOST_CONFIG=D:\Taadaa\machine-config\kibe.yaml` vào môi trường trước khi chạy subprocess Phase 3; nếu thiếu sẽ sập script ngay lập tức với `ConsumerPreflightError`.

---

## 2. Quy Tắc Phân Loại Lỗi & Quyết Định Re-run (Bắt Buộc)

- **RÀNG BUỘC PHỤ THUỘC GIỮA PHASE 1 VÀ PHASE 2:**
  - Phase 2 (Reg TikTok bằng Gmail) CHỈ ĐƯỢC PHÉP nạp các máy mà Phase 1 (Reg Gmail) đã xác nhận `SUCCESS` và tài khoản đã tồn tại trong ứng dụng Gmail trên máy.
  - Tuyệt đối không đưa máy đã fail ở Phase 1 vào batch Phase 2; tránh tình trạng TikTok gửi mã OTP nhưng script mở app Gmail không thấy tài khoản (`account list chua thay ...@gmail.com`), làm lãng phí 15–20 phút vô ích và văng lỗi `FAILED_EXIT_1`.

- **ĐƯỢC PHÉP CHẠY LẠI (Script / Logic Bug):**
  - Lỗi cú pháp lệnh ADB (`Invalid arguments for command: text` do khoảng trắng).
  - Lỗi chưa bắt vòng lặp đổi username khi bị taken.
  - Lỗi cache trạng thái proxy cũ (`proxy_pending` tồn đọng trong `.codex/device-readiness`).
  - Sau khi sửa code và kiểm thử unit test thành công, chạy lại các máy bị lỗi script.

- **TUYỆT ĐỐI CẤM CHẠY LẠI (Google Anti-Bot / Blocks):**
  - **`PHONE_VERIFY`:** Màn hình Google bắt xác minh số điện thoại.
  - **`ACCOUNT_CREATION_ERROR`:** Google chặn tạo tài khoản do IP/thiết bị bị gắn cờ.
  - **Quy tắc:** Khi gặp các lỗi này, BẮT BUỘC ghi nhận là lỗi do Google chặn và DỪNG HẲN trên máy đó; tuyệt đối không tự ý chạy lại làm nát thiết bị/cháy proxy.

---

## 3. Quy Tắc Điều Phối Worker (Coordinator Invariant)

- Session chính đóng vai trò **Coordinator** (đọc log hiện trường, phân tích nguyên nhân, lập kế hoạch, review code, rebase/push).
- **CẤM** session chính tự viết code sửa chữa hoặc chạy test dài trực tiếp; BẮT BUỘC phân phối sang subagent `delegate_task(role='leaf')` để worker xử lý độc lập.
