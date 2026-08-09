# Claude Print-Mode Structured Review Prompt Template

Use this template when running `claude -p` for code reviews. Write it to a file, then:
```bash
claude -p "$(cat /path/to/review-prompt.txt)" --max-turns 10 --allowedTools "Read"
```

## Template

```
You are a senior code reviewer. Review ONLY the following changes for bugs, regressions, and correctness. Do NOT edit any files. Answer with APPROVED or REJECTED and a detailed explanation.

CONTEXT:
[1-2 sentences describing what changed and why. E.g.: "Codex made core parameter changes; consumers now delegate back-navigation to core instead of manual loops."]

CORE CHANGES:
[Concise bullet list of what changed in the core/shared module. Include file paths, function names, old→new values.]

CONSUMER USAGE ANALYSIS:
[Table or list showing each consumer, what it calls, whether it passes explicit arguments, and whether the core change affects it.]

REVIEW QUESTIONS:
- [Specific question about a risky change]
- [Specific question about edge cases]
- [Specific question about consumer impact]

TEST RESULTS:
[Bullet list of all test suites run and their pass/fail counts. Include the command used so Claude knows tests were actually executed.]

Read the actual files at [repo path] if needed. Be thorough and decisive.
```

## Why This Works

1. **CONTEXT** gives Claude the "why" upfront — no guessing about intent.
2. **CORE CHANGES** + **CONSUMER USAGE ANALYSIS** pre-digests the code for Claude. Instead of making it discover which consumers call which functions, you've already done the grep work. Claude can focus on judgment, not exploration.
3. **REVIEW QUESTIONS** focus Claude on the specific risks you care about. Open-ended "review this" produces rambling; targeted questions produce actionable findings.
4. **TEST RESULTS** with actual pass counts (not claims) anchors the review in real execution evidence.
5. **`--allowedTools "Read"`** keeps Claude in read-only mode — it can read files for verification but can't edit anything.

## Pitfalls

- **Never paste full diffs inline if they exceed 5K chars.** Claude will burn turns reading them instead of the actual files. Summarize the changes instead and let Claude `Read` the files.
- **Always write the prompt to a file**, never inline in bash. Inline prompts with code characters `()`, backticks, or `$()` will break bash parsing.
- **Set `--max-turns` to at least 8** for reviews spanning multiple consumer repos. Claude needs turns to read files and cross-reference.
