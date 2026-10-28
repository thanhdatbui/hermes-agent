# Architecture: Search Root & Device Lock Auto-Rewire vs Passive Denials

## 1. Bối Cảnh Sự Cố (The 30+ Block Loop Trap)
Trong báo cáo giám sát tuân thủ 6h (`gate_compliance_watchdog.py`), các Gate vi phạm nhiều nhất:
1. `GUARD_SEARCH_FILES_ROOT`: >30 lần bị chặn.
2. `GUARD_DEVICE_LOCK_REQUIRED`: Chặn lặp lại nhiều lần.
3. `Unremediated-Rejection`: Gate watchdog tự sinh rule ảo.

Nguyên nhân cốt lõi:
- **Substring Matching Bug:** Hook `guard_broad_grep.py` kiểm tra `contains_dangerous_root()` bằng cú pháp `root in norm` với `root = "d:/taadaa"`. Dẫn đến bất kỳ file đơn lẻ hay thư mục con sâu nào (ví dụ `D:/Taadaa/tools/...`, `D:/Taadaa/tiktok-luot nuoi acc/...`) đều bị đánh đồng là "quét toàn bộ đĩa gốc `D:/Taadaa`" và bị BLOCK 100%.
- **Passive Denials thay vì Auto-Rewire:** Hook chỉ trả về `action: "block"`, đẩy toàn bộ gánh nặng sửa lệnh cho Agent. Agent bối rối thử lại các biến thể khác nhau và tiếp tục dính block, làm phình context và hao phí token.

---

## 2. Thiết Kế Auto-Rewire & Fast-Path cho `search_files`

### A. 3 Lớp Kiểm Tra Phân Định Tốc Độ O(1):
1. **Lớp 1 (Single File Target Fast-Path):**
   Nếu `path` kết thúc bằng phần mở rộng file hợp lệ (`.py`, `.json`, `.txt`, `.md`, `.yaml`, `.yml`, `.sh`, `.ps1`...):
   Đây là tìm kiếm văn bản trong một file đơn lẻ O(1) $\rightarrow$ **CHO QUA NGAY (ALLOW / `sys.exit(0)`)**.
2. **Lớp 2 (Scoped Subfolder Allowance):**
   Nếu `path` là thư mục con cụ thể sâu trong repo (không nằm trong danh sách `exact_roots`):
   Đây là tìm kiếm có giới hạn phạm vi $\rightarrow$ **CHO QUA NGAY (ALLOW / `sys.exit(0)`)**.
3. **Lớp 3 (Exact Root Auto-Rewire):**
   Chỉ khi `norm_p` thực sự là root cấp cao nhất (`d:`, `d:/taadaa`, `d:/codexruntime`, `c:`, `c:/users/kibe`, `/`, `""`):
   - **Auto-Rewire:** Nếu CWD hiện tại của session là một thư mục con hợp lệ thuộc dự án (`d:/taadaa/...`), tự động rewrite `path` thành CWD:
     ```python
     updated_args = dict(args)
     updated_args["path"] = cwd
     print(json.dumps({
         "action": "rewrite",
         "rule_id": "GUARD_SEARCH_FILES_ROOT_AUTO_REWIRED",
         "updated_args": updated_args,
         "notice": f"Auto-rewired broad search root '{path}' -> scoped subfolder '{cwd}'.",
     }))
     sys.exit(0)
     ```
   - **Guidance & Required Action:** Nếu CWD cũng là root và không thể tự đoán, trả về `action: "block"` kèm danh sách thư mục con hợp lệ (`D:/Taadaa/tools`, `D:/Taadaa/tiktok-luot nuoi acc`, v.v.) để Agent định vị chính xác O(1).

---

## 3. Thiết Kế Auto-Wrap cho Device Mutex (`guard_device_bulkhead.py`)

### A. Vấn đề:
Khi Agent chạy lệnh ADB hoặc script can thiệp máy mà quên bọc `with_device_lock.py`, hook nhả lỗi `GUARD_DEVICE_LOCK_REQUIRED` và bắt gõ lại từ đầu.

### B. Giải pháp Auto-Wrap:
Khi nhận diện được số máy mục tiêu `mach_id` từ script hoặc đối số lệnh:
Tự động rewrite lệnh bằng cách bọc trước `with_device_lock.py`:
```python
updated_args = dict(args)
updated_args["command"] = f"python D:/Taadaa/tools/with_device_lock.py --machine {mach_id} -- {stmt}"
print(json.dumps({
    "action": "rewrite",
    "rule_id": "GUARD_DEVICE_LOCK_AUTO_WRAPPED",
    "updated_args": updated_args,
    "notice": f"Auto-wrapped script with device lock for M{mach_id}.",
}))
sys.exit(0)
```
Lệnh thực thi an toàn ngay lập tức mà không cần round-trip hay sự can thiệp của operator.

---

## 4. Tinh Gọn Watchdog & Loại Bỏ Synthetic Rules
- **Không tự bịa rule ảo:** Watchdog chỉ thống kê các `rule_id` thật từ log, cấm tự tạo rule như `[Closeout] Unremediated-Rejection`.
- **Đồng bộ cơ giới hóa Closeout O(1):** Đổi tên `Closeout Reviewer Gate` thành `Closeout Gate`, bỏ rubric chấm điểm hình thức, nghiệm thu bằng sự kiện thật (`[GuardEngine ALLOW]`, Pytest 100% pass).
- **Loại bỏ văn bản rác:** Cấm chèn các câu như `(Cần Bổ Sung Guidance)` hay `💡 Actionable: Operator/Agent cập nhật guidance...` vào báo cáo định kỳ.
