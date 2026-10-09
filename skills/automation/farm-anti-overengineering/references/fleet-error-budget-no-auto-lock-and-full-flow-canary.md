# Fleet Error Budget, Bỏ Auto-Lock 1h & Quy chuẩn Canary Full Flow (Taadaa Phone Farm)

Đúc kết ngày 07/09/2026 từ chỉ đạo trực tiếp của Tad Shavershian và kết quả review độc lập của Claude CLI Opus High:

## 1. Bản chất thay đổi: Chuyển từ Per-Device Alert sang End-of-Batch Aggregation
- **Trước đây (Bẫy Alert Fatigue):** Cứ 1 máy vấp lỗi tạm thời (transient: lag proxy 5s, animation trễ trên S7) là kích hoạt Fast-Fail giữ lock 1h và réo chuông Telegram, khiến operator kiệt sức vì chữa cháy vụn vặt và đàn máy bị giam lock.
- **Hiện tại:** 
  - Trong lúc chạy: Im lặng tuyệt đối (Silent Run).
  - Máy lỗi chụp snapshot-on-fail (XML + PNG) lưu ổ đĩa $\rightarrow$ `force-stop` về Home $\rightarrow$ nhả device lock ngay lập tức (không giữ 1h).
  - Cuối batch: Gom lỗi theo Error Signature. Nếu cùng 1 lỗi $\ge 10-15\%$ số máy (và $\ge 3$ máy) thì mới bắn 1 Farm Alert tổng hợp kèm 1-2 ảnh đại diện. Dưới ngưỡng thì bỏ qua hoàn toàn.

## 2. Quy chuẩn Canary MỚI: BẮT BUỘC chạy lại đúng Script của Flow bị lỗi
- **BÃI BỎ:** Bãi bỏ quy định chỉ chạy swipe feed ngẫu nhiên `(Get-Random 2-5 swipes)` khi nghiệm thu bugfix.
- **KỶ LUẬT THỰC CHIẾN:**
  - Sửa bug flow **Reg (Đăng ký TikTok)**: Canary BẮT BUỘC chạy lại đúng script Reg với 1 account mới từ A $\rightarrow$ Z đến khi hoàn thành 100%.
  - Sửa bug flow **Upload Video**: Canary BẮT BUỘC chạy lại đúng script Upload 1 video hoàn chỉnh cho đến khi publish thành công.
  - Sửa bug flow **Login / 2FA / Reconcile**: Canary BẮT BUỘC chạy lại đúng flow tương ứng.
- **Verdict:** Chỉ khi nào flow bị lỗi chạy lại hoàn thành trọn vẹn trên máy thật thì mới đạt chuẩn CANARY PASS để bước vào chốt phiên 6 Gate.

## 3. Bẫy Python Nuance trong Hàm Release/Cleanup (Claude Review Round 2 Catch)
- Khi bọc an toàn trong khối `except` không được nuốt lỗi caller:
  - `sys.exc_info()[1]` bên trong `except ... as exc:` luôn trả về chính `exc`, không bao giờ là `None`.
  - Phải lưu `ambient_exc = sys.exc_info()[1]` TRƯỚC khi vào `try`.
  - Trong `except (OSError, DeviceLockReleaseError): if ambient_exc is None: raise`.
