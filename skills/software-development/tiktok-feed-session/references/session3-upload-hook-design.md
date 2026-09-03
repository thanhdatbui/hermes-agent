# Thiết kế Hook Đăng Video (tiktok_workflow) vào Phiên Cuối Ca Nuôi Acc

Tài liệu này ghi lại kiến trúc, quy tắc phân lập và 5 tầng Preflight Gate đã được kiểm duyệt (`APPROVED` bởi `ag/claude-opus-4-6-thinking`) để nối tự động quy trình upload video vào phiên cuối (phiên 3) của mỗi ca nuôi acc TikTok.

---

## 1. Nguyên tắc cốt lõi & Tính độc lập
- **Giữ nguyên 100% `tiktok_workflow`:** Toàn bộ code trong repo `Tiktok-video` được giữ nguyên nguyên bản, không sửa đổi bất kỳ hàm hay state machine nào.
- **Cách ly hoàn toàn:** Hook upload được gọi qua subprocess (`python -m tiktok_workflow`), kết quả ghi vào `upload_result.json` trong thư mục artifact của phiên chạy (`child_ctx.artifacts.run_dir`). Upload dù thành công, lỗi hay skip đều **không ảnh hưởng hay làm fail kết quả của ca nuôi acc**.
- **Độc lập với Follow Hook:** `_run_follow_hook` và `_run_upload_hook` nằm trong 2 khối `try...except` độc lập — nếu follow hook bị lỗi/timeout thì upload hook vẫn chạy bình thường.

---

## 2. Ánh xạ Ca Nuôi ↔ Workbook Tik
Hệ thống ánh xạ 1-1 theo Account Row / Slot Index (`account.account_row_index` từ 1..6):
```python
WORKBOOK_FILENAMES = {
    1: "Tik1.xlsx",
    2: "Tik2.xlsx",
    3: "tik3.xlsx",   # disk anomaly: chữ thường trên đĩa
    4: "Tik4.xlsx",
    5: "Tik5.xlsx",
    6: "Tik6.xlsx",
}
```
Đường dẫn chuẩn: `D:\OneDrive\TaadaaData\kibe\` + `WORKBOOK_FILENAMES[row_index]`.

---

## 3. Quy trình 5 Tầng Preflight Gate (Kiểm tra an toàn trước khi đụng vào máy)

Khi phiên feed kết thúc thành công (`success` hoặc `degraded`), runner kiểm tra lần lượt:

1. **Session Gate:**
   - Chỉ kích hoạt khi `session_index == 3` (hoặc phiên cuối cùng của ca).
   - Các phiên 1, 2 bỏ qua 100% (`UPLOAD_SKIPPED: not_final_session`).
2. **Sensitive Stop Gate:**
   - Nếu phiên nuôi dừng do lỗi nhạy cảm (`login`, `otp`, `2fa`, `captcha`, `security`, `verify`, `verification`, `password`, `locked`, `banned`, `suspended`) $\rightarrow$ Bỏ qua upload (`UPLOAD_SKIPPED: sensitive_stop_word`).
3. **Workbook Resolution Gate:**
   - Tìm file `Tik{row_index}.xlsx` theo từ điển chuẩn.
   - Nếu file không tồn tại $\rightarrow$ Bỏ qua an toàn (`UPLOAD_SKIPPED: workbook_not_found`).
4. **Account ID & Machine Gate:**
   - Mở file Tik đọc dòng có cột `Máy` == máy hiện tại (`account.machine`).
   - Nếu không tìm thấy máy trong workbook $\rightarrow$ Skip (`UPLOAD_SKIPPED: machine_not_in_workbook`).
   - Nếu `ID` TikTok trống hoặc có giá trị `MISSING_ID` $\rightarrow$ Skip (`UPLOAD_SKIPPED: missing_account_id`).
   - Nếu `Folder Video` trống $\rightarrow$ Skip (`UPLOAD_SKIPPED: missing_video_folder`).
5. **Video Render Ready Gate:**
   - Đọc `Folder Video` và `Video Đã Đăng` từ dòng của máy.
   - Tính video tiếp theo: `next_video = int(Video Đã Đăng) + 1`.
   - Kiểm tra file trên PC: `D:\TIKTOK-videonuoinick\<Folder Video>\<next_video>.mp4`.
   - File mp4 không tồn tại hoặc kích thước `0 KB` (chưa render xong / đang render dở) $\rightarrow$ Skip an toàn (`UPLOAD_SKIPPED: video_not_rendered`).

---

## 4. Lệnh gọi Subprocess
Khi thỏa mãn toàn bộ 5 Gates:
```python
cmd = [
    ctx.config.get("python_exe") or sys.executable,
    "-m", "tiktok_workflow",
    "--config", rf"D:\Taadaa\Tiktok-video\config-machine-{account.machine}.yaml",
    "--workflow-workbook", str(workbook_path),
    "--machine", str(account.machine),
    "--no-dry-run",
]
```
- Subprocess chạy với `timeout=900` (15 phút, configurable qua `upload_timeout`), `cwd=r"D:\Taadaa\Tiktok-video"`.
- Bắt `subprocess.TimeoutExpired` an toàn và log kết quả có cấu trúc vào `upload_result.json`.
- Sau khi upload thành công, state machine của `tiktok_workflow` tự cập nhật tăng cột `Video Đã Đăng` trong file Tik một cách nguyên tử.
