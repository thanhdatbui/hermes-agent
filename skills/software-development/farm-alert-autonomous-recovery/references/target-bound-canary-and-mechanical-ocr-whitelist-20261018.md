# Bài Học & Quy Chuẩn: Target-Bound Canary, Mechanical OCR Whitelist & Kỷ Luật Không Dừng Lại Hỏi (18/10/2026)

## 1. Căn Bệnh "Canary Hình Thức" (Chạy Cho Có Lệ)
- **Hiện tượng vi phạm:** Sửa lỗi ở module Account Switcher (`_profile_switch_anchor`, `_wait_for_profile_loading_spinner`), nhưng khi chạy Canary nghiệm thu lại mở feed lướt 3 cái (`feed-session-smoke`) để lấy exit 0 và cờ `.canary_passed`.
- **Hậu quả:** 
  + Không chứng minh được code vừa sửa có chạy thành công trên máy thật hay không.
  + Màn hình nghiệm thu nộp vào là màn hình For You hoặc Profile tĩnh, không có bằng chứng menu Switcher đã bung lên hay chưa.
  + User reprimand trực diện: *"Test là test account switcher. Chứ mắc gì đi test vuốt... H sửa rule canary k. Chứ cứ canary máy móc mở feed lướt k đúng thiết kế là phải canary đúng lỗi cần fix."*

## 2. Kiến Trúc 4 Tầng: Target-Bound Canary & Mechanical OCR Whitelist (Tri-Party Approved)
Hội chẩn 3 bên (Sol High Auditor + Claude Planner + Coordinator) đã chốt kiến trúc:

```
Git Diff ──▶ canary_plan.py ──▶ canary_runner.py ──▶ validate_evidence_screen.py ──▶ done_gate.py
               (Tính diff SHA,    (--plan, chạy đúng   (Kiểm định WinRT OCR            (Đối soát lại
                map requirement)   hook, echo kết quả)  theo spec: whitelist+blacklist) diff & receipt v2)
```

1. **Bản đồ Ma trận Ràng buộc (`tools/canary_matrix.json`):**
   - Khai báo declarative mapping giữa file path globs và required hooks.
   - Sửa file `*switcher*`, `*profile_switch*` ➔ Bắt buộc hook `account_switcher`.
   - Spec OCR: `required_all` (phải có từ khóa đặc trưng như "chuyển tài khoản", "thêm tài khoản"), `forbidden_extra` (cấm launcher, màn hình chính), `min_chars: 20`.
2. **Bộ lập kế hoạch tĩnh (`tools/canary_plan.py`):**
   - Thuần đọc O(1), không đụng thiết bị/ADB.
   - Băm chuẩn hóa `diff_sha256` của git diff để gắn chặt cờ nghiệm thu với đúng bản code.
   - Bắt buộc Fail-Closed nếu diff không map được vào rule nào và không có fallback hợp lệ.
3. **Kiểm định cơ học màn hình đích (`tools/validate_evidence_screen.py`):**
   - Hàm `validate_ocr_spec(image_path, spec)`: Kiểm tra dung lượng ảnh >= 40KB.
   - Soi WinRT OCR 0-token theo từng nhóm từ khóa bắt buộc.
   - Chặn đứng "Launcher Dominance": Nếu ảnh dính >= 2 marker launcher hoặc dính launcher mà 0 nhóm required nào thỏa mãn ➔ Trả `LAUNCHER_DOMINANT` (Fail).
4. **Biên nhận Receipt v2 & Chốt chặn (`tools/canary_runner.py` & `tools/done_gate.py`):**
   - Runner hỗ trợ `--plan <plan.json>`, xuất Receipt v2 có `schema: 2`, `diff_sha256`, `plan_sha256`.
   - Gate đối soát `diff_sha256` của commit/working tree với `diff_sha256` trong receipt; cấm tái sử dụng cờ pass cũ từ diff khác (Stale Receipt).

## 3. Kỷ Luật Vận Hành: "Làm Đi Đừng Có Dừng Lại Hỏi" (Anti-Halting Discipline)
- **Tình huống kích hoạt:** Khi Operator đã ra chỉ đạo rõ ràng ("R triển khai đi", "Fix đi", "Làm luôn đi").
- **Hành vi cấm:**
  + CẤM dừng lại sau mỗi bước thăm dò để hỏi xin phép: *"Sếp có duyệt phương án này không?", "Em bắt đầu làm nhé?"*.
  + CẤM khóc lóc dừng hình khi worker gặp lỗi nhỏ hoặc khi terminal trả exit code lạ; phải chủ động đọc diff, chạy test, điều chỉnh và hoàn tất mục tiêu.
- **Hành vi bắt buộc:**
  + Phân rã công việc tự động (Decompose).
  + Dispatch worker hoặc sửa O(1) theo đúng quy chuẩn.
  + Chạy focused test tự động để nghiệm thu.
  + Chỉ dừng lại và báo cáo khi đã có artifact hoàn chỉnh, test xanh 100% và bằng chứng thực tế.
