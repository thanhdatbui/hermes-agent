# Startup Heuristic Auto-Resume Cho Hermes Gateway Khi Reboot Tay / Sập Nguồn

## 1. Bối cảnh & Điểm mù của cơ chế cũ
- Trước đây, cơ chế tự động đánh dấu resume session (`preserve_in_flight_sessions`) chỉ được gọi bên trong script cronjob `services/Taadaa_Service/farm_preflight_daily_reset.py` trước khi máy tự reboot theo lịch (05:20, 11:20, 17:20).
- **Điểm mù:** Khi người dùng tự tay bấm Restart Windows (`Start -> Restart`), tắt nóng nút nguồn, mất điện đột ngột hoặc Windows Update tự khởi động lại:
  + Script `farm_preflight_daily_reset.py` hoàn toàn không có cơ hội được thực thi.
  + File `.clean_shutdown` không bị xóa và cờ `resume_pending` trong `gateway_routing` SQLite không được bật.
  + Khi máy tính bật lại, Hermes Gateway khởi động lên thấy không có cờ `resume_pending = true` nên rơi vào trạng thái im lặng chờ tin nhắn mới, buộc người dùng phải gõ nhắc nhở thì session mới tiếp tục.

---

## 2. Kiến trúc giải pháp: Startup Heuristic Hook (00_Hermes_AutoResume_Hook.vbs)

Thay vì cố gắng bắt sự kiện shutdown (dễ bị bỏ sót khi mất điện hoặc tắt đột ngột), hệ thống áp dụng cơ chế **Startup Heuristic Detection**:
Quét kiểm tra trạng thái SQLite ngay lúc Windows vừa khởi động lên, TRƯỚC KHI Hermes Gateway khởi động.

### A. File Thực Thi Lõi: `D:/Taadaa/tools/auto_resume_startup_hook.py`
- Tái sử dụng hàm chuẩn `preserve_in_flight_sessions(lookback_minutes=60)` từ `services.Taadaa_Service.farm_preflight_daily_reset`:
  1. Xóa marker `.clean_shutdown` trong `HERMES_HOME` để mở khóa cho Gateway tự resume.
  2. Quét toàn bộ entry trong bảng `gateway_routing` có hoạt động trong 60 phút gần nhất (`cutoff = now - 60m`).
  3. Kiểm tra tin nhắn cuối cùng trong `messages` của từng session:
     - Nếu tin nhắn cuối là `user` hoặc `tool`, hoặc `assistant` có `tool_calls` chưa hoàn tất (tác vụ đang dở dang):
       $\rightarrow$ Bật cờ `resume_pending = True`, `resume_reason = "restart_interrupted"`.
     - Nếu tin nhắn cuối là `assistant` đã trả lời xong:
       $\rightarrow$ Bỏ qua (không spam tin nhắn rác vào chat sau khi bật máy).

### B. File Kích Hoạt Startup: `00_Hermes_AutoResume_Hook.vbs`
- Nằm tại: `C:\Users\Kibe\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\00_Hermes_AutoResume_Hook.vbs`
- Tiền tố **`00_`** đảm bảo Windows Explorer luôn thực thi script này đầu tiên theo thứ tự bảng chữ cái, trước khi chạy `Hermes_Gateway.vbs`.
- Cấu hình chạy đồng bộ ẩn (`sh.Run "python ...", 0, True`):
  + Cửa sổ ẩn 100% (không popup).
  + Chạy chờ trong ~0.05s để cập nhật xong SQLite trước khi nhường quyền cho `Hermes_Gateway.vbs` khởi động.

---

## 3. Quy trình vận hành & Kiểm chứng
- Khi Gateway khởi động (`gateway/session.py`), nó đọc `storage.sqlite` / `state.sqlite`, nhận diện ngay cờ `resume_pending = True` và tự động gửi prompt đánh thức vào đúng topic/thread Telegram để tiếp tục công việc dở dang.
- Không phụ thuộc vào nguyên nhân reboot (reboot tay, cronjob, hay crash đột ngột).
