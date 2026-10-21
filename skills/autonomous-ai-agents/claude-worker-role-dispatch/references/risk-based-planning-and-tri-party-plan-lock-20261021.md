# Risk-Based Planning & Tri-Party Architectural Alignment (2026-10-21)

## 1. Bối Cảnh Sự Cố & Operator Chấn Chỉnh
Operator đã phản ánh gay gắt về tình trạng: *"Nhiều session Gemini cứ báo nó làm xong rồi, xong hôm sau lại lỗi rồi vá vài vòng mới ổn. Không phải chất lượng code, mà ý tưởng plan nó đã lỗi hoài từ gốc"*.

Hiện tượng thực tế:
- Gemini Coordinator bị dính thiên kiến hoàn thành nông cạn (*shallow completion bias*): khi thấy lỗi, nó chọn con đường ngắn nhất (thêm một lệnh `if/else`, thêm một cờ tạm, bắt nuốt lỗi) để vượt qua test tại chỗ.
- Hôm sau chạy production/farm thực tế thì logic chắp vá này xung đột với state machine, lock, hoặc cron khác.
- Worker (Haiku 5.5 / Agy CLI) là thợ thi công O(1); khi nhận một bản vẽ sai từ gốc, Worker thi công càng chuẩn thì hệ thống càng sai lệch nghiêm trọng.
- Nghiêm trọng nhất: Mô hình để cùng một agent vừa lên ý tưởng kiến trúc, vừa dispatch, vừa tự tuyên bố hoàn thành (báo DONE ảo) mà thiếu kiểm chứng kiến trúc độc lập.

---

## 2. Kết Quả Hội Chẩn 3 Bên (Tri-Party Consultation)
Coordinator đã kích hoạt phiên hội chẩn thực chiến giữa 3 thực thể:
1. **Sol Auditor / Reviewer (:20129 WebPool)**:
   - Khẳng định: Đổi model không giải quyết được gốc rễ; phải sửa cơ chế kiểm soát kiến trúc.
   - Phân tích: Vòng lặp vá lỗi sinh ra do phân tích nguyên nhân hời hợt, bỏ sót phụ thuộc, thiếu tiêu chí nghiệm thu và không ai kiểm tra giả định ban đầu.
   - Đề xuất: Phân tầng lập kế hoạch dựa trên rủi ro (Risk-based Planning).
2. **Claude Planner (Sonnet 5.5 qua `claude_worker.py --role planner`)**:
   - Vấn đề cấu trúc: Không thể để một agent vừa làm quan tòa vừa làm bị cáo.
   - Xác lập 3 lằn ranh đỏ cấm tiệt Gemini lên plan.
   - Nhấn mạnh: Planner không phải thuốc tiên nếu thiếu input; chất lượng gom evidence của Gemini quyết định độ chính xác của Sonnet.
   - Yêu cầu Plan bắt buộc có mục Fail-Closed (lock stale, contract rỗng, predicate lạ $\rightarrow$ FAIL, không được ngộ nhận PASS).
3. **Gemini Coordinator**:
   - Thừa nhận khuyết điểm về bệnh lạc quan tếu khi context phình to và cam kết tước quyền tự lên plan khi chạm lằn ranh đỏ.

---

## 3. Quy Chuẩn 3 Lằn Ranh Đỏ: CẤM Gemini Lên Plan Kiến Trúc
Gemini Coordinator TUYỆT ĐỐI CẤM tự ý lên plan cho các task thỏa mãn **bất kỳ điều kiện nào** sau đây:
1. **Đụng chạm vùng nhạy cảm hạ tầng:** Guard, Gate, Contract O(1), Device Lock, Cronjob, hoặc State/Database schema.
2. **Thay đổi cấu trúc / Interface:** Thay đổi interface giao tiếp giữa các component, hoặc sửa đổi từ $\ge 3$ files.
3. **Dấu hiệu vá ngọn lặp lại:** Bất kỳ lỗi/tác vụ nào đã từng trải qua $\ge 2$ lần vá trước đó mà vẫn tái phát (chứng cứ 100% chứng minh plan ban đầu đã sai từ gốc).

