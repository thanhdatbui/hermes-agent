---
name: model-comparison-research
description: "Research and compare AI model identities, benchmark evidence, provider claims, and reseller/router aliases without conflating marketing claims with head-to-head results."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, macos, linux]
metadata:
  hermes:
    tags: [Research, benchmarks, model identity, citations, fact checking]
    category: research
    related_skills: [grounded-citations]
---

# Model Comparison Research

## Trigger

Use when a user asks whether two AI models are equivalent, requests benchmark-based comparison, challenges a model name/alias, or wants a marketing claim checked against public evidence.

## Core workflow

1. **Lock the identity first.** Determine the exact provider, product family, public model name, API model ID/snapshot, and whether the label comes from an official provider page, a router, a reseller, or a UI. If the user corrects the identity, acknowledge the correction and re-check the authoritative model page before continuing.
2. **Separate claim types.** Classify each statement as exact model identity, provider positioning, reseller marketing, independent benchmark result, or inference from a related model. Never silently promote “competitive with,” “similar to,” or “as smart as” into equivalence.
3. **Collect primary evidence.** Prefer official model pages, model cards/system cards, benchmark papers, and transparent leaderboards. Search snippets are discovery hints only; inspect the underlying page before citing a score or capability claim.
4. **Find exact-match evidence.** Search for the target model name plus benchmark names. If no public score exists for the target model, state that plainly. Do not substitute scores from a sibling model without labeling them as proxy evidence.
5. **Normalize evaluation conditions.** For every score, record benchmark version, harness, tools, reasoning/effort setting, token/time budget, sample count, date/snapshot, and whether it is provider-reported or independent. Mark rows non-equivalent when important conditions differ.
6. **Compare by capability slice.** Separate coding/agent work, terminal use, computer use, science/reasoning, mathematics, and everyday knowledge work. Avoid collapsing all scores into one unsupported overall ranking.
7. **Write the answer in four parts:** verified identity; exact published scores; indirect/proxy evidence; bottom-line judgment and confidence. Keep the conclusion concise when the user asks for a direct answer, while preserving the key caveat.
8. **Cite while drafting and verify citations** using the grounded-citations workflow when that skill is available. Cite the primary page or system card, not a search snippet.

## Evidence labels

- **Same model:** exact provider model ID/snapshot and comparable evaluation configuration.
- **Provider-positioned peer:** provider says it competes with another model but publishes no same-benchmark score.
- **Proxy comparison:** evidence from a predecessor, sibling, or nearby tier; useful context but not proof about the target.
- **Independent head-to-head:** same task set, benchmark version, harness, tool access, and effort setting.

## Reporting rules

- Use “not enough public evidence” instead of inventing a score.
- Explain when an apparent product label is an alias or tier name rather than a separately benchmarked model.
- Do not infer that a cheaper/balanced tier equals a flagship solely from a reseller description.
- Provider-reported results may be valid evidence, but disclose provider ownership and configuration.
- If scores conflict, preserve both, identify the harness/configuration difference, and avoid averaging incompatible numbers.
- A useful conclusion can be directional: “likely in the GPT-5.5 class,” “strong evidence for Opus on long-horizon coding,” or “uncertain for Terra because no Terra-specific public scores were found.”

## Pitfalls

