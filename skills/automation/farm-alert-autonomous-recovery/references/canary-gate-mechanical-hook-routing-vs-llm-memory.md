# Canary Gate: Mechanical Hook Routing vs. LLM Memory Trap

## 1. Bối cảnh & Hiện tượng (The Memory Trap)
- **Vấn đề:** Khi Coordinator/Worker can thiệp sửa code các luồng hook phụ (như `upload-hook`, `follow-hook`, `auto-login recovery`) trong monolith `multi_machine_feed_session.py`, sau đó phát lệnh chạy Canary để kiểm chứng.
- **Bẫy cam kết miệng qua LLM Memory:**
  - Nếu lưu vào `MEMORY` ("Lần sau user bảo chạy canary thì nhớ truyền cờ `--allow-upload-hook`"), LLM sẽ thường xuyên quên, bỏ sót hoặc chạy canary mặc định 2 swipes feed mù.
  - Hậu quả: Canary báo PASSED (Exit Code 0), nhưng thực tế cờ `_allow_upload_hook` = False, tiến trình hoàn toàn **KHÔNG CHẠM VÀO DÒNG CODE VỪA SỬA**. Đây là lỗi kiểm chứng nghiệm thu nghiêm trọng nhất (False-Positive Verification).
- **Quy tắc User:** CẤM TUYỆT ĐỐI dùng `MEMORY` để ghi nhớ cách chạy script hoặc cam kết tuân thủ quy trình kiểm thử. BẮT BUỘC phải cơ giới hóa bằng Gate trong code của runner (`canary_runner.py` / `canary_matrix.json`).

---

## 2. Kiến trúc Cơ Giới Hóa (Mechanical Canary Gate Architecture)

Thay vì trông chờ vào LLM nhớ flag, hệ thống phân tách thành 3 tầng cơ giới hóa:

### A. Ma trận Canary (`canary_matrix.json`)
Ánh xạ các pattern file bị thay đổi (path_globs) sang hook kiểm chứng bắt buộc:
```json
{
  "id": "upload-hook",
  "path_globs": ["*upload*", "**/flows/*upload*", "**/flows/multi_machine_feed_session*"],
  "hook": "upload",
  "scope": "single",
  "ocr": {
    "required_all": [["dành cho bạn", "đang follow", "trang chủ"]],
    "min_chars": 20
  }
}
```

### B. Bộ lập kế hoạch kiểm chứng (`canary_plan.py`)
- Kiểm tra Git diff của repo (`HEAD~1` hoặc uncommitted working tree diff).
- So sánh danh sách file modified với `canary_matrix.json`.
- Trích xuất danh sách `requirements` gồm các hook bắt buộc phải chạy.

### C. Runner tự động định tuyến (`canary_runner.py`)
Khi người vận hành hoặc Agent gọi `canary_runner.py` mà **KHÔNG truyền cờ `--hook`**:
1. Runner tự động gọi `canary_plan.build_canary_plan(repo_dir, DEFAULT_MATRIX)`.
2. Kiểm tra `requirements`: Nếu diff có chạm vào `multi_machine_feed_session.py` hoặc module upload -> tự động xác định `active_hook = "upload"`.
3. Tự động gắn cờ tương ứng vào lệnh thực thi trên thiết bị:
   ```python
   if active_hook and "upload" in str(active_hook).lower():
       cmd.append("--allow-upload-hook")
   ```
4. In cảnh báo rõ ràng ra console:
   ```text
   [CANARY_GATE] Auto-detected hook 'upload' from git diff requirements
   ```

---

## 3. Quy chuẩn Kiểm Thử Hook Phụ trên Monolith
1. **Không chạy Canary mù:** Mỗi lần sửa hook phụ (Upload, Follow, Switcher, Login Recovery), diff phải được kiểm tra xem hook tương ứng có thực sự được kích hoạt không.
2. **Đối soát file kết quả:**
   - Upload hook: Bắt buộc kiểm tra `upload_result.json` trong thư mục run artifact của máy.
   - Follow hook: Bắt buộc kiểm tra `follow_result.json`.
3. **Cơ chế Shift Upload Ledger:** Lưu ý `shift_upload_history.json` có thể trả về `already_uploaded_in_shift` nếu máy đã hoàn thành quota upload trong ngày. Đây là hành vi hợp lệ của cơ chế an toàn, không phải lỗi crash.
