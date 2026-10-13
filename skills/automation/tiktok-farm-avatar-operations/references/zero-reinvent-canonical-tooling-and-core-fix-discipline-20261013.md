# Zero Re-invent, Canonical Tooling & Fix-at-Source Discipline (2026-10-13)

**Author:** Claude Code CLI & Hermes Coordinator  
**Target:** Toàn bộ tác vụ Avatar & Automation trên Taadaa Farm  

---

## 1. Bản Chất Sự Cố & Lỗi Hành Vi Bị User Phạt Nặng
- **Sự cố:** Khi runner chuẩn `run_tiktok_upload_avatar.ps1` chạy cho Máy 33 (Layout C) gặp lỗi `[AVATAR_EDIT_OPEN_FAILED] ENSURE_AVATAR: Màn Sửa hồ sơ không mở`, Agent suýt nữa tái diễn thói quen xấu: **đi tìm script tap tay ngoài lề (`do_upload_avatar_m71.py`) định sửa tọa độ tap bừa bãi**, thay vì phân tích log để sửa vào core runner.
- **User chất vấn gay gắt:**
  > *"Là t ns mày ms đọc script chứ trc đó tính viết nguyên code upload ava lại đúng k"*  
  > *"Xử lý đi. R làm sao có cơ chế cho mày ưu tiên tìm script có sẵn r chạy (kể cả fix cũng handle luôn vào script có sẵn) thay vì tự ngồi chế lại cái bánh xe đã có sẵn"*  
  > *"Bảo claude cli thiết kế để mày ưu tiên tìm script đã có thay vì đi tự chế lại đi"*

---

## 2. Ba Nguyên Tắc Vàng (Invariants Cốt Lõi)

1. **Zero Re-invent (Tìm trước, viết sau):**
   - Trước khi viết bất kỳ dòng code nào, BẮT BUỘC chứng minh bằng bằng chứng (evidence) rằng chưa có tool/runner làm được việc này.
   - Nguồn tra cứu theo thứ tự:
     1. `D:\Taadaa\tools\` (bộ runtime tool dùng chung của farm).
     2. Runner của repo sở hữu theo quy chuẩn Hard Routing (ví dụ: `run_tiktok_upload_avatar.ps1`, `run_avatar_m1.py <M>`).
   - Chỉ đổi input (machine, row, config path) qua CLI hoặc config. **CẤM tạo launcher, loop hay wrapper mới.**

2. **Fix at Source (Lỗi ở đâu, sửa vào core ở đó):**
   - Runner gặp màn hình hoặc popup lạ thì BẮT BUỘC sửa handler, selector hoặc state machine trong chính codebase của runner đó (ví dụ: `tiktok_workflow/profile_layouts/top_left_pencil.py`).
   - Sửa theo hướng parameterized/mở rộng chuẩn hóa, giữ nguyên safety gates (device lock, verifier, recovery ladder 3 bước).
   - **CẤM TUYỆT ĐỐI** viết script tap tay, `adb shell input tap/swipe`, hoặc probe tạm trong `%TEMP%` để "cho qua" target.

3. **Runner là tác nhân duy nhất trên thiết bị:**
   - Chỉ runner chính thức mới được thay đổi trạng thái UI/device.
   - Agent chỉ làm việc read-only để thu evidence: `inspect_machine.py <N>`, `screencap`, `uiautomator dump`, `dumpsys`.
   - Nghiệm thu bằng canary chạy qua chính runner đó, kèm hình ảnh `MEDIA:<path>`. Self-report của worker không phải bằng chứng.

---

## 3. Quy Trình 4 Bước Bắt Buộc Trước Khi Code

| Bước | Tên | Hành động | Output bắt buộc |
|---|---|---|---|
| **1** | **Discover** | Tra theo đích danh trong `D:\Taadaa\tools\` và repo sở hữu (`Script:` → repo → runner). Dùng `ls` hoặc tìm kiếm có phạm vi. CẤM `os.walk`, `grep -r` trên cả `D:\`. Đọc `docs/farm-automation-cases.md` để tránh tái phạm anti-pattern cũ. | Danh sách ứng viên: path, entrypoint, tham số |
| **2** | **Decide** | Chọn đúng 1 nhánh:<br>• **(A)** Dùng nguyên trạng, đổi tham số.<br>• **(B)** Runner thiếu tham số hoặc hardcode $\rightarrow$ Parameterize chính runner đó.<br>• **(C)** Runner lỗi ở hiện trường $\rightarrow$ Sửa handler trong core.<br>*Chỉ khi cả A, B, C đều không khả thi và user đã chốt thì mới được tạo script mới, kèm lý do.* | Quyết định A/B/C + canonical script path + data path/row |
| **3** | **Fix in Core**<br>*(Chỉ khi B hoặc C)* | Check màn thật của đúng serial trước (screencap + dump live, không tin artifact cũ). Ghi baseline rollback trước khi sửa. Phân tầng: **T1** (1 file, ≤15 dòng, có focused test <30s) thì coordinator tự sửa. **T2** (≥2 file, >15 dòng) thì spawn worker kèm contract O(1). Chỉ chạy focused test, không chạy full suite. | Diff trong core, focused test pass |
| **4** | **Verify & Record** | Chạy canary qua đúng runner trên đúng máy target đến hết luồng (`final_status: success`). Chụp screencap `MEDIA:<path>`. Cập nhật `docs/farm-automation-cases.md`. Với automation thì chạy thêm `done_gate.py`. | Log runner, MEDIA, diff docs, commit SHA |

---

## 4. Case Study Thực Chiến (Sửa Core Layout C Cho Máy 33)
- **Vấn đề:** Runner `run_tiktok_upload_avatar.ps1` reject giao diện Samsung S7 (TikTok v47) vì icon Sửa hồ sơ góc trên bên trái có bounds `[0,75][168,243]` (`left = 0 < 10`, `w = 168 > 130`).
- **Thực thi đúng chuẩn:**
  1. Không viết script click tay tạm bợ.
  2. Sửa trực tiếp trong core: `D:/Taadaa/Tiktok-video/scripts/tiktok_workflow/profile_layouts/top_left_pencil.py`:
     ```python
     # Trước:
     if 10 <= n.l <= 45 and 70 <= n.t <= 130:
         if 50 <= n.w <= 130 and 50 <= n.h <= 130:
     # Sau:
     if 0 <= n.l <= 45 and 70 <= n.t <= 130:
         if 50 <= n.w <= 170 and 50 <= n.h <= 170:
     ```
  3. Kích hoạt lại chính runner chuẩn `run_avatar_m1.py 33` để hệ thống tự động hoàn tất.
