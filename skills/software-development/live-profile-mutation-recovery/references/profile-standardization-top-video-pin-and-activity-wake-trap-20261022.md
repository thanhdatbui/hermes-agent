# Chuẩn Hoá Kênh: Kỷ Luật Ghim Video Top View & Bẫy Launch Activity / Lock Reclaim (2026-10-22)

## 1. Ngữ Cảnh & Sửa Đổi Của Người Dùng (User Correction 22/10/2026)
- **Phản hồi của User:** *"Chuẩn hoá là pin video có view cao t thấy có vidoe view cao m có đi pin mẹ đâu"*.
- **Bài học cốt lõi:**
  1. Khi người dùng phát lệnh "Chuẩn hoá kênh / acc": Gói chuẩn hoá BẮT BUỘC gồm 3 hạng mục:
     - **Avatar mới:** Trích xuất ngũ quan nét từ video gốc, crop chuẩn 512x512, khóa marker `.manual_avatar_locked`.
     - **Hashtag & Niche:** Đồng bộ CSDL và Workbook, khóa `.manual_hashtag_locked`.
     - **Ghim Video (Pin Top Videos):** Quét toàn bộ lưới video trên profile, chọn ra 1–3 video có lượt view cao nhất (đặc biệt các clip viral $\ge 1.000$ views) để ghim lên đầu hàng.
  2. **Bẫy Dương Tính Giả (False-Positive Pinned Badge):**
     - Tuyệt đối CẤM kết luận "đã ghim clip viral" khi chỉ thấy trên profile có chữ "Đã ghim" ở clip đầu tiên.
     - Hiện trường thực tế: Kênh có thể đang ghim một clip cũ lẹt đẹt vài trăm view (ví dụ 489 view), trong khi clip viral 28.8K view nằm ở hàng dưới và CHƯA HỀ ĐƯỢC GHIM.
     - Agent BẮT BUỘC soi mắt qua WinRT OCR / Vision đối chiếu đồng thời: nhãn "Đã ghim" PHẢI nằm cùng ô với số view cao nhất (ví dụ `28.8K` hoặc `31.3K`). Nếu chưa, bắt buộc kích hoạt chế độ hoán đổi (`--action swap`).

## 2. Bẫy TikTok Splash Launch Activity trên Samsung S7 (v47.x)
- Khi gọi `am start` đánh thức TikTok:
  - Lệnh gọi sai: `am start -n com.ss.android.ugc.trill/.SplashActivity` -> Báo lỗi:
    `Error type 3: Activity class {com.ss.android.ugc.trill/com.ss.android.ugc.trill.SplashActivity} does not exist.`
  - Lệnh gọi chuẩn xác:
    `am start -n com.ss.android.ugc.trill/com.ss.android.ugc.aweme.splash.SplashActivity`
- Nếu app chưa được đưa lên foreground đúng activity trước khi dump UI, ATX Agent (port 7912) sẽ timeout hoặc trả về non-XML UI state (`UI_DUMP_INVALID`), làm gãy toàn bộ luồng `open_profile_root`.

## 3. Quy Trình Thu Hồi Device Lock Sau Khi Tool Timeout (Dead PID Reclaim)
- Khi `pin_top_videos.py` hoặc runner can thiệp timeout, file lock `machine_N.lock.json` và `serial_SERIAL.lock.json` vẫn nằm lại trong `~/.codex/device-locks/` với trạng thái `status: running`.
- Kỷ luật an toàn:
  1. Kiểm tra liveness của PID sở hữu lock qua `psutil.pid_exists(pid)`.
  2. Nếu PID đã chết hoàn toàn trên hệ điều hành, cho phép dọn file lock rác hoặc gọi `operator_device_lock(..., force_preempt=True)` để lấy lại quyền điều khiển mà không vi phạm an toàn farm.
  3. Tuyệt đối CẤM ngắt hoặc cướp lock của tiến trình nuôi nick (`multi-machine-feed-session`) khi PID đó vẫn đang sống.

## 4. Checklist Nghiệm Thu Bắt Buộc Khi Chuẩn Hoá
- [ ] Ảnh profile trích xuất frame từ video gốc, không dính caption/chữ.
- [ ] Marker `.manual_avatar_locked` & `.manual_hashtag_locked` đã tồn tại trong cả thư mục gốc và thư mục render.
- [ ] Workbook `TaiKhoan` và `Hashtag theo Folder` khớp 100% niche.
- [ ] Clip có view cao nhất trên profile có nhãn "Đã ghim" hiển thị trực tiếp trên ảnh nghiệm thu gửi qua `MEDIA:`.