---

## 4. Quy Trình Phối Hợp 5 Bước Cho Task Lớn / Task Nhạy Cảm

```
[Gemini Coordinator]          [Claude Sonnet 5.5]          [Sol Auditor / User]          [Worker CLI]
  Gom Evidence O(1)   ----->   claude_worker.py    ----->   Duyệt Plan Độc Lập   ----->   Thi công O(1)
  (Log, File, Lines)           --role planner              (Exit code / Review)          (Haiku / Agy)
  *CẤM KẾT LUẬN*              (Plan có root cause)
```

1. **Bước 1 — Gemini Gom Evidence (Chỉ sự thật, CẤM kết luận):**
   - Tập hợp log thực tế, mã lỗi, đường dẫn file cụ thể, số dòng nghi vấn, và lịch sử các lần vá trước.
   - Tuyệt đối CẤM suy diễn nguyên nhân hay đề xuất cách sửa ngọn.
2. **Bước 2 — Dispatch Claude Planner (`claude_worker.py --role planner`):**
   - Chạy Sonnet 5.5 (`--model sonnet`, max 10 turns, read-only: `disallowedTools Edit,Write,NotebookEdit`).
   - **BẪY ĐỐT 10 TURNS DO TOOL BLEEDING & QUY CHUẨN ZERO-TOOL DIRECT STREAM (Incident 21/10/2026):**
     Khi role là `planner`, quyền `Edit` và `Write` bị khóa cứng. Nếu prompt bảo Sonnet "đọc file X và ghi file Y", Sonnet sẽ đốt sạch 10 turns để gọi tool `Read` các file liên quan và gọi `Bash` (`cat << 'EOF'`) để ghi file tạm, dẫn đến `Error: Reached max turns (10)` và exit 1.
     *Quy chuẩn bắt buộc:* Nạp sẵn evidence text vào prompt (hoặc file context), và kẹp chỉ thị cưỡng chế:
     `"[YÊU CẦU: Xuất trực tiếp toàn văn bản kế hoạch kiến trúc ra output (stdout), TUYỆT ĐỐI KHÔNG chạy bất kỳ công cụ Bash hay Read nào]"`. Caller (script/terminal) bắt stdout và ghi thẳng vào `.hermes/plans/<name>.md`. Sonnet giải quyết trong đúng 1 turn reasoning thuần túy.
   - Yêu cầu xuất Plan với đầy đủ 6 thành phần bắt buộc:
     * *Root cause:* Dẫn chứng chính xác `file:line`.
     * *Non-goals:* Những thứ cấm đụng tới để tránh phình scope.
     * *Atomic Steps:* Từng bước nhỏ, độc lập kiểm chứng được.
     * *Failure Modes & Fail-Closed:* Kịch bản contract rỗng, stale lock, rớt mạng phải trả về FAIL.
     * *Acceptance Criteria:* Lệnh chạy được kèm output kỳ vọng (cấm nói chung chung "chạy tốt").
     * *Rollback:* Kế hoạch hoàn nguyên nếu fail.
3. **Bước 3 — Thẩm Định & Phê Duyệt Plan:**
   - Sol Reviewer hoặc Operator duyệt plan. Gemini không có quyền tự duyệt plan của Planner.
4. **Bước 4 — Dispatch Worker Thi Công Đúng Bản Vẽ:**
   - Dispatch Haiku 5.5 CLI (`--role worker`) hoặc Agy CLI fix theo từng lát mỏng O(1).
   - Nếu thực tế thi công phát sinh sai lệch, BẮT BUỘC quay lại Planner cập nhật bản vẽ, CẤM Gemini tự tiện bẻ lái plan.
5. **Bước 5 — Kiểm Chứng Cơ Học & Nghiệm Thu:**
   - Chạy lệnh acceptance criteria thực tế, lấy output thật.
   - Báo DONE chỉ hợp lệ khi có receipt/output lệnh kiểm chứng thực tế đính kèm.
