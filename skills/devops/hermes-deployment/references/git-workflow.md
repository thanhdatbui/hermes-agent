# Git Workflow for Multi-Machine Hermes

Git coordination patterns when multiple machines maintain the same Hermes repository.

## Core Principle

```text
Always: git pull --rebase origin main
Never:  git pull origin main (creates merge commits)
```

## Workflow A: One Machine Ahead

**Machine 1 (leader):**
```powershell
cd D:\Taadaa\Hermes
# Edit skills
git add skills
git commit -m "feat(skills): update shared skills"
git push origin main
```

**Machine 2 (follower, clean state):**
```powershell
cd D:\Taadaa\Hermes
git pull --rebase origin main
.\deploy\sync-skills.ps1
```

## Workflow B: Both Machines Modified (Different Files)

**Machine 1:**
```powershell
git add skills
git commit -m "feat(skills): update from machine 1"
git push origin main
```

**Machine 2 (clean state):**
```powershell
git pull --rebase origin main
git add skills
git commit -m "feat(skills): update from machine 2"
git push origin main
```

**Machine 1 (pulls Machine 2's changes):**
```powershell
git pull --rebase origin main
.\deploy\sync-skills.ps1
```

Result: Linear history, no merge commits.

## Workflow C: Both Machines Modified (Same File)

This causes a conflict. Git cannot auto-merge if both machines edited the same `SKILL.md`.

**Machine 1:**
```powershell
git add skills/autonomous-ai-agents/claude-code/SKILL.md
git commit -m "feat(skills): update claude-code skill"
git push origin main
```

**Machine 2 (also edited claude-code/SKILL.md):**
```powershell
git pull --rebase origin main
```

Git reports:
```text
CONFLICT (content): Merge conflict in skills/autonomous-ai-agents/claude-code/SKILL.md
```

**Resolution:**

1. Open conflicted file:
   ```text
   <<<<<<< HEAD
   content from Machine 1
   =======
   content from Machine 2
   >>>>>>> origin/main
   ```

2. Edit to keep correct content (or merge both)

3. Remove all markers (`<<<<<<<`, `=======`, `>>>>>>>`)

4. Stage and continue:
   ```powershell
   git add skills/autonomous-ai-agents/claude-code/SKILL.md
   git rebase --continue
   ```

5. Push:
   ```powershell
   git push origin main
   ```

**Abort if needed:**
```powershell
git rebase --abort
```

## Workflow D: Uncommitted Changes on Machine 2

If Machine 2 has uncommitted changes when it's time to pull:

### Option 1: Stash (recommended)

```powershell
# Save changes
git stash

# Pull
git pull --rebase origin main

# Restore
git stash pop
```

If `stash pop` causes conflict, resolve it:
```powershell
# Edit conflicted files
git add skills
git stash drop
git commit -m "feat(skills): resolved stash conflict"
```

### Option 2: WIP Commit

```powershell
git add skills
git commit -m "WIP: skills from machine 2"
git pull --rebase origin main
# Handle conflict if any
git push origin main
```

Then continue editing, commit again, push again.

**Stash vs WIP commit:**
- **Stash**: Cleaner history, no WIP commits, but must remember `stash pop`
- **WIP commit**: Safer for substantial changes, but adds "WIP" commits to history

For most cases, use stash.

## Workflow E: Branches for Parallel Work

If you know two machines will edit the same skill:

**Machine 1:**
```powershell
git switch -c skills/machine-1
# Edit skills/autonomous-ai-agents/claude-code/SKILL.md
git add skills
git commit -m "feat(skills): update from machine 1"
git push -u origin skills/machine-1
```

**Machine 2:**
```powershell
git switch -c skills/machine-2
# Edit skills/autonomous-ai-agents/claude-code/SKILL.md
git add skills
git commit -m "feat(skills): update from machine 2"
git push -u origin skills/machine-2
```

**Later, merge both into main:**
```powershell
git switch main
git pull origin main
git merge skills/machine-1
git merge skills/machine-2
git push origin main
```

If conflicts arise during merge, resolve them the same way as rebase conflicts.

## Common Pitfalls

### 1. Forgetting --rebase

Without `--rebase`:
```powershell
git pull origin main
```

Git creates a merge commit:
```text
Merge: abc1234 def5678
Merge branch 'main' of https://github.com/user/hermes-agent
```

Over time, history becomes cluttered with merge commits. Always use:
```powershell
git pull --rebase origin main
```

### 2. Pushing Without Pulling

If Machine 2 tries to push without pulling Machine 1's changes:
```text
error: failed to push some refs to 'https://github.com/user/hermes-agent'
hint: Updates were rejected because the remote contains work that you do not have locally.
```

**Fix:**
```powershell
git pull --rebase origin main
git push origin main
```

### 3. Pulling With Uncommitted Changes

Git blocks the pull:
```text
error: cannot pull with rebase: You have unstaged changes.
error: Please commit or stash them.
```

**Fix:** Use stash or WIP commit (see Workflow D).

### 4. Editing Runtime Skills Directly

If you edit `%LOCALAPPDATA%\hermes\skills\autonomous-ai-agents\claude-code\SKILL.md`, the next `sync-skills.ps1` will overwrite it.

**Fix:** Always edit the repo version (`D:\Taadaa\Hermes\skills\...`), then sync.

### 5. Committing deploy/hermes-home/skills/

This was an early mistake. The deploy bundle should not snapshot skills; that causes divergence.

**Fix:** Ensure `.gitignore` excludes `deploy/hermes-home/skills/`.

## Verification After Sync

After `git pull` and `sync-skills.ps1`:

```powershell
hermes --version
hermes doctor
hermes skills list
claude --version
codex --version
```

All should succeed. If `hermes skills list` doesn't show expected skills, check:
- Did you sync? (`.\deploy\sync-skills.ps1`)
- Did you reload? (`/reload-skills` or restart Hermes)
- Are skills in the right location? (`%LOCALAPPDATA%\hermes\skills\`)

## Summary Decision Tree

```text
Need to update skills?
│
├─ Uncommitted changes?
│  │
│  ├─ Yes → git stash → git pull --rebase → git stash pop
│  │
│  └─ No → git pull --rebase
│
├─ Conflict?
│  │
│  ├─ Yes → resolve → git add → git rebase --continue
│  │
│  └─ No → edit skills → git add → git commit → git push
│
└─ After push → .\deploy\sync-skills.ps1 → /reload-skills
```
