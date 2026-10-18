# Hotmail 6H Lifecycle Report: DONE_WITHOUT_CHATGPT_REG Telemetry Warning Triage

## 1. Bối cảnh & Hiện tượng
Trong báo cáo định kỳ 6h (`cron_hotmail_gpm_lifecycle_6h_report.py`, job_id `61570a1e37b1`), dòng cảnh báo xuất hiện ở cuối báo cáo:
```text
⚠️ Dữ liệu có 1 cảnh báo (DONE_WITHOUT_CHATGPT_REG) - correlation_id=caae5b2be804
```

## 2. Cơ chế Phát hiện của Telemetry
Trong `cron_hotmail_gpm_lifecycle_6h_report.py`:
- Hàm `normalize_profiles()` kiểm tra timestamp:
  ```python
  has_chatgpt = _has_valid_timestamp(raw, "chatgpt_registered_at", key, _flag)
  ```
- Hàm `aggregate_records()` kiểm tra điều kiện lệch chuẩn:
  ```python
  if rec["bucket"] == STAGE_DONE and not rec.get("has_chatgpt"):
      done_without_chatgpt.append(rec["key"])
  ```
- Khi `done_without_chatgpt` có phần tử, telemetry phát cảnh báo mức warning:
  ```python
  telemetry.emit("done_without_chatgpt", level="warning", error_class="DONE_WITHOUT_CHATGPT_REG",
                 farm=farm, count=len(done_without_chatgpt),
                 sample=done_without_chatgpt[:SCHEMA_SAMPLE_LIMIT])
  ```

## 3. Bản chất Dữ liệu Hiện trường
- State file `D:/Taadaa/runtime/kibe/cron-state/batch_gpm_5profiles_supervisor_state.json` có 81 tài khoản ở Kibe Farm (ví dụ: `M01:ginnyhanstein8045@hotmail.com`) đã hoàn tất đổi mật khẩu bảo mật (`stage: "DONE"`, `status: "COMPLETED"`, có `has_chatgpt: true` và `chatgpt_password`) từ các đợt chạy trước khi trường ISO timestamp `chatgpt_registered_at` được đưa vào chuẩn hóa schema.
- Vì không có timestamp `chatgpt_registered_at`, `rec["has_chatgpt"]` được gán `False`, dẫn đến kích hoạt cảnh báo `DONE_WITHOUT_CHATGPT_REG`.

## 4. Tác động Vận hành & Kết luận Đối soát
- **Tính toán chỉ số:** Không bị sai lệch. Hàm `_is_chatgpt_registered(rec)` có điều kiện `rec.get("bucket") == STAGE_DONE`, nên 81 tài khoản này vẫn được tính đầy đủ vào tổng số tài khoản ChatGPT đăng ký thành công (`chatgpt_ok`).
- **Phân loại sự cố:** Đây là cảnh báo quan sát (Observability/Telemetry warning) để truy nguyên dữ liệu lịch sử, không phải lỗi logic, không làm nghẽn hàng đợi và không gây gián đoạn quy trình supervisor tự động.
- **Quy tắc ứng xử khi gặp cảnh báo:** Không sửa mò state file; ghi nhận đối soát hiện trường và giải thích rõ nguồn gốc 81 tài khoản lịch sử cho User.
