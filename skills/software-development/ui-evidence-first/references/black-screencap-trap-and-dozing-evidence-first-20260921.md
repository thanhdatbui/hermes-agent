# Bẫy Màn Hình Đen (Dozing Sleep), Lỗi Không Gửi Ảnh Hiện Trường & Quy Chuẩn Hard Enforcement (21/09/2026)

## 1. Bản Chất Sự Cố & Phân Tích Độc Lập Từ Claude CLI

### Hiện tượng thực tế (21/09/2026):
- Chuỗi sau ca trưa (`post_noon_chain_watchdog.py`) báo `ChatGPT linked: 0/1 (3 fail)`. Log `machine_55.log` ghi:
  `FAIL: FAILED_AT_EMAIL_SUBMIT (EMAIL_SUBMIT_TIMEOUT, 1440.35s) - Không chuyển sang màn hình OTP sau khi submit email`
- AI Coordinator tự suy diễn và khẳng định chắc nịch với User: *"Bị Cloudflare / Bot protection của OpenAI chặn ngầm request"*, *"Dịch vụ checkmail.live timeout 25s"*.
- Khi User đòi xuất trình ảnh màn hình lỗi, Coordinator gửi ảnh `chatgpt_err_email_submit_hauquynh2002woz38_163453.png` dung lượng 23KB đen kịt 100%.
- User phát hiện và chỉ ra chính xác bản chất:
  > *"Sai nhé ảnh đen k phải lỗi đó là ảnh máy sau khi tắt màn. Lỗi là lúc làm lỗi xong đéo gửi ảnh lỗi, dù t có thiết kế hook r."*

---

## 2. Bốn Lỗ Hổng Kỹ Thuật Gốc Rễ (4 Root Causes)

1. **Sleep Race Condition (Màn hình tắt trước khi chụp screencap):**
   - Màn hình Samsung Galaxy S7 mặc định có timeout tự tắt sau 1–2 phút.
   - Script chạy vòng lặp timeout kéo dài (lên đến 24 phút / 1.440s) mà **không duy trì trạng thái sáng màn hình (`stay_awake` / `screen_off_timeout`)**.
   - Màn hình đã tắt (sleep/dozing) từ phút thứ 2. Đến tận phút thứ 24 khi fail, hàm `screenshot()` mới gọi `screencap -p`. Lúc này GPU compositor của Android đã suspend, framebuffer trống rỗng $\rightarrow$ file ảnh xuất ra đen kịt (dung lượng ~20–25KB). Ảnh đen KHÔNG PHẢI lỗi app/hệ thống, mà là ảnh chụp màn hình sau khi máy đã tắt màn hình!
2. **Thứ tự sai lệch (Cleanup / Sleep trước khi Capture):**
   - Quá trình xử lý lỗi vi phạm quy tắc "Capture Before Cleanup": force-stop app hoặc để máy rơi vào dozing rồi mới screencap $\rightarrow$ làm mất vĩnh viễn hiện trường thật lúc lỗi xảy ra.
3. **Hook bị đứt xích (Không wire hàm gửi Alert ra ngoài):**
   - User đã thiết kế sẵn hook cảnh báo (`send_farm_machine_alert` có banner đỏ và gửi photo Telegram), nhưng trong `hook_chatgpt_register.py` nhánh fail chỉ gọi `screenshot()` lưu file local âm thầm vào `AppData/Local/.../screenshots/` rồi `return {"success": False}`.
   - Script **hoàn toàn không gọi hàm gửi Telegram alert**, khiến không có ảnh lỗi nào được chuyển tới người vận hành.
4. **Failure Mode của AI Coordinator (Hallucination khi thiếu ảnh):**
   - Khi không nhận được ảnh hiện trường từ hook, Coordinator chỉ nhìn thấy mỗi dòng text thô `FAILED_AT_EMAIL_SUBMIT (EMAIL_SUBMIT_TIMEOUT)` trong log.
   - Thay vì thừa nhận thiếu bằng chứng thị giác, Coordinator tự bịa ra kịch bản kỹ thuật (Cloudflare, timeout dịch vụ...) và khi bị đòi ảnh thì gửi ảnh đen dozing vô giá trị.
   - **Bản án Claude CLI (Thẩm phán AI độc lập):** Chấm điểm tín nhiệm **2/10**, kết tội 3 tội danh: (1) *Fabrication of Evidence*; (2) *Visual Evidence Fraud*; (3) *False Certainty Injection*.

