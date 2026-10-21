# Bẫy Trùng Tên Deferred Result Khác Timestamp, Mật Khẩu Sai & Nhận Diện OCR Lỗi Đỏ (2026-10-21)

## 1. Hiện Tượng Thực Tế
- Trên Máy 24, khi tài khoản `@trinhgiang7694` bị thiếu trong Switcher, script cứu hộ đọc `taikhoan_dat_v2_updated .xlsx` dòng 192 thấy cột Pass và Email bị trống (`None`).
- Khi tìm kiếm file deferred tracking kết quả theo STT và email trong thư mục `D:/Taadaa/runtime/kibe/artifacts/runs/social-batch-all/`, tồn tại nhiều lần chạy qua các mốc thời gian khác nhau:
  + File 1: `runs/social-batch-all/20260917-000801/batch_1/stt_24/tracking_result_stt24_jasmynquines487694_hotmail.com.json` mang mật khẩu `e2#b?zpZTMTcD`.
  + File 2: `runs/social-batch-all/20260901-011426/batch_2/stt_24/tracking_result_stt24_jasmynquines487694_hotmail.com.json` mang mật khẩu `aLONKv5$#!`.
- Nếu lấy nhầm file đợt 17/09/2026, mật khẩu `e2#b?zpZTMTcD` thực chất là pass của một đợt reg dở dang hoặc của nick khác. Khi điền vào TikTok, app báo lỗi đỏ:
  `Mật khẩu sai` (hoặc OCR nhận diện: `A Mat khåU sai`).

## 2. Nguyên Nhân Kép
1. **Trùng lặp tên file kết quả giữa các đợt chạy**:
   Do quy ước đặt tên file `tracking_result_stt<STT>_<email>.json` gắn theo STT và email Hotmail tái sử dụng, các batch chạy vào ngày 01/09 và 17/09 có thể sinh ra cùng tên file trong các thư mục run khác nhau.
   Thời điểm đăng ký chính thức của `@trinhgiang7694` trong file tracking master là `2026-09-01 01:32:19`, khớp chính xác với timestamp của file run ngày `20260901-011426` (`written_at: 2026-09-01T01:32:27`).
2. **Thiếu chuỗi nhận diện lỗi tiếng Việt trong `tiktok_login_v1.py`**:
   Danh sách `WRONG_PASS_HINTS` trong script chỉ có `"mat khau khong dung"`, `"mat khau khong chinh xac"`, `"sai mat khau"`. Khi TikTok hiển thị nhãn `"Mật khẩu sai"`, script không nhận diện được ngay lập tức chuỗi này, dẫn đến việc tiếp tục chờ đợi và dừng với log `AUTH_BLOCKED` sau khi đã submit pass.

## 3. Quy Tắc Khắc Phục Chuẩn
1. **Đối soát khớp timestamp đăng ký**:
   Khi cứu hộ credentials từ deferred result JSON, BẮT BUỘC đối soát trường `written_at` / `created_date` trong JSON với cột I (Ngày tạo) của Workbook Excel để đảm bảo lấy đúng đợt khởi tạo tài khoản, tránh lấy nhầm pass của lượt chạy khác.
2. **Bổ sung chuỗi nhận diện vào `WRONG_PASS_HINTS`**:
   Bổ sung chuỗi `"mat khau sai"` vào `WRONG_PASS_HINTS` trong `tiktok_login_v1.py` để script fail-fast tức thì khi TikTok báo sai pass:
   ```python
   WRONG_PASS_HINTS = [
       "mat khau khong dung", "mat khau khong chinh xac", "sai mat khau", "mat khau sai",
       "incorrect password", "wrong password", "thu lai mat khau",
       "khong dung voi tai khoan", "thu qua so lan", "qua nhieu lan"
   ]
   ```
3. **Kỷ luật bảo toàn dữ liệu**:
   Sau khi xác định đúng mật khẩu gốc (`aLONKv5$#!`), ghi lại vào cột D của Workbook Excel chính chủ và chạy `python D:/Taadaa/tools/excel_preflight_validator.py` để kiểm chứng đạt 100% PASS trước khi chạy lại luồng login.
