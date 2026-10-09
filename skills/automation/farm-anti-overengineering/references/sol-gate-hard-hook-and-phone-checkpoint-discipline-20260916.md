# Sol Gate Hard Hook & Phone Checkpoint Discipline (16/09/2026)

## 1. Sự Cố & Hiện Trường Thực Tế

### A. Google Hard Phone Checkpoint (`challenge/iap`) Pitfall
- **Hiện trường:** Khi đăng nhập Google trên GPM Browser, Google phát hiện IP/Proxy bất thường và chuyển hướng sang `challenge/iap`:
  *"Xác minh danh tính của bạn — Có điều bất thường về hoạt động của bạn. Để bảo mật tài khoản của bạn, Google muốn đảm bảo rằng người đăng nhập chính là bạn. Nhập số điện thoại để nhận tin nhắn văn bản cùng mã xác minh."*
- **Lỗi logic nghiêm trọng trong script cũ:**
  1. **Spam loop "Thử cách khác":** Script thấy `challenge/iap`, tìm nút `button:has-text("Thử cách khác")`, click và gọi `continue` trong vòng lặp `while time.time() - start_t < 180` mà không có biến đếm. Google không cung cấp cách khác nên sau khi click lại quay về chính màn hình này, dẫn tới script click liên tục 30–40 lần suốt 180 giây cho đến khi cạn timeout!
  2. **Match nhầm SĐT cá nhân:** Điều kiện điền số điện thoại Tad (`0906746624`) có chứa điều kiện lỏng `or "nhận mã xác minh" in b_txt`. Câu trên màn hình có chữ *"để nhận mã xác minh"* khiến script tưởng nhầm là form xác nhận SĐT cũ của Tad và điền số cá nhân vào form đòi SĐT mới của Google.
- **Kỷ luật chuẩn:**
  - **Fail-Fast dừng ngay:** Màn hình `challenge/iap` với lý do *"hoạt động bất thường"* là Hard Phone Checkpoint. Chỉ được click "Thử cách khác" tối đa **1 lần duy nhất** để thăm dò; nếu vẫn ở lại màn này $\rightarrow$ **DỪNG NGAY LẬP TỨC**, chụp ảnh lưu `oauth_{email}_hard_phone_checkpoint_{timestamp}.png`, trả về `status: "PHONE_CHECKPOINT"` để đóng profile/giải phóng tài nguyên.
  - **Khóa SĐT 24:** Chỉ điền `0906746624` khi màn hình ghi rõ yêu cầu xác nhận số điện thoại đuôi 24 có sẵn (`"24"` đi kèm `"xác nhận số điện thoại"`, `"••"`, `"đuôi"`).

---

### B. Sự Cố Coordinator Bỏ Qua Tầng A Sol Plan ("Làm ẩu / Đi tắt")
- **Hiện tượng:** Khi nhận lệnh sửa flow, Coordinator tự suy luận logic, tự viết Patch Contract trong đầu rồi dispatch thẳng Worker subagent luôn, bỏ qua bước gọi Sol Planner (`:20129` qua `sol_planner.py`).
- **Lỗ hổng kỹ thuật:** Hook `guard_dispatch_contract.py` trước đó chỉ kiểm tra chuỗi hoa `FILE:` và `OLD_STRING:`. Coordinator dùng chữ thường (`File cần sửa:`, `old_string:`) khiến hook ngộ nhận đây là nhánh `INVESTIGATE` có trần budget, cho phép dispatch lọt qua mà không bị chặn!

---

## 2. Bản Chất: Tại Sao Soft Prompt / Memory Luôn Thất Bại?

*(Kết luận từ Giám khảo Cấp cao Claude Opus CLI)*

1. **LLM là máy tính xác suất, không phải bộ vi xử lý thực thi IF/ELSE cứng:**
   Khi Coordinator nhìn thấy đoạn code lỗi rõ ràng, pattern matching trong trọng số mô hình nhảy vọt:
   $$\text{Confidence}(\text{"Thấy lỗi rõ, vá ngay"}) \approx 0.94 \quad \gg \quad \text{Confidence}(\text{"Phải gọi Sol Planner"}) \approx 0.71$$
   Sự tự tin và tính "tiện tay" của mô hình lập tức đè bẹp quy tắc trong System Prompt / Memory.
2. **Quy luật bất biến:**
   > *"Memory và System Prompt chỉ là lời khuyên mang tính xác suất để mô hình **MUỐN** làm đúng; chỉ có Code Hook (Level 4) mới khiến mô hình **KHÔNG THỂ** làm sai."*

---

## 3. Kiến Trúc Sol Gate Hard Hook (Level 4 Zero-Bypass)

Hook được cài đặt tại `C:\Users\Kibe\AppData\Local\hermes\hooks\guard_dispatch_contract.py`, bắt sự kiện `PreToolUse` của `delegate_task`:

