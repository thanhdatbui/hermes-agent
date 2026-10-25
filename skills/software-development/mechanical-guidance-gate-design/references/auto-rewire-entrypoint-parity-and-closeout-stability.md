# Auto-Rewire Worker Entrypoint Parity & Closeout Gate Zero-Touch Stability

## 1. Bối cảnh & Hiện tượng (The Problem)

Khi thiết kế các cổng phân tầng luân chuyển (Tier Fallback Ladder: Tier 1 Sol Worker -> Tier 2 Agy CLI -> Tier 3 Claude / Haiku CLI), hệ thống thường gặp 2 căn bệnh đối lập nhau:

1. **Passive Returncode 126 Paralysis:** Khi chặn Coordinator đi cửa sau gọi trực tiếp `claude_worker.py --role worker` hoặc `haiku_worker.py`, nếu script chỉ in thông báo lỗi `⛔ [MECHANICAL TIER GATE VIOLATION]` rồi thoát `return 126` (Fail-Stop), Agent sẽ rơi vào trạng thái bế tắc hoặc lúng túng thử lại mù quáng, sinh ra hàng trăm lỗi G3 Worker Dispatch trong audit log.
2. **Nghi ngờ vô căn cứ & táy máy sửa Closeout Gate:** Khi thấy hệ thống có nhiều gate, Coordinator thường hoang mang nghi ngờ cả Closeout Gate (G5) và muốn can thiệp sửa đổi. Tuy nhiên, nếu Closeout Gate đang tự động chữa lỗi nhanh (3–7 phút) và khép kín qua Sol Repair Monopoly thì việc can thiệp tùy tiện sẽ phá hỏng quy trình nghiệm thu đang chạy trơn tru.

---

## 2. Chuẩn Kiến Trúc Bắt Buộc (Mechanical Invariants)

### A. Auto-Rewire Entrypoint Parity (Nắn Dòng Thay Vì Chặn Đứng)
Mọi worker CLI cấp dưới (`haiku_worker.py`, `claude_worker.py`) khi phát hiện lệnh gọi trực tiếp không có token on-demand hoặc cờ `--from-dispatch` **TUYỆT ĐỐI CẤM** trả về mã lỗi 126 để dừng hệ thống. BẮT BUỘC thực hiện Auto-Rewire 100%:

```python
# Mẫu triển khai chuẩn Auto-Rewire (Đã áp dụng đồng bộ trong haiku_worker & claude_worker):
is_authorized = (
    args.on_demand
    or args.from_dispatch
    or os.environ.get("USER_ON_DEMAND_CLAUDE") == "1"
    or os.environ.get("DISPATCH_TIER_CALLER") == "dispatch_worker"
)
if not is_authorized:
    dispatch_script = Path("D:/Taadaa/tools/dispatch_worker.py")
    print("[AUTO-REWIRE] ⛔ PHÁT HIỆN GỌI CLAUDE TRÁI PHÉP KHI CHƯA QUA THANG LUÂN CHUYỂN!", file=sys.stderr)
    print("[AUTO-REWIRE] 🔄 Tự động chuyển hướng (Rewire) sang Thang Luân Chuyển: Sol (Tier 1) -> Agy (Tier 2)...", file=sys.stderr)
    if dispatch_script.is_file():
        forward_cmd = [sys.executable, str(dispatch_script)]
        if args.file:
            forward_cmd += ["--file", args.file]
        if args.workdir:
            forward_cmd += ["--workdir", args.workdir]
        if args.timeout:
            forward_cmd += ["--timeout", str(int(args.timeout))]
        if args.max_turns:
            forward_cmd += ["--max-turns", str(args.max_turns)]
        forward_cmd.append(args.prompt or "")
        res = subprocess.run(forward_cmd, cwd=args.workdir)
        return res.returncode
    return 126
```

### B. Closeout Gate Zero-Touch Stability & Remediation Round Metrics
Trước khi quyết định can thiệp hoặc sửa bất kỳ Gate nào, BẮT BUỘC kiểm tra nhật ký đối soát (`gate_audit.jsonl` và `gate_compliance_watchdog.py`):
1. **Dữ liệu thực nghiệm số vòng sửa (Remediation Rounds):**
   - **80% trường hợp thành công chỉ tốn 1 đến 2 vòng:**
     * `tools`: 1 vòng (`TEST_FAILED (0)` $\to$ `APPROVED (91)`).
     * `Hermes`: 1 vòng (`DIFF_TOO_LARGE` $\to$ `APPROVED (85)`).
     * `tiktok-add-bao-mat-f2a`: 1 vòng (`REJECTED (76)` $\to$ `APPROVED (82)`).
     * `GPM auto`: 2 vòng (`REJECTED (78)` $\to$ `REJECTED (78)` $\to$ `APPROVED (82)`).
   - **Trường hợp cá biệt tốn 5–6 vòng (loay hoay):** Chỉ xảy ra khi Agent cũ phạm vào 2 lỗi cấm sơ đẳng:
     * Dùng cờ cấm `--skip-test` $\to$ Closeout Gate chém `TEST_SKIPPED` gán điểm 0.
     * Tạo candidate diff > 30.000 ký tự $\to$ dính `DIFF_TOO_LARGE` sập pipeline.
   - **Kết luận vận hành:** Khi không phạm 2 lỗi trên, Sol Repair giải quyết cực nhanh trong 1–2 vòng (3–7 phút).

2. **Quy tắc Bất Biến (Zero-Touch Invariant):** Khi G5 có 0 failures trong audit log rolling 6h, **TUYỆT ĐỐI CẤM SỬA ĐỔI CLOSEOUT GATE**. Mọi hành vi táy máy trên một cổng đang chạy trơn tru đều là over-engineering gây nguy cơ regression.

### C. Kỷ Luật Hành Động Trước - Báo Cáo Sau (Anti-Dithering & Action-First Mandate)
- **Cấm lảm nhảm / phân trần dài dòng:** Khi User đã phát lệnh "R làm đi", Coordinator BẮT BUỘC thực thi dứt điểm bằng lệnh/code/test O(1) tại chỗ trước; tuyệt đối CẤM dừng lại viết sớ lý thuyết, giải thích hay phân trần dài dòng khi chưa có thay đổi thực tế trên đĩa.
- **Tiêu chuẩn hoàn tất:** Phải có tool output thật chứng minh patch đã land, test suite pass hoặc service đã reload thì mới báo cáo kết quả ngắn gọn.

---

## 3. Bằng Chứng Thực Nghiệm (Audit Proof)
- Bộ test suite `D:/Taadaa/tools/tests/test_claude_worker.py` kiểm chứng 100% case `test_tier_gate_auto_rewires_direct_worker`:
  - Input: gọi `claude_worker.py task --role worker` không có flag.
  - Assert: exit code 0, bắt được marker `[AUTO-REWIRE]` trong stderr, và lệnh `dispatch_worker.py` được gọi thay thế an toàn.
