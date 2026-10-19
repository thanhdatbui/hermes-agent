# Benchmark Đối Đầu & Quy Hoạch Định Tuyến: Gemini 3.8 Flash (Medium vs High) & Claude Haiku

## 1. Kết Quả Benchmark 10 Hiệp (Thực Chiến Trên Dàn 22 Profile AGY CLI)

### Tổng quan số liệu:
- **Gemini 3.8 Flash Medium (AGY CLI):**
  - Tỷ lệ hoàn thành: **10/10 (100% AST Valid)**.
  - Tốc độ trung bình: ~225s (~3.7 phút/bài).
  - Quy mô code trung bình: ~20.400 chars (~450 dòng).
  - Độ ổn định: Zero timeout (ở trần 600s), zero dính lỗi tràn token cụt đuôi.
- **Gemini 3.8 Flash High (AGY CLI):**
  - Tỷ lệ hoàn thành: **7/10 (70% AST Valid)**.
  - Tốc độ trung bình: ~323s (~5.4 phút/bài).
  - Quy mô code trung bình: ~25.600 chars (~600 dòng), hiệp 10 lên tới 34.5k chars.
  - Nhược điểm: Bị văng timeout (H4, H7) nếu để timeout mặc định 600s (cần nâng lên 1200s); dễ bị tràn token stream dẫn đến dính SyntaxError cuối file (H6 - 38.8k chars).

## 2. Quy Tắc Phân Vai (Role Architecture Contract)

Tuân thủ nghiêm ngặt chỉ thị kiến trúc của User: **"Case khó dùng Claude plan kĩ rồi phân rã task ra code, cấm nhồi code lớn. Dùng Medium làm Worker."**

1. **Claude CLI (Architect / Planner / Reviewer):**
   - **Vai trò:** Lập kế hoạch, phân rã kiến trúc phức tạp thành các sub-task $O(1)$ (<= 2 files, <= 30 dòng diff, 1 focused test <30s) theo Gate 1 & Gate 2.
   - **Giám định chất lượng (Senior Code Judge):** Khắt khe về xử lý lỗi OS Windows (mã lỗi NT 5, 32, 33, 170), phân lập vị trí retry (chỉ retry `os.replace` thay vì lặp lại toàn bộ I/O ghi đĩa), kiểm tra unit test đa luồng.
2. **Gemini 3.8 Flash Medium (Primary Implementation Worker):**
   - **Vai trò:** Thợ thi công chính (Workhorse) cho toàn bộ task sửa bug, viết test, patch repo Farm.
   - **Lý do chọn:** Tỷ lệ pass 100%, tốc độ nhanh gấp đôi High, độ dài code vừa vặn không lo cụt đuôi, tuân thủ kỷ luật phân rã $O(1)$.
3. **Gemini 3.8 Flash High (Core Library / Algorithm Specialist):**
   - **Vai trò:** Chỉ huy động khi cần thiết kế module thuật toán mới toanh (Binary parsing, Complex Multi-Strategy Jitter, Matrix DCT).
   - **Bắt buộc:** Timeout cấu hình $\ge 1200s$, prompt phải kẹp ràng buộc độ dài để chống tràn token trần.
