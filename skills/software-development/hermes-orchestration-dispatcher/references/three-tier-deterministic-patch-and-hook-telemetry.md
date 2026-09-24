# Three-Tier Task Classification & Deterministic Patch Protocol (Claude Opus & User Correction 2026-09-25)

## 1. Bối cảnh & Bài học xương máu (Subagent Overhead Death Loop)
- **Sự cố:** File monolith 1.876 dòng (`tiktok_dashboard.py`), user yêu cầu 2 tính năng (Modal Overview + Fleet Heatmap). Coordinator gộp cả 2 vào 1 subagent dispatch. Hậu quả: Worker đọc lại từ đầu 90k tokens, vật lộn với HTML/CSS/JS template string, timeout 600s x2 lần, đốt sạch quota của user và trả về `0 files modified`.
- **Nguyên nhân gốc rễ:** Làm đúng luật "Cấm Coordinator sửa code" một cách máy móc, mù quáng giao cả phần suy nghĩ cho worker mà không phân rã ngay từ đầu.
- **Quy tắc kinh tế:** Với sửa đổi cơ học đã biết rõ anchor, Coordinator tự patch mất 15-30s. Đẩy ra subagent ngầm mất 600s để worker "học lại từ đầu" thứ Coordinator đã biết -> lỗ hoàn toàn.

---

## 2. Bảng phân loại 3 lớp công việc (Three-Tier Task Classification)

| Lớp | Điều kiện (phải thỏa TẤT CẢ) | Ai thực hiện | Quy trình & Công cụ |
| :--- | :--- | :--- | :--- |
| **Lớp D: Deterministic Patch** (Sửa cơ học đã biết rõ) | • Đã biết chính xác file và anchor duy nhất (`wc -l == 1`).<br>• Diff $\le$ 80 dòng mỗi patch, $\le$ 3 file.<br>• Có lệnh verify tất định (`pytest`, `py_compile`, `node --check`).<br>• Không đụng thiết bị thật, ADB, mạng ngoài. | **Coordinator tự apply ngay.**<br>*(Đẩy việc Lớp D sang worker = VI PHẠM)* | Dùng `python D:/Taadaa/tools/apply_patch.py patch.json`.<br>Công cụ tự động check `count == 1`, tạo `.bak`, chạy verify, nếu fail tự rollback 100% và ghi telemetry `patch_audit.jsonl`. |
| **Lớp S: Scoped Build** (Viết logic mới trong file) | • Biết file, nhưng cần viết logic mới > 80 dòng.<br>• Cần thử-sai nhỏ trong code, có acceptance test rõ ràng. | **Worker subagent** | Bắt buộc kèm Anchor Map từ Coordinator (file + anchor + focused test). Budget cứng $\le$ 240s (cấm để 600s). Checkpoint `progress.md`. |
| **Lớp E: Exploratory** (Khám phá & Hiện trường Farm) | • Thao tác thiết bị thật, ADB, OCR, 160 máy.<br>• Tái hiện lỗi, debug sự cố chưa rõ nguyên nhân gốc rễ.<br>• Dự kiến > 15 tool calls, kết quả nén được thành báo cáo ngắn. | **Bắt buộc Worker subagent** | Chạy trong context riêng biệt, role=leaf, bảo vệ context Coordinator sạch. |

---

## 3. Quy trình phân rã tức thì (Gate 0 Decomposition)
Ngay giây đầu tiên nhận prompt từ user:
1. **Gate 0 - Tách Deliverable ($\le$ 10s, không tool):**
   - Đếm số tính năng độc lập trong prompt. Nếu $> 1$ tính năng $\rightarrow$ mỗi tính năng là một pipeline riêng, **CẤM TUYỆT ĐỐI GỘP**.
   - Nếu có chỗ mơ hồ về nghiệp vụ: HỎI USER TRƯỚC ở Gate 0, không để worker tự đoán.
