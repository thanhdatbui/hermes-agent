# SSH Remote Python Script Execution and Patching Pitfalls

## Raw inline scripts with Windows paths (`\Users`)

When executing inline Python scripts on Windows remote hosts via `python -c "..."` or multi-line strings embedded in shell/python commands:

1. **Unicode escape errors**:
   Strings containing `\Users` (e.g., `r'C:\Users\...'` or nested quotes) often trigger:
   ```
   SyntaxError: (unicode error) 'unicodeescape' codec can't decode bytes in position X-Y: truncated \UXXXXXXXX escape
   ```
   In Python string literals, `\U` starts an 8-character Unicode code point escape. Even inside raw strings or nested string layers, shell escaping and string interpolation can accidentally turn `\\U` into `\U` before Python parses the outer or inner literal.

2. **Safe Pattern**:
   Instead of trying to escape complex multi-line Python scripts across SSH quotes:
   - Create a local standalone python script using `write_file` (e.g. `C:\Users\Kibe\patch_target.py`).
   - Stream it to the remote Python interpreter via stdin:
     ```bash
     ssh <host> "python -" < /c/Users/<user>/patch_target.py
     ```
   - This completely avoids escaping issues, quotes nesting, and unicodeescape syntax errors.
