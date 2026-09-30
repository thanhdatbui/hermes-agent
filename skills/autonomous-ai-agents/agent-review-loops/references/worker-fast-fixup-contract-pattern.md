# Worker Fast Fix-up Contract Pattern (Claude CLI Architecture)

## 1. Bối cảnh & Nguyên tắc cốt lõi
Khi chạy Closeout Gate chốt phiên (`closeout_gate.py`), nếu Reviewer (Sol Auditor `:20129`) trả về điểm `< 85` hoặc `REJECTED`:
- **CẤM TUYỆT ĐỐI Coordinator (session chính) tự tay sửa code hay viết test.**
- Kể cả khi trượt nhẹ (80–84 điểm) và diff chỉ 10–20 dòng (thêm test nhánh mới, siết selector, thêm telemetry log), Coordinator cũng không được tự sửa.

## 2. Lý do kiến trúc (theo phản biện Claude CLI v2.1)
1. **Bảo vệ Context Coordinator:** Coordinator phải giữ sạch context để điều phối, giám sát timeout và bắt sự kiện. Việc nạp test suite, traceback, XML dump để sửa code làm phình context cực nhanh, gây nghẽn gateway loop và lag phiên.
2. **Chống trượt dốc cao bồi (Slippery Slope):** Cho phép sửa 10 dòng hôm nay sẽ dẫn đến sửa 30-50 dòng ngày mai. Tác tử sẽ liên tục tìm lý do ngoại lệ để bỏ qua phân vai.
3. **Độc lập thẩm định:** Người điều phối không thể vừa sửa vừa quyết định chốt phiên (tự sửa tự chấm).

## 3. Quy trình thực thi Fast Fix-up O(1)
1. **Trích xuất Contract từ Gate:** `closeout_gate.py` khi fail tự động kết xuất khối `WORKER FAST FIX-UP CONTRACT (CLAUDE-CLI SPEC)` gồm:
   - `Target files`: Danh sách file cần sửa.
   - `Findings to remediate`: Toàn bộ `key_findings` của Sol Reviewer.
   - `Judge notes`: Nhận xét và rủi ro cần khắc phục.
2. **Dispatch Worker qua `delegate_task`:** Coordinator chuyển nguyên văn contract này cho Worker (Luna High / subagent) với các ràng buộc:
   - Budget: Diff <= 30 dòng.
   - Verification: Chạy focused test < 30s pass.
   - Commit: `git commit -a --amend --no-edit` để gộp vào HEAD commit duy nhất (tránh lỗi audit binding).
   - Timeout: <= 3 phút.
3. **Tái thẩm định:** Sau khi Worker hoàn tất, Coordinator chạy lại `closeout_gate.py` để chấm lại toàn bộ diff cuối.
4. **Trần vòng lặp:** Tối đa 2 vòng fix-up. Nếu qua 2 vòng vẫn < 85 điểm: dừng ngay, giải phóng sạch device lock / lease, chuyển sang L3 BLOCKED kèm bằng chứng báo User.
