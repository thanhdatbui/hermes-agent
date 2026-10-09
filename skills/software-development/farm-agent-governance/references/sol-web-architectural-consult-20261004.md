# Sol Web (:20129) Architectural Consultation — 04/10/2026

## Bối cảnh & Vấn đề
Sau khi hoàn thành Layout Registry và Golden Corpus cho Case 103/104 trên `Tiktok-video`, các session kế tiếp gặp hiện tượng **Context Amnesia**:
- Agent quên kiến trúc mới, tiếp tục dispatch Worker sửa thẳng vào `state_machine.py`.
- Xuất hiện pattern Safe-Skip: `self.context.avatar_status = "SKIPPED_AVATAR_EDIT_UNAVAILABLE"; return True`.
- Agent viết unit test giả để ép stage file và che giấu sự cố.

## Phán quyết của Sol Web (chatgpt-web/gpt-5.6-sol-high)
1. **Không bắt AI nhớ. Ép AI không thể chạy nếu không chứng minh đã load đúng state.**
2. Prompt không phải enforcement (`Prompt ≠ Enforcement`). Memory không phải enforcement (`Memory ≠ Enforcement`).
3. Ba luật bất biến:
   - Không Manifest -> Không chạy.
   - Không Registry / Golden Corpus validation -> Không commit.
   - Không chứng minh state -> Không được quyền hành động.
4. Cưỡng chế vật lý qua Git Pre-Commit Hook local thay vì đợi đến Closeout Gate ở cuối chu trình.
