# Anti-Complacency Watchdog Triage & Guard Block Death Spiral

## 1. Bối Cảnh & Sự Cố "Thủ cái lồn"
Khi báo cáo đối soát 6H (`gate_compliance_watchdog.py`) trả về `FAIL` với các vi phạm ở Gate G7 (Anti-Scan Terminal Guard) như `GUARD_SEARCH_FILES_ROOT`, `GUARD_RECURSIVE_GREP`, `GUARD_FIND_SCAN`, `GUARD_DANGEROUS_ROOT`:
- **Lỗi nhận thức nghiêm trọng của Coordinator:** Vội vã kết luận *"Guard đã hoạt động chính xác và chặn đứng 100% các hành vi quét đĩa trái phép... Hệ thống phòng thủ cơ giới vẫn đang vận hành chuẩn xác"*.
- **Phản ứng thực tế của Operator:** *"Thủ cái lồn. Tại sao vi phạm khủng khiếp v guidance auto rewiree đéo cái nào dẫn đường được cho agent à?"*.
- **Bản chất thực tế:** Việc Guard giơ cờ chặn (BLOCK) hàng loạt **KHÔNG PHẢI LÀ CHIẾN TÍCH**. Đó là dấu hiệu cho thấy **Agent đang bị dồn vào chân tường, Guidance bị sai lệch hoặc vô hiệu, và Auto-Rewire bị tắt hoặc hỏng**, khiến Agent quay cuồng tìm mọi cách quét đĩa để làm việc rồi lần lượt kích hoạt toàn bộ các bẫy Guard.

---

## 2. Chuỗi Bế Tắc Cơ Học (The Block Death Spiral)
Khi phân tích log thật `guard_scan_audit.jsonl`, chuỗi sự cố thường diễn ra theo đúng kịch bản dồn cục:
1. **Bước 1 (Subfolder False Positive):** Agent gọi `search_files` vào một thư mục con hợp lệ (ví dụ `D:/Taadaa/tiktok-follow`, `D:/Taadaa/tools`). Hook `guard_broad_grep.py` bị lỗi kiểm tra chuỗi (`root in norm`) nên chặn oan với lý do *"Broad content search blocked on protected root"*.
2. **Bước 2 (Chỉ đường mù / Guidance Misalignment):** Thông báo lỗi của Hook hướng dẫn: *"DÙNG LỆNH O(1): python D:/Taadaa/tools/inspect_machine.py <N>"*. Trong khi Agent đang tìm file code, Guidance lại xúi đi soi máy farm Android!
3. **Bước 3 (Thử đường vòng qua Bash):** Thấy `search_files` bị chặn, Agent chuyển sang gõ bash `grep -rn` $\rightarrow$ bị `GUARD_RECURSIVE_GREP` chặn.
4. **Bước 4 (Cố tìm file bằng tool khác):** Agent dùng `find /d/Taadaa -name "..."` $\rightarrow$ bị `GUARD_FIND_SCAN` chặn.
5. **Bước 5 (Liều mạng với Python):** Quá bí bách, Agent viết inline `python -c "import os ... for root, dirs, files in os.walk(...)"` $\rightarrow$ bị `GUARD_DANGEROUS_ROOT` chặn.

Hậu quả: 4-5 vi phạm liên tiếp nổ ra trong vòng 30 phút vì Agent không có bất kỳ lối thoát (Active Pivot / Auto-Rewire) nào để tiếp tục task.

---

## 3. Các Bất Biến Điều Phối & Đánh Giá Báo Cáo (Invariants)

### Invariant 1: Cấm Tự Hài Lòng / Ca Ngợi Chốt Chặn Khi Báo Cáo FAIL
- Tuyệt đối cấm Coordinator dùng các từ ngữ ca ngợi chốt chặn như *"phòng thủ chuẩn xác"*, *"chặn đứng 100%"* khi nhận báo cáo Gate FAIL.
- BẮT BUỘC coi mỗi lượt BLOCK là một **tổn thất token và tắc nghẽn workflow**.
- Phản xạ đầu tiên khi thấy Gate G7 FAIL: Truy vết trực tiếp file log audit (`guard_scan_audit.jsonl`), bóc tách:
  1. Câu lệnh thật (Target) là gì?
  2. Tại sao câu lệnh đó bị phát ra? Agent đang cố giải quyết việc gì?
  3. Tại sao Auto-Rewire không tự động nắn lệnh về phạm vi an toàn?
  4. Guidance trả về lúc bị chặn có chỉ đường đúng ngữ cảnh hay đang spam hướng dẫn vô nghĩa?

### Invariant 2: Phân Biệt Scoped Subfolder vs Protected Root
- Chốt chặn quét đĩa (`guard_broad_grep.py`) CHỈ ĐƯỢC PHÉP chặn khi đường dẫn là root trần trụi (`/`, `C:/`, `D:/`, `D:/Taadaa`, `D:/Taadaa/`).
- BẮT BUỘC cho phép các thư mục dự án / subfolder cụ thể (`D:/Taadaa/tools`, `D:/Taadaa/orders`, `D:/Taadaa/tiktok-*/*`).
- Nếu Hook đưa ra gợi ý *"Vui lòng scope vào thư mục con (vd D:/Taadaa/tools)"* thì TUYỆT ĐỐI KHÔNG ĐƯỢC chặn chính thư mục `D:/Taadaa/tools`.

### Invariant 3: Guidance Theo Ngữ Cảnh Thao Tác (Contextual Guidance)
- Khi chặn thao tác tìm kiếm file code: Guidance BẮT BUỘC hướng dẫn dùng `search_files(target='files', pattern='...')` hoặc `git ls-files`.
- CẤM TUYỆT ĐỐI nhồi nhét chỉ dẫn Farm Android (`inspect_machine.py <N>`) vào các lỗi tìm kiếm mã nguồn hoặc thao tác repo.

### Invariant 4: Watchdog JSON Log Parse Fidelity
- `gate_compliance_watchdog.py` khi bóc tách `rule_id` từ `guard_scan_audit.jsonl` hoặc các log JSON khác:
  BẮT BUỘC parse bằng `json.loads(line.strip())` an toàn, lấy đúng trường `rule_id`, `category`, `reason`.
  CẤM regex cắt chuỗi thô dẫn đến việc các đoạn text chứa dấu ngoặc kép `"` bị biến thành các mục ảo như `[Unclassified] ": "[GUARD_SEARCH_FILES_ROOT]...`.
