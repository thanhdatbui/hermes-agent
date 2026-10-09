# TikTok Registration & Password Integrity Guidelines

References:
- `references/evidence-first-ocr-readback-and-anti-blind-diagnosis-20260917.md`

## 1. Nguyên tắc cốt lõi: Mật khẩu thực tế vs Excel
- **Không suy diễn:** Khi đăng ký TikTok, nhiều trường hợp app bỏ qua bước tạo mật khẩu (flow email-only/OTP).
- **Cấm sinh pass ảo:** Nếu TikTok không hiển thị form đặt mật khẩu hoặc không điền pass thành công, cột `PASS` trong file Excel (`taikhoan_dat_v2_updated .xlsx`) **BẮT BUỘC PHẢI ĐỂ TRỐNG (`None` hoặc `""`)**.
- **Tuyệt đối cấm:** Gọi các hàm fallback sinh mật khẩu ngẫu nhiên (`make_tiktok_password`) để ghi đè vào file khi app chưa thực sự lưu mật khẩu trên server.

## 2. Kỷ luật kiểm tra bằng chứng (OCR Readback Gate)
- Khi chụp ảnh hiện trường lỗi đăng nhập, đổi mật khẩu hoặc xác minh danh tính:
  1. Chụp ảnh screencap đóng băng tại chỗ.
  2. BẮT BUỘC chạy `winrt_ocr.py` trích xuất 100% văn bản hiển thị.
  3. Quét các từ khóa báo lỗi: `Mật khẩu sai`, `Sai tài khoản hoặc mật khẩu`, `giới hạn`, `thử lại sau`, `phiên đã hết hạn`.
  4. Trích xuất nguyên văn câu thông báo lỗi làm căn cứ kết luận. Cấm chỉ dựa vào accessibility XML để kết luận bừa.
