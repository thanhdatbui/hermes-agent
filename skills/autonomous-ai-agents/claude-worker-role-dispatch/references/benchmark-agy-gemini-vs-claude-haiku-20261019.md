# Benchmark & Phân Định Worker: Gemini 3.8 Flash vs Claude Haiku 5.5

## 1. Kết Quả Benchmark Thực Tế 10 Hiệp (19/10/2026)

### A. Gemini 3.8 Flash: Medium vs High
- **Medium (Workhorse Sức Bền 100%):** 10/10 hiệp đạt chuẩn cú pháp AST hợp lệ (`valid_code: 10/10`). Thời gian trung bình: 225s (~3.7m), độ dài ~20,412 chars. Rất an toàn, không bị tràn token.
- **High (Kiến Trúc Sư Chuyên Sâu):** Code khổng lồ (~25,593 chars, cá biệt 38k-39k chars, 9 classes, 41 defs). Điểm yếu: Dễ chạm trần timeout 600s nếu không nâng trần lên 1200s, và bài quá dài (>38k chars) chạm token cap gây cụt đuôi dính `SyntaxError`.

### B. Gemini 3.8 Flash Medium vs Claude Haiku 5.5
- **Tốc độ:** Claude Haiku 5.5 trung bình **130.6s** (~2.1 phút), nhanh gấp đôi Gemini Medium (**262.5s**).
- **Quy mô & Kiến trúc:** Cả hai đều sinh code từ 20k - 37k ký tự. Claude Haiku có khả năng bóc tách mã lỗi Windows NT chi tiết hơn và unit test có tính mock lỗi thực tế cao hơn.
- **Tài nguyên:** AGY CLI dùng pool 22 acc Google Pro độc lập (không tốn token cá nhân). Claude Haiku dùng chung hạn mức session 5h của Claude CLI.

## 2. Kỹ Thuật & Cạm Bẫy Windows CLI
- **Lỗi `The command line is too long.` (lpCommandLine 32k):** Khi gọi `claude -p` chứa code 2 file lớn, Windows ném lỗi độ dài tham số. Bắt buộc ghi ra file tạm và truyền path để Claude đọc, hoặc pipe stdin.
- **Timeout Scaling:** Các module toàn diện (>25k chars) bắt buộc cấp timeout 600s - 900s thay vì 180s - 300s để tránh báo timeout giả.
- **Tham số Reasoning Effort:** Claude CLI hỗ trợ `--effort low|medium|high`.
