# Quy Chuẩn Điều Phối Tứ Trụ Taadaa Farm (Tiered Workflow 2.0)
*Ngày cập nhật: 28/09/2026*

## I. Nguyên Tắc Cốt Lõi: Tốc Độ Hiện Trường vs An Toàn Hệ Thống

1. **Gemini Coordinator (Hiện trường):**
   - Giữ nguyên tính chủ động, xốc vác, tốc độ phản hồi 5–15s.
   - Trị bệnh ẩu / báo cáo láo: Bắt buộc **Canary Gate trên đúng 1 máy/profile thật** (ảnh `MEDIA:` + OCR readback + log sạch) trước khi nhân rộng batch.
   - Hậu kiểm cuối phiên: Sol High chấm điểm `closeout_gate.py` >= 85/100.

2. **Luna High Worker (Thợ vặn ốc trong Lồng Vô Trùng `cage_gate.py`):**
   - Vô địch Tournament Benchmark 15 trận thực chiến (462.0đ, tính nhất quán và kỷ luật vượt trội Terra High ở các ca Reconcile và Teardown).
   - Trị bệnh khóc nhè / over-engineer:
     + CẤM báo BLOCKED mơ hồ hoặc viết văn bản giải trình.
     + Chỉ chấp nhận: nộp DIFF <= 30 dòng HOẶC đúng 1 dòng `BLOCKED:<MÃ_LÝ_DO>:<Mô tả <= 120 ký tự>`.
     + Khi gặp dòng BLOCKED hoặc timeout 3 phút: Hệ thống đá văng ngay để chuyển cho Gemini/Terra làm, không cho ngâm việc.

## II. Phân Tầng Công Việc Thực Tế (Phân biệt Shared Host vs Per-Device Script)

- **T0 (Vận hành & Khảo sát - Không chạm code):**
  - Restart, kill process, đọc log O(1) (`inspect_machine.py`), ADB trực tiếp, đổi value `.env`/config.
  - Gemini tự làm 100% không cần dispatch.

- **T1 (Vá hiện trường script per-device <= 15 dòng):**
  - Áp dụng cho các script chạy riêng trên từng thiết bị (TikTok follow, login, GPM profile...).
  - Gemini ĐƯỢC PHÉP TỰ SỬA TRỰC TIẾP O(1) (<= 15 dòng diff, 1 file, không đổi signature).
  - Bắt buộc chạy Canary 1 máy thật ngay sau khi sửa.
  - NGOẠI LỆ: Các file hạ tầng dùng chung toàn host (Hermes gateway, OmniRoute, proxy TUN sing-box, `guard_*.py`) bị khóa cứng khỏi T1 tự do.

- **T2 (Thi công kiến trúc lớn > 15 dòng hoặc module lõi):**
  - **Bước 1 (3-5s):** Terra High (`codex/gpt-5.6-terra-high`) lên plan, chốt exact anchor `count == 1`, soi rủi ro.
  - **Bước 2:** Luna High (`codex/gpt-5.6-luna-high`) thi công trong Lồng Vô Trùng (`cage_gate.py`): <= 30 dòng, 1 file duy nhất, cấm tạo file thừa, cấm refactor.
  - **Bước 3:** Chạy Canary Gate trên 1 máy thật.

- **Closeout Gate:**
  - Sol High (`chatgpt-web/gpt-5.6-sol-high` qua :20129) độc lập chấm điểm toàn bộ diff trong phiên >= 85/100 mới được đóng phiên/push.

## III. Chốt Chặn Vật Lý Bằng Code (Physical Gates)

1. `D:/Taadaa/tools/hooks/guard_dispatch_contract.py`:
   - HARD GATE #3: Quét mọi file code trong prompt (`_get_declared_code_files`). Nếu >= 2 file nghiệp vụ -> BLOCK NGAY TỨC KHẮC tại dòng đầu tiên (exit 0 kèm JSON block).
   - T1 Bypass: Cho phép bypass Sol Plan nếu diff <= 15 dòng code.
2. `D:/Taadaa/tools/cage_gate.py`:
   - Kiểm tra `git diff --numstat` <= 30 dòng, đúng 1 file, test focused < 30s pass, auto kill process quá 30s bằng `taskkill`.
