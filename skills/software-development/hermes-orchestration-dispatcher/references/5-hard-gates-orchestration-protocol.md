# 5 Hard Gates Orchestration Protocol (Anti-Insanity Loop & Monolith Protection)

Tài liệu này chuẩn hoá và khắc phục triệt để lỗi điều phối Coordinator từng xảy ra tại Taadaa Phone Farm (2026-09-11):
- Giao "goal mở" vào file monolith (8.800+ dòng) với ngân sách 15 iterations.
- Worker cạn 15 iterations với 0 files modified (thất bại cấu trúc) nhưng Coordinator lại retry y hệt prompt cũ.
- Gộp hai task khác bản chất (Code surgery vài phút vs Batch render hàng giờ) vào cùng một batch.

---

## 5 GATE BẮT BUỘC TRƯỚC VÀ TRONG KHI DISPATCH WORKER

### GATE 1 — DECOMPOSE TRƯỚC DISPATCH (Chống gộp task sai vòng đời)
- **Quy tắc**: Khi yêu cầu của user chứa từ nối (`và`, `+`, `rồi`, `sau đó`):
  - BẮT BUỘC phân rã thành các sub-tasks riêng biệt.
  - Phân loại rõ:
    * **Code-surgery**: Sửa bug, thêm hook, patch logic (thực thi vài phút, 1 worker + Patch Contract).
    * **Batch-job / Render**: Kéo video, render hàng loạt, migration diện rộng (thực thi hàng giờ, I/O-bound).
  - **CẤM TUYỆT ĐỐI** nhét Code-surgery và Batch-job vào cùng một đợt dispatch song song `delegate_task(tasks=[...])`.

### GATE 2 — FEASIBILITY CHECK & MANDATORY PATCH CONTRACT (Chống goal mở trên monolith)
- **Quy tắc**:
  ```python
  IF target_file_loc > 1500 AND task_type == "modify":
      REQUIRE patch_contract với anchor grep -c == 1
      FORBID goal mở (từ khoá cấm: "tự tìm", "tự phân tích", "tìm hiểu", "khám phá")
  IF không có anchor đã verify:
      BLOCK dispatch → Coordinator phải tự inspect O(1) trong session chính trước
  ```
- **Patch Contract Artifact chuẩn**:
  * File path tuyệt đối.
  * Anchor string độc nhất (`grep -c == 1`).
  * Đoạn code thay thế chính xác (old_string → new_string).
  * Scope lock: Cấm sửa ngoài anchor, cấm refactor.
  * Test contract rõ ràng (<30s).

### GATE 3 — CIRCUIT BREAKER (Chống Insanity Loop)
- **Quy tắc**:
  * Khi worker trả về: `files_modified == 0` VÀ `iterations_exhausted == True` (hoặc timeout/max budget):
    $\rightarrow$ **ĐÂY LÀ THẤT BẠI CẤU TRÚC (STRUCTURAL FAILURE), KHÔNG PHẢI THẤT BẠI NGẪU NHIÊN.**
  * **CẤM TUYỆT ĐỐI** re-dispatch với prompt cũ hoặc lặp lại cùng scope.
  * BẮT BUỘC:
    1. Dừng lại, đọc tín hiệu từ kết quả worker.
    2. Thu hẹp scope hơn nữa HOẶC dán trực tiếp code anchor vào prompt HOẶC tách nhỏ thành micro-task.
    3. Số lần dispatch cùng một sub-task tối đa là 2. Nếu lần 2 vẫn không đổi $\rightarrow$ báo cáo user ngay.

### GATE 4 — WORKER FAIL-FAST PROTOCOL
- Inject vào context/prompt của mọi worker:
  > "NẾU trong ≤3 iterations đầu, bạn xác định scope quá rộng hoặc bất khả thi với ngân sách 15 calls:
  > DỪNG NGAY. CẤM đốt hết 15 iterations để mò file.
  > Trả về ngay: `{status: 'ABORT_SCOPE', anchor_found: <file:line>, proposed_contract: <đề xuất thu hẹp>}`."

### GATE 5 — COORDINATOR SELF-CHECK (Checklist 5 điểm trước khi gọi `delegate_task`)
1. [ ] Task này đã được phân rã tới đơn vị không-thể-chia-nhỏ-hơn chưa?
2. [ ] File target > 1.500 dòng? Đã có Patch Contract với anchor `grep -c == 1` chưa?
3. [ ] Ngân sách (15 iters) có khả thi về mặt vật lý cho scope này không?
4. [ ] Đây là code-surgery hay batch-job hàng giờ? (Batch job không bao giờ giao leaf worker ngồi chờ).
5. [ ] Nếu là re-dispatch: Contract/Scope có KHÁC và HẸP HƠN lần trước không?
