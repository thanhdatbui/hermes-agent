# Static Skill Dump Anti-Patterns vs Dynamic O(1) Routing

## 1. Case Study: The 350+ "Kitchen-Sink" Dump Pattern

Repositories like `sharkrebel/everything-everywhere-for-antigravity` attempt to maximize agent capability by bundling 348+ diverse skills (developer tools, bioinformatics, marketing, design, etc.) directly into agent system paths (`~/.claude/skills/`, `~/.gemini/config/plugins/`).

### Quantitative Breakdown
- **Catalog Size:** 348+ skills, 11,400+ files.
- **Header Injection Overhead:** 348 skills × ~45 tokens (name + summary description) = **15,000 - 18,000 tokens** injected into the system prompt on **every single turn**.
- **Context Pollution:** Skills spanning unrelated domains (e.g., AlphaFold DNA modeling, Astropy astronomy alongside React UI components and Git workflows).

## 2. Failure Modes on LLM Coding Agents

1. **Attention Dilution ("Lost in the Middle"):**
   - High density of similar/overlapping skill triggers (e.g., `smart-test`, `verification-loop`, `systematic-debugging`, `qa`, `eval-harness`) causes false-positive skill activations.
   - Irrelevant domain signatures distract reasoning attention from the user's specific codebase context.

2. **Working Memory Depletion ("Fix 1 bug, spawn 2 new bugs"):**
   - When 15k+ tokens of system prompt overhead are processed every turn, the model's effective attention span for local file modifications degrades.
   - Result: Model generates shallow or hallucinated edits that break surrounding dependencies.

3. **Installer Failure Modes:**
   - Multi-ecosystem install scripts often desync (e.g., `install-to-antigravity.ps1` copying only `plugins/` while completely dropping the root `skills/` directory containing 346 skills).

4. **Soft-Prompt Drift in Intent Classifiers:**
   - Monolithic markdown classifiers (e.g., `AGENTS.md` with 60+ static regex-style mappings) collide when user queries contain natural compound phrasing.

## 3. The Correct Architecture: Mechanical O(1) Routing

| Dimension | Static Dump Pattern | Mechanical Dynamic Routing (Hermes) |
| :--- | :--- | :--- |
| **Storage** | Flat unpruned directory | External indexed directory (`D:/Taadaa/Hermes/skills/`) |
| **Catalog Prompt Cost** | 15,000 – 18,000 tokens/turn | < 1,100 tokens (curated core ~30 skills) |
| **Skill Injection** | All skills loaded unconditionally | O(1) keyword bucket lookup (`top_k=5`, max 15k chars total context) |
| **Context Safety** | No budget clamp | Hard clamp at `<!-- END SKILL: -->` boundary |
| **Irrelevant Domains** | Dumped into prompt | Quarantined in `.archive/` |
