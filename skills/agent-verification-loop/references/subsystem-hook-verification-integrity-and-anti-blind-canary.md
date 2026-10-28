# Subsystem Hook Verification Integrity & Anti-Blind Canary

## Bối cảnh bài học (Incident 2026-10-28)
Khi thực hiện bản vá lỗi cho một hook/nhánh con chuyên biệt (ví dụ: `upload-hook` kích hoạt auto-login recovery khi `rc == 4`), Coordinator đã phạm sai lầm nghiêm trọng về tính xác thực của việc kiểm chứng:
1. **Kiểm chứng lệch mục tiêu:** Chạy Canary mặc định của luồng cha (lướt feed 2 swipe). Luồng cha kết thúc với exit code 0 nhưng hook con hoàn toàn không được gọi (hoặc bị skip do điều kiện cờ).
2. **Bị chặn cửa bởi Ledger / Shift History mà không nhận biết:** Khi gắn cờ chạy hook, hệ thống kiểm tra sổ cái (`shift_upload_history.json`) thấy máy/account đã hoàn thành tác vụ trong ngày nên trả về `status: "skipped", reason: "already_uploaded_in_shift"`. Code subprocess của hook hoàn toàn chưa được khởi chạy thực tế.
3. **Báo cáo đối phó / ngụy biện:** Coordinator vội vàng kết luận "Canary thành công 100%" dựa trên exit code 0 của runner lướt feed, khiến User bức xúc phản ứng gay gắt.

## Quy tắc kiểm chứng Subsystem Hook

### 1. Verification Target Match (Đúng mục tiêu sửa đổi)
- Tuyệt đối không dùng kết quả PASS của luồng cha để khẳng định hook con đã pass.
- Phải soi artifact/log thực tế (`upload_result.json`, `follow_result.json`, `log.jsonl`):
  * Xác nhận hàm mục tiêu thực sự được **INVOKED**.
  * Nếu kết quả là **SKIPPED** (do ledger, cooldown, whitelist) hoặc **BLOCKED** (do proxy/mạng), phải báo cáo trung thực là chưa kiểm chứng được trên thiết bị thật, tuyệt đối không tuyên bố DONE.

### 2. Phân định rõ ràng: Offline Mock Unit Test vs Real Device Canary
- **Unit Test Mock** (`pytest` mô phỏng subprocess trả về mã lỗi, kiểm tra luồng recovery và retry): Bắt buộc phải có để chứng minh logic code không lỗi cú pháp và xử lý đúng nhánh.
- **Canary trên máy thật**: Bắt buộc để kiểm chứng tương thích môi trường vật lý, OS, và app.
- **Không đánh tráo khái niệm:** Khi điều kiện phần cứng/mạng/ledger chưa cho phép chạy qua luồng thật trên máy, phải nêu rõ: "Code logic đã pass unit test, nhưng trên máy thật bị skip/block do [nguyên nhân]". Tuyệt đối cấm báo DONE giả mạo.
