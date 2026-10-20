# Sol Repair Syntax Error Fallback & Pre-Push Grace Band Verification (20/10/2026)

## 1. Sol Repair Syntax Failure & Fallback Worker Trigger
- **Hiện tượng:** Khi Closeout Gate trả về điểm < 85 (ví dụ 78/100, REJECTED), quy chuẩn Strike 1 kích hoạt `python D:/Taadaa/tools/sol_repair.py`.
- **Sự cố:** `sol_repair.py` sinh patch đề xuất nhưng bị lỗi thụt dòng (`syntax_ok: false`, `unindent does not match any outer indentation level`), hoặc Sol hiểu sai nghiệp vụ (đòi hỏi `end_time` sớm phải trả về `False`).
- **Xử lý chuẩn:** 
  - Điều kiện Fallback Worker được kích hoạt hợp lệ: `sol_repair.py valid=false` / `syntax_ok=false`.
  - Coordinator chuyển ngay sang Single Dispatch Gateway:
    `python D:/Taadaa/tools/dispatch_worker.py --workdir <repo> --file <file> "<prompt O(1)>"`
  - Haiku CLI (`claude-haiku-5-5`) xử lý dứt điểm trong 15-20s, bảo toàn target file và không tạo file rác.

## 2. Closeout Gate Grace Band (80-84) & Pre-Push Hook Alignment
- **Grace Band:** Khi điểm số đạt 80-84 điểm (ví dụ 83/100) và thỏa mãn các điều kiện an toàn, Closeout Gate cấp token:
  `[CLOSEOUT_TOKEN: ...] (Tier: grace)` và exit code 0 (`APPROVED`).
- **Pre-Push Hook (`.git/hooks/pre-push`):**
  - Hook đọc `gate_audit.jsonl` tìm bản ghi khớp `head_sha` hoặc diff.
  - Ngưỡng phê duyệt chấp nhận cả Grace Band (`score >= 80 and is_grace is True`).
  - Lệnh `git push origin master` được hook thông qua an toàn:
    `✅ [pre-push] Closeout Gate OK: verdict=APPROVED score=83 passed=True commit=...`
