# Pitfall: Thứ tự kiểm tra Overwrite Guard trong deferred_tracking_writer

## Bối cảnh
Khi ghi kết quả reg vào tracking workbook (`taikhoan_dat_v2_updated.xlsx`) qua `scripts/deferred_tracking_writer.py`, hệ thống cần đảm bảo không ghi đè vào dòng đã có tài khoản sẵn (có ID/PASS của email khác).

## Vấn đề gặp phải
- Test case `test_tracking_overwrite_guard.py` mong đợi trả về blocker có chứa `OVERWRITE_REJECTED_EXISTING_ACCOUNT_...`.
- Tuy nhiên hàm `apply_deferred_result(ws, result)` gọi `_check_expected_row(ws, result)` trước:
  ```python
  def apply_deferred_result(ws, result: dict) -> TrackingWriteResult:
      check = _check_expected_row(ws, result)
      if check.status != "READY":
          return check

      # HARD GUARD nằm ở đây bị unreachable khi email mismatch
      existing_id = ws.cell(check.row, 3).value
      existing_pass = ws.cell(check.row, 4).value
      ...
  ```
- Do `_check_expected_row` kiểm tra email khớp trước và trả về `status="BLOCKED_DATA_CONFLICT"` kèm `blocker="EXPECTED_EMAIL_..."`, hàm bị return sớm và Hard Guard không bao giờ được kích hoạt.

## Giải pháp chuẩn hóa
1. Kiểm tra Hard Guard chống ghi đè tài sản người dùng trước khi thực hiện các validation khác, hoặc tích hợp trực tiếp vào `_check_expected_row`.
2. Nếu slot mục tiêu (`expected_row`) đã có `ID` hoặc `PASS` và email của slot khác với email trong kết quả cần ghi, lập tức trả về `OVERWRITE_REJECTED_EXISTING_ACCOUNT_{existing_id}_{existing_mail}`.
