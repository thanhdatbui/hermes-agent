# Zero Re-invent & Fix-at-Source Protocol (Claude Code Design Spec)

**Incident Date:** 2026-10-13  
**Trigger:** User gắt gao chất vấn Agent tự chế lại code upload avatar thay vì tìm đọc và sử dụng script canonical đã có sẵn:  
*"Là t ns mày ms đọc script chứ trc đó tính viết nguyên code upload ava lại đúng k"*  
*"Bảo claude cli thiết kế để mày ưu tiên tìm script đã có r chạy (kể cả fix cũng handle luôn vào script có sẵn) thay vì tự ngồi chế lại cái bánh xe đã có sẵn"*

---

## 1. 3 Nguyên Tắc Vàng (Bất Biến)

1. **Zero Re-invent (Tìm trước, viết sau):**
   - Trước khi viết bất kỳ dòng code nào, phải chứng minh bằng evidence rằng chưa có tool/runner làm được việc này.
   - Nguồn tra cứu bắt buộc theo thứ tự:
     1. `D:\Taadaa\tools\` (runtime dùng chung; source ở repo `AI-Tools`).
     2. Runner của repo sở hữu, xác định theo trường `Script:` của alert hoặc bảng Hard Routing (ví dụ: `run_tiktok_upload_avatar.ps1`, `run_avatar_m1.py <M>`).
   - Chỉ đổi input (machine, row, config path) qua tham số CLI hoặc config. **CẤM TUYỆT ĐỐI tạo launcher, loop hay wrapper mới.**

2. **Fix at Source (Lỗi ở đâu, sửa vào core ở đó):**
   - Khi runner chính thức gặp lỗi hiện trường (ví dụ: `[AVATAR_EDIT_OPEN_FAILED] ENSURE_AVATAR: Màn Sửa hồ sơ không mở` do layout detector reject Samsung S7), **BẮT BUỘC sửa/handle trực tiếp vào core codebase của chính runner đó** (`top_left_pencil.py`).
   - Sửa theo hướng parameterized/mở rộng, giữ nguyên các safety gates (device lock, verifier, recovery ladder 3 bước).
   - **CẤM TUYỆT ĐỐI** viết script tap tay, `adb shell input tap/swipe`, hoặc code probe tạm trong `%TEMP%` để "bấm qua" màn hình lỗi thay cho sửa code runner.

3. **Runner là tác nhân DUY NHẤT tác động lên thiết bị:**
   - Chỉ runner chính thức mới có quyền thay đổi trạng thái UI/device.
   - Coordinator và subagent chỉ làm việc read-only để thu thập bằng chứng: `inspect_machine.py <N>`, `screencap`, `uiautomator dump`, `dumpsys`.
   - Nghiệm thu bằng canary chạy qua chính runner đó kèm hình ảnh nghiệm thu thị giác `MEDIA:<path>`. Self-report của worker không phải bằng chứng.

---

## 2. Quy Trình 4 Bước Bắt Buộc Trước Khi Động Đến Code

| Bước | Tên | Hành Động | Output Bắt Buộc |
|---|---|---|---|
| **1** | **Discover** | Tra theo đích danh trong `D:\Taadaa\tools\` và repo sở hữu (`Script:` → repo → runner). Dùng `ls` hoặc file search có phạm vi. Cấm `os.walk`, `grep -r` diện rộng. Đọc `docs/farm-automation-cases.md` để tránh tái phạm anti-pattern cũ. | Danh sách ứng viên: path, entrypoint, tham số |
| **2** | **Decide** | Chọn đúng 1 trong 3 nhánh:<br>**(A)** Dùng nguyên trạng, đổi tham số CLI.<br>**(B)** Runner thiếu tham số hoặc hardcode $\rightarrow$ Parameterize chính runner đó.<br>**(C)** Runner lỗi ở hiện trường $\rightarrow$ Sửa handler/selector trong core.<br>*Chỉ khi cả A, B, C đều không khả thi và User đã chốt thì mới được tạo script mới, kèm lý do.* | Quyết định A/B/C + path script canonical + data row |
| **3** | **Fix in Core**<br>*(Chỉ khi B hoặc C)* | Kiểm tra màn hình thật của đúng serial thiết bị live (screencap + XML dump live). Ghi baseline rollback trước khi sửa. Phân tầng: T1 (1 file, ≤15 dòng) thì coordinator tự sửa; T2 (≥2 files, >15 dòng) thì spawn worker kèm contract O(1). Chỉ chạy focused test <30s, không chạy full suite. | Diff trong core + focused test PASS |
| **4** | **Verify & Record** | Chạy canary qua đúng runner trên đúng máy target đến hết luồng (`final_status: success`). Chụp ảnh nghiệm thu `MEDIA:<path>`. Cập nhật `docs/farm-automation-cases.md`. Với automation thì chạy Closeout Gate. | Log runner PASS + MEDIA ảnh thật |

---

## 3. Điều Kiện Dừng & Cấm Tuyệt Đối

- **Chưa tìm thấy runner phù hợp:** Dừng lại báo cáo `NO_CANONICAL_RUNNER` kèm danh sách đã tra cứu, chờ User định hướng; **CẤM tự ý chế script**.
- **Runner fail sau khi hết budget tầng:** Chuyển `BLOCKED` kèm bằng chứng lỗi thật, không vá tạm bợ ngoài lề.
- **Cấm tạo script tap tay:** Mọi hành vi dùng `input tap` để lách lỗi màn hình đều bị phạt nặng vì phá vỡ tính tự động hóa dài hạn của hệ thống.
