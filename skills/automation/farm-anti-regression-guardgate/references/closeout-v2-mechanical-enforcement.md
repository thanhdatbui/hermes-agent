# Closeout v2 Mechanical Enforcement & Zero-Score-Chasing Invariant

## 1. Bãi Bỏ Đánh Giá Cảm Tính & Thang Điểm >= 85
- Cơ chế Reviewer LLM chấm điểm cảm tính `>= 85/100` đã chính thức bị **KHAI TỬ 100%**.
- Coordinator tuyệt đối **CẤM** nhắc lại thang điểm 85, cấm đòi điểm reviewer, và cấm in báo cáo chứa "Verdict: APPROVED (Score >= 85)".
- **Đồng bộ triệt để trên toàn bộ System Rules & Prompts**: Khi user nhắc nhở bỏ thang điểm 85, phải rà soát và gỡ sạch mọi câu chữ liên quan trong `SOUL.md`, `AGENTS.md`, `PROJECT_RULES.md`, không để sót quán tính nhắc lại ở bất kỳ báo cáo closeout nào.
- **Quy tắc phản hồi khi nhận lệnh chốt phiên (`done` / `chốt phiên`)**: Báo cáo chỉ tập trung vào: (1) Kết quả thẩm định máy `closeout_v2.py` (Exit code 0, GuardGate invariants PASS, Pytest PASS), (2) Commit SHA & remote push status, (3) Tóm tắt 2-3 gạch đầu dòng tính năng hoàn tất. Tuyệt đối không chèn bảng điểm scorecard hay câu chữ Reviewer $\ge 85$.

## 2. Quy Chuẩn Người Gác Cổng Duy Nhất (`closeout_v2.py`)
Closeout Gate hiện tại là bộ lọc cơ giới hóa $O(1)$ thuần túy:
1. **`GuardGate` (`rules.json`)**: Quét diff tĩnh $O(1)$ kiểm tra bất biến và bắt buộc comment định danh bước (`# Bước X: ...` / `# Step X: ...`) trên các khối code mới $\ge 15$ dòng (`case_invariant_require_step_by_step_structure`).
2. **`Pytest Suite`**: Chạy toàn bộ unit test tập trung liên quan đảm bảo logic pass 100%.
3. **Thẩm định tự động**: Khi đạt cả 2 điều kiện $\rightarrow$ Exit Code 0 (`APPROVED 100/100`), tự động ghi nhận audit log để pre-push hook cho phép đẩy thẳng lên Git remote.

## 3. Kỷ Luật Dọn Dẹp Hiện Trường (Zero Artifacts & Memory Hygiene)
- Sau khi commit/push thành công:
  - BẮT BUỘC xóa sạch các file tạm trung gian (`.patch`, `.json`, `.tmp`) qua `python D:/Taadaa/tools/safe_recycle.py`.
  - **Kỷ luật Memory khi User bảo "dọn dẹp"**: Khi user ra lệnh dọn dẹp hiện trường / dọn sạch vết, hành động đúng là dọn các file tạm, dọn workspace và dọn các dòng thừa/sai trong config/SOUL.md; **CẤM TUYỆT ĐỐI tự ý đẻ thêm entry persistent memory mới** (dùng `memory(action='add')`) làm rác bộ nhớ dài hạn.
