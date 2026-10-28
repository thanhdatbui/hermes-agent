# Canary Gate Auto-Wiring vs Memory Enforcement Fallacy (28/10/2026)

## 1. Bối Cảnh & Sự Cố Trực Tiếp Từ Operator
Trong phiên làm việc ngày 28/10/2026 khi xử lý lỗi máy thiếu nick không tự động auto-login recovery trong luồng `upload-hook` của repo `tiktok-luot nuoi acc`:
1. **Ảo Tưởng Tuân Thủ Bằng Memory (Memory Enforcement Fallacy):**
   - Coordinator sau khi sửa code đã cố gắng ghi nhớ vào `MEMORY.md`: "Khi user yêu cầu chạy canary sau khi sửa upload-hook bắt buộc phải truyền cờ `--allow-upload-hook`".
   - Operator (Sếp) chấn chỉnh gay gắt:
     *"đéo dùng memory nhé, dùng memory mày đéo bh tuân thủ"*
     *"k thiết kế trong script ddc à, có gate canary k?"*
   - Bản chất: LLM Memory là "cam kết miệng" mềm (soft), rất dễ bị trôi context, bị nén hoặc bị bỏ qua khi phát lệnh CLI. Ép hành vi runtime qua Memory là sai lầm kiến trúc cơ bản.

2. **Kẽ Hở Trong Canary Gate Cũ:**
   - `canary_matrix.json` chỉ có rule cho `account-switcher` và `feed-swipe`, hoàn toàn thiếu rule cho `upload-hook`.
   - Kết quả: Khi diff sửa `multi_machine_feed_session.py`, `canary_plan.py` rơi vào fallback `full_flow` (chỉ lướt feed 2 swipe cơ bản), bỏ qua hoàn toàn phần code upload vừa sửa.
   - `canary_runner.py` không tự động phân tích Git diff để gắn cờ `--allow-upload-hook`, buộc con người phải nhớ và gõ tay.

3. **Bẫy Sổ Cái Skip (`already_uploaded_in_shift`):**
   - Thiết bị thật đã đăng video trong ngày, khi gọi hook upload thì `_ShiftUploadLedger` thấy ground truth report hoặc ledger entry đã có nên trả về `status: skipped`.
   - Subprocess upload và logic recovery hoàn toàn không được kích hoạt, nhưng runner vẫn exit 0 và Agent nhầm tưởng là Canary PASS ("Mày bị nhảm lồn à sửa upload thì canary đc upload chưa lải nhải clg bị ngu k").
   - Đối sách: Khi Canary hook upload, bắt buộc kiểm tra xem row/nick đã đăng chưa. Nếu đã đăng, phải chuyển sang row/account khác chưa đăng để kích hoạt subprocess upload thật sự.

---

## 2. Quy Tắc Thiết Kế Cơ Giới Hóa (Mechanical Canary Gate Codification)

Mọi luồng kiểm thử Canary bắt buộc tuân thủ 3 tầng cơ giới hóa khép kín:

### A. Ma trận Rule Diff (`canary_matrix.json`)
Mọi component/flow có hook tương ứng đều phải được khai báo trong ma trận ánh xạ:
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

### B. Tự Động Soi Diff & Nối Dây Hook Trong Runner (`canary_runner.py`)
Khi người vận hành hoặc agent gọi `canary_runner.py` mà không truyền cờ `--hook` thủ công:
- Runner BẮT BUỘC gọi `canary_plan.build_canary_plan(repo_dir, DEFAULT_MATRIX)` để đọc Git Diff (`HEAD~1` / working tree).
- Tự động phát hiện requirement và bật cờ tương ứng xuống core runner của farm (ví dụ: `--allow-upload-hook`).
- **Cảnh báo lỗi ngoài ý muốn:** Bọc try/except phải in `[CANARY_GATE] Warning: ...` minh bạch, tuyệt đối cấm `except Exception: pass` nuốt lỗi ngầm.

### C. Bẫy Logic Chí Mạng Đa Requirement (Multi-Requirement Trap)
*Bài học phát hiện từ Claude CLI Sonnet Reviewer:*
- **LỖI (TRƯỢT HOOK):**
  ```python
  # SAI: Chỉ lấy phần tử đầu tiên reqs[0]
  candidate_hook = reqs[0].get("hook")
  if candidate_hook and "upload" in candidate_hook: ...
  ```
  Khi một commit sửa nhiều file (ví dụ cả file switcher và file upload), thứ tự trong `reqs` phụ thuộc vào đường dẫn file trong git diff. Nếu switcher đứng trước, `reqs[0]` sẽ là switcher ➔ cờ upload bị rơi mất và runner quay lại lỗi lướt feed mù!
- **ĐÚNG (QUÉT TOÀN BỘ REQS):**
  ```python
  # ĐÚNG: Quét toàn bộ requirements có trong plan
  if any("upload" in str(r.get("hook", "")).lower() for r in reqs):
      cmd.append("--allow-upload-hook")
  ```

---

## 3. Ranh Giới: Memory vs Mechanical Gate & Kiểm Chứng Thực Chất
- **CẤM:** Lưu hướng dẫn chạy script, tên cờ lệnh, mapping file hay quy tắc canary vào `MEMORY.md`.
- **BẮT BUỘC:** Đưa toàn bộ vào `canary_matrix.json`, `canary_plan.py` và `canary_runner.py`. Điểm kết thúc kiểm tra bằng `done_gate.py` bắt buộc verify `tree_diff_sha256` của receipt khớp với HEAD git diff.
- **CHỐNG BÁO PASS MÙ:** Không bao giờ chấp nhận kết quả Canary là PASS nếu hook mục tiêu bị `skipped` do sổ cái (`already_uploaded_in_shift`). Phải kích hoạt subprocess thực sự hoặc chạy test case cơ học mô phỏng mã lỗi để chứng minh logic hoạt động.
