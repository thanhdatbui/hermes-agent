# Path Normalization Pipeline & Anti-Bypass Invariants for Filesystem Guards

## 1. Context & Incident
When restricting broad filesystem scanning (e.g. `search_files(target="content")` or recursive terminal tools) on protected roots (`D:/`, `D:/Taadaa`, `C:/Users/Kibe`), naive string matching or unnormalized checks introduce two critical failure modes:
1. **False-Positive Root Blocking on Valid Subfolders**:
   - Substring matching `root in path.lower()` falsely classifies legitimate subfolders (e.g., `D:/Taadaa/tools`, `D:/Taadaa/orders`, `D:/Taadaa/tiktok-follow`) as protected root, blocking developer progress and driving agents into deadlocks.
2. **Path Traversal & Alias Bypass**:
   - Simple equality checks against an exact list of roots without full path canonicalization allow bypasses via:
     - Windows extended-length and device namespaces: `\\?\D:\Taadaa`, `//?/D:/Taadaa`, `//./D:/Taadaa`.
     - Trailing wildcards: `D:/Taadaa/*`, `D:/Taadaa/**`.
     - Directory traversal: `D:/Taadaa/tools/..` resolving to `D:/Taadaa`.
   - Naive string stripping of `/..` or `/.` *before* normalization breaks path resolution: `D:/Taadaa/tools/..` stripped naively of `/..` becomes `D:/Taadaa/tools` (allowed), creating an inadvertent fail-open bypass.

---

## 2. Invariant Pipeline Contract

Filesystem guard checks MUST follow this strict canonicalization sequence:

```python
import os
import re
import sys

# 1. Early exit on concrete file targets
if os.path.isfile(path):
    sys.exit(0)

# 2. Strip Windows extended-length and device UNC prefixes (//?/, //./, /?/)
norm_p = normalize(path)
norm_p = re.sub(r"^(?:[/\\][/\\][?.][/\\]|[/\\][?][/\\])", "", norm_p)

# 3. Strip trailing glob wildcards BEFORE normpath: "D:/Taadaa/**" -> "D:/Taadaa"
norm_p = re.sub(r"[/\\]+\*+.*$", "", norm_p)

# 4. Resolve dot segments and directory traversal via normpath:
#    "D:/Taadaa/tools/.." -> "d:/taadaa" (blocked)
#    "D:/Taadaa/tools/*" -> "d:/taadaa/tools" (allowed)
norm_p = os.path.normpath(norm_p).replace("\\", "/").lower().rstrip(" /.")

# 5. Exact match against protected root registry
if norm_p in exact_dangerous_roots:
    block("GUARD_SEARCH_FILES_ROOT", ...)
```

---

## 3. Terminal Scanner Boundary Contract
For shell commands (`find`, `grep -r`, `rg`), regex matchers targeting root paths MUST use boundary assertions:
- **Boundary Regex**: `(?<![\w.-])<root>(?:/|\\)?(?=[\s\"'`;|)&$]|$)`
- Avoid `root in cmd.lower()` which intercepts valid arguments like `grep -rn foo D:/Taadaa/tools`.

---

## 4. Guidance & Farm Term Discriminating Invariant
- **No Blanket Keywords**: Do not trigger farm hardware hints (`inspect_machine.py <N>`) on generic terms like `log`, `logs`, `farm`, or `machine`.
- **Machine Identifier Anchor**: Only append hardware inspection guidance when a concrete device identifier is present:
  `r"\b(?:machine\s*\d+|phone\s*\d+|m\d{1,3})\b"`
- **Actionable Tool Alternatives**: When blocking content search on root, guide the agent to use non-scanning alternatives:
  - `git ls-files`
  - `search_files(target='files', pattern='*.py')`
