# Triết Lý & Quy Chuẩn Target-Bound Differential Canary Toàn Farm (25/10/2026)

## 1. Triết Lý Cốt Lõi: "Sửa đâu — Canary nhắm trúng đó" (Target-Bound Differential Canary)
- **Quy tắc User Invariant:** Tuyệt đối cấm chạy kịch bản Canary generic full-flow cướp máy hay can thiệp phá hủy dữ liệu (đổi pass, đổi mail, post clip rác) khi chỉ sửa một phần nhỏ trong code.
- **Diff Matching (Phân loại theo vết sửa):**
  - **Exempt (Miễn trừ):** Nếu git diff chỉ chạm vào tests (`tests/**`), tài liệu (`*.md`, `docs/**`), hoặc file cấu hình mẫu (`*.example.yaml`), Canary tự động miễn trừ, cấm bắt máy thật ra chạy làm phiền farm.
  - **Dispatcher / Lock Surgery:** Nếu sửa logic điều phối, hàng đợi, lock máy (`*run_batch*`, `*lock*`) -> Canary chỉ kiểm tra cơ chế cấp/nhả lock và launch plan trên 1 máy test rảnh. CẤM chạy sâu vào quy trình biến đổi tài khoản.
  - **UI Probe (Navigation-Only):** Nếu sửa logic điều hướng UI (màn hình Switcher, màn hình Security settings, form chọn media) -> Hook Canary chỉ mở đúng màn hình đó, chụp ảnh, OCR nhận diện rồi quay về HOME.
  - **State-Mutating Operations:** Các thao tác biến đổi dữ liệu (đổi pass, submit OTP, đăng clip) bắt buộc mock / offline sandbox trong Canary trừ khi User yêu cầu rõ ràng.

## 2. Chuẩn Hóa Toàn Diện 100% Repos Trong Farm (`canary_matrix.json`)
Mọi repository có tác vụ tự động hóa trên Farm bắt buộc phải được đăng ký trong `canary_matrix.json` và `canary_runner.py`:
1. `tiktok-follow`: Tab navigation hook (`open_following_tab`) & core runner.
2. `tiktok-luot nuoi acc`: `account-switcher` hook & `feed-swipe` hook.
3. `tiktok-add-bao-mat-f2a`: `batch-dispatch-lock` (JIT lock test) & `phase-b-security-ui` (UI bảo mật).
4. `Tiktok-video`: `media-push-manager` (kiểm tra push media) & `upload-select-ui` (mở UI chọn video đăng).
5. `tiktok-log-in`: `login-switcher` (mở giao diện chuyển tài khoản).
6. `Tiktok_Reg`: `reg-signup-ui` (mở giao diện đăng ký tài khoản).

## 3. Cơ Chế Dry-Run An Toàn Trong Ca Chạy Của Farm
- Khi farm đang chạy ca (máy bận), cấm cướp máy đang nuôi làm gián đoạn phiên.
- `canary_runner.py` cung cấp cờ `--dry-run`:
  - Kích hoạt focused test cô lập của từng repo (`test_run_batch_live_2fa.py`, `test_adapter.py`, `test_shared_core_usage.py`, `test_account_switcher_bridge.py`).
  - Kiểm tra 100% cú pháp, commit hash và working tree.
  - Cấp biên nhận Canary an toàn (`.canary_receipt.json`) để mở khóa `safe_push` mà không ảnh hưởng tới thiết bị thật.

## 4. Xử Lý Đường Dẫn & Tránh Fallback Sai Repo
- Trong `check_canary_status()`, bắt buộc kiểm tra tuần tự: (1) `Path(repo).is_dir()`, (2) `(Path("D:/Taadaa") / repo).is_dir()`.
- Tuyệt đối CẤM fallback về `Path.cwd()` khi không tìm thấy repo, vì sẽ dẫn tới việc kiểm tra nhầm commit SHA và working tree của repo hiện hành thay vì repo mục tiêu.
