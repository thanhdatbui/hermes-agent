# Persisted State Verification & UI Accent-Stripped Extraction Rubric (2026-10-21)

## 1. Context & Root Cause
Trong quá trình chạy Closeout Gate cho `social_reg_v1.py` và `tests/test_tap_add_account_safe_point.py`:
- **Điểm số bị chặn ở mức 78-79/100 (REJECTED):**
  Sol Reviewer ghi nhận 10-11 tests pass nhưng vẫn từ chối cấp token vì hai lỗ hổng bằng chứng:
  1. *Thiếu xác minh trạng thái lưu trữ thực tế (Persisted State Verification):*
     Test gọi `upsert_tracking_account` với mật khẩu mục tiêu rỗng và kỳ vọng hàm bảo toàn mật khẩu cũ trong sổ cái. Tuy nhiên, test chỉ kiểm tra giá trị trả về (`assert row == 2`), không mở lại file Excel để đọc ô `ws.cell(2, 4).value`. Reviewer nhận xét: *"Phần bằng chứng được cung cấp không hiển thị giá trị thực tế của mật khẩu sau cập nhật, nên chưa đủ để xác minh độc lập tính bảo toàn dữ liệu."*
  2. *Thiếu kiểm thử biến thể trích xuất UI tiếng Việt (UI Accent & Edge Cases):*
     Khi bổ sung thuộc tính `hint` vào `list_edittext_nodes`, Reviewer yêu cầu:
     - Xử lý XML lỗi (`<invalid xml`) trả về `[]` thay vì văng unhandled parse exception.
     - Nhiều node EditText cùng xuất hiện thì phải có cơ chế chọn lọc ưu tiên rõ ràng (`password="true"` ưu tiên hơn text hint).
     - Chuẩn hóa tiếng Việt có dấu (`strip_accents`) để các chuỗi `"Nhập mật khẩu"` khớp với từ khóa tìm kiếm `"mat khau"`.

---

## 2. Invariants & Implementation Patterns

### A. Kiểm Chứng Dữ Liệu Đã Lưu Vào Đĩa (Persisted State Re-Verification)
Khi viết unit test cho các hàm cập nhật/bảo toàn dữ liệu (như tracking workbook, database, state file):
- **Không chỉ assert return code:** Sau khi gọi hàm production, BẮT BUỘC re-open file lưu trữ trên đĩa để đọc lại giá trị vật lý.
- **Pattern chuẩn:**
  ```python
  # 1. Gọi hàm production với input rỗng để kiểm tra nhánh bảo toàn mật khẩu cũ
  with open(tracking_file, "r+b") as f:
      monkeypatch.setattr(social, "_acquire_tracking_write_phase", lambda reason: MockLock(f))
      row = social.upsert_tracking_account(24, "serial1", "test@example.com", "user123", "")
      assert row == 2

  # 2. BẮT BUỘC MỞ LẠI WORKBOOK KIỂM CHỨNG GIÁ TRỊ VẬT LÝ ĐÃ PERSIST
  wb_check = openpyxl.load_workbook(tracking_file)
  ws_check = wb_check.active
  assert ws_check is not None
  assert ws_check.cell(2, 4).value == "pass123", "Mật khẩu cũ phải được bảo toàn nguyên vẹn trên đĩa"
  wb_check.close()
  ```

### B. UI Element Extraction & Precedence Matrix
Khi bóc tách các trường nhập liệu từ XML giao diện:
1. **Trích xuất thuộc tính bổ trợ:**
   Trong `list_edittext_nodes`, bổ sung `"hint": attrs.get("hint", "")`.
2. **Khớp từ khóa chống dấu (Accent-Insensitive Matching):**
   Thay vì so sánh chuỗi thô, luôn chuẩn hóa qua `strip_accents`:
   ```python
   pass_nodes = [
       n for n in list_edittext_nodes(xml_pw_check)
       if n.get("password") or any(
           h in strip_accents(n.get("hint") or n.get("text") or "").lower()
           for h in ["mat khau", "password"]
       )
   ]
   ```
3. **Thứ tự ưu tiên khi có nhiều node:**
   Luôn ưu tiên node có thuộc tính `password="true"` rõ ràng trước khi fallback sang node có hint/text:
   ```python
   pass_node = next((n for n in pass_nodes if n["password"]), pass_nodes[0])
   ```

### C. Offline Mocking Cho Network/ADB Calls Trong Unit Test
Hàm `wait_login_success` trong môi trường thật sẽ gọi ADB shell (`dumpsys activity activities`) để kiểm tra foreground app.
- Khi viết unit test, BẮT BUỘC mock `shell` để trả về package name (`"com.ss.android.ugc.trill"`), tránh việc test cố gọi binary ADB ngoài đời dẫn đến timeout / hang 20s.
- Mô phỏng bước nhảy thời gian qua `time.time` và `time.sleep` để kiểm tra nhanh cả hai nhánh (thành công tức thì và timeout 75s) trong < 0.1s.

---

## 3. Strike 3 Reviewer Hand-Off Invariant
Khi hệ thống từ chối 3 lần liên tiếp trên cùng `scope_hash` (`[REVIEWER_HANDOFF_TRIGGERED]`):
1. **Ý nghĩa của marker:** Dừng toàn bộ các nỗ lực tự vá mò của Coordinator hoặc proposal của Sol Repair.
2. **Hành động bắt buộc:** Lập tức dispatch `python D:/Taadaa/tools/claude_worker.py --role worker` (model `claude-haiku-5-5`, `--max-turns 15`) hoặc fallback sang `ag_cli.py fix` để Reviewer tự tay thi công bản vá.
3. **Anti-Clarify:** Tuyệt đối CẤM gọi công cụ `clarify` để hỏi ý kiến người dùng khi gặp marker này. Quyền chuyển giao đã được ủy quyền sẵn theo quy chế Closeout Gate.
