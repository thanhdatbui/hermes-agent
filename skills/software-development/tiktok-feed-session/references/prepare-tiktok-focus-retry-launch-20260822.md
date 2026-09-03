# Prepare TikTok Focus Failure & Startup Monkey Retry (2026-08-22)

## 1. Triệu chứng & Báo động
- Farm Alert trên Telegram: `🚨 [MÁY XX] DỪNG PHIÊN`
- `• Script: multi-machine-feed-session`
- `• Lý do: prepare-tiktok failed to focus TikTok after launch`
- `• Trạng thái: 🟡 GIỮ HIỆN TRƯỜNG ĐỂ HERMES AGENT XỬ LÝ`
- Ảnh đính kèm: Thiết bị dừng ở Android Launcher / Home Screen.

## 2. Nguyên nhân gốc rễ (Root Cause)
- Tại bước `prepare_app_for_automation` (`automation_core/startup.py`):
  1. Quy trình chạy `am force-stop` rồi gửi 1 lệnh `monkey -p <target> -c android.intent.category.LAUNCHER 1`.
  2. Sau đó vòng lặp kiểm tra `verify_app_focus` chạy tối đa 10 lần (delay 1.5s mỗi lần).
  3. Trên các máy Samsung Galaxy S7 cấu hình thấp, khi tải cao hoặc hệ thống trễ xử lý intent monkey, sự kiện launch ban đầu có thể bị trượt/drop mà không có bất kỳ lệnh kích hoạt lại nào trong suốt 15s polling thụ động.
  4. Hết 10 lần thử, hệ thống kết luận `failed to focus target app after launch` (`prepare-tiktok failed to focus TikTok after launch`) và dừng phiên.

## 3. Giải pháp chuẩn & Cơ chế phục hồi
- Trong `automation_core/startup.py` (`prepare_app_for_automation`):
  - Bổ sung cơ chế chủ động kích hoạt lại (re-launch via `monkey`) tại attempt 4 và attempt 7 trong vòng lặp chờ focus.
  - Đảm bảo nếu sự kiện launch đầu tiên bị drop, app vẫn được đánh thức lại mà không phải chờ hết timeout 10 attempts gây fail phiên.
