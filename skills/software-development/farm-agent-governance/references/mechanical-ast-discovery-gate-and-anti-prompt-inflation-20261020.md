# Case Study: Cơ Giới Hóa Tra Cứu Logic 8 Repo & Triệt Tiêu Nhồi Nhét Prompt Mềm (2026-10-20)

## 1. Hiện Tượng & Sự Cố (Problem Statement)
- Sau khi xây dựng xong công cụ tra cứu AST chéo 8 repo (`find_existing_logic.py`), Coordinator lại mở các file kỹ năng (`SKILL.md`) ra nhồi nhét thêm quy định dặn dò prompt dài dòng.
- Operator phản ứng gay gắt: *"đã có cơ giới hoá sao cứ nhồi nhét prompt chi mệt v r gọi claude review chưa"*.
- **Căn nguyên bệnh lý:** Thói quen xấu cũ của AI Coordinator: ỷ lại vào dặn dò prompt mềm thay vì chốt chặn cơ học. Khi đã có công cụ quét AST, hashing receipt và unit test, việc chèn thêm prompt giải thích chỉ làm loãng context window, tăng token overhead và gây chỉ thị trôi dạt (instruction drift).

## 2. Giải Pháp Cơ Giới Hóa Thay Thế (Mechanical Replacement)
1. **Công Cụ Tra Cứu Tự Động Toàn Farm 8 Repo (`tools/find_existing_logic.py`):**
   - Thay vì dặn dò "hãy tìm trong automation-core", công cụ quét tự động 1.078 file Python trên cả 8 repo (`automation-core`, `Tiktok_Reg`, `tiktok-follow`, `tiktok-luot nuoi acc`, `tiktok-add-bao-mat-f2a`, `GPM auto`, `tools`, `Hermes`).
   - Tốc độ tra cứu dưới 0.2s nhờ cache AST `tools/farm_logic_index.json` (schema v2, TTL 24h).
2. **Cơ Chế Khóa Bằng Receipt Token & Ledger Append-Only:**
   - Lệnh tra cứu: `python D:/Taadaa/tools/find_existing_logic.py "<keywords>" --top 5 --receipt`
   - Token mã hóa `ELR-<hash>` được lưu vào sổ cái `tools/find_existing_logic_receipts.jsonl`.
   - Gate cơ học xác thực tính hợp lệ và thời hạn: `python D:/Taadaa/tools/find_existing_logic.py --verify <TOKEN>`.
3. **Claude Reviewer Audit Bắt Buộc:**
   - Đưa công cụ mới vào vòng lặp đối kháng độc lập qua Claude Reviewer (Sonnet 5.5).
   - Claude Reviewer chỉ ra các lỗ hổng fail-open: cache đầu độc khi repo offline, thiếu kiểm tra repo coverage, crash do `RecursionError` trên file AST sâu.
   - Chỉ chốt công cụ khi đạt 100% test pass (52/52 tests) và thẩm định độc lập thông qua.

## 3. Kỷ Luật Bất Biến (Invariant)
- **CẤM NHỒI PROMPT KHI ĐÃ CƠ GIỚI HÓA:** Nếu một quy trình đã được đóng gói thành CLI / Hook / Unit Test cơ học, CẤM TUYỆT ĐỐI mở file `SKILL.md` hay `MEMORY.md` ra viết lại các hướng dẫn dặn dò trùng lặp.
- Mọi ràng buộc phải thể hiện bằng **lệnh gọi công cụ có thể kiểm chứng được** (`exit code == 0`, `receipt token`), không dùng lời hứa suông.