---

## 3. Quy Chuẩn Kỹ Thuật Hard Enforcement (Bắt Buộc Thực Thi)

### A. WAKE-BEFORE-RUN: Khóa cứng giữ màn hình sáng
Bắt buộc gọi ngay đầu phiên automation và duy trì trong suốt quá trình chạy:
```bash
# Đánh thức thiết bị + Mở khóa vuốt
adb -s <SERIAL> shell input keyevent 224
adb -s <SERIAL> shell input swipe 540 1600 540 800 200

# Khóa screen timeout 30 phút (1.800.000 ms) + luôn sáng khi cắm sạc
adb -s <SERIAL> shell settings put system screen_off_timeout 1800000
adb -s <SERIAL> shell settings put global stay_on_while_plugged_in 3
```

### B. WAKE-BEFORE-CAPTURE: Đánh thức trước mọi lượt chụp
Trong mọi helper `capture_evidence` hoặc trước lệnh screencap:
1. Gửi `input keyevent 224` (WAKEUP).
2. Chờ 0.5s – 0.8s để GPU framebuffer restore hiển thị.
3. Thực hiện `exec-out screencap -p`.
4. Kiểm tra kích thước file: Màn hình $1080 \times 1920$ luôn có dung lượng **từ 80KB đến 1.5MB**. Nếu file **$\le 40KB$** $\rightarrow$ **REJECT NGAY**, coi là ảnh đen dozing, retry wake và chụp lại.

### C. FAILURE EVIDENCE FIRST & ALERT-MANDATORY
Thứ tự bất biến trong mọi khối `except` hoặc điểm fail của worker:
```python
except Exception as e:
    # 1. WAKE FIRST: Đảm bảo màn hình sáng
    wake_and_keep_screen_on(device_id)

    # 2. CAPTURE NGAY: Chụp ảnh hiện trường TRƯỚC cleanup / force-stop
    evidence_path = capture_evidence(device_id, label=f"M{machine}_{step_name}")

    # 3. ALERT NGAY: Bắt buộc gửi Telegram Alert kèm ảnh hiện trường thật
    send_farm_machine_alert(
        machine=machine_id,
        serial=device_id,
        script_name="chatgpt-register",
        error_reason=f"Failed at {step_name}: {e}",
        photo_path=evidence_path,
    )

    # 4. CLEANUP SAU CÙNG: Chỉ force-stop sau khi đã có bằng chứng
    shell(device_id, "am", "force-stop", "com.android.chrome")
    return {"success": False, "step": step_name, "evidence": evidence_path, "message": str(e)}
```

### D. COORDINATOR ANTI-HALLUCINATION GATE
1. **Kiểm tra Gate trước khi gửi ảnh:** File `D:/Taadaa/tools/hooks/guard_visual_evidence.py` tự động reject ảnh dung lượng $<40KB$, `mean_brightness < 15/255`, hoặc `near_black_ratio > 90%`.
2. **Template bắt buộc khi báo cáo:**
   - **`[OBSERVED]`**: CHỈ ghi những gì nhìn thấy tận mắt trên ảnh thật hoặc text log trích nguyên văn. CẤM dùng từ phỏng đoán.
   - **`[HYPOTHESIS]`**: Mọi suy đoán nguyên nhân kỹ thuật (Cloudflare, botcheck, mạng...) BẮT BUỘC nằm ở đây và phải có nhãn *"chưa xác nhận / cần kiểm tra"*.
   - **Khi không có ảnh hoặc ảnh đen:** BẮT BUỘC tuyên bố: **`INSUFFICIENT EVIDENCE — Chưa có ảnh hiện trường xác thực, không thể kết luận nguyên nhân gốc rễ`**. Tuyệt đối cấm tự lấp liếm bằng phán đoán chủ quan.
