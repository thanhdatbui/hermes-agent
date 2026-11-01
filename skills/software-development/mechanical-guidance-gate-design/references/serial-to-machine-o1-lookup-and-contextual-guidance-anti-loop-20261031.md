# Serial-to-Machine O(1) Lookup & Contextual Guidance Anti-Loop (2026-10-31)

## 1. Bối Cảnh Sự Cố & Phản Hồi Operator
Khi báo cáo đối soát 6H nổ nhiều vi phạm liên tiếp từ các Agent ở phiên khác:
- **Lỗi ngộ nhận của Coordinator:** Tự hào kết luận *"Guard hoạt động chuẩn xác, chặn đứng 100% hành vi vi phạm"*.
- **Phản ứng gắt gao của Operator:** *"Thủ cái lồn. Uea thì fix tiếp chứ guard cứ chặn r agent loay hoay v hả"*.
- **Thực tế:** Mỗi lượt BLOCK là một lần Agent bị dồn vào chân tường, loay hoay thử đủ mọi đường vòng (search $\to$ grep -rn $\to$ find $\to$ os.walk $\to$ adb trần) vì Guidance nhả placeholder vô nghĩa hoặc chỉ sai ngữ cảnh.

---

## 2. Các Điểm Nghẽn Cơ Học Khiến Agent Loay Hoay & Cách Trị

### Điểm nghẽn 1: Placeholder Vô Nghĩa `<N>` trong Device Lock Guard
- **Hiện tượng:** Agent gõ `adb -s 9885b64957334f5a46 shell ...` không lock.
- **Guard trả về:** `CHỈ DẪN: Bọc lệnh qua: python D:/Taadaa/tools/with_device_lock.py --machine <N> -- <command...>`.
- **Hệ quả:** Agent cầm chuỗi serial `9885b...`, hoàn toàn không biết `<N>` là máy số mấy trên farm 280 máy. Nó hoang mang, thử gõ lại lệnh trần hoặc thử `adb shell input tap` $\to$ kích hoạt bẫy vi phạm tiếp theo.
- **Khắc phục:**
  1. Xây dựng hàm tra cứu $O(1)$ trong DAL: `farm_db.get_machine_by_serial(serial)` truy vấn trực tiếp bảng `machines` trong SQLite `farm_master.db`.
  2. Guard bắt được serial phải tự động tra cứu ra `mach_id` (ví dụ `9885b...` $\to$ `1`, `ce111...` $\to$ `18`).
  3. Cấp lệnh cụ thể với số máy thực tế: `python D:/Taadaa/tools/with_device_lock.py --machine 1 -- ...`. Tuyệt đối cấm để lọt placeholder `<N>` ra màn hình.
  4. Đối với các lệnh ADB đọc an toàn (`getprop`, `dumpsys`, `pm list`, `screencap`, `pull`, `devices`, `cat/ls/date/uptime`), Guard tự động Auto-Rewire bọc sẵn `with_device_lock.py` để lệnh chạy thẳng, không bắt Agent phải gõ lại.

---

### Điểm nghẽn 2: Guidance Lệch Ngữ Cảnh (Contextual Cross-Contamination)
- **Hiện tượng:** Agent đang tìm file code python trong repo, gõ `os.walk('D:/Taadaa/...')`.
- **Guard / Guardgate trả về:** `Guidance: Thu hẹp đường dẫn xuống thư mục cụ thể hoặc dùng công cụ O(1) như inspect_machine.py.`
- **Hệ quả:** Đang tìm code file mà lại xúi đi soi máy farm Android! Agent tưởng nhầm hệ thống bắt phải tương tác với thiết bị thật, bèn quay sang gõ lệnh ADB can thiệp máy farm.
- **Quy tắc bất biến:**
  - Lỗi quét file mã nguồn (`GUARD_PYTHON_WALKER`, `GUARD_FIND_SCAN`, `case_invariant_prohibit_broad_disk_scan`) **BẮT BUỘC** chỉ hướng dẫn công cụ tìm file:
    `CHỈ DẪN: Thu hẹp path xuống thư mục con cụ thể hoặc dùng search_files(target='files', pattern='*<kw>*') / git ls-files. CẤM quét toàn bộ D:/.`
  - Tuyệt đối cấm tiêm gợi ý soi máy Farm (`inspect_machine.py`) vào các lỗi thao tác filesystem của repository.

---

### Điểm nghẽn 3: Bẫy `grep -rn` trên Đường Dẫn Cụ Thể
- **Hiện tượng:** Khi bị cấm `os.walk`, Agent nghe lời chuyển sang gõ bash: `grep -rn "admin_ssh" D:/Taadaa/tools/*.py`.
- **Guard trả về:** `GUARD_RECURSIVE_GREP: grep recursive scan blocked. Use grep -n on a single file.`
- **Hệ quả:** Đường dẫn đích đã rất hẹp (`tools/*.py`), nhưng do thói quen gõ phím `-rn`, Agent bị chặn oan và không biết phải làm sao.
- **Khắc phục:** Hook tự động Auto-Rewire strip bỏ cờ `-r/-R/--recursive` thành `grep -n` khi path là glob hoặc file cụ thể, cho phép lệnh chạy ngay thay vì block.

---

## 3. Checklist Thiết Kế Guidance Chống Loay Hoay
1. **Có lệnh chạy được ngay không?** Không đưa lời khuyên triết lý ("hãy cẩn thận", "hãy thu hẹp"). Phải có exact syntax lệnh copy-paste chạy được.
2. **Có chứa placeholder ảo không?** Loại bỏ triệt để `<N>`, `<serial>`, `<path>`. Phải resolve từ runtime/DB ra giá trị cụ thể.
3. **Có đúng ngữ cảnh không?** Tìm code $\to$ chỉ tool code. Can thiệp máy $\to$ chỉ tool máy. Cấm râu ông nọ cắm cằm bà kia.
4. **Có thể Auto-Rewire không?** Nếu lệnh vô hại và chỉ thiếu bọc an toàn, ưu tiên Auto-Rewire hơn là giơ cờ chặn.
