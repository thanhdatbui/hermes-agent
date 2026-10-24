# SOP Thẩm Định Thị Giác Đa Tầng (Mechanical Tiered Vision SOP)

Cập nhật: 2026-10-24

## 1. Bối cảnh & Nguyên nhân cải tiến
- Khi công cụ thị giác chính của Coordinator (`browser_vision` / native vision) gặp sự cố (503 Service Unavailable, 429 Rate Limit, hết quota), Coordinator có xu hướng vi phạm nghiêm trọng:
  1. Tự ý hạ cấp bằng chứng: dùng WinRT OCR đọc text thô rồi báo cáo chữ suông mà không gửi ảnh.
  2. Gian dối thị giác: gửi ảnh cũ hoặc không soi mắt thực tế trước khi gửi thẻ `MEDIA:`.
  3. Lạm dụng ghi nhớ memory thay vì xây dựng giải pháp cơ học bền vững.

## 2. Thứ tự Fallback Đọc Ảnh Chuẩn Hoá (Đồng bộ Worker Dispatch)
Bình thường Coordinator tự soi mắt trong phiên. Khi xảy ra lỗi thị giác, hệ thống bắt buộc kích hoạt thang fallback cơ học tự động qua `vision_fallback_reader.py`:
- **Tier 0 (Primary):** Coordinator tự soi mắt (`browser_vision`).
- **Tier 1 (Fallback 1):** Sol Web Vision (`http://127.0.0.1:20129` qua OmniRoute - model `auto/best-vision`). Miễn phí 100%, phản hồi nhanh.
- **Tier 2 (Fallback 2):** Agy CLI Vision (`ag_cli.py ask` qua pool 29 tài khoản Google One Pro).
- **Tier 3 (Fallback 3):** Claude Worker Reviewer (`claude_worker.py --role reviewer`).

## 3. Lệnh Thực Thi & Ký HMAC Receipt Tự Động
Mọi quy trình fallback đã được gói gọn trong công cụ cơ học:
```bash
python D:/Taadaa/tools/vision_fallback_reader.py --image "<đường_dẫn_ảnh>" --question "<tiêu chí kiểm tra>" --mode auto_fallback
```
- Khi Coordinator tự soi mắt thành công bằng `browser_vision`:
```bash
python D:/Taadaa/tools/vision_fallback_reader.py --image "<đường_dẫn_ảnh>" --question "<tiêu chí>" --mode register_coordinator
```
Cả hai chế độ đều tự động tạo signed receipt HMAC vào `D:/Taadaa/runtime/audit_logs/vision_receipts.jsonl` để pass 100% kiểm tra của `guard_media_vision_gate.py`.

## 4. Kỷ Luật Bất Biến (Fail-Closed)
- Nếu cả 3 tầng fallback đều thất bại: CẤM gửi ảnh mù, CẤM hạ cấp sang OCR text thô, bắt buộc giữ trạng thái `UNVERIFIED / BLOCKED_VISION_UNAVAILABLE`.
- CẤM lưu memory thủ công khi hệ thống đã có tầng cơ học và marker file đảm nhiệm.
