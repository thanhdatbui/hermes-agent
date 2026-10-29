---
name: taadaa-farm-ops-rules
description: "Taadaa farm safety, close-session, and multi-machine operations."
---
# Taadaa Farm Operations Rules & Invariants

## 1. Nguyên Tắc Cốt Lõi (Invariants)
- **Tra cứu O(1):** Khi nhận Farm Alert `[MÁY N]`, chạy duy nhất `python D:/Taadaa/tools/inspect_machine.py <N>`. (Hook `guard_broad_grep.py` chặn đệ quy).
- **Chụp ảnh trước Teardown (Capture-Before-Cleanup):**
  1. Chụp ảnh hiện trường (`MEDIA:<path>`).
  2. WinRT OCR / Vision kiểm chứng chữ trên màn hình.
  3. Chỉ thực hiện `am force-stop` và `input keyevent KEYCODE_HOME` sau khi đã có ảnh. CẤM chụp ảnh màn hình HOME làm nghiệm thu.
- **Cấm tap tay qua ADB:** Không chạy `input tap`, `input keyevent`, `input swipe` để bấm qua màn hình lỗi. Sửa code trong script để cả dàn máy tự động vượt qua.
- **Task ngầm / Cronjob:** Hook `guard_cronjob_safety.py` tự động ép cứng `CREATE_NO_WINDOW (0x08000000)` và `Hidden`, cấm pop console cướp focus. Mọi lệnh subprocess trên Windows bắt buộc OR-merge `creationflags |= 0x08000000`.
- **Cấm quét đĩa diện rộng (Anti-Scan Guard):** CẤM chạy `search_files` trên root `D:/Taadaa` hoặc `D:/Taadaa/tools`, cấm script có `os.walk` / `glob recursive`. Bắt buộc chỉ định đích danh file hoặc thư mục con hẹp.
- **Khóa thiết bị JIT (Device Lock Mandatory):** Mọi can thiệp ADB vào máy thật bắt buộc giữ JIT device lock (`inspect_machine.py <N>` hoặc `with_device_lock.py --machine <N> -- ...`), cấm can thiệp trần.
- **Độc Lập Tuyệt Đối 3 Quy Trình:** Ba quy trình Feed — Follow — Upload chạy độc lập tuần tự; trước fail thì sau vẫn chạy bình thường. Chu kỳ 3 ngày lệch pha an toàn.
- **Phân Cấp Nhịp Sync Hạ Tầng (Cold Backup Cadence):** Khi máy phụ (Admin) chỉ làm cold backup, các cron job sync hạ tầng Hermes (skills, brain memories, jobs.json) bắt buộc giãn nhịp lên 6h–24h/lần (cấm để 5m–15m gây xung đột `.git/index.lock`, nghẽn I/O 4.500+ skills và lock file OneDrive). Chi tiết: `references/cold-backup-host-sync-cadence-and-git-lock-prevention.md`.

## 2. Chu Trình Điều Phối Farm (Coordinator vs Worker)
- **T0 (Hiện trường):** Đọc log, inspect ADB O(1), restart process, kiểm tra proxy. Tự do thực thi.
- **T1 (Vá hiện trường <= 15 dòng):** Sửa trực tiếp O(1) 1 file, verify < 30s, chạy Canary trên 1 máy thật đại diện (chụp ảnh `MEDIA:` + OCR sạch).
- **T2 (Thi công lớn > 15 dòng):** Dispatch qua Single Dispatch Gateway `python D:/Taadaa/tools/dispatch_worker.py "<contract O(1)>" --workdir <repo>`.
- **Chốt phiên (Closeout v2 O(1)):**
  - **Phiên Vận Hành (farm, nick, device, excel - không có code delta):** `python D:/Taadaa/tools/closeout_v2.py --repo <repo> --operational --json-output` (PASS ngay trong < 0.1s; cấm gọi LLM Reviewer).
  - **Phiên Sửa Code:** `python D:/Taadaa/tools/closeout_v2.py --repo <repo> --json-output` (py_compile cú pháp + pytest focused; cấm LLM chấm điểm cảm tính).

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
