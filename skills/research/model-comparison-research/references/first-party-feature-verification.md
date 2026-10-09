# First-party feature verification: advisor claims

## Session-derived evidence pattern

A social screenshot claimed that Sonnet could run as the main model and invoke Opus through `/advisor`, with labels such as Sonnet 5.5 and Opus 5.5. The authoritative Anthropic announcement confirmed the broader advisor strategy but exposed a different public interface and model IDs.

## What the first-party announcement confirmed

Source: https://claude.com/blog/the-advisor-strategy

- Sonnet or Haiku can act as the executor.
- Opus can act as the advisor when the executor needs guidance.
- The advisor returns guidance and does not call tools or produce user-facing output.
- The feature is described as a Claude Platform / Messages API tool.
- The documented tool identifier is `advisor_20260301`; the example uses `claude-sonnet-4-6` as executor and `claude-opus-4-6` as advisor.
- The handoff occurs within one `/v1/messages` request.

## What was not established

- The announcement did not establish that `/advisor` is a Claude Code slash command.
- It did not establish Claude Desktop support.
- The announcement did not use the screenshot's 5.5 model labels.

## Reusable conclusion language

"The underlying strategy is confirmed, but the screenshot's command syntax and product-surface claim are not confirmed by the first-party source. The exact API tool is documented; do not assume the same feature is available in Claude Code or Claude Desktop without checking that product's official command/help documentation."

## Verification checklist

- [ ] Capture the exact model names and version strings.
- [ ] Capture the exact command/tool identifier.
- [ ] Identify the claimed surface: API, CLI, desktop, web, or experimental UI.
- [ ] Check the official announcement.
- [ ] Check the official surface-specific reference/help output.
- [ ] Separate confirmed, not-confirmed-for-this-surface, and uncertain claims.
- [ ] Cite the first-party URL and quote the exact code or wording used as evidence.
