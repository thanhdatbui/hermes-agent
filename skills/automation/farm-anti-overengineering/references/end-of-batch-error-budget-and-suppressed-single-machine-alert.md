# End-of-Batch Error Budget, Auto-Lock Elimination, and Immediate Alert Suppression (Taadaa Farm)

Đúc rút từ phiên tái cấu trúc cơ chế báo động và quản lý khóa thiết bị trên Taadaa Phone Farm (07/09/2026).

---

## 1. Bối cảnh & Vấn đề gốc rễ (Alert Fatigue & False Lock Gridlock)

### 1.1. Bẫy kiệt sức vì báo động (Alert Fatigue)
- Trên đàn hàng chục thiết bị Android cũ (Samsung S7) qua proxy xoay vòng, việc dính 1 nhịp lag mạng 5s, trễ animation hay frame drop là **nhiễu môi trường tự nhiên (Transient Blip)**.
- Khi hệ thống cấu hình `send_farm_machine_alert` bắn tin Telegram ngay lập tức cho từng máy đơn lẻ, người vận hành phải hứng chịu 10–20 alert rác mỗi ngày, dẫn tới kiệt sức và mất tập trung vào các sự cố hệ thống thật sự.

### 1.2. Bẫy tê liệt thiết bị vì giữ Lock 1h (Fast-Fail Lock Trap)
- Quy định cũ: Cứ máy nào vấp lỗi thì giữ `device_lock` 1h dạng `handoff` để làm hiện trường inspect.
- Hậu quả: Các máy lỗi ngẫu nhiên bị khóa cứng 1 tiếng đồng hồ, làm giảm nghiêm trọng throughput của các batch chạy kế tiếp, gây thiếu hụt tài nguyên đàn máy trong khi lỗi không hề lặp lại.

---

## 2. Ba Nguyên Tắc Cải Cách Tối Thượng (User Mandate)

### Nguyên tắc 1: Tách bạch Forensics khỏi Lock (Snapshot-on-Fail)
- **Snapshot (Bằng chứng tĩnh):** Cực rẻ (~300ms, vài trăm KB). Khi máy vấp lỗi, script BẮT BUỘC chụp ngay 1 screencap PNG + 1 UI XML dump lưu vào thư mục run (`.ai-runs/` hoặc `runs/`).
- **Lock (Giữ máy live):** Cực đắt. BỎ HOÀN TOÀN cơ chế tự động lock 1h khi lỗi. Chụp snapshot xong là `am force-stop` đưa app về Home và **nhả device lock ngay lập tức** (`release_on_terminal=True` mặc định trong `automation_core.device_lock`).

### Nguyên tắc 2: Gom lỗi cuối batch với Ngưỡng Kép (Dual-Threshold Batch Aggregator)
- Trong lúc batch đang chạy: **Im lặng tuyệt đối (Silent Run)**. Khóa cứng `send_farm_machine_alert` trong `alerts.py` (chỉ ghi log, suppress không bắn Telegram trừ khi có cờ `AUTOMATION_CORE_IMMEDIATE_MACHINE_ALERT=1`).
- Sau khi batch kết thúc: Module `automation_core.batch_aggregator` gom kết quả toàn đàn theo **Error Signature** đã chuẩn hóa (loại bỏ serial máy, timestamp, toạ độ ngẫu nhiên, PID).
- **Bộ lọc Ngưỡng Kép:**
  $$\text{Tỷ lệ cùng 1 lỗi} \ge 10 - 15\% \quad \mathbf{VÀ} \quad \text{Số máy dính} \ge 3 \text{ máy}$$
  - **Dưới ngưỡng:** Silent Skip, ghi nhận nội bộ, KHÔNG gửi alert Telegram, không làm phiền người vận hành.
  - **Vượt ngưỡng:** Kích hoạt đúng **1 Farm Alert tổng hợp** kèm danh sách máy dính, tỷ lệ % và 1–2 ảnh snapshot đại diện (`MEDIA:<path>`).

### Nguyên tắc 3: Quy chuẩn Canary MỚI — Bắt buộc chạy lại full script lỗi
- **CẤM TUYỆT ĐỐI** việc kiểm chứng Canary chỉ bằng vài cú swipe feed ngẫu nhiên (`random swipes`) khi lỗi nằm ở các flow nghiệp vụ (Reg, Upload, Login/2FA).
- **Quy tắc thực chiến:** Sau khi vá code:
  - Lỗi ở Flow Reg $\rightarrow$ Canary bắt buộc chạy lại đúng script Reg từ A $\rightarrow$ Z với 1 account mới cho đến khi đăng ký thành công.
  - Lỗi ở Flow Upload $\rightarrow$ Canary bắt buộc chạy lại đúng script Upload 1 video hoàn chỉnh cho đến khi publish thành công.
  - Chỉ khi nào kịch bản nghiệp vụ chạy hoàn tất 100% mới được nghiệm thu Canary PASS.

---

## 3. Cạm Bẫy Thực Thi & Kỷ Luật Điều Phối (Coordinator Discipline)

| Cạm bẫy thực tế | Hậu quả | Kỷ luật bắt buộc |
| :--- | :--- | :--- |
| **Bỏ quên suppression trong `alerts.py`** | Đã viết aggregator nhưng caller trong worker (`feed_swipe_smoke.py`) vẫn gọi `send_farm_machine_alert` bắn lẻ giữa chừng. | Bắt buộc đặt guard kiểm tra env `AUTOMATION_CORE_IMMEDIATE_MACHINE_ALERT` trong `send_farm_machine_alert`, mặc định suppress 100% khi chạy batch. |
| **Bỏ quên hook trên các runner khác nhau** | Gắn hook ở batch Upload (`run_tiktok_upload_batch.ps1`) nhưng quên luồng Feed (`run-feed-session.ps1`) khiến ca lướt feed chạy xong không có báo cáo tổng kết. | Kiểm tra và gắn hook `python -m automation_core.batch_aggregator <run_dir|summary.csv> --telegram` vào tất cả các batch runner chính thức. |
| **Dừng lại hỏi han / báo từng sub-phase vụn vặt** | Khi user đã ra lệnh *"Rồi làm đi"*, Coordinator lại dừng ở từng phase (xong Phase 1 hỏi có làm Phase 2 không) làm ngắt quãng trải nghiệm của user (*"Làm xong hết luôn r báo đừng dừng lại báo từng phase nữa"*). | **Kỷ luật End-to-End Execution:** Khi đã có lệnh triển khai, Coordinator điều phối worker thực thi trọn gói từ A $\rightarrow$ Z (Sửa code $\rightarrow$ Test $\rightarrow$ Hook $\rightarrow$ Claude Review APPROVED), chỉ báo cáo tổng kết một lần khi đã hoàn tất toàn bộ. |
| **Đổi cờ lock làm nuốt exception trên Windows** | Khi nhả lock trong `__exit__` hoặc `finish()`, lệnh unlink có thể ném `OSError` (WinError 32) che mất exception gốc của ứng dụng. | Bọc `try/except (OSError, DeviceLockReleaseError)` quanh `release()`, bảo lưu `ambient_exc = sys.exc_info()[1]` trước khối `try:`, không re-raise nếu đang unwind exception gốc. |
