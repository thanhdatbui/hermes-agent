# Telegram Mobile Copy UX & Codeblock Formatting

## Problem & Pitfall
When Hermes outputs draft messages, canned responses, or text templates for the user to copy and forward to a third party on Telegram Mobile (iOS/Android):
1. **Blockquote Breakdown (`> quote`):** Tapping or long-pressing a blockquote on Telegram mobile only copies the single tapped line or paragraph rather than the entire block, causing truncated copies.
2. **Context Pollution:** If sample text is mixed with bot explanations or conversational preamble in standard text, copying the entire message captures bot reasoning and conversational prose that the user must manually strip before sending.

## Protocol for Outbound Sample Messages
When asked to draft a message, reply, or template for the user to send:
1. **Isolated Code Block:** Put the target message strictly inside a standalone ````text ... ```` code block.
2. **Single-Tap Copy:** In Telegram mobile apps, tapping directly on a monospace code block copies 100% of the block's text cleanly to the clipboard with zero extra UI clicks.
3. **Zero Explanatory Bleed:** Never embed reasoning, metadata, or instructions inside the code block. Surrounding commentary must be kept outside and minimal.
4. **Tone Discipline:** Match requested conversational tone (e.g., concise colloquial Vietnamese, proper address terms such as 'anh' vs 'cụ') without corporate fluff or excessive bullet points.
