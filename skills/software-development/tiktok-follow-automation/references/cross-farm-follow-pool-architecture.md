# Cross-Farm Follow Pool Architecture: Kibe + Admin Expansion

## Bối cảnh & Hiện trạng Farm (2026-09)
- **Farm Kibe**: 597 UIDs, dàn Tik1/Tik2 có 115 nick đã đăng $\ge 10$ video (đạt chuẩn Anchor Mode 2).
- **Farm Admin**: 332 UIDs, mới vận hành, 100% video còn mỏng (1–2 video/nick), chưa đủ chuẩn làm Anchor.

## Vấn đề Cốt lõi & Rủi ro Sơ đồ chéo (Graph-based Detection)
1. **Rủi ro mạng đóng (Closed-loop Clique)**:
   - Nếu nick nội bộ Farm Kibe chỉ follow vòng tròn lẫn nhau trên cùng dải IP/thiết bị Kibe, hệ thống Anti-Spam / Shadowban của TikTok sẽ phát hiện đồ thị mạng bất thường (Follow-back ring).
   - Khi các máy Kibe follow cạn nhau, Mode 2 sẽ cạn nick nội bộ chưa follow trong list Anchor $\rightarrow$ fallback Mode 1 $\rightarrow$ Mode 1 gặp toàn nick `already_followed` $\rightarrow$ lãng phí budget và thời gian phiên.
2. **Rủi ro nếu bỏ rơi Kibe chỉ follow Admin**:
   - Dàn Admin chưa nick nào $\ge 10$ video $\rightarrow$ Mode 2 liên tục safe-skip do thiếu Anchor chuẩn $\rightarrow$ dồn 100% vào Mode 1 (Search-Follow thuần túy, nguy cơ cao hơn).

## Chiến lược "Cross-Farm Combined Pool"
- **Pha loãng mạng lưới (Network Dilution)**: Gộp chung pool UID Kibe (597) + Admin (332) thành tổng 929 UIDs.
- **Tận dụng Anchor Gate tự nhiên**:
  - Script giữ nguyên logic: Anchor Mode 2 BẮT BUỘC là nick Tik1/Tik2 và $\ge 10$ video. Do đó, Anchor tự động được chọn từ dàn Tik1/Tik2 cứng cáp của Kibe.
  - Khi máy Admin bắt đầu chạy, máy Admin sẽ từ dải IP/thiết bị Admin tìm follow sang Anchor của Kibe $\rightarrow$ tạo luồng organic follower ngoại vi cho Tik1/Tik2 Kibe (tín hiệu Trust cao).
- **Mode 1 bù budget**:
  - Khi Mode 2 hết slot/budget, Mode 1 sẽ tìm kiếm và follow ngẫu nhiên cả nick Admin và Kibe chưa follow $\rightarrow$ dàn nick Admin được kéo follow sớm, máy Kibe không bị cạn UID.

## Triển khai Khuyến nghị (Data-Layer vs Code-Layer)
- **Data-layer (Ưu tiên số 1 - Chống Over-engineering)**:
  - Tự động sync/merge 2 file `kibe/taikhoan_run_safe.xlsx` và `admin/taikhoan_run_safe.xlsx` thành một safe workbook tổng hợp (`taikhoan_run_safe_combined.xlsx`).
  - Config của follow runner trỏ vào file gộp này. Runner không cần sửa core logic, tự động hưởng lợi từ 929 UIDs và Anchor filter có sẵn.
