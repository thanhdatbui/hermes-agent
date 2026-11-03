---
name: gate6-canary-atomic-evidence-discipline
description: Kỷ luật Gate 6 Canary phát thẻ MEDIA tức thời (Atomic Emission), chống cạm bẫy trì hoãn giao ảnh (Deferred Delivery Trap) và cháy turn.
version: 1.0.0
---
# Gate 6 Canary Atomic Evidence Discipline & Anti-Deferred-Delivery Protocol

> **Bối cảnh ghi nhận:** Sự cố ngày 03/11/2026 trên cụm Farm Admin (Canary M208), được Hội đồng Cố vấn (Sol + Gemini Web + Claude) điều tra và thống nhất chốt chặn $O(1)$.

## 1. Bản Chất Lỗi Sụp Đổ Kiến Trúc (Architectural Failure)
- **Hiện tượng:** 
  - Ảnh hiện trường đã chụp và lưu thành công xuống đĩa cứng, WinRT OCR đã đọc và xác nhận `VALID`.
  - Nhưng trong câu trả lời cuối cùng gửi cho User, Coordinator chỉ xuất toàn text tóm tắt mà **thiếu thẻ `MEDIA:<path>`**.
- **Hai mắt xích sai lầm cốt lõi:**
  1. **Anti-pattern Trì hoãn bàn giao (Deferred Reporting Trap):** Chụp ảnh ở các bước nhưng không emit ngay thẻ `MEDIA:` mà giữ trong đĩa cứng để "chờ cuối lượt tổng kết rồi gửi một thể". Điều này tạo ra độ trễ bàn giao (delivery lag) nguy hiểm.
  2. **Cạn kiệt ngân sách lượt do Scope Creep (Turn Exhaustion):** Coordinator tiện tay đi soi thêm 5 máy khác (M253, M265, M268, M270, M272), đốt sạch ~30 lượt gọi tool. Khi chạm trần platform (`Tool-calling iterations limit reached`), harness platform ép tóm tắt khẩn cấp -> LLM rơi vào trạng thái Emergency Wrap-up, tự động lược bỏ các meta-tag kỹ thuật (`MEDIA:`), khiến bằng chứng bị chôn vùi trên đĩa.

## 2. Ba Chốt Chặn Cơ Học O(1) Triệt Tiêu Lỗi (Không Over-engineer, Không Bại Liệt)

### Chốt chặn 1: Atomic Emission (MAX BLIND STEPS = 1 — Chụp đâu phát đó)
- Tuyệt đối tuân thủ nguyên tắc `MAX BLIND STEPS = 1`: Thao tác UI nào sinh ảnh (Mở app / Switcher / Chọn nick / Lướt feed), ngay tại turn đó **BẮT BUỘC PHẢI XUẤT NGAY THẺ `MEDIA:<path>`** kèm kết quả WinRT OCR thực tế.
- **CẤM TUYỆT ĐỐI** gom ảnh lại lưu tạm trên đĩa để chờ turn sau mới báo cáo.

### Chốt chặn 2: Tự Động Hóa Output Binding Trong Runner (Stdout-Embedded Evidence)
- Trong các script canary (`canary_runner.py` / `inspect_machine.py`), khi tool thực hiện chụp ảnh và kiểm định WinRT OCR pass, script **tự động print trực tiếp dòng `MEDIA:<path_anh_that>` ra stdout**.
- Khi stdout trả về, thẻ `MEDIA:` đã nằm sẵn trong luồng dữ liệu chuẩn của hệ thống, loại trừ 100% rủi ro LLM "quên", "sót", hay bị platform ngắt turn khẩn cấp.

### Chốt chặn 3: Khóa Cứng Ngân Sách Canary (Budget Cap <= 5 Calls)
- Một ca Canary máy thật chỉ được phép tiêu tốn tối đa **5 tool calls**:
  `1. Inspect (1) -> 2. Action/Trigger (1) -> 3. Screencap (1) -> 4. WinRT OCR (1) -> 5. Emit MEDIA (1)`.
- CẤM TIỆN TAY kiểm tra hoặc can thiệp các máy khác ngoài thiết bị canary được chỉ định trong cùng một phiên.

---

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
