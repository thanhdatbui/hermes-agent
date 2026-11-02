# Unified Patch Pipeline: Council Votes Invariant & Session Scope Grounding

## 1. Bản Chất Sự Cố Kỹ Thuật (Pipeline Output Bug)
- **Vấn đề**: `gate_b_planner.py` khi lập plan (Stage S1) đã gọi Hội đồng Cố vấn (Council: Argon, Claude Sonnet, Sol) và ghi nhận đầy đủ chi tiết vào `plan.json`:
  ```json
  {
    "planner": "Council (Argon: OK, Claude Sonnet: OK, Sol: OK -> ĐỒNG THUẬN 3/3...)",
    "consensus_summary": "Argon: OK, Claude Sonnet: OK, Sol: OK -> ĐỒNG THUẬN 3/3...",
    "council_details": {
      "gemini": {"status": "OK", "latency": 10.7, "edits_count": 1},
      "claude": {"status": "OK", "latency": 10.7, "edits_count": 1},
      "sol": {"status": "OK", "latency": 43.0, "edits_count": 1}
    }
  }
  ```
- **Nguyên nhân code bị thiếu**: Hàm `_print_report` trong `unified_patch_pipeline.py` đã viết sẵn logic render bảng `COUNCIL VOTES:`, nhưng ở dòng ~1612 (lời gọi `_print_report` tại stage S5 Hold Awaiting User), lập trình viên quên truyền tham số `council_details=plan_data.get('council_details')`. Do đó tham số này nhận giá trị `None`, console nuốt mất bảng biểu quyết.
- **Khắc phục**: Đã vá qua pipeline run `4dfc73f6` (bổ sung tham số `council_details` tại dòng 1620), vượt qua kiểm thử cú pháp S3 và đạt thẩm định Closeout Gate APPROVED.

---

## 2. Kỷ Luật Session Scope Grounding (Chống Bị Lạc Đề & Lảm Nhảm)
- **Hiện tượng**: Khi User chất vấn "Sao m trả kết quả k có?", Coordinator bị panic và lạm dụng `session_search` quét toàn bộ lịch sử trò chuyện cross-session, lôi hàng loạt sự cố không liên quan (sập Gateway sáng 02/11, xung đột code C vs D, avatar hallucination kho 394, alert máy 223/28) ra giải trình thay vì tập trung vào câu hỏi của User.
- **Hậu quả**: Khiến User vô cùng ức chế vì "nói nhảm và không biết session đang làm cái gì".
- **Quy tắc thực thi**:
  1. Khi nhận câu hỏi về task đang làm hoặc lỗi vừa xảy ra trong phiên, **LUÔN kiểm tra ngữ cảnh session hiện tại trước tiên**.
  2. Tra cứu trực tiếp state của pipeline gần nhất tại `D:/Taadaa/runs/<run_id>/state.json` và `plan.json`.
  3. Tuyệt đối không đem các vấn đề cũ đã giải quyết ở các session khác ra bao biện hoặc phân bua khi User không hề hỏi đến.
