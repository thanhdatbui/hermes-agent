# Multi-Repo Closeout & Chained Verification Protocol

## 1. Local Commit Before Pull & Rebase in Multi-PC Environment
Khi làm việc trên nhiều máy hoặc nhiều repository cùng một lúc:
1. **Commit Local Trước:** Đóng băng các thay đổi và test đã pass vào commit local (`git commit -m "..."`), tuyệt đối không pull khi working tree chưa commit sạch phần cho phép để tránh conflict hoặc mất code.
2. **Xử lý Dirty Files Ngoài Allowlist:** Nếu working tree còn uncommitted changes hoặc untracked files ngoài allowlist mà `git pull --rebase` từ chối thực hiện, dùng `git stash -k -u` để tạm cất các file ngoài scope, sau đó `git pull --rebase <remote> <branch>`, rồi `git stash pop` để khôi phục nguyên vẹn.
3. **Pull Rebase Sau:** Kéo commit mới nhất từ remote về và rebase commit local lên đầu (`git pull --rebase origin master`).
4. **Kiểm Thử Sau Rebase & Remote Verification:** Sau khi rebase thành công, chạy lại quick test suite / syntax check, sau đó push và dùng `git ls-remote origin <branch>` để đối chiếu exact SHA với `HEAD`.

## 2. Ghost IME & Chained Allowlist Token Pattern
- **Positive-Only XML Keyboard Detection:** UI XML chỉ dùng làm bằng chứng khẳng định bàn phím hiển thị (`visible=True`). Không suy đoán âm tính từ XML để tránh lỗi `adjustPan` / edge-to-edge; luôn fallback xuống `dumpsys input_method` với bitmask `mImeWindowVis` bit 1 (`0x2 = IME_VISIBLE`) làm nguồn sự thật cao nhất.
- **Fail-Closed Chained Token Authorization:** Khi một flow (như Add Phone) hoàn tất và sinh ra popup kế tiếp thuộc package khác (như Facebook permission), sử dụng token ngắn hạn (30s) băm SHA-256 nội dung XML (`xml_hash`) và tiêu thụ nguyên tử (atomic pop) trước khi tap để ngăn chặn triệt để replay và unauthorized standalone popups.