```
Coordinator phát lệnh delegate_task
             │
             ▼
   [guard_dispatch_contract.py]
             │
             ├─ 1. Case Normalization: Bắt FILE/File/file, OLD_STRING/old_string, NEW_STRING/new_string
             │    CẤM đánh lận task sửa code thành INVESTIGATE.
             │
             ├─ 2. Đánh giá ngoại lệ T0 Bypass:
             │    - diff = abs(len(new_s) - len(old_s)) < 60 ký tự.
             │    - CẤM 100% từ khóa logic: if, elif, else, for, while, def, class, return, try, except,...
             │    - Chỉ chấp nhận comment (#) hoặc gán hằng số đơn thuần (^[A-Z_0-9]+ = ...).
             │    -> Nếu ĐẠT: Cho phép bypass T0.
             │
             ├─ 3. Enforce Sol Plan Tầng A (Nếu Non-T0):
             │    - Bắt buộc có nhãn `SOL_PLAN_ID: <id>`.
             │    - Kiểm tra đĩa vật lý: file `D:/Taadaa/runtime/sol_plans/<id>.json` phải tồn tại.
             │    - Kiểm tra TTL: thời gian tạo plan phải <= 600s (10 phút).
             │    -> Nếu THIẾU/SAI: BLOCK VẬT LÝ, dội ngược lỗi đỏ ép gọi `sol_planner.py`.
             │
             ├─ 4. Van xả áp khẩn cấp (Emergency Fallback Valve):
             │    - Bắt các nhãn: SOL_FALLBACK, EMERGENCY_OVERRIDE, SOL_OFFLINE, USER_OVERRIDE.
             │    - Khi Sol Planner offline hoặc có lệnh khẩn cấp -> Cho phép bypass Sol Plan check.
             │    - Cấm Deadlock: Hệ thống không bị tê liệt khi hạ tầng :20129 gặp sự cố.
             │    - 100% HARD GATES VẬT LÝ VẪN GIỮ NGUYÊN (File tồn tại, FOCUSED_TEST, c==1).
             │
             └─ 5. Physical Verification:
                  - File đích tồn tại trên đĩa.
                  - Bắt buộc có FOCUSED_TEST < 30s.
                  - Uniqueness c == 1 của OLD_STRING trong file.
```

---

## 4. Module Sol Planner CLI (`D:\Taadaa\tools\sol_planner.py`)

Bổ sung hàm `save_sol_plan()` và CLI:
- **Lưu plan nguyên tử:** Tạo file `sol_plan_<uuid[:8]>.json` trong `D:\Taadaa\runtime\sol_plans/` chứa `created_at`, `target_file`, `patch_contracts`, `all_c_invariants_passed`.
- **CLI chuẩn để Coordinator sử dụng:**
  ```bash
  python D:/Taadaa/tools/sol_planner.py --goal "<mục tiêu>" --file "<đường dẫn file>"
  ```
  Trả về JSON chứa trường `sol_plan_id` để Coordinator trích xuất và đưa vào contract.

---

## 5. Kết Quả Thẩm Định Đối Kháng từ Claude Opus CLI

```text
╔══════════════════════════════════════════════════════╗
║                                                      ║
║        ✅  APPROVED — ĐẠT (5/5 TIÊU CHÍ)             ║
║                                                      ║
║  Tất cả 5/5 tiêu chí PASS.                          ║
║  Triển khai Sol Gate Hard Hook đúng đắn, chặt chẽ,  ║
║  đủ điều kiện đưa vào production.                   ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
```

- **Tiêu chí 1 (Case-Sensitivity):** PASS — Triệt tiêu toàn bộ biến thể chữ thường/hoa.
- **Tiêu chí 2 (T0 Bypass Lockdown):** PASS — Khóa cứng 100% control keywords.
- **Tiêu chí 3 (Enforce Sol Plan):** PASS — Kiểm tra file đĩa + TTL 600s + hướng dẫn lệnh gọi.
- **Tiêu chí 4 (c==1 & FOCUSED_TEST):** PASS — Bảo vệ bất biến 3 tầng.
- **Tiêu chí 5 (sol_planner save + CLI):** PASS — Tích hợp đầy đủ CLI và UUID plan persistence.
- **Thẩm định Vòng 2 (Van xả áp khẩn cấp SOL_FALLBACK / EMERGENCY_OVERRIDE):** APPROVED 100% — Giải phóng deadlock hoàn toàn khi Sol offline, trong khi 4 Hard Gates vật lý cốt lõi (file đĩa, test command, old_string uniqueness) giữ nguyên vẹn 100%.

---

## 6. Quy Trình Đồng Bộ Sang Máy Admin (OneDrive Sync)
- **Vấn đề:** Các file hooks nằm ở `%LOCALAPPDATA%\hermes\hooks\` cục bộ trên máy Kibe. Nếu chỉ sync `skills` và `config.yaml` qua OneDrive, máy Admin sẽ không có hooks và bị gãy đường dẫn hardcode `C:/Users/Kibe/...`.
- **Giải pháp chuẩn hóa:**
  1. Đồng bộ toàn bộ `hooks/*.py` sang `D:\OneDrive\Taadaa_Sync_Shared\hermes-sync\hooks\` và `D:\Taadaa\Hermes\deploy\hermes-home\hooks\`.
  2. Script `apply_sync_admin.py` và `sync-from-kibe.ps1` tự động kéo hooks về `%LOCALAPPDATA%\hermes\hooks\` của Admin và chuẩn hóa đường dẫn trong `config.yaml` cho khớp với user Admin thực tế.
