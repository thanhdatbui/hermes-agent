# Mass Upload Alert Triage & Slot Recovery Protocol (16/10/2026)

Hướng dẫn đối soát, phân loại và xử lý khi nhận cảnh báo Farm Alert lỗi script upload hàng loạt (15+ máy) trong các ca nuôi TikTok Phone Farm.

---

## 1. Phân Loại 3 Tầng Lỗi Upload Hàng Loạt (Mass Upload Triaging)

Khi nhận bản tin cảnh báo hàng loạt (ví dụ: `15 máy lỗi script Upload - Ca 2 - Phiên 2/2 (Row 4)`), **CẤM TUYỆT ĐỐI** quy chụp toàn bộ do bug code hoặc đứt cáp phần cứng. Bắt buộc đối soát log và phân loại thành 3 nhóm độc lập:

### Tầng 1: Rớt kết nối ADB / USB Timeout tức thời (Transient EHCI Drop)
- **Triệu chứng trong log:**
  - `[DEVICE_OFFLINE] device is offline or ADB/USB disconnected ... adb.exe: device '...' not found`
  - `adb command timed out: ... ip addr show tun0`
  - `[OPEN_TIKTOK_FAILED] ... force_stop_app failed: device not found`
- **Bản chất kỹ thuật:**
  - Xảy ra khi 20–40 workers cùng chạy tác vụ nặng (render FFmpeg, đẩy file MP4 qua USB, chụp màn hình, ATX-agent dump XML). Buffer bus USB 2.0 EHCI của host bị nghẽn tạm thời, khiến một số lệnh ADB bị rớt hoặc timeout >10s.
- **Kiểm chứng tức thời O(1):**
  - Chạy `python D:/Taadaa/tools/inspect_machine.py <N>` hoặc kiểm tra `adb devices` sau khi ca chạy kết thúc.
  - Nếu thiết bị báo `device`, pin sạc tốt và phản hồi shell bình thường: Khẳng định 100% là lỗi **TRANSIENT (L0)**.
  - Thiết bị hoàn toàn khỏe mạnh, không cần reboot vật lý và sẽ tự động được cuốn chiếu nạp lại ở ca tiếp theo.

---

### Tầng 2: Lỗi Giao Diện UI / Verification / Idempotency
- **Trường hợp A: Video đã upload nhưng Profile grid chưa kịp hiển thị (`POST_RECHECK_UNAVAILABLE`)**
  - **Dấu hiệu:** `report.json` và `checkpoint.json` ghi nhận:
    * `post-published-surface.png` đã được chụp lưu trong thư mục run.
    * Submission đã rời Composer.
    * `media_fingerprint` đã ở trạng thái `RESERVED`.
  - **Bản chất:** Video thực tế đã được gửi lên server TikTok thành công. Tuy nhiên TikTok có độ trễ duyệt nội bộ, khiến bước `POST_RECHECK` quét 3 viewports chưa thấy số lượng video tăng so với baseline.
  - **Xử lý:** Idempotency Guard đã chặn repost để chống đăng trùng clip. **CẤM** cố tình ép đăng lại ngay lập tức. Tracker định kỳ (`cron_tiktok_daily_tracker.py`) sẽ tự động quét và cập nhật số lượng video chính xác.
- **Trường hợp B: Gate thị giác từ chối nút tạo video (`VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED`)**
  - **Dấu hiệu:** Log ghi nhận `Visual create-button gate rejected screenshot: white=0.845, dark=0.052, cyan=0.000, red=0.034`.
  - **Bản chất:** App TikTok hiển thị popup khảo sát, onboarding, hoặc giao diện Home bị che khuất khiến script không định vị được nút `[+]` ở đáy màn hình.
- **Trường hợp C: Lỗi Account Switcher (`ACCOUNT_SWITCHER_FAILED`)**
  - Mở switcher thành công nhưng thiếu nick mục tiêu (`ACCOUNT_MISSING`) hoặc không xác nhận được marker của switcher. Cần kiểm tra lại phiên đăng nhập TikTok.

---

### Tầng 3: Bẫy Hết Video / Nhảy Cóc Dãy Số Thứ Tự
- **Triệu chứng:** Runner báo lỗi `[VIDEO_PATH_ERROR] RESOLVE_NEXT_VIDEO: Cannot resolve video path: Video file not found: D:\TIKTOK-videonuoinick\<F_vid>\<N>.mp4`.
- **Bản chất bẫy nhảy cóc (Discontinuous Sequence Trap):**
  - Cột `Video Đã Đăng` trong file Excel (ví dụ `Tik4.xlsx`) ghi `10` clip (clip tiếp theo cần đăng là `11.mp4`).
  - Trong folder `D:\TIKTOK-videonuoinick\<F_vid>`, tồn tại các clip `1..10.mp4` và `27..61.mp4`, nhưng hoàn toàn thiếu các clip ở giữa (`11..26.mp4`) do các đợt render trước bị ngắt quãng.