- Treating a reseller/router description as an official benchmark or model card.
- Citing a search-result snippet as if it were the page body.
- Using a nearby model’s score as the target model’s score.
- Presenting a table without benchmark version or harness details.
- Claiming “equal” from one benchmark or from qualitative anecdotes.
- Fabricating evaluation commentary or scoring from `ast.parse`/exit codes alone without reading and verifying actual response code and prompt-specific keyword alignment.
- Silent model fallback when automating Web UI: ignoring disabled switcher items (`aria-disabled="true"`) when a premium model hits its quota limit, causing all subsequent prompts to run against a lower-tier model (e.g. Flash-Lite) while falsely reporting it as the flagship model.
- Reusing dirty Web UI chat threads during live head-to-head benchmarks (picks up stale DOM from prior turns, producing false identical outputs and fake runtimes).
- Scraping only outer text containers (`.model-response-text`) while target code resides in modular web components (`<code-block>`).
- Overexplaining the research process when the user only wants the verdict; lead with the verdict, then show the minimum evidence needed.
- Conflating Free Tier API quotas with Subscription IDE/Companion limits: preview models (e.g. Gemini 3.8 Flash) often have a strict 20 RPD cap on AI Studio Free Tier, breaking large-context CLI harnesses (like omp) while companion IDE pools (agy) run unrestricted.
- Pushing CLI harness authentication tasks to the user when background OAuth fails instead of autonomously configuring local proxy routes (`models.yml` pointing to OmniRoute `:20129`).
- Assuming CLI harnesses like `omp` honor standard `OPENAI_BASE_URL` env vars for arbitrary model IDs without declaring explicit provider blocks in `~/.omp/agent/models.yml`.
- Benchmarking CLI harnesses across asymmetric network routes: pitting a native direct-binary harness (`agy.exe` direct to Google Cloud) against a proxied harness (`omp` via local OmniRoute port 20129) skews latency measurements by 15-20s due to local SSE re-serialization; fair head-to-head benchmarking requires identical egress architecture (both direct native OAuth or both through the identical proxy pipeline).
- Benchmarking CLI harnesses with asymmetric reasoning/thinking effort: claiming "same model" while testing one harness configured with explicit medium/high reasoning (e.g. `gemini-3.8-flash-medium` in `ag_cli`) against another harness running at default/minimal thinking (e.g. `omp` invoked without `--thinking medium`). This distorts both latency and output quality (docstrings, assertion rigor, reasoning depth) and invalidates the evaluation; valid head-to-head comparisons require strict parity across model ID, thinking budget, and task constraints.
- Ignoring producer harness affinity: expecting universal multi-provider CLI wrappers to match the single round-trip HTTP CONNECT efficiency, binary token streaming, and raw throughput of the model producer's own first-party native compiled harness (e.g., Google's Go-compiled `agy.exe` vs Node/Bun multi-handshake orchestrators).
- Missing OMP `install-id` isolation across multi-profile pools: `getInstallId()` in `dirs.ts` defaults to reading `~/.omp/install-id` across all profiles unless `USERPROFILE`/`HOME` is explicitly sandboxed per profile directory, creating a machine-level sybil correlation leak across accounts.

## First-party product-surface verification

When checking a screenshot or social post about an AI feature, verify more than the model name:

1. Extract the concrete claims separately: model/version identity, command syntax, API/tool identifier, product surface, and availability.
2. Check the vendor's announcement and the relevant command/API reference. A documented server-side API tool does not establish that a similarly named slash command exists in the CLI or desktop app.
3. Compare exact strings in code and UI (`advisor_20260301` versus `/advisor`, model IDs, endpoint names, and dates). Treat mismatches as evidence of an experimental UI, stale post, edited image, or mixed product—not automatic proof of fabrication.
4. Report three buckets: **confirmed by first-party source**, **not confirmed for the claimed surface**, and **uncertain/inferred**. Do not collapse “not documented” into “does not exist.”
5. Lead with the verdict when the user asks “kiểm tra này coi” or otherwise wants a quick check; include only the key evidence and the authoritative URL before optional detail.

## Gateway, router, and screenshot-claim verification

When the claim comes from a social-media screenshot saying that a free account can call a normally unavailable model through Cockpit, 9Router, or another gateway, treat the screenshot as a lead, not proof.

1. Transcribe only legible text. Preserve uncertainty in model names, versions, and aliases; do not silently turn OCR such as `sol 6.1` into a canonical model ID.
2. Draw the request path: client → gateway/router → upstream provider → model. Separate the user's visible account from the credential/account actually used by the gateway.
3. Verify the gateway's documented capabilities separately from the entitlement claim. OpenAI-compatible endpoints, aliasing, fallback, multi-account routing, quota tracking, and format translation explain *how a request can be accepted*; they do not prove which upstream model ran.
4. Require provenance fields where possible: `requested_model`, `resolved_model`, `provider`, `credential/account`, `fallback_reason`, and `usage/quota`. A 200 response, dashboard label, or returned `model` field alone is insufficient.
5. Classify explanations as hypotheses until logs or metadata confirm them: (a) a different upstream credential, (b) model alias/remapping, (c) fallback to another model, (d) an entitlement check gap/experimental endpoint, or (e) an actual authorized entitlement.
6. Use an authorized, minimal side-by-side probe: same short prompt direct versus through the gateway, then compare request logs and provider metadata. Do not attempt to bypass quotas, entitlement checks, or access controls.
7. Report three buckets: **observed in the screenshot**, **documented by the gateway/provider**, and **inferred/unverified**. If the model ID cannot be corroborated publicly, say so plainly.

A local endpoint returning `401 Unauthorized` proves only that authentication is required. It does not prove that the named model exists, is available to the account, or was used upstream.

## Reference material

See `references/model-comparison-evidence.md` for a condensed evidence bank and a worked Terra-versus-Opus research pattern. See `references/first-party-feature-verification.md` for the advisor/API-versus-CLI verification pattern. See `references/gateway-router-provenance.md` for the screenshot-led Cockpit/9Router provenance checklist. Pair this skill with `grounded-citations` for source registration and citation verification.
