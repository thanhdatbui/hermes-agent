# Dual/Triple Advisor Parallel Query Timeout Clamp & Fallback Latency Tuning

## 1. Hiện Tượng: Chỉ có Gemini Argon Phản Hồi, Sol & Claude CLI Bị Mất Tích
Khi User phát lệnh gọi Hội đồng Cố vấn (`consult_advisor.py --advisor both` hoặc `--advisor all`):
- **Argon (Gemini Web):** Phản hồi siêu tốc (~2-3s) qua 15 tài khoản Google AI Pro kẹp 15 proxy Viettel 4G.
- **Sol (`gpt-web-sol` qua `:20129`):** Nếu gặp prompt dài hàng chục dòng, stream token đầu tiên có thể mất 60-80s hoặc dính hàng đợi OmniRoute. Nếu wrapper tổng đặt `timeout=60s` cho cả lệnh thì Sol bị kill trước khi kịp sinh đủ token.
- **Claude CLI (`claude_worker.py`):** Khi prompt quá dài kèm bối cảnh hiện trường, lệnh chạy qua Claude Code headless mất ~45-55s. Nếu timeout cứng của `consult_advisor.py` chỉ đặt 40s thì subprocess bị timeout và trả về rỗng.

## 2. Ranh Giới Chuẩn Hóa Kiến Trúc
1. **Không ngộ nhận "Claude hoặc Sol chết":** 
   - Kiểm tra độc lập: `python D:/Taadaa/tools/claude_worker.py "test" --role reviewer --timeout 10` (trả về OK trong 5s).
   - Kiểm tra độc lập Sol: `python D:/Taadaa/tools/consult_advisor.py --advisor sol --query "test"` (trả về OK).
2. **Kẹp Timeout Bậc Thang (Tiered Timeout):**
   - Subprocess Claude CLI trong `_consult_claude_inner`: Nâng `--timeout` từ 40s lên tối thiểu **60s - 75s** khi gặp query kiến trúc phức tạp.
   - Subprocess `consult_advisor.py` khi chạy foreground từ terminal: Bắt buộc kẹp `timeout=120` đến `180s` để đủ thời gian gom đủ 3 luồng (Sol + Gemini + Claude), tránh foreground timeout của Guard (60s) ngắt sớm làm rớt 2 advisor chậm hơn.
