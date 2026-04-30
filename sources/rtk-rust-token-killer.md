# RTK: Rust Token Killer

**Source:** https://github.com/rtk-ai/rtk
**Website:** https://www.rtk-ai.app/guide
**Stars:** 38.9k | **Forks:** 2.4k | **License:** Apache 2.0 / MIT | **Language:** Rust (92%)

---

## Purpose

A CLI proxy tool that reduces LLM token consumption by 60–90% when working with AI coding assistants. Intercepts command outputs and compresses them before they reach the model's context window. Single Rust binary, zero dependencies, <10ms overhead per command.

## How It Works

RTK sits between the shell and the LLM's execution environment as a transparent command interceptor. Four optimization strategies applied per command:

1. **Smart Filtering** — removes noise, comments, whitespace
2. **Grouping** — aggregates similar items (files by directory, errors by type)
3. **Truncation** — preserves relevant context, removes redundancy
4. **Deduplication** — collapses repeated log lines with occurrence counts

## Auto-Rewrite Hook

After `rtk init`, Bash commands are transparently rewritten before execution (e.g., `git status` → `rtk git status`). This achieves 100% adoption across all conversations and subagents with zero manual effort.

## Token Savings Example (30-min Claude Code session)

| Command type | Before | After | Savings |
|---|---|---|---|
| `ls` / `tree` | 2,000 tokens | 400 tokens | -80% |
| Test execution | 25,000 tokens | 2,500 tokens | -90% |
| Full session | ~118,000 tokens | ~23,900 tokens | -80% |

## Installation

```bash
# Homebrew
brew install rtk

# Quick install (Linux/macOS)
curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh | sh

# Cargo
cargo install --git https://github.com/rtk-ai/rtk
```

Pre-built binaries available for macOS (x86/ARM), Linux (x86/ARM), and Windows.

## Initialization

```bash
rtk init -g                      # Claude Code / GitHub Copilot (default)
rtk init -g --gemini             # Gemini CLI
rtk init --agent cursor          # Cursor
rtk init --agent cline           # Cline / Roo Code

# Uninstall hook
rtk init -g --uninstall
```

## Supported Commands (100+)

| Category | Commands |
|---|---|
| Files | `ls`, `read`, `smart`, `find`, `grep`, `diff` |
| Git | `status`, `log`, `diff`, `add`, `commit`, `push`, `pull` |
| Testing | `jest`, `pytest`, `cargo test`, `go test`, `playwright` |
| Build / Lint | `tsc`, `ruff`, `cargo clippy`, `golangci-lint` |
| Containers | `docker ps/logs`, `kubectl pods` |
| AWS | `sts`, `ec2`, `lambda`, `s3`, `dynamodb`, `cloudformation` |
| Other | `pnpm`, `pip`, `prisma`, `curl`, `json` |

## Supported AI Tools

Claude Code, GitHub Copilot, Cursor, Gemini CLI, Codex, Windsurf, Cline/Roo Code, OpenCode, OpenClaw, Kilo Code, Google Antigravity. Each uses its own hook mechanism (PreToolUse, BeforeTool, etc.) for transparent command rewriting.

## Configuration (`~/.config/rtk/config.toml`)

On macOS: `~/Library/Application Support/rtk/config.toml`

```toml
[hooks]
exclude_commands = ["curl", "playwright"]

[tee]
enabled = true
mode = "failures"   # "failures" | "always" | "never"
```

`tee` mode saves failed command output for LLM review without flooding the context on successes.

## Analytics Commands

```bash
rtk gain              # summary statistics
rtk gain --graph      # ASCII graph (last 30 days)
rtk discover          # find optimization opportunities
rtk session           # adoption across recent sessions
```

## Telemetry (Opt-in, disabled by default)

**Collected (anonymized):** device hash (salted), OS, architecture, RTK version, command counts, token savings estimates, top command categories.

**Never collected:** source code, file paths, command arguments, secrets, environment variables, personal data.

```bash
rtk telemetry status
rtk telemetry enable
rtk telemetry disable
rtk telemetry forget     # delete local data + request remote erasure
```

Override: `export RTK_TELEMETRY_DISABLED=1`

## Platform Notes

- **WSL (recommended for Windows):** full support with auto-rewrite hook
- **Native Windows:** filters work; hook unavailable — falls back to CLAUDE.md injection mode. Run from Command Prompt, PowerShell, or Windows Terminal (not by double-clicking `rtk.exe`)

## Core Team

Patrick Szymkowiak (Founder), Florian Bruniaux, Adrien Eppling
