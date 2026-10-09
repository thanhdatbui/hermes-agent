# Batch Alert & Machine Alert Clustering Guidelines

## 1. Nguyên Tắc Cảnh Báo (Alert Discipline)
- **Cảnh báo theo cụm lỗi (Dual-Threshold Grouping):**
  - Mọi cảnh báo lỗi thông thường (timeout, app crash, proxy/network jitter, adb glitch) BẮT BUỘC phải qua cơ chế gom cụm `batch_aggregator.py`.
  - Chỉ kích hoạt Batch Alert khi thỏa mãn ngưỡng kép: Tỷ lệ thất bại $\ge 10\%$ toàn batch VÀ $\ge 3$ máy có cùng một signature lỗi (`min_rate=0.10, min_count=3`).
  - Lỗi dưới ngưỡng này được xếp vào Sporadic (lỗi đơn lẻ) và bị silently skipped, không bắn tin nhắn Telegram.

## 2. Trường Hợp Ngoại Lệ Duy Nhất (Critical Account / Login Screen)
- Ngoại lệ bypass cơ chế suppress alert máy lẻ (`send_farm_machine_alert`) CHỈ áp dụng cho **vấn đề tài khoản / đăng nhập thực tế**:
  - Máy bị văng tài khoản, hiển thị màn hình Login/Sign Up hoặc checkpoint verification thực sự.
  - Từ khóa: `account_missing`, `account-switcher-missing-expected`, `login screen detected`.

## 3. Pitfall: False-Positive Bypass Do Lỗi Script / Switcher Crash
- **Hiện tượng:** Khi worker hoặc script gặp bug runtime (ví dụ NameError, syntax error, UI selector crash trong flow feed/upload), flow tiếp theo gọi `run_upload` hoặc `account_switcher` và ném ra thông báo dạng:
  `[ACCOUNT_SWITCHER_FAILED] select account failed: ACCOUNT_MISSING: expected account was not found...`
- **Hậu quả:** Hàm `send_farm_machine_alert` quét trúng substring `ACCOUNT_MISSING` và hiểu lầm là máy bị văng nick khẩn cấp -> bypass suppression và bắn liên hoàn hàng chục tin nhắn Farm Alert đỏ `[MÁY N]` về Telegram, gây spam và làm người dùng khó chịu.
- **Quy tắc khắc phục:**
  - Nếu lỗi xuất phát từ script crash / NameError / pipeline abort trước đó, mã lỗi phải được phân loại là `script_error` hoặc `runtime_error`, KHÔNG được gán `ACCOUNT_MISSING`.
  - Kiểm tra điều kiện bypass alert máy lẻ phải đảm bảo đó là màn hình đăng nhập / văng nick thực tế (dựa trên UI dump / XML class/text cụ thể), không chỉ dựa vào substring regex thô trên `error_reason`.
