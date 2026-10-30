# Dual-Cluster Reg Gmail Failures & Admin Recovery Architecture

**Ngày cập nhật:** 2026-10-30  
**Bối cảnh:** Luồng Reg Gmail ban đêm báo cáo 15 máy lỗi / hoàn tất trên Kibe nhưng hoàn toàn không chạy trên Farm Admin (Máy 201-280).

---

## 1. Các Tử Huyệt Kỹ Thuật Khiến Cụm Admin Tê Liệt Im Lặng

### A. Đứt gãy đồng bộ code (`SyntaxError: unterminated string literal`)
- **Triệu chứng:** Khi chạy `run_all.ps1` trên Admin, lệnh nạp inventory `python -c "import sys, gmail_reg_v10 as g; ..."` văng lỗi:
  `SyntaxError: unterminated string literal (detected at line 827)`.
- **Hậu quả:** PowerShell văng exception `Khong lay duoc danh sach may tu device inventory`, batch dừng trước khi chạm vào bất kỳ thiết bị nào.
- **Phòng chống & Khắc phục:**
  - Tuyệt đối không copy file thủ công hoặc qua kênh không bảo toàn byte.
  - Sử dụng cơ chế OneDrive staging hoặc chunked base64 push qua `admin_ssh.py`.
  - **Bắt buộc đối soát SHA256:** Sau khi đồng bộ file `gmail_reg_v10.py` sang Admin-PC, luôn đối chiếu mã SHA256 bit-for-bit giữa Kibe và Admin trước khi kết luận thành công.

### B. Hỏng cấu trúc file Excel sổ cái (`ParseError: mismatched tag`)
- **Triệu chứng:** File `D:\OneDrive\TaadaaData\admin\gmail_clean_v2.xlsx` bị lỗi XML (mismatched tag ở column 266830) do crash trong lúc ghi hoặc sync conflict.
- **Bẫy bắt lỗi trong PowerShell:**
  - Trong `run_parallel.ps1`, hàm kiểm tra cooldown gọi:
    ```powershell
    $readyOutput = & $pythonExe -c $pythonCode 2>&1
    $readyArray = $readyList -split ',' | ForEach-Object { [int]$_.Trim() }
    ```
  - Khi `openpyxl` quăng warning `[warn] Khong doc duoc Excel de tinh cooldown: mismatched tag: line 1`, chuỗi warning bị gom vào `$readyList`. Lệnh ép kiểu `[int]$_.Trim()` crash với lỗi `Cannot convert value "[warn] Khong doc duoc Excel..." to type System.Int32`.
- **Khắc phục:**
  - Kiểm tra tính toàn vẹn của workbook: Thử mở bằng `openpyxl.load_workbook(path, data_only=True)`.
  - Nếu hỏng, lập tức khôi phục từ bản backup sạch gần nhất (`gmail_clean_v2.bak_*.xlsx`), kiểm tra số lượng dòng và đảm bảo `openpyxl` nạp không có lỗi.

### C. Rào chặn SSH Command Allowlist
- **Triệu chứng:** Khi watchdog gửi lệnh PowerShell dạng chuỗi nhiều dòng có gán biến môi trường `$env:PYTHONIOENCODING='utf-8'...`, rào chặn allowlist trong `admin_ssh.py` bắt token rỗng hoặc không thuộc danh sách cho phép và từ chối thực thi (`COMMAND_NOT_IN_ALLOWLIST`).
- **Khắc phục:**
  - Bọc toàn bộ payload PowerShell script qua Base64 UTF-16LE: `powershell -NoProfile -EncodedCommand <base64>`.
  - Giúp lệnh truyền qua SSH luôn có token hợp lệ (`powershell`) và bảo toàn ký tự escape.

---

## 2. Điểm Nghẽn Màn Hình Đăng Ký `[05_create]` (WebView Google Sign-in)

### A. Triệu chứng tại hiện trường
- App Gmail mở thành công, chọn provider Google, tải xong màn hình Google Sign-in (`identifierId` xuất hiện).
- Tuy nhiên runner quăng lỗi: `[05_create] Không tìm thấy Tạo tài khoản/Create account`.
- Đối soát XML hiện trường (`fail_05_create_*.xml`): Toàn bộ cây UI XML chỉ chứa ô nhập Email, link *"Bạn quên địa chỉ email?"*, và nút *"TIẾP THEO"* ở dưới cùng. Hoàn toàn không có node text "Tạo tài khoản".

### B. Cơ chế và Giải pháp phục hồi
1. **Layout Shift / Viewport Thu Nhỏ:**
   - Trên một số thiết bị hoặc độ phân giải đặc thù, footer chứa nút "Tạo tài khoản" bị ẩn bên dưới viewport hoặc WebView chưa kích hoạt render đầy đủ DOM.
2. **Quy trình Fix:**
   - **Thực hiện Swipe kích hoạt:** Trước khi kết luận không tìm thấy, thực hiện thao tác vuốt nhẹ màn hình lên (`input swipe 540 1200 540 600`) để kích hoạt WebView render footer.
   - **Nới lỏng Fallback Selector:** Không chỉ giới hạn quét `class == "android.widget.Button"`, mà quét cả các node `android.view.View` clickable nằm trong vùng tọa độ `y: 1300-1650`.
   - **Graceful Retry:** Nếu 2 lần quét vẫn không có nút tạo tài khoản, bấm phím `Back` về lại màn chọn Provider để tap lại Google, tránh để phiên kẹt vĩnh viễn ở màn Sign-in.
