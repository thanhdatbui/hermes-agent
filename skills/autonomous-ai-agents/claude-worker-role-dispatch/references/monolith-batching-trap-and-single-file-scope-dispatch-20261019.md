# Bẫy Gộp File Monolith & Cơ Chế Khắc Phục L1 Single-File Scope (`dispatch_worker.py`)

Bài học rút ra từ sự cố dispatch worker ngày 19/10/2026 trong phiên sửa lỗi báo cáo nuôi Gmail GPM.

---

## 1. Sự Cố "Reached Max Turns 8 & Agy CLI Timeout 180s"

### Bối cảnh
Coordinator phát lệnh dispatch gộp 2 file cùng lúc:
- `cron_gpm_gmail_nurture_6h_report.py` (file nhỏ, 100 dòng).
- `cron_gpm_gmail_nurture.py` (monolith lớn, 1.043 dòng).
- Tham số dòng lệnh: Không truyền `--file`, để `--max-turns 8` mặc định.

### Chuỗi Thất Bại Tự Động
1. **Haiku Attempt 1 & 2:** Worker Haiku 5.5 nhận prompt gộp, phải gọi `Read` đọc qua lại cả 2 file lớn để hiểu ngữ cảnh. Với trần 8 turns mặc định, Haiku đốt sạch lượt gọi công cụ trước khi kịp phát sinh diff $\rightarrow$ văng lỗi `Error: Reached max turns (8)`.
2. **Agy CLI Fallback Timeout:** Khi Haiku fail 2 attempts, `dispatch_worker.py` leo thang sang Agy CLI (`ag_cli.py fix`). Agy CLI chạy deep reasoning trên 2 file lớn và bị treo timeout 180s $\rightarrow$ tiến trình kết thúc với `exit code 124`.

---

## 2. Bài Học & Quy Chuẩn Khắc Phục L1 Single-File Contract

### 2.1. Invariant: CẤM Gộp File Nhỏ Với Monolith Trong 1 Dispatch
- Khi một task liên quan đến 1 file báo cáo/wrapper nhỏ (≤ 150 dòng) và 1 monolith (≥ 500 dòng), **BẮT BUỘC** tách thành 2 đợt dispatch độc lập:
  * Lượt 1: Xử lý dứt điểm file báo cáo/wrapper.
  * Lượt 2: Xử lý monolith với Patch Contract O(1) duy nhất (`old_string` $\rightarrow$ `new_string`).

### 2.2. Khóa Cứng `--file` & Nâng Trần `--max-turns 15`
- Luôn chỉ định tường minh tham số `--file <path>` để khóa phạm vi đọc/sửa của worker.
- Với các tác vụ có chạy kiểm thử (pytest), luôn cấu hình `--max-turns 15` (thay vì 8) để worker có đủ turn đọc file, patch code và chạy test nghiệm thu:
```bash
python D:/Taadaa/tools/dispatch_worker.py \
  --workdir "D:/Taadaa/GPM auto" \
  --file scripts/cron_gpm_gmail_nurture_6h_report.py \
  --max-turns 15 \
  "Fix scripts/cron_gpm_gmail_nurture_6h_report.py: Add get_group10_emails()... Run python scripts/cron_gpm_gmail_nurture_6h_report.py to verify."
```

### 2.3. Kết Quả Thực Nghiệm
- Sau khi áp dụng L1 Single-File Scope với `--max-turns 15`: Haiku hoàn thành trong 1 shot (45.0s, exit code 0), test suite mở rộng lên 46/46 tests passed 100%.
