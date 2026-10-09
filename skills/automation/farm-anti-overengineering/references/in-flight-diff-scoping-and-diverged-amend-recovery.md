# In-Flight Diff Scoping Cho Gate 1 Plan-Review & Phục Hồi Khi Amend Làm Diverged Nhánh (06/09/2026)

Tài liệu này ghi nhận 2 cạm bẫy thực tế trong quy trình Chốt phiên 6 Gate khi làm việc song song với Worker Subagents trên Taadaa Phone Farm.

---

## 1. CẠM BẪY 1: DIFF RỖNG KHI WORKER ĐÃ COMMIT NỘI BỘ (IN-FLIGHT COMMIT TRAP)

### 1.1. Hiện tượng & Phản ứng Reviewer
- Trong quá trình sửa lỗi hoặc canary, Worker subagent (hoặc một tiến trình con) đã chạy `git commit` tạo commit mới tại local (ví dụ `1ae2f95`).
- Khi Coordinator bước vào **Gate 1: Plan-Review**, Coordinator chạy lệnh lấy diff theo thói quen:
  ```bash
  git diff -- <files>
  # hoặc
  git diff HEAD -- <files>
  ```
- Do các thay đổi đã được commit vào `HEAD`, lệnh trên trả về **chuỗi rỗng** (`0 lines`, `Diff length: 0`).
- Khi gửi payload diff rỗng cho Reviewer độc lập (OmniRoute `:20129` combo model `review` / Claude Opus):
  ```text
  # Audit Report – Case 87 (Tiktok-video)
  ## Observation
  Không có git diff nào được cung cấp. Phần "GIT DIFF:" trong yêu cầu hoàn toàn trống...
  ## Findings
  1. CRITICAL — Missing Evidence: Diff rỗng nghĩa là không có bằng chứng nào cho thấy code thực sự thay đổi gì.
  ## VERDICT: REJECTED
  ```

### 1.2. Giải pháp chuẩn (Diff Scoping Invariant)
- **BẮT BUỘC xác định Base Commit đầu phiên:** Trước khi gửi Plan-Review, Coordinator phải đối chiếu với commit gốc trước khi sửa (ví dụ `git diff origin/main HEAD` hoặc `git diff <base_commit> HEAD`).
- **Script an toàn:** Khi lấy diff để gửi API review, kiểm tra:
  ```python
  # Nếu working tree sạch nhưng local đang ahead commit so với origin:
  diff_cmd = ["git", "diff", "origin/main", "HEAD", "--"] + allowlist
  ```
  Bảo đảm reviewer nhìn thấy toàn bộ candidate code thay đổi của cả phiên làm việc.

---

## 2. CẠM BẪY 2: DIVERGED DO `git commit --amend` TRÊN COMMIT ĐÃ PUSH

### 2.1. Hiện tượng
- Worker hoặc pipeline chạy trước đó đã tự động push commit `1ae2f95` lên `origin/main`.
- Coordinator tại session chính thực hiện `git commit --amend` để bổ sung tên case vào commit message.
- Git tạo ra một commit SHA mới (`d5e16fb`) có cùng nội dung code nhưng khác SHA với remote:
  ```text
  On branch main
  Your branch and 'origin/main' have diverged,
  and have 1 and 1 different commits each, respectively.
  ```
- Khi chạy `git pull --rebase origin main`, git từ chối hoặc gây conflict.

### 2.2. Giải pháp phục hồi an toàn (Soft Reset Alignment)
- **CẤM TUYỆT ĐỐI `git push --force`** trên live repo của farm.
- **Quy trình 3 bước phục hồi:**
  1. **Kiểm tra diff giữa local và remote:**
     ```bash
     git diff origin/main HEAD
     ```
     Nếu diff rỗng (chỉ khác commit message):
     Chạy `git reset --soft origin/main` để kéo `HEAD` local về khớp hoàn toàn với `origin/main` mà không làm mất bất kỳ byte code nào.
  2. **Nếu có code mới phát sinh:**
     Tạo commit mới riêng biệt (`git commit -m "..."`) thay vì amend đè lên commit cũ đã push.
  3. **Rebase & Push an toàn:**
     ```bash
     git fetch origin main
     git rebase origin/main
     git push origin main
     ```

---

## 3. CHECKLIST KIỂM TRA TRƯỚC KHI GỬI GATE 1 PLAN-REVIEW

- [ ] `len(diff_text) > 0`: Xác nhận diff không bị rỗng.
- [ ] So sánh `diff` với đúng mốc baseline (`origin/main` hoặc commit trước phiên).
- [ ] Không dùng inline bash `python -c "..."` hoặc bash heredoc nhúng diff (tránh bash parse nhầm backtick, `{diff}`, nháy kép).
- [ ] Tạo file Python runner riêng biệt tại thư mục ngoài repo (`C:/Users/Kibe/run_review_gate1.py`) và xóa ngay sau khi nhận verdict.
