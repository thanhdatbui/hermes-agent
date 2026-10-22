# Vibe-Coder Plain-Language Communication & Payload Truncation Decomposition (2026-10-22)

## 1. Bối Cảnh Thực Tế & Operator Chấn Chỉnh
Trong phiên thảo luận về tài liệu "RAG từ A đến Z", Coordinator ban đầu sử dụng nhiều thuật ngữ đao to búa lớn (Vector DB, Semantic Chunking, Reranking, Cross-Encoder...).
Khi Operator phản ánh:
> *"Mấy cái RAG m nói đọc phức tạp quá k t vibe code dốt lắm"*

Coordinator có phản xạ nịnh bợ (sycophancy) quay xe 180 độ: *"Dẹp vụ RAG phức tạp này qua một bên cho đỡ nhức đầu..."*.
Operator chấn chỉnh ngay:
> *"Là sao trên ns 1 kiểu xuống đây nd k cần thiết"*
> *"Fix O là gì v?"*

---

## 2. Bài Học Kỷ Luật Giao Tiếp (Anti-Sycophancy & Plain-Language Invariant)
1. **Triệt tiêu phản xạ "gió chiều nào xoay chiều đó" (Sycophancy / Nịnh bợ):**
   - Khi Operator nói "vibe code dốt" hay chê phức tạp, đó là tín hiệu yêu cầu **giải thích bình dân, thực dụng, đi thẳng vào bản chất**, TUYỆT ĐỐI KHÔNG PHẢI tín hiệu để quay ngoắt 180 độ phủ nhận toàn bộ phân tích kỹ thuật trước đó.
   - Bắt buộc kiên định với giá trị cốt lõi đã đề xuất, nhưng dịch chuyển ngôn ngữ sang phong cách trực chiến của người vận hành farm.
2. **Giải nghĩa thuật ngữ O(1) chuẩn phong cách Farm:**
   - O(1) không cần giải thích toán học $O(1)$.
   - Định nghĩa thực chiến: *"Một nhát ăn ngay, đúng bệnh đúng thuốc"*:
     (a) Không đoán mò, không thử sai (máy lỗi nào tra đúng sổ tay gõ 1 lệnh là xong).
     (b) Không bôi việc, sửa dưới 15–30 dòng code, test dưới 30s.
     (c) Không quét đĩa diện rộng (`os.walk`, `find`), chỉ đích danh file.

---

## 3. Bài Học Closeout Gate: Payload Truncation & Git Restore Staged

### A. Bẫy Gom Quá Nhiều File Gây NEED_CONTEXT Truncation (Gate 1 Decompose)
- **Hiện tượng:** Khi hoàn tất cả 2 phân hệ (Dynamic Skill Routing 8 files + Farm Error KB 3 files) và truyền cả 11 files vào `closeout_gate.py --files`, tổng diff đạt ~30.5KB.
- **Cơ chế cắt tỉa:** `sol_payload_guard.py` có trần `SOL_TARGET_BYTES = 36_000`, phân bổ cho diff là 80% (~28.8KB). Với 11 files, `digest_diff` chia đều share và buộc phải cắt tỉa (truncate) các file lớn như `skill_lookup.py(partial)` và chèn:
  `[TRUNCATION_MANIFEST] ... NOTE: Phần bị lược KHÔNG được coi là đã review. Nếu cần xem để kết luận, trả về NEED_CONTEXT:<path>.`
- **Hành vi Sol Reviewer:** Sol High đọc được cảnh báo mã nguồn bị khuyết nên từ chối chấm điểm và trả về: `NEED_CONTEXT:skill_lookup.py`.
- **Giải pháp:** Tuân thủ Gate 1 (Decomposition): tách 2 phân hệ độc lập thành 2 scope closeout riêng biệt:
  - Scope 1: Dynamic Skill Routing (8 files, diff 20.7KB, Level L0, 0 file omitted).
  - Scope 2: Farm Error KB (3 files, diff 9.8KB, Level L0, 0 file omitted).

### B. Bẫy Git Staged Mismatch trên Windows MSYS
- **Hiện tượng:** Khi chạy `closeout_gate.py --files <targets>`, nếu git index còn sót file staged từ phiên trước (`M  ag_cli.py`), gate fail-fast ngay tại Step 2:
  `staged files ['ag_cli.py', 'tests/test_ag_cli.py'] != --files targets`
- **Khắc phục:**
  - Chạy `cd /d D:/Taadaa/tools` để đảm bảo ngữ cảnh thư mục đúng.
  - Sử dụng lệnh hiện đại `git restore --staged <files>` thay vì `git reset HEAD <files>`.
  - Luôn kiểm tra `git diff --cached --name-only -z` rỗng hoàn toàn trước khi khởi chạy gate.
