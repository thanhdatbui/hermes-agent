# Canary Gate Verification Pattern for Feed Session & Account Switcher

## 1. Kỷ luật bắt buộc (User & Claude Disciplinary Rule)
- Khi sửa bất kỳ code/selector/logic nào liên quan đến hành vi tương tác thiết bị thật (bounds, tap coordinates, dropdown switcher, popup dismissal):
  * **CẤM TUYỆT ĐỐI** chỉ chạy `pytest` offline hoặc test mock rồi vội vàng báo DONE với User.
  * **BẮT BUỘC** phải kích hoạt Canary Gate trên ≥ 1 máy thật để kiểm chứng kết quả thực tế trên runtime.

## 2. Lệnh chạy Canary chuẩn (Né deadlock khóa kép)
Khi gọi qua `with_device_lock.py`, bắt buộc truyền `--no-lock` vì `run_tiktok.py` đã sở hữu cơ chế atomic device lock riêng:

```bash
python D:/Taadaa/tools/with_device_lock.py -m <N> --no-lock -- env -u PYTHONPATH "D:/Taadaa/python-envs/automation/Scripts/python.exe" "D:/Taadaa/tiktok-luot nuoi acc/python_runner/run_tiktok.py" --machine <N> --account-workbook "D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx" --account-row-index <Row> --mode multi-machine-feed-session --machines <N> --allow-navigation-only --allow-feed-swipe --allow-benign-popup-dismiss --verify-current-account --recovery-test-swipes 1 --config "D:/Taadaa/tiktok-luot nuoi acc/config.example.yaml"
```

## 3. Nghiệm thu & Soi mắt Gate 6
- Kiểm tra `summary.txt` xác nhận `final_status: success`.
- Dùng `run_winrt_ocr.py` hoặc Vision kiểm tra các screenshot:
  1. `profile_preflight_switch_.../attempt_1/screen.png`: Tìm thấy anchor.
  2. `profile_preflight_switcher_.../attempt_1/screen.png`: Bottom sheet mở ra, chọn đúng hàng tài khoản (tọa độ lề trái `x=300-350`).
  3. `profile_preflight_verify_.../attempt_1/screen.png`: Profile đã chuyển đổi sang đúng username và display name.
- Đính kèm thẻ `MEDIA:<screenshot_path>` trong báo cáo cuối cùng gửi User.
