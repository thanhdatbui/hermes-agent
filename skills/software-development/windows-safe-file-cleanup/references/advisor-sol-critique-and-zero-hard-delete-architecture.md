# Advisor Sol — Phản biện kiến trúc Zero Hard-Delete & Windows Recycle Bin

## 1. Kết luận kiến trúc từ Advisor Sol (:20129 `gpt-web-sol`)
- **Đánh giá:** Chấp thuận có điều kiện. Hướng tiếp cận đưa vào Recycle Bin là đúng, nhưng phương án không được chỉ dừng lại ở việc thay API xóa tệp, mà phải bảo đảm tính bất biến **Fail-Closed: Không bao giờ mất dữ liệu và luôn kiểm chứng được kết quả**.

## 2. Các điểm phản biện chuyên sâu:

### A. Win32 `SHFileOperationW` vs `IFileOperation`
- `FOF_ALLOWUNDO` yêu cầu đưa đối tượng vào Recycle Bin, nhưng không bảo đảm thành công trong mọi trường hợp (ví dụ tệp quá lớn so với quota Recycle Bin của phân vùng).
- `SHFileOperationW` là API cũ của Shell, dễ gặp vấn đề với đường dẫn dài (`MAX_PATH`). Phải kiểm tra mã trả về (`int == 0`), cờ hủy thao tác (`fAnyOperationsAborted == False`), và xác minh tệp nguồn đã biến mất.
- Khuyến nghị dài hạn: Dùng `IFileOperation` với `FOFX_RECYCLEONDELETE` trên môi trường hỗ trợ COM; nếu dùng `SHFileOperationW` thì bắt buộc bọc tiền tố `\\?\` và null-terminator kép (`\0\0`).

### B. PowerShell / .NET Fallback
- `Microsoft.VisualBasic.FileIO.FileSystem.DeleteFile` với `UIOption.OnlyErrorDialogs` và `RecycleOption.SendToRecycleBin` chỉ là adapter dự phòng khi không thể gọi trực tiếp native ctypes.
- Cảnh báo: Các service chạy dưới tài khoản không tương tác, Session 0 hoặc tài khoản khác user đăng nhập có thể không có Recycle Bin đầy đủ. Không bao giờ giả định Recycle Bin luôn khả dụng trên mọi ngữ cảnh.

### C. Quarantine Cùng Volume — Lớp Phòng Thủ Bắt Buộc
- Nếu Recycle Bin từ chối (hoặc thất bại), bắt buộc chuyển sang Quarantine cùng volume (`D:/Taadaa/.quarantine/YYYY-MM-DD/`).
- Di chuyển cùng volume đảm bảo tính nguyên tử (Atomic Rename / `MoveFileExW`) trong $O(1)$, không tốn dung lượng I/O và không lo lỗi mạng.
- Ghi kèm `manifest.json` chứa: `original_path`, `quarantined_path`, `sha256`, `size_bytes`, `timestamp`, `reason`.
- **Nếu cả Recycle Bin lẫn Quarantine đều thất bại:** DỪNG, BÁO LỖI, GIỮ NGUYÊN TỆP NGUỒN. Tuyệt đối không tự động xóa để giải phóng dung lượng.

### D. Corner Cases Cần Kiểm Soát
- **File lock / Permission:** Không ép đóng handle; thử lại có giới hạn (retry backoff), nếu vẫn kẹt thì bỏ qua và cảnh báo.
- **Symlink / Reparse Point:** Mặc định không đi theo liên kết; chỉ thao tác trên chính entry symlink, không đụng vào đích trỏ tới.
- **MAX_PATH:** Chuẩn hóa đường dẫn dài, Unicode và UNC.
- **Multi-threading:** Khóa theo canonical path để tránh tranh chấp hai worker cùng di chuyển hoặc truy cập một tệp.
