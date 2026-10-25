# Static AST Scanner False Positives & Cross-Gate Deadlock Resolution

## 1. Bối Cảnh Sự Cố & Tín Hiệu Người Dùng
Trong quá trình vận hành, người dùng phản ánh: *"Còn các guard hook đó có tự huỷ tự bóp nhau k! Tối hqua t ms fix tùm lum vì gây khóc lóc bại liệt đó"* và chỉ thị *"Fix vụ guard đá nhau đi"*. 

Kiểm tra hiện trường thực tế đã phát hiện 2 vấn đề kỹ thuật nghiêm trọng:
1. **Lỗi AST False Positive:** Hook kiểm tra an toàn chạy nền tự chặn đứng runner chính thống của farm (`do_rename_canonical_runner.py`), khiến bộ test an toàn nền bị rớt 1 test (`test_real_runner_passes_guard` FAIL).
2. **Tam Giác Khóa Chéo Triệt Tiêu Lối Thoát (Catch-22 Deadlock):** Sự mâu thuẫn giữa 3 tầng bảo vệ độc lập khiến Agent bị bại liệt 100% khi thực hiện các tác vụ dài hơi hoặc chạy ngầm.

---

## 2. Nguyên Nhân Gốc Rễ & Bản Vá Kỹ Thuật

### A. Lỗi AST False Positive Do Thuộc Tính Động (`getattr`)
- **Cơ chế quét an toàn:** Hook kiểm tra an toàn console phân tích cú pháp trừu tượng (AST) của file Python khi đăng ký cronjob hoặc chạy ngầm để đảm bảo mọi lệnh spawn tiến trình (`subprocess.run`, `Popen`) đều có cờ ẩn cửa sổ `creationflags=subprocess.CREATE_NO_WINDOW` (hoặc `0x08000000`).
- **Điểm gãy tại runner:** Tại dòng 413 của `do_rename_canonical_runner.py`:
  ```python
  cflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
  res = subprocess.run(login_cmd, capture_output=True, text=True, timeout=180, creationflags=cflags)
  ```
- **Hệ quả:** Bộ kiểm tra AST chỉ giải quyết các hằng số hoặc thuộc tính trực tiếp `subprocess.CREATE_NO_WINDOW`. Khi gặp hàm `getattr(...)`, scope dynamic đánh dấu là không xác định, dẫn tới việc bị chặn nhầm:
  `subprocess.run() thiếu cờ creationflags=subprocess.CREATE_NO_WINDOW (0x08000000) làm bật cửa sổ CMD cướp focus!`
- **Bản vá dứt điểm:** Chuẩn hóa trực tiếp thành thuộc tính tĩnh:
  ```python
  res = subprocess.run(
      login_cmd,
      capture_output=True,
      text=True,
      timeout=180,
      creationflags=subprocess.CREATE_NO_WINDOW,
  )
  ```
- **Kiểm chứng:** Bộ test an toàn nền khôi phục trạng thái **96/96 passed (100% PASS)** trong 13.57s.

---

## 3. Bản Đồ Tam Giác Khóa Chéo Gây Bại Liệt

| Tầng Kiểm Soát | Quy Định & Rào Cản | Xung Đột Với Tầng Khác |
|---|---|---|
| **Chống Cửa Sổ Đen Nền** | Background BẮT BUỘC dùng `pythonw` hoặc `powershell -WindowStyle Hidden` (chống console đen) | Đâm chéo với Coordinator Policy: ép dùng `pythonw` nhưng Coordinator lại bị cấm gõ `pythonw`. |
| **Coordinator Policy** | `DEFAULT-DENY`: Chỉ cho phép `python`, `git`, `claude`, `pytest`, `inspect_machine.py`. CẤM `pythonw` và `powershell`. | Triệt tiêu hoàn toàn khả năng chạy nền của Coordinator. |
| **Foreground Timeout Clamp** | Foreground clamp cứng <= 60s cho các lệnh thông thường; chỉ mở 360s cho các tool trong danh sách cho phép. | Các tác vụ truyền file LAN, sync mạng lớn không nằm trong danh sách cho phép nên bị chém văng ở giây 60. |

---

## 4. Quy Tắc Phòng Ngừa & Kiến Trúc Độc Lập

1. **Quy Tắc AST-Friendly Coding Trong Automation Core:**
   - Khi viết mã nguồn liên quan đến `subprocess` trên Windows, BẮT BUỘC truyền thẳng `creationflags=subprocess.CREATE_NO_WINDOW` hoặc hằng số `0x08000000`.
   - TUYỆT ĐỐI CẤM dùng các hàm động như `getattr()`, `eval()`, biến trung gian phức tạp ngoài module khi khai báo `creationflags` để tránh đánh lừa các bộ phân tích tĩnh.
2. **Quy Tắc Đồng Bộ Allowlist Cho Công Cụ Nền (`pythonw` Parity):**
   - Bất kỳ hệ thống nào ép buộc chạy nền không console qua `pythonw` thì bộ lọc lệnh Coordinator tương ứng BẮT BUỘC phải mở `pythonw` đi kèm với danh sách các script canonical an toàn.
3. **Quy Tắc Chạy Test Cấp Repo (`workdir` Invariant):**
   - Khi chạy `pytest` cho các test suite chứa logic dò tìm Git root, BẮT BUỘC chỉ định `workdir` trỏ đúng vào root của repo mục tiêu (`D:/Taadaa/tools`), tránh để `cwd` mặc định ở home directory (`C:/Users/Kibe`) làm sai lệch phép tính resolve đường dẫn tương đối.
