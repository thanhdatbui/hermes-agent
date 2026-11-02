# Case Study: Phân Tầng Gate 6 Canary (UI vs. Backend) trong Unified Pipeline

## 1. Triệu chứng & Sai lầm
- Khi thực hiện chuẩn hoá dữ liệu sang SQLite (`farm_master.db`, `account_source.py`), Coordinator gọi `unified_patch_pipeline.py`.
- Pipeline tự động ép chạy `canary_runner.py` trên Máy 64, cố bật màn hình điện thoại chụp splash screen TikTok để thỏa mãn Gate 6.
- Hậu quả:
  - Báo cáo đối phó bằng ảnh vô nghĩa (ảnh màn hình app không chứng minh được tính đúng đắn của code database/backend).
  - Gây lãng phí tài nguyên máy farm và làm gián đoạn thiết bị.
  - User phê bình gay gắt vì logic gate đã được hướng dẫn phân tầng nhưng code pipeline vẫn hardcode chặn `--no-canary`.

## 2. Gốc rễ kỹ thuật
Trong `unified_patch_pipeline.py`, đoạn kiểm tra cờ `--no-canary` bị hardcode:
```python
if args.no_canary:
    if farm_repo or keyword_match:
        print("[GATE 6 GUARD] Phát hiện lệnh sửa code repo Farm/Device; cờ --no-canary của Agent bị từ chối!")
        need_canary = True
```
Do `farm_repo` hoặc từ khóa `tiktok` luôn khớp trong repo `Tiktok-video`, cờ `--no-canary` bị gạt bỏ hoàn toàn dù task chỉ sửa DAL SQLite.

## 3. Giải pháp chuẩn hóa
1. **Chạy `canary_plan.py` sớm:** Đọc `evidence_type` (`backend`, `ui`, `hybrid`) và `requires_screencap` từ `git diff`.
2. **Cho phép skip canary máy thật:**
   - Nếu `requires_screencap=False` hoặc `evidence_type == 'backend'`: chấp thuận `--no-canary` hoặc tự động skip canary máy thật.
   - Chỉ ép canary điện thoại khi diff thực sự thay đổi UI / App flow (`requires_screencap=True`).
3. **Nghiệm thu backend:** Sử dụng Focused Test + DB Read-back làm Ground Truth.
