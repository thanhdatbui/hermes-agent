# Jobs.json Diff Inflation & Targeted Scope Hygiene in Closeout Gate (20/10/2026)

## 1. Hiện Tượng & Ngữ Cảnh Sự Cố

Khi chạy quy trình Closeout Gate (`closeout_gate.py`) để chốt phiên cho tác vụ cập nhật cronjob / watchdog:
```bash
python "D:/Taadaa/tools/closeout_gate.py" \
  --repo "D:/Taadaa/Hermes" \
  --files deploy/hermes-home/scripts/cron_night_tiktok_2fa_watchdog.py \
          tests/test_cron_night_tiktok_2fa_watchdog.py \
          deploy/hermes-home/cron/jobs.json \
  --base HEAD --json-output
```

Hệ thống lập tức kích hoạt Fail-Fast và thoát với mã lỗi 3:
```text
══════════════════════════════════════════════════════════════════════
  STEP 2: EXTRACT CANDIDATE DIFF
══════════════════════════════════════════════════════════════════════
  ✘ GATE-FAIL(diff-too-large): [Gate Fail-Fast: DIFF_TOO_LARGE] targeted diff quá lớn (80012 > 30000 bytes).
    Vi phạm quy chuẩn phân rã task O(1). Phải thu hẹp diff trước khi gọi Reviewer.
```

---

## 2. Phân Tích Nguyên Nhân Gốc Rễ (Root Cause)

1. **Bản chất của file `jobs.json`:**
   - `deploy/hermes-home/cron/jobs.json` lưu trữ toàn bộ định nghĩa của hơn 50 cronjob trên farm Taadaa.
   - Khi có cronjob được cập nhật tham số (ví dụ đổi `deliver: local` hoặc sửa prompt/schedule), `cron_sync_watchdog.py` đồng bộ toàn bộ file JSON giữa Kibe runtime và Git deploy.
   - Quá trình format JSON hoặc cập nhật timestamp/state thường làm thay đổi hàng trăm dòng (ở trường hợp này: 352 insertions, 258 deletions = 610 dòng, kích thước diff riêng của `jobs.json` vượt quá 47,000 bytes).

2. **Cơ chế Fail-Fast của `closeout_gate.py` (`MAX_DIFF_BYTES_GATE = 30_000`):**
   - Để ngăn chặn tràn context của LLM Reviewer và ép buộc phân rã task O(1), `closeout_gate.py` thiết lập trần cứng `effective_max = 30_000` bytes đối với toàn bộ diff đầu vào.
   - Hai file code và test (`cron_night_tiktok_2fa_watchdog.py` và `test_cron_night_tiktok_2fa_watchdog.py`) có tổng diff khoảng 32KB. Khi bị kẹp chung với `jobs.json` (47KB), tổng diff vọt lên **80,012 bytes**, vượt xa giới hạn 30,000 bytes.

---

## 3. Quy Tắc Điều Phối & Khắc Phục (Discipline & Invariants)

### A. Tách bạch Code Thẩm Định vs Runtime Sync Artifacts
- `jobs.json` và các file runtime state (`*_state.json`) là các tạo tác đồng bộ máy móc (machine-synced artifacts) được quản lý tự động bởi `cron_sync_watchdog.py` và cron `sync-hermes-skills-and-brain-to-git`.
- LLM Reviewer (`Sol High` / `Claude`) chỉ thẩm định tính đúng đắn về mặt logic, kiến trúc và test coverage của mã nguồn thực thi (`.py`) và test suite (`test_*.py`).
- **CẤM gom `jobs.json` vào danh sách `--files` của `closeout_gate.py`**:
  - Khi chạy closeout review, danh sách `--files` CHỈ ĐƯỢC CHỨA file code triển khai và file unit test tương ứng (`deploy/.../scripts/<script>.py` và `tests/test_<script>.py`).

### B. Quy trình Commit & Closeout Khi Có Sửa Đổi Jobs.json
1. **Bước 1 (Closeout Code Thẩm Định):**
   - Chỉ định danh sách file logic và test vào `--files`:
     ```bash
     python "D:/Taadaa/tools/closeout_gate.py" --repo "D:/Taadaa/Hermes" \
       --files deploy/hermes-home/scripts/cron_night_tiktok_2fa_watchdog.py \
               tests/test_cron_night_tiktok_2fa_watchdog.py \
       --base HEAD --json-output
     ```
2. **Bước 2 (Đồng bộ Jobs.json & Commit riêng biệt):**
   - Để `cron_sync_watchdog.py` đồng bộ `jobs.json` về kho lưu trữ, hoặc commit `jobs.json` với tiền tố `chore(cron): sync jobs.json` riêng biệt, không để diff cấu hình làm vỡ diff budget của logic code.
