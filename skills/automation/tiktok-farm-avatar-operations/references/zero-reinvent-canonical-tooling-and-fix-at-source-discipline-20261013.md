# Kỷ Luật Zero Re-invent & Fix-at-Source (Thiết Kế Bởi Claude Code CLI)

## 1. Bối Cảnh & Chỉ Thị Người Dùng (13/10/2026)
- **User Instruction:** *"Làm sao có cơ chế cho mày ưu tiên tìm script có sẵn r chạy (kể cả fix cũng handle luôn vào script có sẵn) thay vì tự ngồi chế lại cái bánh xe đã có sẵn."*
- **Quy định thiết kế:** Claude Code CLI thiết kế bản Design Spec đóng đinh kỷ luật: Mọi tác vụ vận hành farm BẮT BUỘC sử dụng canonical runner có sẵn. Khi gặp sự cố ở hiện trường, BẮT BUỘC sửa trực tiếp vào core codebase của chính runner đó, tuyệt đối không chắp vá bằng script tap tay ngoài lề.

## 2. 3 Nguyên Tắc Vàng (Claude Code Design Spec)
1. **Zero Re-invent (Tìm trước, viết sau):**
   - Trước khi viết bất kỳ dòng code nào, phải tra cứu danh mục tool chuẩn:
     1. `D:\Taadaa\tools\` (bộ công cụ runtime chuẩn của farm: `inspect_machine.py`, `do_logout_account.py`, v.v.).
     2. Runner canonical của repo sở hữu (ví dụ: `run_tiktok_upload_avatar.ps1`, `run_avatar_m1.py <M>`).
   - Chỉ thay đổi input (máy, row, config) qua tham số CLI hoặc config. **CẤM tạo launcher, vòng lặp loop hay script bấm tay mới.**
2. **Fix at Source (Lỗi ở đâu, sửa vào core ở đó):**
   - Khi runner vấp màn hình lạ / selector đổi / bounds lệch / timeout: BẮT BUỘC sửa trực tiếp handler, selector, hoặc state machine trong codebase của chính runner đó (`scripts/tiktok_workflow/profile_layouts/`, `automation-core`, v.v.).
   - Sửa theo hướng mở rộng có tham số/bounds chuẩn, giữ nguyên safety gates (device lock, verifier, recovery ladder).
   - **CẤM TUYỆT ĐỐI** viết script tap tay, `adb shell input tap/swipe`, hoặc code probe tạm để bấm vượt qua màn hình lỗi.
3. **Runner là tác nhân DUY NHẤT tác động lên thiết bị:**
   - Chỉ runner chính thức mới có quyền thay đổi trạng thái UI/device.
   - Agent chỉ làm các việc read-only để thu thập bằng chứng hiện trường: `inspect_machine.py <N>`, `screencap`, `uiautomator dump`.
   - Nghiệm thu kết quả bằng canary chạy qua chính runner đó kèm hình ảnh `MEDIA:<path>`.

## 3. Quy Trình 4 Bước Bắt Buộc Trước Khi Code
| Bước | Tên | Hành Động | Output Bắt Buộc |
|---|---|---|---|
| **1** | **Discover** | Tra cứu đích danh trong `D:\Taadaa\tools\` và repo runner. Đọc `docs/farm-automation-cases.md`. | Danh sách ứng viên: path, entrypoint, tham số |
| **2** | **Decide** | Chọn 1 trong 3 nhánh:<br>**(A)** Dùng nguyên trạng, đổi tham số CLI / workbook row.<br>**(B)** Runner thiếu tham số/hardcode $\rightarrow$ Parameterize chính runner đó.<br>**(C)** Runner lỗi ở hiện trường $\rightarrow$ Sửa handler/layout trong core codebase.<br>*Chỉ khi cả A, B, C đều không thể và User chốt mới được tạo tool mới.* | Quyết định A/B/C + path script canonical |
| **3** | **Fix in Core**<br>*(Chỉ khi B hoặc C)* | Kiểm tra màn hình thật của đúng serial thiết bị live (screencap + XML dump). Phân tầng T1 (<= 15 dòng) hoặc T2 (dispatch worker contract O(1)). Chạy focused test offline/mocked <30s. | Diff chuẩn trong core + focused test PASS |
| **4** | **Verify & Record** | Chạy canary qua đúng runner trên đúng máy target đến khi thành công. Chụp ảnh nghiệm thu `MEDIA:<path>` theo Gate 6. | Log runner PASS + MEDIA ảnh thật |

## 4. Case Study Điển Hình: Máy 33 (Samsung S7, TikTok v47, Layout C)
- **Hiện tượng:** Runner chuẩn `run_avatar_m1.py 33` vấp lỗi `UNKNOWN_LAYOUT` -> `[AVATAR_EDIT_OPEN_FAILED] ENSURE_AVATAR: Màn Sửa hồ sơ không mở`.
- **Phân tích hiện trường:** Kiểm tra `popup_before.xml`, icon bút chì góc trên bên trái có bounds `[0,75][168,243]`. Code cũ trong `top_left_pencil.py` chặn cứng `10 <= n.l <= 45` và `w <= 130`, nên trả về `False`.
- **Hành động Fix-at-Source:**
  - Nới bounds trong `scripts/tiktok_workflow/profile_layouts/top_left_pencil.py`: `0 <= n.l <= 45` và `w, h <= 170`.
  - Bổ sung loại trừ Feed video `long_press_layout` và telemetry log `event=top_left_pencil_matched`, `event=top_left_pencil_excluded`.
- **Nghiệm thu:**
  - Kích hoạt lại chính runner chuẩn: `python D:/Taadaa/run_avatar_m1.py 33`.
  - Runner tự động mở Sửa hồ sơ, upload avatar bé Mina, crop, lưu, cập nhật `Tik2.xlsx` cột `Avatar = OK`, đạt `verified=True`.
  - Thẩm định độc lập qua Closeout Gate (`closeout_gate.py`): Đạt verdict APPROVED (Overall Score 87/100).
