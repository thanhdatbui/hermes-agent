# Gmail Runner Telemetry Truncation & ChatGPT Hook Pass Key Pitfalls

## 1. Phân loại kết quả lệch trong `run_parallel.ps1` (Log Tail Truncation & ADB Warning)
### Triệu chứng
- Báo cáo chuỗi sau ca trưa hoặc telemetry batch báo `Phase 1 (Reg Gmail - Code 1): Success (4), Fail (11)`.
- Tuy nhiên kiểm tra `merge_success_summary.json` và sổ cái `gmail_clean_v2.xlsx` thì thấy có tới **7 tài khoản tạo thành công** và đã nạp vào Excel.

### Nguyên nhân gốc rễ
1. **Log Tail 80 Lines Truncation**:
   - `run_parallel.ps1` dùng hàm `Get-RunResultFromLog` lấy `$tail = $content | Select-Object -Last 80` để tìm từ khóa `SUCCESS:\s+([^\s]+@gmail\.com)`.
   - Sau khi reg Gmail thành công trên S7, script tiếp tục thực hiện:
     - Warmup ChatGPT hook (tương tác ADB, mở Chrome/app, in hàng chục dòng log).
     - Warmup Newsletter (kích hoạt newsletter service).
   - Tổng số dòng log sau khi tạo xong tài khoản thường vượt quá 80 dòng, đẩy dòng `✓ SUCCESS:` ra ngoài phạm vi 80 dòng cuối.
2. **False Positive Error từ ADB Warning**:
   - Lệnh disable Samsung Pay / Spaymini phát ra cảnh báo:
     `[adb warn] Error: java.lang.IllegalArgumentException: Unknown package: com.samsung.android.spaymini`
   - Bộ lọc regex PowerShell `-match "ERROR:\s+(.+)$"` không phân biệt hoa thường và bắt nhầm chữ `Error:` trong adb warn thành lỗi dừng, đánh dấu máy thành công thành `FAILED_OTHER`.
3. **Chốt chặn phân loại chuẩn**:
   - ĐỐI SOÁT CHUẨN XÁC NHẤT: Luôn kiểm tra sự tồn tại của file kết quả `results/machine_<N>.success.json` và `merge_success_summary.json` thay vì chỉ dựa vào phân tích regex 80 dòng cuối log.

---

## 2. Lỗi Hook ChatGPT: `object of type 'NoneType' has no len()`
### Triệu chứng
- File log máy thành công xuất hiện:
  `⚠ [WARMUP_CHATGPT] Loi khi goi hook ChatGPT: object of type 'NoneType' has no len()`

### Nguyên nhân
- Trong `gmail_reg_v10.py` (`persist_success_result`):
  ```python
  email_target = f"{acc.get('id')}@gmail.com".lower()
  pwd_target = acc.get("password")  # BUG: Dictionary sinh bởi [ACCOUNT_GEN] dùng key 'pass', không phải 'password'
  dob_target = acc.get("dob")
  chatgpt_res = register_chatgpt_on_device(device_id, email_target, password=pwd_target, dob=dob_target)
  ```
- Biến `pwd_target` bị `None`. Khi truyền vào `register_chatgpt_on_device(...)`:
  ```python
  res["telemetry"] = {
      ...
      "password_length": len(password),  # password=None -> TypeError
  }
  ```
### Giải pháp
- Đọc mật khẩu linh hoạt: `pwd_target = acc.get("password") or acc.get("pass") or ""`.
- Trong hook `register_chatgpt_on_device`: Luôn bảo vệ an toàn `password_length`: `len(password or "")`.
