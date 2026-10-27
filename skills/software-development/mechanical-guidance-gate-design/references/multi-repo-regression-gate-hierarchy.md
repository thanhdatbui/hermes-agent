# Multi-Repo Protection Regression Gate Architecture

## 1. Problem Statement: Cross-Repo False Positives
When managing invariant enforcement across multi-repository workspaces, evaluating all rules on any commit causes **Cross-Repo False Positives (Leaky Abstraction)**.
- *Example:* Editing a desktop/CDP automation project gets blocked by mobile device timing thresholds, or an agent modifying browser flows receives irrevelant hardware triage guidance.

## 2. 3-Tier Invariant Hierarchy

To eliminate cross-repo interference, Protection Regression Gates must be structured into three distinct tiers:

### Tier 0: Global Invariants (`repos: ["*"]`, `paths: ["*"]`)
Rules that protect host machine integrity, event loop stability, and gateway architecture. A violation in ANY repository is immediately blocked:
- Broad root-level filesystem traversals that exhaust memory or freeze event loops.
- Deprecated UI dump utilities on legacy mobile devices that trigger OOM exits.
- Terminal stdout flooding (e.g. giant payloads/base64 strings).
- Unsupported network proxy protocol schemes in messaging gateway configuration.

### Tier 1: Repo-Scoped Invariants (`repos: ["<repo_name>"]`)
Rules that apply strictly to the repository owning that domain logic:
- **Phone Farm Automation:** Device connection timing floors, friend follow limits, and avoiding global rest-day overrides.
- **Desktop / CDP Automation (GPM):** Initial stage ordering, ensuring reg scripts return non-zero exit codes on failure, prohibiting direct IP fallbacks when proxies drop, and worker concurrency limits.
- **Core Tooling:** Subagent execution timeout floors.

### Tier 2: Path-Level Invariants (`paths: ["<path_glob>"]`)
Narrowing rule execution within a repo to only modified files that actually contain the protected function or logic.

## 3. Storage Architecture: Canonical Base vs Repo-Local Rules

### Centralized Base
- Acts as the Single Source of Truth for Global Invariants and shared cross-repo policies.
- Prevents workers from modifying rule definitions inside PRs to bypass gates.

### Repo-Local Extension (`<repo>/rules.json`)
- Repositories can define domain-specific rules locally.
- The gate runner automatically discovers and merges repo-local rules when evaluating diffs against a specific target repo.
- Merging must deduplicate rule IDs to prevent configuration errors.

## 4. Separation of Concerns: Pre-Execution Interceptors vs Commit Gates

- **Pre-execution interceptors (Runtime layer):** Intercept command executions on the live terminal/session before commands run to prevent immediate system disruption.
- **Regression Gates (Commit layer):** Analyze git diffs at closeout/push time to prevent improper patterns from entering version control history.
- The two layers operate at different lifecycle moments and complement each other.
