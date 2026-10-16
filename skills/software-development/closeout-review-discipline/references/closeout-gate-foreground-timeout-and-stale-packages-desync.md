# Closeout Gate Foreground Timeout Guard & Shared Library Pytest PYTHONPATH Desync Trap (2026-10-16)

## 1. Bẫy Timeout Lệnh Foreground (> 60s) Khi Chạy Closeout Gate

### Hiện tượng & Lỗi Guard
Khi Coordinator chạy `closeout_gate.py` trực tiếp ở chế độ foreground với timeout dự phòng:
```bash
python D:/Taadaa/tools/closeout_gate.py --repo "D:/Taadaa/tiktok-follow" --files ... --timeout 120
```
Lệnh lập tức bị Coordinator Guard chặn cứng (Fail-Closed):
`⛔ [GUARD_FOREGROUND_TIMEOUT_EXCEEDED] Lệnh terminal foreground có timeout=120s > 60s! Hãy hạ timeout <= 60s hoặc dùng background=True.`

### Nguyên nhân cốt lõi
- Quy trình Closeout Gate thực hiện hai công đoạn nặng:
  1. Chạy focused `pytest` trên các file test liên quan (có thể mất 15-30s).
  2. Gửi diff và test log tới Sol High qua OmniRoute (`:20129`) để reviewer chấm điểm rubric 100 (mất 30-90s tùy tải mô hình).
- Tổng thời gian chạy thực tế thường dao động từ 45s đến 120s, vượt quá ngưỡng an toàn foreground 60s của Coordinator.

### Kỷ luật bắt buộc
Coordinator **BẮT BUỘC** gọi `closeout_gate.py` qua tiến trình nền (background):
```python
terminal(
    command='python D:/Taadaa/tools/closeout_gate.py --repo "D:/Taadaa/<repo>" --files ... --json-output',
    background=True,
    notify_on_complete=True,
    timeout=300
)
```
Sau đó kết thúc turn để hệ thống harness tự động đánh thức khi tiến trình kết thúc.

---

## 2. Bẫy Stale Site-Packages Desync Khi Closeout Gate Chạy Focused Pytest

### Hiện tượng
Khi `closeout_gate.py` thực thi, cờ `--files` kích hoạt chạy focused test tự động. Một số test case mới viết trong repo consumer (ví dụ `test_ocr.py` trong `tiktok-follow`) bất ngờ fail với lỗi assertion sai logic cũ:
```
FAILED test_classify_button_from_ocr_message_alone_is_unknown - AssertionError: assert 'followed' == 'unknown'
FAILED test_classify_button_ignores_feed_top_nav_tabs - AssertionError: assert 'followed' == 'unknown'
```
Trong khi đó, chạy test riêng lẻ với môi trường chuẩn lại pass.

### Nguyên nhân kỹ thuật
- `closeout_gate.py` triệu hồi pytest bằng `[sys.executable, "-m", "pytest", ...]`.
- `sys.executable` là Python của môi trường chạy gate (ví dụ Hermes venv). Môi trường này có thể có thư mục tĩnh `site-packages/automation_core` cũ được cài từ trước.
- Khi module trong repo consumer (như `follow_runner/core/ocr.py`) import từ thư viện dùng chung:
  ```python
  from automation_core.ocr import classify_profile_action_ocr
  ```
  Python của gate ưu tiên nạp module từ `site-packages` thay vì source code live `D:/Taadaa/automation-core/src/`.
- Hậu quả: `pytest` trong closeout gate kiểm thử code mới trên nền thư viện dùng chung bị cũ (stale bytecode/package), khiến kết quả thẩm định bị đánh rớt oan (Verdict: REJECTED).

### Kỷ luật phòng chống & Khắc phục
1. **Kiểm tra Shadowing:** Đối soát đường dẫn import qua:
   ```bash
   python -c "import automation_core; print(automation_core.__file__)"
   ```
   Nếu trỏ vào `Lib/site-packages/automation_core/` thay vì `D:/Taadaa/automation-core/src/`, đó là dấu hiệu shadowing.
2. **Kỷ luật trong Consumer `conftest.py`:**
   Nếu consumer repo phụ thuộc vào các tính năng đang phát triển của `automation-core`, `conftest.py` hoặc file test bắt buộc phải bảo đảm `D:/Taadaa/automation-core/src` nằm ở đầu `sys.path`:
   ```python
   import sys
   from pathlib import Path
   core_src = Path("D:/Taadaa/automation-core/src")
   if core_src.exists() and str(core_src) not in sys.path:
       sys.path.insert(0, str(core_src))
   ```
3. **CẤM DÙNG `--skip-test` Để Lách Cổng:** Khi test fail trong closeout gate, tuyệt đối cấm thêm cờ `--skip-test` để ép Sol High chấm điểm. Phải phân loại rõ: nếu do logic sai -> sửa code; nếu do lệch pha môi trường/import stale -> bổ sung path resolution chuẩn vào test fixture.

---

## 3. Kỷ Luật Canary Đa Kịch Bản Trước Khi Mời Thẩm Định (User Mandate)

- **Nhắc nhở từ User:** *"Canary nên chạy nhiều trường hợp để nắm đc script có ổn định khi gặp nhiều màn khác nhau k ấy"* và *"Sao canary có 1 máy thì lấy gì đảm bảo máy khác k lỗi"*.
- **Quy chuẩn trước Closeout:**
  - CẤM chạy Canary trên 1 máy duy nhất rồi vội vàng gọi Closeout Gate.
  - Phải kiểm chứng tối thiểu 3-4 máy bao phủ 4 trạng thái giao diện:
    1. Profile đối tượng có nút Nhắn tin (thử thách bẫy phân loại).
    2. Profile chính chủ (chống nhận nhầm stat count `1 Đã follow`).
    3. Màn hình Video Feed (chống nhận nhầm tab bar điều hướng `Bạn bè` ở $y < 200$).
    4. Màn hình Cài đặt / Sửa hồ sơ (fail-closed trả về `unknown`).
  - Toàn bộ bằng chứng phải được soi mắt qua Vision (`MEDIA:`) trước khi đưa vào báo cáo nghiệm thu chốt phiên.
