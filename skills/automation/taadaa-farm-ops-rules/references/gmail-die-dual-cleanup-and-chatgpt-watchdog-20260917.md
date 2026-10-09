# Quy Tắc Dọn Dẹp Kép Khi Gmail DIE & Báo Cáo Chuỗi Reg Gmail / ChatGPT (17/09/2026)

## 1. Cơ Chế Preflight Live Check & Dọn Dẹp Kép (TikTok Reg)
- **Vấn đề thực tế:** Khi chạy batch đăng ký TikTok qua `_run_all_targets.py`, nếu các tài khoản Gmail nguồn đã bị Google vô hiệu hóa (DIE) từ trước, thiết bị Samsung S7 sẽ vào màn hình chờ OTP và bị treo timeout 150 giây (`[7c][BLOCKED_GMAIL_OTP_TIMEOUT]`).
- **Giải pháp chuẩn hóa:**
  1. **Tiền kiểm tra (Preflight check live):** Tự động lọc danh sách Gmail mục tiêu qua `check_gmail_live_batch` (`checkmail.live`) trước khi phân bổ vào máy S7.
  2. **Cơ chế fail-open:** Nếu lỗi mạng hoặc timeout service ngoài, giữ nguyên danh sách target để không chặn toàn bộ farm.
  3. **Quy tắc dọn dẹp kép (Dual Cleanup) khi Gmail DIE (`result is False`):**
     - **Dọn ở Excel:** Xóa dòng khỏi file nguồn `gmail_clean_v2.xlsx` qua `remove_captcha_dead_email_from_source(email)` để các đợt sau không bốc lại.
     - **Dọn trên máy S7:** BẮT BUỘC gọi `remove_device_account_fast(serial, email)` kiểm tra `dumpsys account` và gỡ bỏ tài khoản Google chết khỏi Android Settings của máy, tránh làm rác và kẹt slot thiết bị.

## 2. Lỗi Biến Cục Bộ (Scope Shadowing) Khi Import Cục Bộ Trong Hàm Python
- **Pitfall:** Khi một hàm có `from pathlib import Path` ở khối code phía dưới, Python coi `Path` là local variable của cả hàm. Nếu phần đầu hàm có gọi `Path(__file__)` trước đó sẽ bị văng `UnboundLocalError: cannot access local variable 'Path' where it is not associated with a value`.
- **Khắc phục:** Dùng `Path` đã import ở module level đầu file, tuyệt đối không re-import cục bộ `Path` trong thân hàm.

## 3. Thống Kê & Báo Cáo ChatGPT Sau Ca Reg Gmail (`post_noon_chain_watchdog.py`)
- Khi kết thúc Phase 1 (Reg Gmail), Watchdog bóc tách trực tiếp số lượng máy liên kết ChatGPT thành công/thất bại (`✓ [WARMUP_CHATGPT]` / `⚠ [WARMUP_CHATGPT]`) từ log của batch:
  ```text
  - Phase 1 (Reg Gmail - Code 0):
    + Tổng máy: 15
    + Success (10)
      * ChatGPT linked: 10/10
    + Fail (5)
  ```
- Giúp người vận hành nhận biết ngay lập tức tài khoản nào đã kích hoạt xong ChatGPT, tránh trường hợp reg Gmail xong nhưng hook ChatGPT bị xịt ngầm mà không ai hay biết.

## 4. Kỷ Luật Device Lock Trong Ca Nuôi Acc (Feed Session)
- Khi cron nuôi acc (feed session) đang chạy trên farm, TUYỆT ĐỐI CẤM tự ý gọi hook hoặc chạy bù can thiệp lên các máy S7 vì sẽ gây tranh chấp device-lock và phá vỡ phiên nuôi. Mọi tác vụ bù phải chờ hết ca hoặc chạy trong dead-window.
