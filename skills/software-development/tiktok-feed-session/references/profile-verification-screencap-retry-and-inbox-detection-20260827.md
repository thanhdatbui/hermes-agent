# Profile Verification Screencap Retry and Inbox Selection Invariant (2026-08-27)

## 1. Context & Symptom
- **Alert:** `profile verification capture-artifact-incomplete: profile verification navigation retry artifact incomplete`
- **Symptom:** Máy 30 (`susannemorti9`) và Máy 59 (`carlosfwagne2`) dừng phiên, lock giữ hiện trường tại bước đối soát hồ sơ (`_verify_profile_after_session`).
- **Log detail:** `"capture_artifact_error": "screenshot: screencap output is not a PNG"` hoặc `"capture_artifact_status": "incomplete"`.

## 2. Root Cause
1. **Screencap đơn lẻ không retry:**
   - Trong `_persist_profile_capture_artifacts`, lệnh `ctx.adb.exec_out(["screencap", "-p"])` chỉ thực thi đúng 1 lần.
   - Khi điện thoại trong box chuyển cảnh, màn hình tắt (`mWakefulness=Asleep`), hoặc buffer surface bị khóa tạm thời, `screencap -p` trả về header rỗng (12 bytes `\x00`*12).
   - Lệnh văng exception và để lại metadata `capture_artifact_status: incomplete`, khiến gate `_profile_capture_artifact_is_complete` từ chối `screen.png` và fail-closed dừng phiên.
2. **False trigger nhận diện màn hình Hộp thư (Inbox):**
   - Quét text `initial_normalized & message_markers` trên toàn màn hình XML. Do thanh Navigation Bar dưới đáy luôn có nhãn "Hộp thư", điều kiện này luôn `True`, gây kích hoạt nhánh re-tap không cần thiết.
3. **Thiếu độ trễ chuyển cảnh sau Camera Recovery:**
   - Sau khi bấm BACK thoát Camera overlay, script re-tap Profile nhưng chụp XML ngay lập tức khi trang chưa kịp load xong.

## 3. Solution Pattern
1. **Screencap retry loop + wake-up recovery:**
   - Thực hiện retry tối đa 3 lần cho `screencap -p`.
   - Kiểm tra `dumpsys power` để phát hiện màn hình tắt (`mInteractive=false` hoặc `mWakefulness=asleep`) và gửi `keyevent 224` để đánh thức.
   - Validate PNG chặt chẽ qua `_is_valid_png(payload)` (kiểm tra signature 8-byte, IHDR, scanline, CRC).
2. **Xác nhận tab Inbox chính xác từ XML Attributes:**
   - Chỉ kích hoạt nhánh retry navigation khi tab "Hộp thư" thực sự mang thuộc tính `selected="true"` (dùng `_is_inbox_tab_selected_from_xml` duyệt `root.iter()` đọc `attrib.get("text")`, `attrib.get("content-desc")`, `attrib.get("selected")`).
3. **Độ trễ chuyển cảnh và Fail-closed an toàn:**
   - Bổ sung `time.sleep(1.5)` sau camera recovery re-navigation trước khi chụp XML đối soát.
