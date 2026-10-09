# Farm Alert 5-Step Recovery Template Specification (2026-09-04)

## 1. Mục đích & Bối cảnh
Chuẩn hóa toàn bộ tin nhắn Farm Alert phát sinh từ `automation_core.alerts.send_farm_machine_alert` theo cấu trúc **5 bước recovery**. Cấu trúc này nhằm:
- Ép chặt bước sửa codebase (B3 - Patch Code), tuyệt đối cấm can thiệp lệnh ADB chữa cháy cục bộ.
- Cấm quét đĩa / grep đệ quy (`os.walk`, `grep -rn`, `search_files`) khi điều tra lỗi.
- Đóng gói sẵn lệnh trích xuất hiện trường và lệnh canary test thực tế.

## 2. Template Payload Chuẩn
```text
🚨 [FARM ALERT: MÁY {machine_id}] DỪNG PHIÊN
• Quy trình / Script: {process_name} ({repo_name})
• Máy: {machine_id} | Serial: {serial} | Nick: {nick}
• Triệu chứng: {symptom}
• Hiện trường: ĐANG MỞ

📋 BẮT BUỘC THỰC THI (5 BƯỚC RECOVERY - CẤM ADB TAY / CẤM QUÉT ĐĨA):
1. B1 (Inspect): python D:/Taadaa/tools/inspect_machine.py {machine_id}
2. B2 (Root Cause): Đọc log run ({log_path}) & mở flow ({flow_path})
3. B3 (Patch Code): SỬA CODEBASE trong repo để script tự xử lý lỗi (CẤM gõ lệnh ADB ngoài chữa ngọn)
4. B4 (Canary Test): Chạy lệnh kiểm chứng thực tế:
   {canary_cmd}
5. B5 (Closeout): Báo cáo file/hàm đã sửa + kết quả canary (CẤM dán code diff lớn làm tốn context/quota; chỉ xuất diff khi user yêu cầu "cho xem diff")
```

## 3. Vị Trí Triển Khai Trong Mã Nguồn
- **Source of Truth:** `D:/Taadaa/automation-core/src/automation_core/alerts.py` (`send_farm_machine_alert`).
- **Unit Test:** `D:/Taadaa/automation-core/tests/test_alerts.py`.
- **Consumer Callers:** Mọi repo farm (`tiktok-luot nuoi acc`, `tiktok-follow`, `Tiktok-video`, `Tiktok_Reg`, `tiktok-add-bao-mat-f2a`) khi bắt lỗi dừng máy đều gọi qua `automation_core.alerts.send_farm_machine_alert`.

## 4. Quy Tắc Động Hóa Row & Nick Thực Tế (Cấm Tuyệt Đối Hardcode Row 1)
1. **Lỗi kinh điển cần tránh:**
   - Template `default_canary` trong `alerts.py` hoặc caller `_send_farm_machine_alert_once` trong flow hardcode cố định `-Row 1`.
   - Alert luôn bốc Nick của Row 1 thay vì Nick tương ứng với ca đang chạy của máy.
2. **Quy tắc phân giải Row theo lịch ca:**
   - **Ngày lẻ:** Ca 1 (~06:00) -> Row 1 | Ca 2 (~12:30) -> Row 3 | Ca 3 (~19:00) -> Row 5.
   - **Ngày chẵn:** Ca 1 (~06:00) -> Row 2 | Ca 2 (~12:30) -> Row 4 | Ca 3 (~19:00) -> Row 6.
3. **Quy tắc lấy Nickname:**
   - Tra cứu đúng Row của máy trong workbook `taikhoan_run_safe.xlsx` hoặc session manifest/account context đang hoạt động.
   - Tuyệt đối không fallback mù về account slot 1 (Row 1).
4. **Lệnh Canary B4:**
   - Bắt buộc format động: `powershell.exe ... -Row {actual_row} ...`.
