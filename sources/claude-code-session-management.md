# Using Claude Code: Session Management and 1M Context

**Source:** https://claude.com/blog/using-claude-code-session-management-and-1m-context
**Author:** Thariq Shihipar, Member of Technical Staff at Anthropic
**Published:** April 15, 2026
**Category:** Claude Code

---

## Overview

Explores how session management, context windows, and compaction strategies impact the Claude Code experience. Anthropic also released the `/usage` slash command to help users understand their usage patterns.

## Context, Compaction, and Context Rot

The context window is all information the model can access when generating responses — system prompts, conversation history, tool calls, file contents. Claude Code offers a 1 million token context window.

**Context rot:** As context grows, performance degrades because attention distributes across more tokens and older content becomes distracting.

When approaching the context limit, the system automatically compacts: it summarizes the task into a compact description and continues in a new window. Users can also trigger compaction manually.

## Every Turn as a Branching Point

After Claude completes a task, the options are:

- **Continue** — Send another message in the same session
- **`/rewind` (Esc Esc)** — Jump to a previous message and try again, dropping subsequent messages from context
- **`/clear`** — Start a new session with a distilled brief (manual, precise)
- **Compact** — Summarize the session and proceed (lossy but low-effort, steerable with instructions)
- **Subagents** — Delegate work to an agent with a clean context window

## When to Start a New Session

General rule: when you start a new task, start a new session. Context rot may still occur even within the 1M window. Related tasks can sometimes justify continuing if some context remains essential (e.g., writing docs for just-implemented features).

## Rewinding Instead of Correcting

Double-tap Esc (or `/rewind`) to jump back to any prior message, dropping everything after it. Rewind is usually better than adding correction instructions — rewind to after the file reads and re-prompt with new insights.

## Compact vs. Clear

| | Compact | Clear |
|---|---|---|
| Effort | Low — automatic summary | High — manual documentation |
| Control | Steerable with hints | Precise, user-defined |
| Risk | Lossy; model compacts at its least intelligent moment (late in a long session) | Only as good as your brief |

Proactive `/compact` with a hint about upcoming work avoids bad autocompacts caused by the model not knowing the work direction.

## Subagents and Fresh Context

When Claude spawns a subagent via the Agent tool, that subagent gets its own fresh context window. Subagents are ideal when a chunk of work generates substantial intermediate output that won't be needed again.

Mental test: *"Will I need this tool output again, or just the conclusion?"*

Good subagent use cases:
- Verify results against spec files
- Research other codebases and summarize implementations
- Generate documentation from git changes

## Decision Table

| Situation | Tool | Reasoning |
|---|---|---|
| Same task, context still relevant | Continue | Everything in window remains essential |
| Claude pursued wrong path | Rewind (Esc Esc) | Keep useful reads, drop failed attempts |
| Session bloated with stale content | `/compact <hint>` | Low effort; steer with instructions |
| Starting genuinely new task | `/clear` | Zero rot; precise control over carryover |
| Next step generates substantial output | Subagent | Intermediate noise stays contained; only results return |
