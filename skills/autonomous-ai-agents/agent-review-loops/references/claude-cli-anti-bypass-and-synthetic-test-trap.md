# Claude CLI Anti-Bypass, Real Behavioral Test Evidence & Closeout Staging Rules

## 1. Cấm Lạm Dụng Claude CLI Làm Lối Thoát Tiện Lợi (Anti-Bypass Invariant)
- **Bối cảnh vi phạm:** Khi lệnh terminal bị Coordinator Guard chặn (ví dụ `git reset`, `git checkout`), Coordinator tiện tay gọi `claude -p "..."` hoặc `claude --dangerously-skip-permissions` để né guard, rồi tống luôn toàn bộ việc code và test cho Claude CLI làm.
- **Hậu quả nghiêm trọng:** 
  1. Đốt sạch quota session 5 tiếng của Claude CLI (`You've hit your session limit`), làm mất công cụ cứu hộ duy nhất khi cần cứu hộ guard/gate.
  2. Phá vỡ toàn bộ cấu trúc phân vai: Coordinator phải chủ động điều phối Worker (`delegate_task`) qua Scope Lock và Patch Contract O(1), không được ỷ lại hoặc trốn việc.
- **Kỷ luật bất biến:**
  - Claude CLI CHỈ ĐƯỢC PHÉP dùng cho việc cứu hộ guard/gate đã được cấp quyền, TUYỆT ĐỐI CẤM dùng làm "lối thoát tiện lợi" để gõ thay lệnh Git hay làm thay việc của Worker.
  - Mọi thao tác sửa code, refactor, viết test BẮT BUỘC thực thi qua Worker subagent (`delegate_task`).

## 2. Bẫy Test Giả Lập Thuần Túy (Synthetic Test / Implementation Re-implementation Trap)
- **Hiện tượng bị Sol Reviewer từ chối (REJECT):**
  - Khi được yêu cầu viết unit test cho các hàm production mới (ví dụ: `merge_taikhoan_dat_candidates`, `merge_taikhoan_dat_proxies`), Worker hoặc Coordinator lại tự viết một đoạn logic phân tích Excel ngay trong thân hàm test rồi `assert` trên biến cục bộ đó, hoàn toàn KHÔNG gọi hàm thật từ module production (`sync_gpm_lifecycle`).
- **Phán quyết của Reviewer:**
  - Bằng chứng kiểm thử bị coi là **vô giá trị / giả lập (synthetic evidence)** vì không chứng minh được code production có chạy được hay không.
- **Quy chuẩn viết test hành vi thực tế (Behavioral Runtime Test):**
  - Test bắt buộc phải import và gọi trực tiếp hàm production thật:
    ```python
    import sync_gpm_lifecycle as sgl
    # Gọi trực tiếp hàm production với fixture workbook tạm:
    added = sgl.merge_taikhoan_dat_candidates(str(wb_path), candidates, excluded_set)
    sgl.merge_taikhoan_dat_proxies(str(wb_path), serials, proxy_map)
    ```
  - Bắt buộc kiểm tra cả:
    1. Giá trị trả về và các side effect lên dict/state truyền vào.
    2. Các nhánh ngoại lệ và khả năng chịu lỗi (resilience): lỗi I/O file, thiếu cột, sai định dạng.

## 3. Quản Lý Index & Staging Khi Chạy Closeout Gate
- **Lỗi `staged files != --files targets`:**
  - Xảy ra khi repo còn dính các file staged từ phiên trước không nằm trong `--files`.
  - CẤM chạy `--skip-test` để lách luật (Closeout Gate sẽ exit 1 với lỗi `FATAL: --skip-test is forbidden in repo mode`).
  - Phải dùng Worker hoặc lệnh chuẩn để đưa staged set về khớp chính xác với tập file thay đổi của task trước khi chạy `closeout_gate.py`.
- **Kỷ luật chốt phiên:**
  - CẤM TUYỆT ĐỐI báo `Done`, `DONE`, `Chốt phiên` khi Closeout Gate chưa trả về `Verdict: APPROVED` và `Score >= 85/100`.
