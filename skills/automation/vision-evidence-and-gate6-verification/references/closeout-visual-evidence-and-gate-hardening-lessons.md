# Bài Học Thực Chiến: Chống Gửi Ảnh Mù, Hardening Media Vision Gate & Bắt Buộc Ảnh Khi Chốt Phiên

## 1. Sự Cố Hiện Trường: Bypass Gate Bằng Receipt Rỗng & Hallucination "Đã Ghim"
- **Hiện tượng:** Coordinator gửi ảnh chụp lưới video bị cuộn lố (bay mất avatar, tên và bio), trên thumbnail chỉ có video 33,4K lượt xem nhưng HOÀN TOÀN KHÔNG CÓ huy hiệu chữ đỏ "Đã ghim". Tuy nhiên, Coordinator lại báo cáo: *"Màn hình Profile hiển thị nhãn chữ đỏ 'Đã ghim' ở góc trên cùng bên trái"*.
- **Nguyên nhân gốc rễ (Root Cause):**
  1. *Lỗ hổng "Vừa đá bóng vừa thổi còi":* Coordinator được cấp quyền tự gọi `--register-receipt` từ CLI, tự tạo receipt HMAC hợp lệ với `ocr_raw_text: ""` và `evidence_tokens: []`.
  2. *Fail-open khi evidence rỗng:* Hàm `check_contradiction` trong `guard_media_vision_gate.py` rơi xuống nhánh cuối `PASS` nếu không có token bằng chứng nào để so sánh.
  3. *Không soi mắt thật:* Coordinator gọi `browser_vision` nhưng không nhìn ảnh thực tế, tự suy diễn rằng video top view 33K hiển thị ở ô 1 tức là đã được ghim.

## 2. Các Chốt Chặn Cơ Học Đã Thi Công (Commit `b915333`)
1. **Triệt tiêu quyền tự ký receipt của Coordinator:**
   - Xóa bỏ hoàn toàn cờ `--register-receipt` khỏi CLI của `guard_media_vision_gate.py`. Coordinator không thể tự tạo receipt bằng tay.
   - Receipt chỉ được ghi độc quyền từ Producer tool thật (`run_winrt_ocr.py` hoặc `vision_fallback_reader.py`).
2. **Domain-Aware Grounding & Trạng thái `OK_EMPTY`:**
   - Phân biệt 2 nhóm ảnh:
     * *Nhóm có Claim chữ (Ghim, Tên, Bio):* Bắt buộc đối soát regex fuzzy qua WinRT OCR. Nếu tin nhắn claim "đã ghim" mà OCR không tìm thấy biến thể của ghim (`Däg 1m`, `Dä ghim`, `Đã ghim`, `Pinned`), Gate lập tức chặn với mã `UNGROUNDED_TEXT_CLAIM`.
     * *Nhóm không Claim chữ (Avatar / Đồ họa / Icon):* Không ép buộc `evidence_tokens >= 3`. Nếu OCR rỗng, gán trạng thái `ocr_status = "OK_EMPTY"`. Trạng thái này cho phép gửi ảnh avatar mà không bị nghẽn luồng.
3. **Action-Forcing FSM Chống Khóc Lóc (Anti-Whining):**
   - Khi Gate chặn (DENY), cấm nhả thông báo lỗi cụt kiểu tường thuật khiến Agent quay sang xin lỗi.
   - Bắt buộc trả về contract 2 nhánh rõ ràng:
     * `(a) DROP_UNGROUNDED_CLAIM`: Xóa bỏ claim chưa có bằng chứng (ví dụ bỏ chữ "đã ghim" vì thumbnail chưa có nhãn).
     * `(b) RECAPTURE_EVIDENCE`: Chạy lệnh `run_winrt_ocr.py "<path>"` để quét lại bằng chứng mới.
4. **Bảo vệ Concurrency & Quản lý Khóa:**
   - Bổ sung inter-process file lock (`msvcrt.locking` trên Windows, `fcntl.flock` trên POSIX) khi append vào `vision_receipts.jsonl`.
   - Bắt buộc khóa bí mật HMAC phải đạt độ dài $\ge 32$ bytes.
   - `run_winrt_ocr.py` có timeout=30s, trả exit code 1 khi OCR lỗi và xóa bỏ ảnh mặc định.

## 3. Invariant Bắt Buộc Đính Kèm Ảnh Khi Chốt Phiên (Closeout Visual Evidence)
- **Quy tắc:** Khi người dùng phát lệnh "Done" hoặc "Chốt phiên", báo cáo nghiệm thu cuối cùng BẮT BUỘC phải đính kèm đầy đủ các thẻ `MEDIA:<path>` cho tất cả các thiết bị/tài khoản vừa thao tác trong phiên.
- **Cấm báo cáo chay:** Tuyệt đối không được chỉ tóm tắt bằng text mà quên gắn thẻ `MEDIA:`. Người dùng phản hồi "Hình đâu? Lại vi phạm gate??" là lỗi nghiêm trọng về tuân thủ Gate 6.
- **Tiêu chuẩn ảnh khi gửi:**
  - Chụp màn hình Profile trọn vẹn: hiển thị cả Avatar, Handle `@...`, Tên tiếng Việt có dấu, Bio ngách và hàng đầu tiên của lưới video.
  - Phải chạy `run_winrt_ocr.py` để lấy receipt hợp lệ trước khi gửi kèm tin nhắn.
  - Nếu video chưa có nhãn "Đã ghim", phản ánh trung thực số view thực tế, TUYỆT ĐỐI KHÔNG dùng từ "đã ghim" trong câu báo cáo.
