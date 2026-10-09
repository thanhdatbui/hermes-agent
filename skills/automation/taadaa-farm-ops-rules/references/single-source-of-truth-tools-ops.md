# Quy chuẩn Single Source of Truth cho Tools dùng chung toàn Farm (2026-09-05)

## 1. Bối cảnh & Nguyên lý Kiến trúc
Hệ thống Phone Farm Taadaa có nhiều repo độc lập (`Hotmail`, `Tiktok_Reg`, `Tiktok-video`...) cùng cần sử dụng các công cụ vận hành phụ trợ (`buy_hotmail.py`, `inspect_machine.py`, `install_farm_apks.py`...).
Việc sao chép mã nguồn các tool này sang thư mục `tools/` của từng repo gây ra:
- Phân mảnh mã nguồn và khó bảo trì khi cần nâng cấp logic tool.
- Rủi ro xung đột dữ liệu (conflicted copy) trên OneDrive giữa các máy Kibe và Admin.
- Khó kiểm soát quyền hạn (Master vs Client).

---

## 2. Quy tắc Bắt buộc 3 Trụ Cột

### 2.1. Runtime (Chạy thực tế)
- Toàn bộ tool vận hành chung BẮT BUỘC đặt tại:
  `D:\Taadaa\tools\` (được đồng bộ tự động qua OneDrive giữa Kibe và Admin).
- Mọi quy trình farm gọi trực tiếp qua terminal:
  `python D:/Taadaa/tools/<tool_name>.py`
  hoặc import trực tiếp từ đường dẫn `D:\Taadaa\tools\`.
- CẤM tạo bản sao thực thi cục bộ bên trong thư mục con của từng repo consumer.

### 2.2. Quản lý mã nguồn (Git)
- Mã nguồn các tools dùng chung được quản lý tập trung DUY NHẤT tại repo:
  `AI-Tools` (`D:\Taadaa\AI-Tools\tools\`).
- CẤM sao chép / nhân bản file mã nguồn tool sang thư mục `tools/` của các repo khác (`Hotmail`, `Tiktok_Reg`...).
- Mọi sửa đổi, cập nhật tính năng, refactor cho tool farm phải được thực hiện và commit tại repo `AI-Tools`.

### 2.3. Phân quyền Master/Client & Chống Xung Đột Đồng Bộ
- Máy Kibe đóng vai trò **Master**: được phép chỉnh sửa, ghi đè, cập nhật file tool tại `D:\Taadaa\tools\`.
- Máy Admin đóng vai trò **Client/Worker**: chỉ thực thi (**Read-Only**).
- Tuyệt đối cấm máy Admin tự động ghi đè hoặc tạo file cùng tên gây ra `conflicted copy` trên thư mục đồng bộ OneDrive.

---

## 3. Phân Biệt Rạch Ròi: Tools Tiện Ích vs Script Nghiệp Vụ Farm

Cần phân biệt rõ hai loại thành phần mã nguồn trên Farm:

### A. Nhóm Tools Tiện Ích Dùng Chung (`D:\Taadaa\tools\`)
- **Bao gồm**: `buy_hotmail.py`, `inspect_machine.py`, `install_farm_apks.py`...
- **Đặc điểm**: Các script CLI phụ trợ, không chứa vòng lặp trạng thái ca chạy farm, độc lập với ngữ cảnh từng máy.
- **Cơ chế phân phối**: Đồng bộ tự động qua **OneDrive NTFS Junction** (`D:\OneDrive\Taadaa_Sync_Shared\tools\`).
- **Mục đích**: Khi Kibe sửa hoặc thêm tính năng mới, máy Admin có thể gọi lệnh ngay lập tức ở terminal mà không cần thao tác commit hay `git pull`.

### B. Nhóm Script Nghiệp Vụ Farm (BẮT BUỘC QUA REPO GIT)
- **Bao gồm**: `Tiktok_Reg`, `tiktok-follow`, `tiktok-luot nuoi acc`, `automation-core`, `register gmail`...
- **Đặc điểm**: Chứa logic tự động hóa cốt lõi, state machine, tương tác app, quản lý device lock, tracking workbook, bộ unit tests và quy trình chốt phiên (Gate 0 → Gate 4).
- **Cơ chế phân phối**: **100% quản lý độc lập qua GitHub (`origin/main`)**:
  - Máy nào cần fix/nâng cấp: Sửa trực tiếp trên repo máy đó → chạy test → Plan-Review → Commit & Push lên GitHub.
  - Máy còn lại nhận code mới: Mở repo gõ `git pull origin main` (hoặc chạy batch pull).
- **CẤM TUYỆT ĐỐI ĐỒNG BỘ REPO QUA ONEDRIVE**:
  - OneDrive làm hỏng cấu trúc `.git/` (lock index, refs, objects) khi 2 máy cùng truy cập.
  - Làm xung đột trạng thái runtime (Kibe chạy máy 1–80, Admin chạy máy 201–280; đồng bộ OneDrive sẽ làm ghi đè log và tracking workbook của nhau).

---

## 4. Cơ Chế Cập Nhật Quy Tắc Toàn Cục (`AGENTS.md`) Sang Máy Admin

- **Tại sao Tools tự cập nhật còn Rules cần lệnh copy?**
  - Thư mục `D:\Taadaa\tools\` được liên kết bằng **NTFS Junction** trỏ thẳng vào OneDrive, nên mọi thay đổi file `.py` sẽ phản ánh tức thì trên Admin khi OneDrive sync.
  - File rule toàn cục `D:\Taadaa\AGENTS.md` trên máy Admin là bản copy tĩnh từ `D:\OneDrive\Taadaa_Sync_Shared\AGENTS.md` (do file đơn lẻ không thể tạo NTFS Directory Junction).
- **Quy trình khi Kibe cập nhật `AGENTS.md`:**
  1. Kibe cập nhật nội dung vào cả `D:\Taadaa\AGENTS.md` và `D:\OneDrive\Taadaa_Sync_Shared\AGENTS.md`.
  2. OneDrive tự động đồng bộ file về thư mục `D:\OneDrive\Taadaa_Sync_Shared\AGENTS.md` của máy Admin.
  3. Để Agent bên Admin nạp quy tắc mới, máy Admin cần chạy lệnh copy đè:
     ```cmd
     cmd /c copy /Y "D:\OneDrive\Taadaa_Sync_Shared\AGENTS.md" "D:\Taadaa\AGENTS.md"
     ```
  4. Mọi session mới của Hermes / AI Agent bên Admin khi mở ra sẽ tự động đọc `D:\Taadaa\AGENTS.md` bản mới nhất vào context.