- **Quy trình Render bù O(1) bằng script canonical:**
  1. Xác định folder video nguồn trong `D:\video goc\<F_src>` (ví dụ Folder 300).
  2. Tạo danh sách file cần render bù vào file tạm (ví dụ `tmp_list.txt` chứa `D:\video goc\300\11.mp4`).
  3. Gọi `random_batch_render.py` với cấu hình chuẩn:
     ```bash
     python -u scripts/random_batch_render.py \
       --input-dir "D:/video goc/<F_src>" \
       --output-dir "D:/TIKTOK-videonuoinick/<F_vid>" \
       --preset "presets/preset_owner.json" \
       --file-list "tmp_list.txt" \
       --start-seq <N> \
       --slot <slot> \
       --machine-id <m_idx> \
       --randomize \
       --parallel 1
     ```
  4. Xác nhận file rendered sinh ra đủ dung lượng (>5MB) và ffprobe hợp lệ.

---

## 2. Quy Chuẩn Khởi Chạy Canary Phục Hồi Đơn Máy (Single-Device Recovery)

Khi cần chạy thử nghiệm hoặc phục hồi upload bù cho 1 máy lẻ mà không kích hoạt batch toàn farm:

1. **Tạo script wrapper canary chuẩn (`run_canary_m<N>.py`):**
   ```python
   import sys, subprocess

   SERIAL = "<serial_thiet_bi>"
   MACHINE = <so_may>
   SLOT = <slot>
   VIDEO_NUM = "<clip_can_dang>"

   cmd = [
       sys.executable,
       "-m", "scripts.tiktok_workflow",
       "--config", "config.example.yaml",
       "--workflow-workbook", rf"D:\OneDrive\TaadaaData\kibe\Tik{SLOT}.xlsx",
       "--single-device", SERIAL,
       "--video-number", str(VIDEO_NUM),
       "--video-source-root", r"D:\TIKTOK-videonuoinick",
       "--allow-device-reboot-recovery",
       "--no-dry-run",
   ]
   res = subprocess.run(cmd, input="YES\n", text=True, cwd=r"D:\Taadaa\Tiktok-video")
   sys.exit(res.returncode)
   ```
2. **Kỷ luật Event-Driven (Cấm Polling):**
   - Với tác vụ chạy >30s (upload thường mất 2–4 phút), bắt buộc khởi chạy qua:
     `terminal(command="python D:/Taadaa/Tiktok-video/run_canary_m<N>.py", background=True, notify_on_complete=True, timeout=300)`
   - CẤM TUYỆT ĐỐI viết vòng lặp `while True: sleep(5)` để thăm dò tiến trình. Để harness tự đánh thức khi tiến trình hoàn thành.

---

## 3. Kỷ Luật Thị Giác: Invariant Chống Gửi Ảnh Cho Có Lệ (GATE 6)

- **Nguyên tắc cốt lõi:** Trước khi đính kèm bất kỳ thẻ `MEDIA:<path>` nào lên chat, Coordinator **BẮT BUỘC** gọi `browser_vision` (hoặc WinRT OCR) mở ảnh ra soi mắt kiểm tra trước.
- **Tiêu chuẩn kiểm tra:**
  1. **Đúng màn hình đích:** Phải là Profile grid, Composer, hoặc Switcher.
  2. **Nội dung mới:** Số video tăng, tên nick khớp.
  3. **Không lỗi hiển thị:** Không gửi ảnh đen (`màn hình đen`), không gửi màn hình bị popup che, không gửi ảnh bay mép lẹm chữ.
- **Xử lý tình huống màn hình tắt/ngủ:**
  - Nếu chụp màn hình thiết bị khi máy đang ở chế độ ngủ (sau khi watchdog `farm-idle-screen-and-app-healer` đưa về HOME và tắt màn hình): Ảnh thu được sẽ là màn hình đen hoàn toàn (~12KB).
  - **Hành động bắt buộc:** CẤM gửi thẻ `MEDIA:` đối với ảnh đen này. Báo cáo rõ bằng lời cho User: *"Đã kiểm tra qua vision, thiết bị đang ở trạng thái sleep/tắt màn hình bảo vệ pin theo đúng watchdog"* thay vì ném link ảnh vô cảm.
