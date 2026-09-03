# Git Branch Main Promotion & Worktree Cleanup Checklist

Khi user yêu cầu đưa nhánh hiện tại (vd `reg-stable-0722`) làm nhánh `main` và dọn sạch nhánh cũ:

## 1. Fast-forward & Force update branch `main`
```bash
# 1. Ép branch main trỏ vào commit mới nhất của nhánh hiện tại
git branch -f main <branch-name>

# 2. Chuyển sang main
git checkout main

# 3. Force push lên remote main (được smart approval hỗ trợ)
git push origin main --force

# 4. Thiết lập tracking upstream
git branch -u origin/main main
```

## 2. Dọn dẹp branch cũ
```bash
# Xóa branch local cũ
git branch -d <branch-name>

# Xóa branch remote cũ
git push origin --delete <branch-name>

# Prune refs
git fetch origin --prune
```

## 3. Xác nhận
- `git status -sb` → `## main...origin/main` (đồng bộ 100%).
- `git branch -a` → chỉ còn `main` và các nhánh backup chuẩn.
