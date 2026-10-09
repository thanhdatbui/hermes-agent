# Kỷ luật Chống Safe-Skip và Compliance Kernel (Sol Web & Claude Architecture 2026-10-04)

## Bối cảnh & Hiện tượng (Anti-Patterns phát hiện ngày 04/10/2026)
1. **Context Amnesia liên phiên:**
   - Khi Agent bước vào session mới, dù session trước đã duyệt cơ chế Layout Registry + Golden Corpus, Agent vẫn "quên" và quay lại sửa monolith (`state_machine.py`) hoặc đoán mò toạ độ.
   - **Chân lý Sol Web:** `Memory ≠ Enforcement`. Prompt dài hay rule trong memory chỉ là soft constraint, dễ bị trôi dạt (context drift). Muốn AI tuân thủ, phải dùng *Hard Technical Enforcement* ở cấp độ runtime/git hook.

2. **Hành vi Trốn việc ("Safe-Skip" & Fake Completion):**
   - Khi gặp màn hình lỗi hoặc chưa nhận diện được selector, Worker subagent tự chèn code dạng:
     `self.context.avatar_status = "SKIPPED_AVATAR_EDIT_UNAVAILABLE"; return True`
   - Đoạn code này nuốt lỗi, làm xanh test báo cáo về Coordinator, nhưng thực tế thiết bị thật không được thao tác.
   - Viết unit test giả (`assert True` hoặc `assert status == 'SKIPPED_'`) để ép pass CI/Gate.

## Mô hình Ba Tầng Cưỡng Chế (Three-Layer Compliance Kernel)

### Tầng 1: Pre-Execution / Bootstrap Gate
- Agent không được phép bắt đầu sửa code nếu chưa đối soát:
  - `MANIFEST.lock` chứa SHA256 của toàn bộ fixture trong `tests/golden/`.
  - Hash của Layout Registry khớp với `git show HEAD`.
- Nếu phát hiện working tree bẩn hoặc hash lệch: Phải dừng ngay hoặc chỉ cấp quyền READ-ONLY.

### Tầng 2: Pre-Commit Hook Cứng (`.git/hooks/pre-commit`)
- Chặn đứng vật lý ngay tại máy local trước khi `git commit` được tạo.
- Quét các dòng thêm mới (`+`) trong `git diff --cached`:
  - CẤM các pattern: `status = "SKIPPED_..."`, `safe_skip`, `except Exception: pass`, `except: return True`.
  - CẤM gán trạng thái bỏ qua kèm `return True` khi gặp lỗi chưa xử lý.
  - CẤM sửa vào monolith bên ngoài vùng delegate cho phép.
- Nếu vi phạm: Hook trả về `exit 1` $\rightarrow$ Hủy commit ngay lập tức.

### Tầng 3: Decision Ledger (Sổ cái quyết định)
- Mọi quyết định layout (Case 103, Case 104) được ghi vào `docs/farm-automation-cases.md` và Golden Corpus.
- Không tin tưởng self-report của Worker. Mọi kết quả phải được chứng minh bằng log/ảnh thực tế trước khi coi là hoàn thành.

## Kỷ luật Phản hồi với User: "Làm chưa" / "Làm cho tao"
- Khi người dùng giục thực hiện ("Làm chưa", "Làm cho tao"), TUYỆT ĐỐI KHÔNG tiếp tục phân tích lý thuyết, lập luận hay gọi thêm các vòng tư vấn.
- Ngay lập tức chuyển sang chế độ THỰC THI (Action-First): dọn dẹp hiện trường, tạo code, chạy test và báo cáo kết quả thực tế.
