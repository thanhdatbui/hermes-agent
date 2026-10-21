---
name: windows-safe-file-cleanup
description: "Use when deleting files on Windows via safe Recycle Bin."
version: 1.0.0
platforms: [windows]
category: software-development
metadata:
  hermes:
    tags: [recycle-bin, cleanup, safe-delete, windows, quarantine, zero-hard-delete]
    related_skills: [taadaa-farm-ops-rules, desktop-automation]
---

# Windows Safe File Cleanup & Zero Hard-Delete

Use this skill whenever removing, cleaning, pruning, or purging files or directories in Windows development, farm, or production environments.

## 1. Core Invariants (Bất biến tối cao)
1. **Zero Hard-Delete Invariant:** CẤM TUYỆT ĐỐI các lệnh xóa hủy trực tiếp trên đĩa: `shutil.rmtree`, `os.remove`, `os.unlink`, `Path.unlink`, `rm -rf`. Mọi thao tác loại bỏ file/thư mục bắt buộc phải đưa vào **Windows Recycle Bin (`$Recycle.Bin`)**.
2. **Fail-Closed on Rejection:** Nếu Windows Recycle Bin từ chối nhận (file vượt dung lượng quota, ổ đĩa ngoài/mạng không có Recycle Bin, lỗi quyền), hệ thống **bắt buộc di chuyển sang Thư mục Cách ly (Quarantine)** trên cùng volume. Nếu cả Recycle Bin và Quarantine đều lỗi: **DỪNG LẠI NGAY LẬP TỨC (ABORT), GIỮ NGUYÊN FILE NGUỒN**, cấm xóa ép.
3. **Audit Trail Bắt Buộc:** Mọi thao tác dọn dẹp đều phải ghi nhận log hoặc `manifest.json` chứa: đường dẫn gốc, kích thước, SHA-256 hash, thời điểm và danh tính tiến trình thực thi.

## 2. Kiến Trúc Thực Thi Kỹ Thuật (3 Tầng Đồng Thuận 3 Bên 18/10/2026)

Theo biên bản thống nhất 100% giữa Coordinator, Advisor Sol (:20129) và Reviewer Claude Sonnet 5.5:

### Tầng 1: Atomic Quarantine Cùng Volume (BẮT BUỘC & CỐT LÕI AN TOÀN)
- **Vị trí:** Đặt tại thư mục ẩn ngay trên cùng ổ đĩa: `D:/Taadaa/.quarantine/YYYY-MM-DD/<timestamp>_<uuid>_<filename>`.
- **Atomic Move NTFS:** Dùng `MoveFileExW` / `os.replace` trên cùng filesystem để hoàn thành trong $O(1)$, không copy tránh đứt gãy, không phụ thuộc Shell Explorer, hoạt động bền bỉ trong mọi ngữ cảnh (service, cron, watchdog).
- **Write-Ahead Logging (WAL):** Ghi log audit JSONL (nguồn, đích, timestamp, SHA-256 hash, actor/process) **trước khi move** để không bao giờ mất dấu nếu crash giữa chừng.
- **Post-Verification Bắt Buộc:** Sau khi move, bắt buộc đọc lại metadata tại quarantine path (tồn tại, kích thước khớp, hash khớp) VÀ xác nhận đường dẫn nguồn không còn tồn tại.

### Tầng 2: Recycle Bin Native API (TIỆN ÍCH UX TÙY CHỌN, BEST-EFFORT)
- Dùng `IFileOperation` với cờ `FOFX_RECYCLEONDELETE` (hoặc PowerShell `Microsoft.VisualBasic.FileIO.FileSystem.DeleteFile` với `RecycleOption.SendToRecycleBin`) để đưa vào Recycle Bin của Explorer phục vụ người dùng xem trực quan.
- **Tuyệt đối cấm dùng `SHFileOperationW` cũ** vì rủi ro tràn `MAX_PATH` 260 ký tự và không bắt được mã lỗi chi tiết.
- Lớp này là best-effort (không làm gián đoạn pipeline nếu thất bại, vì Tầng 1 Quarantine đã bảo vệ 100%).

### Tầng 3: Nguyên Tắc FAIL-CLOSED Tuyệt Đối
- Nếu gặp file lock (`WinError 32`), thiếu quyền, symlink trỏ ra ngoài, hoặc bất kỳ lỗi không xác định nào: **DỪNG LẠI NGAY LẬP TỨC (ABORT), GIỮ NGUYÊN FILE NGUỒN**, ném exception và phát alert. Tuyệt đối không có nhánh "xóa ép cho được".

