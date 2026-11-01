# Scoped Transaction Architecture vs Overengineered Repository-Wide Baseline

## Bối cảnh & Hiện tượng Bại liệt (System Paralysis)
Khi `unified_patch_pipeline.py` hoạt động trên repository có nhiều file dirty/untracked (như `D:/Taadaa/tools` với >500 file nháp/log):
1. **Repository-Wide Baseline Hash Trap:** S0 snapshot SHA256 của toàn bộ file untracked/dirty (`--untracked-files=all`).
2. **False Scope Violation:** Các tool tiện ích nội bộ (như `find_existing_logic.py`) sinh receipt token hoặc file log trong working tree, làm SHA256 baseline thay đổi -> Pipeline hiểu lầm là Worker tự ý sửa file ngoài scope và kích hoạt **Full Rollback** vô cớ (`FAIL-CLOSED`).
3. **Guard Block Death Spiral:** Sau rollback, Agent loay hoay tìm đường khác, va phải Guard tự vệ (`GUARD SELF-PROTECTION`) hoặc guidance "chỉ đường mù" (tìm file code lại bảo chạy `inspect_machine.py`), dẫn tới đứng im hoàn toàn.

## Giải pháp Kiến trúc O(1) Scoped Transaction
1. **Loại bỏ Untracked Files khỏi Baseline Git:**
   - Trong `unified_patch_pipeline.py`: chuyển `git status` sang `--untracked-files=no`.
   - Baseline S0 chỉ snapshot đúng các file đã được Git theo dõi (`tracked changed files`), biến bước S0 thành $O(1)$ (< 0.1s).
2. **Cách ly Runtime Logs/Receipts khỏi Git Tree:**
   - Chuyển `find_existing_logic_receipts.jsonl` và mọi file cache/receipt sang `D:/Taadaa/runtime/audit_logs/`.
   - Cấm mọi công cụ tiện ích ghi log đè lên working tree của repo Git.
3. **Exact Patch Direct Layer O(1) tại S2:**
   - Sử dụng `apply_patch.py` làm tầng thi công ưu tiên số 0 trước khi gọi Worker LLM.
   - Nếu AI Planner trả về Exact Patch Contract có anchor khớp tuyệt đối, áp dụng trực tiếp trong 0.05s, không tốn token và không phụ thuộc quota Claude/Worker.
4. **Miễn trừ Device Canary cho Tooling Repos:**
   - Trong `is_farm_device_related` và `is_taadaa_farm_repo`: loại trừ các repo hạ tầng CLI (`tools`, `hermes`) khỏi việc ép chạy Canary trên máy thật Android.
5. **Smart Machine Resolution thay vì Placeholder mù:**
   - Guard ADB (`guard_device_bulkhead.py`) tra cứu $O(1)$ `farm_db.get_machine_by_serial(serial)` để điền đích danh `--machine {id}` thay vì in placeholder generic `<N>`.
   - Guidance quét đĩa (`guardgate/rules.json`) phải chỉ đúng tool tìm file (`search_files(target='files')`, `git ls-files`), cấm xúi sang lệnh ADB farm.
