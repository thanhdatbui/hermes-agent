# Zero Re-invent & Fix-at-Source Discipline for Avatar Operations (2026-10-13)

## 1. Bối cảnh Sự cố & Lời Phạt Của User
Khi runner chính thức `run_tiktok_upload_avatar.ps1` vấp lỗi nhận diện icon Sửa hồ sơ do layout TikTok v47 trên Samsung S7, Agent suýt quay sang sửa script tap tay ad-hoc (`do_upload_avatar_m71.py`).
User đã nhắc nhở và phạt gay gắt:
> *"Là t ns mày ms đọc script chứ trc đó tính viết nguyên code upload ava lại đúng k. Xử lý đi. R làm sao có cơ chế cho mày ưu tiên tìm script có sẵn r chạy (kể cả fix cũng handle luôn vào script có sẵn) thay vì tự ngồi chế lại cái bánh xe đã có sẵn. Bảo claude cli thiết kế để mày ưu tiên tìm script đã có thay vì đi tự chế lại đi"*

## 2. 3 Nguyên Tắc Vàng (Thiết Kế Bởi Claude Code CLI)
1. **Zero Re-invent (Tìm trước, viết sau):**
   - Trước khi viết code mới, BẮT BUỘC chứng minh bằng evidence rằng hệ thống chưa có tool/runner làm việc này.
   - Nguồn tra cứu: (1) `D:\Taadaa\tools\`, (2) Runner chính thức của repo (`run_tiktok_upload_avatar.ps1` trong `Tiktok-video`).
   - CẤM tạo launcher mới, tạo loop riêng, hoặc viết wrapper ngoài lề. Chỉ đổi tham số qua CLI hoặc config.
2. **Fix at Source (Lỗi ở đâu, sửa vào core ở đó):**
   - Khi runner gặp màn hình lạ, popup mới, selector đổi hoặc timeout: BẮT BUỘC sửa trực tiếp handler, selector, bounds trong core codebase của runner (`top_left_pencil.py`, `state_machine.py`).
   - Sửa theo hướng chuẩn hóa parameterized, giữ nguyên safety gates (device lock, recovery ladder).
   - CẤM viết script tap tay `adb shell input tap`, cấm tạo file probe tạm để bấm qua màn hình lỗi.
3. **Runner là Tác Nhân Duy Nhất Trên Thiết Bị:**
   - Chỉ runner chính thức mới được thay đổi trạng thái UI/device.
   - Agent chỉ làm các việc read-only (`inspect_machine.py`, `screencap`, `dumpsys`).
   - Nghiệm thu kết quả BẮT BUỘC chạy canary qua chính runner đó kèm `MEDIA:<path>` sau khi đã soi mắt qua vision.

## 3. Quy Trình 4 Bước Bắt Buộc Trước Khi Code
1. **Discover:** Tra cứu đích danh trong `D:\Taadaa\tools\` và repo sở hữu (theo bảng Hard Routing). Dùng `ls` hoặc grep có phạm vi hẹp. Cấm quét đĩa diện rộng.
2. **Decide:** Chọn 1 trong 3 nhánh:
   - (A) Dùng nguyên trạng: Chỉ đổi tham số CLI.
   - (B) Parameterize runner: Bổ sung cờ tham số còn thiếu vào chính runner.
   - (C) Fix in core: Sửa lỗi handler/selector trong core codebase của runner.
   *(Chỉ khi cả A, B, C đều không thể và User duyệt mới được tạo script mới).*
3. **Fix in Core (nếu B hoặc C):** Kiểm tra màn hình thật của thiết bị live (screencap + XML dump). Phân tầng can thiệp T1 (<= 15 dòng) hoặc T2 (Worker contract O(1)). Chỉ chạy focused test < 30s.
4. **Verify & Record:** Chạy canary qua chính runner trên đúng máy target đến trạng thái verified (`exit=0`). Chụp ảnh nghiệm thu `MEDIA:<path>`.
