# Anti-Premature-Block in Closeout Loop

## Nguyên Tắc Điều Phối Chốt Phiên: CẤM Dừng Báo BLOCKED Khi Chưa Hết Thang Leo Thang
- Khi user phát lệnh chốt phiên (`Done`, `chốt`, `wrap up`), `closeout_gate.py` trả về `REJECTED (< 85)` hoặc lỗi cấu trúc như `binding mismatch` (staged vs unstaged), Coordinator **tuyệt đối không được dừng lại báo cáo BLOCKED** và đẩy việc cho User.
- User phản ánh: *"ủa thì mày phải tự xử lý tiếp chứ sao báo blocked"* — việc báo BLOCKED ngay khi Reviewer vừa từ chối hoặc khi worker gặp timeout/lỗi cục bộ là hành vi thụ động (bại liệt điều phối).
- **Hard Invariant Sol Mandate (`references/sol-no-inspect-no-blocked-invariant.md`)**: NO INSPECT → NO BLOCKED. Worker timeout là trigger để inspect, KHÔNG PHẢI bằng chứng để block. CẤM phát lệnh BLOCKED khi chưa inspect hiện trường live O(1) và verify artifact thực tế. Báo BLOCKED giả khi artifact đã DONE bị coi là lỗi nặng nhất của Coordinator.

## Hành Động Tự Động Bắt Buộc (Autonomous Remediation)
1. **Lỗi Binding Mismatch**:
   - Nguyên nhân: File vừa có staged diff vừa có unstaged diff trên working tree.
   - Xử lý: Tự động đồng bộ staging area qua worker hoặc git add các file trong scope contract để `reviewed diff == tested tree`, sau đó chạy lại gate.
2. **Reviewer Chấm < 85/100**:
   - Bóc tách danh sách `Findings to remediate` từ scorecard JSON của Reviewer.
   - Dispatch Worker với Patch Contract O(1) giải quyết đúng các findings đó (xóa side-effects, bỏ markers gây false-positive, sửa test thật).
   - Lặp lại cho đến khi `closeout_gate.py` trả `APPROVED >= 85`.

---

## 3. Chống Bại Liệt Nấp Sau Quy Tắc (Anti-Bureaucratic L3-Block)
- **Tình huống kích hoạt sai**: Coordinator chạm trần dispatch budget (`20/20 worker`), hoặc gặp test fail nhỏ do import cache, liền lập tức tuôn một sớ báo cáo hành chính dài dằng dặc tuyên bố *"L3 BLOCKED theo đúng điều lệ Escalation Ladder 2.0"*.
- **Phản ứng bức xúc của User**: *"Là sao nữa mệt ghê cứ l3 blocked hoài rule óc lồn vc"* — User cực kỳ dị ứng việc Agent trốn tránh trách nhiệm bằng cách trích dẫn luật lệ rườm rà trong khi hiện trường kỹ thuật chỉ còn một bước nhỏ (ví dụ 45/47 test đã pass, chỉ lỗi 2 test do import module sai).
- **Kỷ luật cốt lõi**:
  * **CẤM tụng kinh quy tắc để viện cớ Block**: Tuyệt đối không được dùng sớ lý do "Theo đúng quy tắc phân vai...". Hãy nhìn thẳng vào bản chất kỹ thuật: Còn lỗi gì? File nào fail? Sửa được không?
  * **Xử lý khi chạm trần Dispatch Budget (20/20)**:
    1. Không buông tay đóng băng phiên.
    2. Kiểm tra van an toàn Gate/Guard: Nếu Claude CLI đã qua khung giờ reset limit (sau mốc 5h reset), được phép dùng Claude CLI với vai trò Cứu Hộ Gate/Guard để sửa lỗi test nhỏ và chạy Closeout Gate.
    3. Kiểm tra xem lỗi test có phải do `import shadowing` không để sửa dứt điểm, không để fail test giả mạo kéo dài phiên.
  * **Bẫy Runtime Import Shadowing trong Pytest**:
    - Khi import script từ `deploy/hermes-home/scripts/`: KHÔNG ĐƯỢC dùng `import <module>` thông thường nếu cùng tên module đó có thể đang tồn tại trong `%LOCALAPPDATA%` hay `sys.modules`.
    - BẮT BUỘC dùng dynamic import với đường dẫn tuyệt đối của repo script:
      ```python
      import importlib.util
      from pathlib import Path
      SCRIPT_PATH = Path(r"D:\Taadaa\Hermes\deploy\hermes-home\scripts\<target>.py")
      _spec = importlib.util.spec_from_file_location("<target>_deploy", SCRIPT_PATH)
      mod = importlib.util.module_from_spec(_spec)
      _spec.loader.exec_module(mod)
      ```
    - Tránh `AttributeError` giả mạo làm fail test oan uổng và dẫn đến báo Block vô lý.