2. **Gate 1 - Recon (Coordinator, $\le$ 3 Read/Grep, $\le$ 60s):**
   - Lập Anchor Map: định vị toạ độ vật lý duy nhất trong file (`grep -o ... | wc -l == 1`).
3. **Gate 2 - Chia nhỏ:**
   - Mỗi unit = 1 lớp (SQL / API / HTML / CSS / JS), diff $\le$ 80 dòng, đúng 1 lệnh verify.
4. **Gate 3 - Gán nhãn D/S/E & Báo user:**
   - Báo user 1 dòng: "N unit, X lớp D tự làm, Y dispatch, ước ~Z phút".
5. **Gate 4 - Thực thi tuần tự:**
   - Apply $\rightarrow$ Verify $\rightarrow$ Checkpoint $\rightarrow$ Unit tiếp theo. Test fail $\rightarrow$ Rollback unit đó.

---

## 4. Công cụ `tools/apply_patch.py` & Chuẩn Telemetry
- **Đường dẫn:** `D:/Taadaa/tools/apply_patch.py`
- **Cách dùng:** `python D:/Taadaa/tools/apply_patch.py patch.json [--keep-bak]`
- **Cấu trúc `patch.json`:**
  ```json
  {
    "patches": [{"file": "path/to/file.py", "old": "exact_anchor", "new": "replacement"}],
    "verify": "python -m pytest tests/test_x.py -q",
    "timeout": 120
  }
  ```
- **Hành vi an toàn:**
  * Anchor count != 1 $\rightarrow$ thoát mã 2 `ANCHOR_FAIL`, không sửa file.
  * Tự tạo `<file>.bak` trước khi ghi.
  * Chạy `verify`: nếu exit code != 0 hoặc timeout $\rightarrow$ tự phục hồi từ `.bak`, thoát mã 1 `ROLLED_BACK`.
  * Thành công $\rightarrow$ xóa `.bak`, thoát mã 0 `PATCH_OK`.
  * Tự động ghi nhật ký bất biến vào `D:/Taadaa/runtime/audit_logs/patch_audit.jsonl`.

---

## 5. Cạm bẫy Hook Dispatch & Đồng bộ Quad-Location
1. **Cạm bẫy tiếng Anh lọt qua Investigate:**
   - `guard_dispatch_contract.py` phải phân loại dựa trên thứ tự ưu tiên:
     * `OLD_STRING` / `NEW_STRING` $\rightarrow$ 100% Code Edit.
     * Cụm động từ biến đổi code thật (`patch`, `sửa code`, `refactor`, `viết code`, `implement feature`, `thay thế code`) $\rightarrow$ Code Edit. (Không dùng từ đơn lẻ `add`, `update`, `feature` vì gây false positive).
     * Cụm từ đọc mã (`inspect`, `investigate`, `audit`, `review`, `trace`, `chỉ đọc`, `soi log`) $\rightarrow$ Investigate (bắt buộc budget $\le 5$ calls). Budget $> 5$ calls $\rightarrow$ Block ngay.
2. **Lệch Timeout trong `config.yaml`:**
   - Hook gọi Sol Planner cần 15-25s. Do đó `timeout` của hook `guard_dispatch_contract.py` trong `config.yaml` **bắt buộc phải đặt $\ge 30$s** (không để 5s gây kill ngầm).
3. **Đồng bộ 4 vị trí (Quad-Location Parity):**
   - Mọi thay đổi trên hook bắt buộc sync đều 4 nơi:
     * `D:/Taadaa/tools/hooks/guard_dispatch_contract.py`
     * `%LOCALAPPDATA%/hermes/hooks/guard_dispatch_contract.py`
     * `D:/OneDrive/Taadaa_Sync_Shared/hermes-sync/hooks/guard_dispatch_contract.py`
     * `D:/Taadaa/Hermes/deploy/hermes-home/hooks/guard_dispatch_contract.py`
