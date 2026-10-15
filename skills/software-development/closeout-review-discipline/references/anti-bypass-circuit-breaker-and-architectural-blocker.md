# Kỷ Luật Chống Vòng Lặp Bại Não, Bẫy Điểm Sol và Cấm Tuyệt Đối Bypass Hook

## 1. Cấm Tuyệt Đối Bypass Pre-Push Hook (`--no-verify`)
- **Nguyên tắc bất biến:** `pre-push` hook và `Closeout Gate` (APPROVED >= 85) là **Hard Invariant tối cao** của farm Taadaa.
- **Cấm tự ý luồn cờ:** CẤM TUYỆT ĐỐI Coordinator tự ý truyền `--no-verify` vào `safe_push.py` hoặc `git push`.
- **Phân biệt câu hỏi bức xúc vs chỉ thị:**
  - Khi User nói: *"sao không push luôn đi"*, *"push luôn đi khỏi qua sol nữa"*: Đây là tín hiệu bức xúc vì vòng lặp kéo dài, **KHÔNG PHẢI chỉ thị hợp lệ để bypass Hard Invariant**.
  - Coordinator BẮT BUỘC phản hồi trung thực: Giải thích rõ lý do Gate chưa pass (điểm số, blocker), đưa ra các lựa chọn cụ thể, và tuyệt đối không tự ý bẻ khóa an toàn.
  - Nếu User kiên quyết muốn push thủ công bỏ qua gate, Coordinator phải báo cáo rõ ràng và để User tự quyết định hoặc xác nhận ngoại lệ có lưu vết audit log.

## 2. Circuit Breaker Cho Closeout Gate (Chống Chạy Theo Điểm Số)
- **Bẫy chi phí chìm (Sunk Cost Fallacy):** Cứ sau mỗi vòng sửa vụn vặt, Coordinator lại tưởng lầm "sắp tới 85 rồi" (72 -> 52 -> 62 -> 72 -> 82). Điểm số nhích nhẹ chỉ là nhiễu ngẫu nhiên của LLM judge, không phản ánh chất lượng thực.
- **Quy tắc dừng cứng (Hard Stop):**
  1. **Strike 3 Scope Frozen:** Cùng một `scope_hash` bị từ chối 3 lần liên tiếp -> BẮT BUỘC DỪNG NGAY mọi hành động retry/amend.
  2. **Score Plateau:** Khi 2 lần liên tiếp mức tăng điểm $\Delta < 3$ điểm (hoặc giảm điểm) -> Đánh giá ngay là bẫy hội tụ giả, DỪNG VÒNG LẶP.
  3. **Không quá 20 phút cho closeout:** Nếu việc đóng phiên kéo dài quá 20 phút mà chưa đạt APPROVED, BẮT BUỘC dừng lại, xuất báo cáo hiện trường và xin chỉ thị User.

## 3. Nhận Diện Sớm Architectural Blocker (Chống Sửa Ngọn)
- **Dấu hiệu nhận biết:**
  - Điểm `code_architecture < 7/10` trên scorecard của Sol.
  - Findings nhắc đến: `DRY`, `duplication`, `copy-paste`, `monolith`, `trùng lặp code` (ví dụ giữa file `scripts/` và `scripts/hermes_cron/`).
- **Hành vi cấm:**
  - CẤM TUYỆT ĐỐI sửa vi mô (microsecond, whitespace, đổi comment đối phó, viết thêm hàng loạt test phụ cho 1 hàm utility).
- **Hành vi bắt buộc:**
  - Gắn nhãn ngay `[ARCHITECTURAL_BLOCKER]`.
  - Dừng can thiệp T1 micro-fix.
  - Đề xuất dứt điểm: Tách shared module (ví dụ đưa helper vào `scripts/watchdog/`) HOẶC báo cáo User để xin chủ trương chấp nhận nợ kỹ thuật (nếu task khẩn cấp).
