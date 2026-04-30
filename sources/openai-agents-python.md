# OpenAI Agents SDK (Python)

**Source:** https://github.com/openai/openai-agents-python
**Docs:** https://openai.github.io/openai-agents-python/
**Stars:** 25.6k | **License:** MIT | **Requires:** Python 3.10+

---

## Purpose

A lightweight, provider-agnostic framework for building multi-agent workflows. Supports OpenAI Responses and Chat Completions APIs, plus 100+ other LLM backends via LiteLLM / any-llm.

A JavaScript/TypeScript version also exists at `openai/openai-agents-js`.

## Installation

```bash
# pip
pip install openai-agents
pip install 'openai-agents[voice]'   # voice support
pip install 'openai-agents[redis]'   # Redis session persistence

# uv (recommended)
uv init
uv add openai-agents
uv add 'openai-agents[voice]'
```

## Core Concepts (9)

### 1. Agents
LLMs configured with instructions, tools, guardrails, and handoff capabilities. The basic unit of work.

### 2. Sandbox Agents *(new in v0.14.0)*
Agents preconfigured to operate inside a container environment with a real filesystem. Useful for tasks requiring file inspection, running commands, applying patches, or carrying workspace state across longer tasks.

```python
from agents import Runner
from agents.run import RunConfig
from agents.sandbox import Manifest, SandboxAgent, SandboxRunConfig
from agents.sandbox.entries import GitRepo
from agents.sandbox.sandboxes import UnixLocalSandboxClient

agent = SandboxAgent(
    name="Workspace Assistant",
    instructions="Inspect the sandbox workspace before answering.",
    default_manifest=Manifest(
        entries={
            "repo": GitRepo(repo="openai/openai-agents-python", ref="main"),
        }
    ),
)

result = Runner.run_sync(
    agent,
    "Inspect the repo README and summarize what this project does.",
    run_config=RunConfig(sandbox=SandboxRunConfig(client=UnixLocalSandboxClient())),
)
print(result.final_output)
```

### 3. Agent Handoffs / Agents as Tools
Two delegation patterns:
- **Handoffs** — an agent fully transfers control to a specialized peer
- **Agents as tools** — an agent calls another agent like a function and receives its result

### 4. Tools
Three categories:
- **Function tools** — Python functions decorated and exposed to the agent
- **MCP integrations** — connect to any Model Context Protocol server
- **Hosted tools** — pre-built tools provided by OpenAI

### 5. Guardrails
Configurable safety checks for both input validation (before the agent acts) and output validation (before results are returned). Can block, flag, or transform.

### 6. Human-in-the-Loop
Built-in mechanisms to pause execution and request human input or approval at any point in an agent run.

### 7. Sessions
Automatic conversation history management across multiple agent runs. Optional Redis-backed persistence for distributed or long-running deployments.

### 8. Tracing
Native tracking of every agent run — view, debug, and optimize workflows. Integrates with OpenAI's tracing UI.

### 9. Realtime Agents
Voice agent support using `gpt-realtime-1.5`. Enables full agent features (tools, handoffs, guardrails) over a voice interface. Requires the `[voice]` optional install.

## Dependencies

**Required:**
- `pydantic` — configuration and data validation
- `requests` — HTTP
- `mcp` (MCP Python SDK) — MCP tool integrations

**Optional:**
- `websockets` — realtime/voice agents
- `sqlalchemy` — session persistence backends
- `any-llm` + `litellm` — multi-provider LLM support
- `redis` — Redis session persistence

**Dev toolchain:** `uv`, `ruff`, `mypy`, `pyright`, `pytest`, `coverage.py`, `mkdocs`

## Notable Design Decisions

- **Provider-agnostic** — not locked to OpenAI models; any LLM backend supported via LiteLLM
- **Pydantic throughout** — strong typing and validation at every layer
- **Composable infrastructure** — integrates with SQLAlchemy, MCP Python SDK, websockets rather than reinventing them
- **90+ releases** — actively maintained, rapid iteration