## 3. Invariants Kỹ Thuật Bắt Buộc Cho `safe_recycle.py`
1. **FAIL-CLOSED:** Mọi lỗi/exception đều giữ nguyên file nguồn, không xóa mạo hiểm.
2. **Same-volume atomic move:** Quarantine cùng volume `D:`, tắt flag replace ẩn, tạo tên file đích unique bằng UUID/timestamp chống va chạm.
3. **Pre-move lock/symlink check:** Resolve symlink/junction trước (không theo symlink xóa target thật); test lock bằng `CreateFileW` exclusive trước khi move.
4. **TOCTOU Guard:** Re-verify identity (file id / inode / size) ngay trước khi gọi lệnh move.
5. **Post-verification:** Đọc lại metadata đích và xác nhận nguồn biến mất.
6. **No privilege escalation / no `--force`:** Không tự ý nâng quyền admin để ép xóa.
7. **AST Gate cưỡng chế:** Chặn ở mức code review trong `closeout_gate.py` và pre-commit: cấm mọi hàm `os.remove`, `os.unlink`, `Path.unlink`, `shutil.rmtree` trên toàn repo; mọi thao tác dọn dẹp bắt buộc import và gọi qua `safe_recycle.py`.

## 3. Corner Cases & Pitfalls
1. **File Lock (WinError 32):** Nếu file đang bị tiến trình khác (adb, python daemon, excel) khóa handle, **CẤM ép đóng handle bằng tool bạo lực**. Thử lại tối đa 2 lần với backoff 1s; nếu vẫn khóa thì bỏ qua file đó, ghi warning và báo cáo.
2. **Symlink / Reparse Point:** Tuyệt đối không xóa đệ quy xuyên qua symlink/junction trỏ ra ngoài repo. Chỉ xóa chính junction entry đó.
3. **Hiểu nhầm ý định Operator về Backup:** Khi người dùng bảo "backup xong dọn hết đi", ý là **di chuyển/gom các tệp rác vào thư mục lưu trữ backup để giải phóng repo**, TUYỆT ĐỐI KHÔNG ĐƯỢC XÓA BẢN BACKUP.
4. **Pytest Verification Vacuous Passing Pitfall:** Tuyệt đối không dùng `if p.exists(): assert ...` trong integration test cho file cấu hình/proxy. Nếu file thiếu, test sẽ bỏ qua assertion và pass ảo (vacuous truth), bị Closeout Auditor từ chối. Bắt buộc dùng `assert p.exists()`.
5. **Bẫy Un-staged Tool Bị Xóa Khi Dọn Rác Untracked:** Khi một script tool cốt lõi (`sol_repair.py`, `canary_runner.py`...) bị un-stage ra khỏi commit để thu hẹp diff byte (`git restore --staged <file>`), file đó rơi vào trạng thái untracked (`??`). Khi chạy script dọn dẹp file untracked, nếu không có allowlist bảo vệ, các file tool này sẽ bị xóa nhầm gây tê liệt hệ thống (ví dụ `sol_worker.py` crash do mất `sol_repair.py`). Mọi thao tác dọn dẹp bắt buộc dùng `safe_recycle.py`, cấm quét đĩa diện rộng để xóa mù các file `.py` untracked, và bắt buộc commit các tool canonical vào Git.
6. **Kỷ Luật Phân Vùng Ổ C vs Ổ D (User Invariant 21/10/2026):** Toàn bộ file scratch, frame video, audio dub, temporary test artifacts BẮT BUỘC ghi vào ổ D: (`D:/Taadaa/runtime/`, `D:/Taadaa/.quarantine/`), CẤM xả rác vào User Home trên ổ C: khiến phân vùng hệ thống bị cạn kiệt dung lượng. Khi phát hiện rác bị nhồi vào ổ C:, di chuyển nguyên khối sang `D:/Taadaa/.quarantine/c_drive_migration/` theo quy trình Zero Hard-Delete.

## 4. Canonical Tool: `D:/Taadaa/tools/safe_recycle.py`
Đã thi công và nghiệm thu 9/9 unit tests (`D:/Taadaa/tools/tests/test_safe_recycle.py`):
- **CLI:** `python D:/Taadaa/tools/safe_recycle.py <file|dir> [<file|dir> ...]`
- **Python API:**
  ```python
  from safe_recycle import safe_recycle, SafeRecycleError
  records = safe_recycle(["path/to/file1.png", "path/to/folder"])
  ```
- **Hành vi:** Tự động đưa vào `<volume>/.quarantine/YYYY-MM-DD/<HHMMSS>_<uuid8>_<name>`, ghi WAL `manifest.jsonl`, atomic move `os.replace`, và post-verification (khớp size, đích tồn tại, nguồn biến mất).

## 5. References & Chi Tiết Kiến Trúc
- Phản biện kiến trúc chuyên sâu từ Advisor Sol: [`references/advisor-sol-critique-and-zero-hard-delete-architecture.md`](references/advisor-sol-critique-and-zero-hard-delete-architecture.md)
- Biên bản đồng thuận 3 bên (Coordinator + Advisor Sol + Reviewer Claude Sonnet 5.5): [`references/three-party-consensus-zero-hard-delete-20261018.md`](references/three-party-consensus-zero-hard-delete-20261018.md)
- Bẫy Closeout Scope Binding & Downstream Integration: [`references/closeout-scope-and-downstream-integration-pitfalls.md`](references/closeout-scope-and-downstream-integration-pitfalls.md)
