# Anti-Multi-File Hook Enforcement & Blast Radius Boundary
*Ngày ghi nhận: 28/09/2026*

## I. Bài Học Thực Tế & Lỗi Dispatch Kẹt 1200s (deleg_302c6b85)

### 1. Hiện tượng:
- Task gộp 2 file (`hashtag_selector.py` và `test_hashtag_selector.py`) được dispatch cho worker `codex/gpt-5.6-luna-high`.
- Worker bị cuốn vào vòng lặp đọc file, sửa file nghiệp vụ, sửa file test, chạy test -> Cháy sạch 17 tool calls và bị timeout 1200s (20 phút).

### 2. Nguyên nhân gốc rễ:
- Hook kiểm tra `guard_dispatch_contract.py` trước đó bị đặt sai vị trí (chỉ sửa ở AppData thay vì file thật `D:/Taadaa/tools/hooks/guard_dispatch_contract.py`).
- Regex quét đuôi code bị dính ký tự thoát escape `\x08` (backspace).
- Kiểm tra Multi-File bị đặt sau luồng `[SOL_GATE AUTO-RESOLVE]`, khiến Sol sinh plan trước khi Multi-File kịp chặn.

## II. Khắc Phục Bằng Chốt Chặn Vật Lý (Physical Gate)

1. **Vị trí ưu tiên số 1:**
   - Trong `D:/Taadaa/tools/hooks/guard_dispatch_contract.py`, hàm `_get_declared_code_files(text)` và khối kiểm tra `len(_code_paths_check) >= 2` được đưa lên ngay đầu file (ngay sau khi đọc payload và trích xuất `combined`).
   - Nếu phát hiện >= 2 file code nghiệp vụ trong prompt -> In JSON block và `sys.exit(0)` dập tắt ngay lập tức, không cho phép Sol Auto-Resolve hay bất kỳ luồng nào chạy tiếp.

2. **Regex quét file code an toàn trên Windows:**
   - Dùng chuỗi động `pattern = re.compile(r"[^\s,;<>()[\]{}]+(?:\.py|\.js|\.ts|\.sh|\.ps1|\.yaml|\.yml|\.json|\.toml)" + chr(92) + 'b', re.IGNORECASE)` để tránh lỗi string parser Python trên Windows.

## III. Phân Biệt Phạm Vi Ảnh Hưởng (Blast Radius: Per-Device vs Shared Host)

- **Script per-device (TikTok, GPM profiles, feed session, follow):**
  - Chạy độc lập trên từng máy -> Rủi ro giới hạn.
  - Cho phép Gemini Coordinator tự vá T1 (<= 15 dòng diff, 1 file) rồi chạy Canary trên đúng 1 máy thật (chụp ảnh `MEDIA:` + OCR readback + log sạch) trước khi chạy batch.
- **Thành phần dùng chung toàn host (Hermes gateway, OmniRoute, proxy TUN sing-box, .env):**
  - Tuyệt đối CẤM Gemini tự ý sửa ở T0/T1. Bắt buộc qua luồng thẩm định T2.

## IV. Cơ Chế Chống Luna Khóc Nhè & Chống Bịa Diff

1. **Cấm tuyệt đối văn bản giải trình:** Hệ thống vứt bỏ mọi báo cáo phân tích/đề xuất kiến trúc dài dòng.
2. **Chỉ chấp nhận 1 dòng:** `BLOCKED:<MÃ_LÝ_DO>:<Mô tả <= 120 ký tự>`.
3. **Xử phạt nghiêm khắc:** Báo BLOCKED hoặc sau 3 phút không nộp diff -> Đá văng ngay lập tức. Nộp diff bịa làm rớt Canary máy thật bị xử phạt nặng hơn cả việc báo BLOCKED thật thà.
