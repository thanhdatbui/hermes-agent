# Pipeline Baseline Over-Engineering & Scoped Transaction Recovery

## 1. Hiện Tượng: Vòng Lặp Tự Triệt Tiêu (Paralysis Death Loop)
Trong các repository có nhiều file dirty/untracked hoặc file log hoạt động hàng ngày (như `D:/Taadaa/tools` với >500 file), cơ chế an toàn quá mức (over-engineering) của patch pipeline dẫn đến tình trạng tê liệt:
1. **Repository-wide Baseline Hash Trap:** S0 Precheck chụp SHA256 snapshot của TOÀN BỘ file dirty/untracked trong repo.
2. **Subprocess Side-Effect Collision:** Khi một utility nội bộ (như `find_existing_logic.py`) chạy ở S0 và ghi thêm 1 dòng receipt token vào `find_existing_logic_receipts.jsonl`, file này bị thay đổi nội dung (drift SHA256).
3. **False Positive Scope Violation:** Tầng S2 Patch kiểm tra baseline hash drift và quy kết đây là hành vi "Worker sửa lén file baseline ngoài scope".
4. **Fail-Closed & Rollback:** Pipeline hoảng loạn kích hoạt rollback toàn bộ, huỷ bỏ cả patch hợp lệ.
5. **Watchdog Failure & Death Spiral:** Watchdog ghi nhận thất bại, Agent loay hoay tìm cách thử lại và kích hoạt các bẫy Guard khác.

---

## 2. Bản Chất Lỗi Kiến Trúc (Architecture Anti-Pattern)
- **Nhầm lẫn ranh giới bảo vệ:** Nhầm giữa việc *bảo vệ toàn vẹn tài sản hệ thống* và *kiểm soát tuyệt đối mọi byte thay đổi trên filesystem*.
- **Giả định sai về `git status`:** Coi mọi file untracked/dirty xuất hiện trong lúc chạy pipeline đều là do Worker phá hoại, bỏ qua thực tế rằng các tiến trình nền, logging hoặc chính công cụ precheck đang ghi artifact.
- **Tự bẫy Guard Self-Protection:** Hook bảo vệ (`GUARD_SOURCE_BLACKLISTED`) chặn đứng Worker sửa chính file Hook ngay cả khi đó là nhiệm vụ được chỉ định qua Pipeline.

---

## 3. Kiến Trúc Khắc Phục: Scoped Transaction Model (O(1))

### Quy Tắc 1: Scoped Snapshot (Chỉ Hash Target Files)
- Pipeline CHỈ chụp baseline và kiểm soát hash của đúng danh sách `target_files` (các file trong Scope sửa).
- Không quét, không hash toàn bộ 500+ file rác/untracked trong repo tại S0.

### Quy Tắc 2: Cách Ly Tuyệt Đối Runtime Artifacts Khỏi Git Repo
- Các file receipt (`find_existing_logic_receipts.jsonl`), cache index (`farm_logic_index.json`), state tạm BẮT BUỘC lưu tại `D:/Taadaa/runtime/` hoặc được khai báo triệt để trong `.gitignore`.
- Tuyệt đối không để utility tool ghi đè trực tiếp lên working tree của Git.

### Quy Tắc 3: Contextual Guidance Thay Vì Cấm Đoán Mù
- Khi Guard chặn thao tác quét đĩa (`GUARD_DANGEROUS_ROOT`, `GUARD_PYTHON_WALKER`): Guidance BẮT BUỘC chỉ đường dùng công cụ tìm kiếm code hợp lệ (`search_files(target='files', pattern='...')` hoặc `git ls-files`).
- CẤM TUYỆT ĐỐI nhồi nhét chỉ dẫn Farm Android (`inspect_machine.py <N>`) vào các vi phạm liên quan đến tìm kiếm mã nguồn.

### Quy Tắc 4: Tra Cứu Máy O(1) Bằng Serial
- Thay vì để Guard trả về placeholder generic `<N>` khiến Agent loay hoay, dùng `farm_db.get_machine_by_serial(serial)` để phân giải trực tiếp số máy cụ thể (ví dụ: `9885b...` -> `M1`), hoặc auto-rewire bọc lock cho các lệnh read-only an toàn.
